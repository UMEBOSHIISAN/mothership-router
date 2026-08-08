import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from mothership_router.core import advisory_route, registry_digest


NOW = datetime(2026, 8, 8, tzinfo=timezone.utc)
TASK = {"capability": "review", "risk": "low"}
REGISTRY = {
    "executors": [
        {"alias": "local-review", "status": "ready", "capabilities": ["review"], "max_risk": "medium", "cost_rank": 1},
        {"alias": "staged-review", "status": "staged", "capabilities": ["review"], "max_risk": "medium", "cost_rank": 0},
    ]
}


class RouterTests(unittest.TestCase):
    def test_high_risk_requires_human_review(self):
        manifest = advisory_route({"capability": "review", "risk": "high"}, REGISTRY, now=NOW)
        self.assertEqual(manifest["status"], "human_review_required")
        self.assertIsNone(manifest["recommended_alias"])

    def test_recommendation_is_dry_run_without_approval(self):
        manifest = advisory_route(TASK, REGISTRY, now=NOW)
        self.assertEqual(manifest["status"], "approval_required")
        self.assertEqual(manifest["recommended_alias"], "local-review")
        self.assertFalse(manifest["authority_effect"])
        self.assertFalse(manifest["execution_effect"])

    def test_valid_approval_is_registry_bound_and_temporary(self):
        approval = {
            "event": "approve", "approver_class": "human", "alias": "local-review",
            "registry_sha256": registry_digest(REGISTRY), "expires_at": "2026-08-09T00:00:00Z",
        }
        manifest = advisory_route(TASK, REGISTRY, approval, now=NOW)
        self.assertEqual(manifest["status"], "approved_dry_run")

    def test_wrong_digest_or_expired_approval_is_not_accepted(self):
        bad = {"event": "approve", "approver_class": "human", "alias": "local-review", "registry_sha256": "bad", "expires_at": "2026-08-07T00:00:00Z"}
        self.assertEqual(advisory_route(TASK, REGISTRY, bad, now=NOW)["status"], "approval_required")

    def test_staged_executor_is_never_eligible(self):
        registry = {"executors": [REGISTRY["executors"][1]]}
        self.assertEqual(advisory_route(TASK, registry, now=NOW)["status"], "no_ready_executor")

    def test_cli_reads_only_two_json_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = root / "task.json"
            registry = root / "registry.json"
            task.write_text(json.dumps(TASK), encoding="utf-8")
            registry.write_text(json.dumps({"executors": []}), encoding="utf-8")
            result = subprocess.run([sys.executable, "-m", "mothership_router", str(task), str(registry)], text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout)["status"], "no_ready_executor")


if __name__ == "__main__":
    unittest.main()

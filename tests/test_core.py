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
WGM_HANDOFF = {
    "schema_version": "1.0",
    "task_id": "review-20260808-001",
    "capability": "review",
    "risk": "low",
    "token_budget": 4000,
    "evidence_references": ["evidence:design-note-v1"],
}
REGISTRY = {
    "executors": [
        {"alias": "local-review", "status": "ready", "capabilities": ["review"], "max_risk": "medium", "cost_rank": 1},
        {"alias": "staged-review", "status": "staged", "capabilities": ["review"], "max_risk": "medium", "cost_rank": 0},
    ]
}


class RouterTests(unittest.TestCase):
    def assert_manifest_identity(self, manifest, *, task_id, capability):
        self.assertEqual(
            set(manifest),
            {
                "schema_version",
                "task_id",
                "capability",
                "status",
                "recommended_alias",
                "registry_sha256",
                "reasons",
                "authority_effect",
                "execution_effect",
            },
        )
        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(manifest["task_id"], task_id)
        self.assertEqual(manifest["capability"], capability)

    def test_every_production_branch_has_the_versioned_manifest_shape(self):
        approval = {
            "event": "approve",
            "approver_class": "human",
            "alias": "local-review",
            "registry_sha256": registry_digest(REGISTRY),
            "expires_at": "2026-08-09T00:00:00Z",
        }
        cases = [
            (advisory_route([], REGISTRY, now=NOW), None, None),
            (
                advisory_route({**WGM_HANDOFF, "command": "false"}, REGISTRY, now=NOW),
                "review-20260808-001",
                "review",
            ),
            (advisory_route({"capability": [], "risk": "low"}, REGISTRY, now=NOW), None, None),
            (advisory_route({"capability": "review", "risk": "high"}, REGISTRY, now=NOW), None, "review"),
            (advisory_route(TASK, {}, now=NOW), None, "review"),
            (advisory_route(TASK, {"executors": []}, now=NOW), None, "review"),
            (advisory_route(TASK, REGISTRY, now=NOW), None, "review"),
            (advisory_route(WGM_HANDOFF, REGISTRY, approval, now=NOW), "review-20260808-001", "review"),
        ]
        for manifest, task_id, capability in cases:
            with self.subTest(status=manifest["status"]):
                self.assert_manifest_identity(manifest, task_id=task_id, capability=capability)

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

    def test_malformed_ready_executor_is_never_emitted(self):
        malformed = {
            "executors": [
                {
                    "alias": None,
                    "status": "ready",
                    "capabilities": ["review"],
                    "max_risk": "medium",
                    "cost_rank": True,
                }
            ]
        }
        manifest = advisory_route(TASK, malformed, now=NOW)
        self.assertEqual(manifest["status"], "no_ready_executor")
        self.assertIsNone(manifest["recommended_alias"])

    def test_path_bearing_executor_alias_is_never_emitted(self):
        registry = {
            "executors": [
                {
                    "alias": "/Users/example/private-worker",
                    "status": "ready",
                    "capabilities": ["review"],
                    "max_risk": "medium",
                    "cost_rank": 1,
                }
            ]
        }
        manifest = advisory_route(TASK, registry, now=NOW)
        self.assertEqual(manifest["status"], "no_ready_executor")
        self.assertNotIn("/Users/example", json.dumps(manifest))

    def test_cli_reads_only_two_json_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = root / "task.json"
            registry = root / "registry.json"
            task.write_text(json.dumps(TASK), encoding="utf-8")
            registry.write_text(json.dumps({"executors": []}), encoding="utf-8")
            result = subprocess.run([sys.executable, "-m", "mothership_router", str(task), str(registry)], text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout)["status"], "no_ready_executor")

    def test_public_wgm_handoff_routes_as_reviewed_metadata(self):
        manifest = advisory_route(WGM_HANDOFF, REGISTRY, now=NOW)
        self.assertEqual(manifest["task_id"], WGM_HANDOFF["task_id"])
        self.assertEqual(manifest["capability"], WGM_HANDOFF["capability"])
        self.assertEqual(manifest["status"], "approval_required")
        self.assertEqual(manifest["recommended_alias"], "local-review")
        self.assertFalse(manifest["authority_effect"])
        self.assertFalse(manifest["execution_effect"])

    def test_public_wgm_handoff_rejects_authority_fields(self):
        handoff = {**WGM_HANDOFF, "execution_permission": "approved"}
        manifest = advisory_route(handoff, REGISTRY, now=NOW)
        self.assertEqual(manifest["status"], "invalid_input")
        self.assertIn("wgm_handoff_contains_unsupported_fields", manifest["reasons"])

    def test_public_wgm_handoff_rejects_path_bearing_identifiers(self):
        for private_path in (
            "/Users/example/private.json",
            "~/private.json",
            r"C:\Users\example\private.json",
        ):
            for field in ("task_id", "capability"):
                with self.subTest(field=field, private_path=private_path):
                    manifest = advisory_route(
                        {**WGM_HANDOFF, field: private_path}, REGISTRY, now=NOW
                    )
                    self.assertEqual(manifest["status"], "invalid_input")
                    self.assertNotIn(private_path, json.dumps(manifest))
            with self.subTest(field="evidence_references", private_path=private_path):
                manifest = advisory_route(
                    {**WGM_HANDOFF, "evidence_references": [private_path]},
                    REGISTRY,
                    now=NOW,
                )
                self.assertEqual(manifest["status"], "invalid_input")
                self.assertNotIn(private_path, json.dumps(manifest))

    def test_invalid_identity_values_are_null_not_stringified(self):
        manifest = advisory_route(
            {"task_id": ["not", "an", "id"], "capability": {"not": "a string"}, "risk": "low"},
            REGISTRY,
            now=NOW,
        )
        self.assertEqual(manifest["status"], "invalid_input")
        self.assertIsNone(manifest["task_id"])
        self.assertIsNone(manifest["capability"])


if __name__ == "__main__":
    unittest.main()

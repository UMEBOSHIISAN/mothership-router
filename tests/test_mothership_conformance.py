import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path

from jsonschema import Draft202012Validator

from mothership_router.core import advisory_route, registry_digest


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 8, tzinfo=timezone.utc)
WGM_HANDOFF = {
    "schema_version": "1.0",
    "task_id": "demo-review-001",
    "capability": "code-review",
    "risk": "low",
    "token_budget": 4000,
    "evidence_references": ["evidence:demo-change-v1"],
}
READY_REGISTRY = {
    "executors": [
        {
            "alias": "fictional-code-reviewer",
            "status": "ready",
            "capabilities": ["code-review"],
            "max_risk": "medium",
            "cost_rank": 1,
        }
    ]
}


class MothershipConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema_text = resources.files("mothership_router.schema").joinpath(
            "router-manifest.1.0.schema.json"
        ).read_text(encoding="utf-8")
        cls.schema = json.loads(schema_text)
        cls.validator = Draft202012Validator(cls.schema)

    def test_closed_conformance_manifest_points_to_owner_artifacts(self):
        manifest_path = ROOT / "suite/mothership-0.2-conformance.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_keys = {
            "schema_version",
            "suite_release",
            "repository",
            "protocol_kind",
            "protocol_version",
            "schema_path",
            "schema_sha256",
            "example_path",
            "authority_effect",
            "execution_effect",
        }
        self.assertEqual(set(manifest), expected_keys)
        self.assertEqual(manifest["schema_version"], "mothership.conformance.v1")
        self.assertEqual(manifest["suite_release"], "0.2.0")
        self.assertEqual(manifest["repository"], "mothership-router")
        self.assertEqual(manifest["protocol_kind"], "router-manifest")
        self.assertEqual(manifest["protocol_version"], "1.0")
        self.assertEqual(
            manifest["schema_path"],
            "src/mothership_router/schema/router-manifest.1.0.schema.json",
        )
        self.assertEqual(manifest["example_path"], "examples/router-manifest.json")
        self.assertFalse(manifest["authority_effect"])
        self.assertFalse(manifest["execution_effect"])
        schema_path = ROOT / manifest["schema_path"]
        example_path = ROOT / manifest["example_path"]
        self.assertTrue(schema_path.is_file())
        self.assertTrue(example_path.is_file())
        self.assertEqual(
            hashlib.sha256(schema_path.read_bytes()).hexdigest(),
            manifest["schema_sha256"],
        )

    def test_every_route_status_validates_against_owner_schema(self):
        approval = {
            "event": "approve",
            "approver_class": "human",
            "alias": "fictional-code-reviewer",
            "registry_sha256": registry_digest(READY_REGISTRY),
            "expires_at": "2026-08-09T00:00:00Z",
        }
        documents = [
            advisory_route([], READY_REGISTRY, now=NOW),
            advisory_route({"capability": "code-review", "risk": "high"}, READY_REGISTRY, now=NOW),
            advisory_route(WGM_HANDOFF, {}, now=NOW),
            advisory_route(WGM_HANDOFF, {"executors": []}, now=NOW),
            advisory_route(WGM_HANDOFF, READY_REGISTRY, now=NOW),
            advisory_route(WGM_HANDOFF, READY_REGISTRY, approval, now=NOW),
        ]
        self.assertEqual(
            {document["status"] for document in documents},
            {
                "invalid_input",
                "human_review_required",
                "no_ready_executor",
                "approval_required",
                "approved_dry_run",
            },
        )
        for document in documents:
            with self.subTest(status=document["status"]):
                self.validator.validate(document)
                self.assertFalse(document["authority_effect"])
                self.assertFalse(document["execution_effect"])

    def test_public_example_is_exact_synthetic_production_output(self):
        expected = advisory_route(WGM_HANDOFF, READY_REGISTRY, now=NOW)
        actual = json.loads((ROOT / "examples/router-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(actual, expected)
        self.validator.validate(actual)

    def test_owner_schema_rejects_nonportable_identifiers_and_true_end_drift(self):
        example = json.loads((ROOT / "examples/router-manifest.json").read_text(encoding="utf-8"))
        unsafe = (
            "private/path",
            r"private\path",
            "private\n",
            "private\x85value",
            "private\u2028value",
            "C:private",
            "日本語",
        )
        for value in unsafe:
            for field in ("task_id", "capability", "recommended_alias"):
                with self.subTest(field=field, value=value):
                    self.assertFalse(self.validator.is_valid({**example, field: value}))
            with self.subTest(field="reasons", value=value):
                self.assertFalse(self.validator.is_valid({**example, "reasons": [value]}))
        self.assertFalse(
            self.validator.is_valid({**example, "registry_sha256": "0" * 64 + "\n"})
        )

    def test_cli_is_canonical_and_errors_are_fixed_and_path_free(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task_path = root / "private-task-name.json"
            registry_path = root / "private-registry-name.json"
            task_path.write_text(json.dumps(WGM_HANDOFF), encoding="utf-8")
            registry_path.write_text(json.dumps(READY_REGISTRY), encoding="utf-8")
            valid = subprocess.run(
                [sys.executable, "-m", "mothership_router", str(task_path), str(registry_path)],
                text=True,
                capture_output=True,
                check=False,
            )
            task_path.write_text("{broken", encoding="utf-8")
            invalid = subprocess.run(
                [sys.executable, "-m", "mothership_router", str(task_path), str(registry_path)],
                text=True,
                capture_output=True,
                check=False,
            )
            missing = subprocess.run(
                [sys.executable, "-m", "mothership_router", str(root / "secret.json"), str(registry_path)],
                text=True,
                capture_output=True,
                check=False,
            )
            usage = subprocess.run(
                [sys.executable, "-m", "mothership_router"],
                text=True,
                capture_output=True,
                check=False,
            )
        expected = json.dumps(
            advisory_route(WGM_HANDOFF, READY_REGISTRY, now=NOW),
            sort_keys=True,
            separators=(",", ":"),
        ) + "\n"
        self.assertEqual(valid.returncode, 0)
        self.assertEqual(valid.stdout, expected)
        self.assertEqual(valid.stderr, "")
        for result in (invalid, missing):
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "input_error: unable to read valid JSON inputs\n")
            self.assertNotIn(str(root), result.stderr)
        self.assertEqual(usage.returncode, 2)
        self.assertEqual(usage.stdout, "")
        self.assertEqual(
            usage.stderr,
            "usage: python -m mothership_router TASK.json REGISTRY.json\n",
        )


if __name__ == "__main__":
    unittest.main()

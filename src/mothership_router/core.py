"""Pure routing and approval checks with no execution capability."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


_RISK = {"low": 0, "medium": 1, "high": 2}
_WGM_HANDOFF_KEYS = {
    "schema_version",
    "task_id",
    "capability",
    "risk",
    "token_budget",
    "evidence_references",
}


def registry_digest(registry: object) -> str:
    return hashlib.sha256(json.dumps(registry, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def advisory_route(
    task: object,
    registry: object,
    approval: object | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    """Return a dry-run manifest; never starts a command or changes state."""
    if not isinstance(task, dict) or not isinstance(registry, dict):
        return _manifest("invalid_input", None, None, ["task_and_registry_must_be_objects"])
    if "schema_version" in task:
        handoff_error = _validate_wgm_handoff(task)
        if handoff_error:
            return _manifest("invalid_input", None, None, [handoff_error])
    risk = task.get("risk")
    capability = task.get("capability")
    if risk not in _RISK or not isinstance(capability, str):
        return _manifest("invalid_input", None, None, ["task_requires_capability_and_supported_risk"])
    if risk == "high":
        return _manifest("human_review_required", None, None, ["high_risk_is_not_auto_routed"])
    candidates = registry.get("executors")
    if not isinstance(candidates, list):
        return _manifest("invalid_input", None, None, ["registry_requires_executor_list"])
    eligible = [row for row in candidates if isinstance(row, dict) and row.get("status") == "ready" and capability in row.get("capabilities", []) and row.get("max_risk") in _RISK and _RISK[row["max_risk"]] >= _RISK[risk] and isinstance(row.get("cost_rank"), int)]
    if not eligible:
        return _manifest("no_ready_executor", None, None, ["no_ready_executor_matches_task"])
    selected = min(eligible, key=lambda row: (row["cost_rank"], row.get("alias", "")))
    digest = registry_digest(registry)
    approved = _valid_approval(approval, selected.get("alias"), digest, now)
    status = "approved_dry_run" if approved else "approval_required"
    return _manifest(status, selected.get("alias"), digest, ["manifest_only", "manual_execution_not_implemented"])


def _manifest(status: str, alias: object, digest: object, reasons: list[str]) -> dict[str, object]:
    return {"status": status, "recommended_alias": alias, "registry_sha256": digest, "reasons": reasons, "authority_effect": False, "execution_effect": False}


def _valid_approval(
    approval: object, alias: object, digest: str, now: datetime | None
) -> bool:
    if not isinstance(approval, dict):
        return False
    if not (
        approval.get("alias") == alias
        and approval.get("registry_sha256") == digest
        and approval.get("approver_class") == "human"
        and approval.get("event") == "approve"
    ):
        return False
    expires_at = approval.get("expires_at")
    if not isinstance(expires_at, str):
        return False
    try:
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if expiry.tzinfo is None:
        return False
    current = now or datetime.now(timezone.utc)
    return expiry > current.astimezone(timezone.utc)


def _validate_wgm_handoff(task: dict[str, object]) -> str | None:
    if set(task) - _WGM_HANDOFF_KEYS:
        return "wgm_handoff_contains_unsupported_fields"
    if set(task) != _WGM_HANDOFF_KEYS:
        return "wgm_handoff_requires_all_public_fields"
    if task.get("schema_version") != "1.0":
        return "wgm_handoff_requires_schema_version_1_0"
    if not isinstance(task.get("task_id"), str) or not task["task_id"]:
        return "wgm_handoff_requires_task_id"
    budget = task.get("token_budget")
    if not isinstance(budget, int) or isinstance(budget, bool) or budget < 1:
        return "wgm_handoff_requires_positive_token_budget"
    references = task.get("evidence_references")
    if not isinstance(references, list) or not references or any(
        not isinstance(value, str) or not value for value in references
    ):
        return "wgm_handoff_requires_evidence_references"
    return None

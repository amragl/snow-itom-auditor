"""Remediation plan creation, tracking, and validation MCP tools.

Provides tools to create actionable remediation plans from audit findings,
track progress on remediation items, and validate that fixes resolved the issue.
"""

from __future__ import annotations

from snow_itom_auditor.client import ServiceNowClient
from snow_itom_auditor.config import AuditConfig
from snow_itom_auditor.engine import AuditEngine
from snow_itom_auditor.models import AuditCheck, RemediationItem, RemediationPlan
from snow_itom_auditor.storage import AuditStorage
from snow_itom_auditor.tools.assets import (
    check_expired_hardware,
    check_license_overallocation,
    check_unassigned_assets,
)
from snow_itom_auditor.tools.cmdb import (
    check_duplicate_compliance,
    check_missing_field_compliance,
    check_orphan_compliance,
    check_stale_compliance,
)
from snow_itom_auditor.tools.discovery import (
    check_ci_reconciliation,
    check_pattern_coverage,
    check_stale_schedules,
)

# Map check names to their check functions and recommended remediation actions
CHECK_REGISTRY: dict[str, dict] = {
    "orphan_cis": {
        "fn": check_orphan_compliance,
        "action": "Review orphan CIs and either create relationships or decommission",
    },
    "stale_records": {
        "fn": check_stale_compliance,
        "action": "Update stale CI records or mark as retired if no longer valid",
    },
    "duplicate_cis": {
        "fn": check_duplicate_compliance,
        "action": "Merge or deduplicate CIs with matching name and class",
    },
    "missing_ip_address": {
        "fn": check_missing_field_compliance,
        "action": "Populate IP address field on server CIs or run discovery",
    },
    "stale_discovery_schedules": {
        "fn": check_stale_schedules,
        "action": "Review and re-enable stale discovery schedules",
    },
    "pattern_coverage": {
        "fn": check_pattern_coverage,
        "action": "Add more discovery patterns to improve coverage",
    },
    "ci_reconciliation": {
        "fn": check_ci_reconciliation,
        "action": "Run discovery or manually set discovery_source on unreconciled CIs",
    },
    "license_overallocation": {
        "fn": check_license_overallocation,
        "action": "Reduce installed count or procure additional licenses",
    },
    "expired_hardware": {
        "fn": check_expired_hardware,
        "action": "Plan hardware refresh for end-of-life assets",
    },
    "unassigned_assets": {
        "fn": check_unassigned_assets,
        "action": "Assign active assets to responsible users or teams",
    },
}


def create_remediation_plan(storage: AuditStorage, audit_id: str) -> dict:
    """Create a remediation plan from failed checks in an audit result.

    Args:
        storage: Audit storage instance.
        audit_id: The audit result to build a plan from.

    Returns:
        Dict representation of the RemediationPlan.
    """
    result = storage.load_audit_result(audit_id)

    items: list[RemediationItem] = []
    for check in result.checks:
        if check.status != "fail":
            continue
        registry_entry = CHECK_REGISTRY.get(check.name, {})
        action = registry_entry.get("action", f"Remediate: {check.description}")
        items.append(RemediationItem(
            check_name=check.name,
            priority=check.severity,
            action=action,
            target_sys_ids=check.affected_sys_ids[:50],
        ))

    # Sort by priority: critical first
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    items.sort(key=lambda item: priority_order.get(item.priority, 4))

    plan = RemediationPlan(
        audit_result_id=audit_id,
        items=items,
        status="active" if items else "empty",
        progress_pct=0.0,
    )

    storage.save_remediation_plan(plan)
    return plan.model_dump(mode="json")


def track_remediation_progress(storage: AuditStorage, plan_id: str) -> dict:
    """Return the current status and progress of a remediation plan.

    Args:
        storage: Audit storage instance.
        plan_id: The remediation plan ID.

    Returns:
        Dict with plan status, progress percentage, and item breakdown.
    """
    plan = storage.load_remediation_plan(plan_id)

    total = len(plan.items)
    done = sum(1 for i in plan.items if i.status == "done")
    in_progress = sum(1 for i in plan.items if i.status == "in_progress")
    pending = sum(1 for i in plan.items if i.status == "pending")
    skipped = sum(1 for i in plan.items if i.status == "skipped")

    progress = (done / total * 100) if total > 0 else 0.0
    plan.progress_pct = round(progress, 2)

    # Auto-complete the plan if all items are done or skipped
    if total > 0 and (done + skipped) == total:
        plan.status = "completed"

    storage.save_remediation_plan(plan)

    return {
        "plan_id": plan.id,
        "audit_result_id": plan.audit_result_id,
        "status": plan.status,
        "progress_pct": plan.progress_pct,
        "total_items": total,
        "done": done,
        "in_progress": in_progress,
        "pending": pending,
        "skipped": skipped,
        "items": [i.model_dump(mode="json") for i in plan.items],
    }


def validate_compliance_fix(
    config: AuditConfig,
    client: ServiceNowClient,
    storage: AuditStorage,
    plan_id: str,
    item_id: str,
) -> dict:
    """Re-run the specific check for a remediation item to verify the fix.

    Args:
        config: Application configuration.
        client: ServiceNow REST client.
        storage: Audit storage instance.
        plan_id: The remediation plan ID.
        item_id: The remediation item ID to validate.

    Returns:
        Dict with validation result (before/after status).
    """
    plan = storage.load_remediation_plan(plan_id)

    target_item: RemediationItem | None = None
    for item in plan.items:
        if item.id == item_id:
            target_item = item
            break

    if target_item is None:
        return {"status": "error", "message": f"Item {item_id} not found in plan {plan_id}"}

    registry_entry = CHECK_REGISTRY.get(target_item.check_name)
    if registry_entry is None:
        return {"status": "error", "message": f"No check function registered for {target_item.check_name}"}

    check_fn = registry_entry["fn"]
    engine = AuditEngine(config, client)
    new_check: AuditCheck = engine.run_check(check_fn, client=client)

    is_fixed = new_check.status == "pass"

    if is_fixed:
        target_item.status = "done"
        target_item.notes = "Validated: check now passes"
    else:
        target_item.notes = f"Validation failed: {new_check.details}"

    # Recalculate progress
    total = len(plan.items)
    done = sum(1 for i in plan.items if i.status == "done")
    skipped = sum(1 for i in plan.items if i.status == "skipped")
    plan.progress_pct = round((done / total * 100) if total > 0 else 0.0, 2)
    if total > 0 and (done + skipped) == total:
        plan.status = "completed"

    storage.save_remediation_plan(plan)

    return {
        "plan_id": plan_id,
        "item_id": item_id,
        "check_name": target_item.check_name,
        "previous_status": "fail",
        "new_status": new_check.status,
        "is_fixed": is_fixed,
        "details": new_check.details,
    }

"""Full audit orchestration MCP tool.

Runs CMDB, Discovery, and Asset audits sequentially, then aggregates
the results into a single consolidated AuditResult.
"""

from __future__ import annotations

from datetime import UTC, datetime

from snow_itom_auditor.client import ServiceNowClient
from snow_itom_auditor.config import AuditConfig
from snow_itom_auditor.models import AuditCheck, AuditResult
from snow_itom_auditor.scoring import ComplianceScorer
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


def run_full_audit(
    config: AuditConfig,
    client: ServiceNowClient,
    storage: AuditStorage,
) -> dict:
    """Run CMDB, Discovery, and Asset audits and produce a consolidated result.

    Executes all check functions sequentially, aggregates findings into a single
    AuditResult of type 'full', calculates the overall compliance score, and
    saves the result to storage.

    Args:
        config: Application configuration.
        client: ServiceNow REST client.
        storage: Audit storage for persisting results.

    Returns:
        Dict representation of the consolidated AuditResult.
    """
    started = datetime.now(UTC)

    all_check_fns = [
        # CMDB checks
        lambda: check_orphan_compliance(client),
        lambda: check_stale_compliance(client),
        lambda: check_duplicate_compliance(client),
        lambda: check_missing_field_compliance(client),
        # Discovery checks
        lambda: check_stale_schedules(client),
        lambda: check_pattern_coverage(client),
        lambda: check_ci_reconciliation(client),
        # Asset checks
        lambda: check_license_overallocation(client),
        lambda: check_expired_hardware(client),
        lambda: check_unassigned_assets(client),
    ]

    checks: list[AuditCheck] = []
    for fn in all_check_fns:
        try:
            checks.append(fn())
        except Exception as exc:
            checks.append(AuditCheck(
                name=fn.__name__ if hasattr(fn, "__name__") else "unknown_check",
                description=f"Check failed: {exc}",
                severity="medium",
                status="error",
                details=str(exc),
            ))

    scorer = ComplianceScorer()
    score = scorer.calculate_score(checks)

    passed = sum(1 for c in checks if c.status == "pass")
    failed = sum(1 for c in checks if c.status == "fail")
    errors = sum(1 for c in checks if c.status == "error")

    result = AuditResult(
        audit_type="full",
        started_at=started,
        completed_at=datetime.now(UTC),
        checks=checks,
        score=score,
        status="completed_with_errors" if errors else ("completed" if failed else "passed"),
        summary=f"Full audit: {passed} passed, {failed} failed, {errors} errors out of {len(checks)} checks",
    )

    storage.save_audit_result(result)
    return result.model_dump(mode="json")

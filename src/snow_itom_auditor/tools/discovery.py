"""Discovery audit checks and MCP tool.

Performs compliance checks against ServiceNow Discovery configuration
including schedule staleness, pattern coverage, and CI reconciliation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from snow_itom_auditor.client import ServiceNowClient
from snow_itom_auditor.config import AuditConfig
from snow_itom_auditor.engine import AuditEngine
from snow_itom_auditor.models import AuditCheck
from snow_itom_auditor.storage import AuditStorage


def check_stale_schedules(client: ServiceNowClient) -> AuditCheck:
    """Detect discovery schedules that haven't run in 7+ days."""
    cutoff = datetime.now(UTC) - timedelta(days=7)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    stale = client.get_records(
        "discovery_schedule",
        fields=["sys_id", "name", "last_run_time"],
        query=f"last_run_time<{cutoff_str}^active=true",
        limit=100,
    )

    affected_ids = [r.get("sys_id", "") for r in stale if r.get("sys_id")]
    status = "fail" if stale else "pass"
    return AuditCheck(
        name="stale_discovery_schedules",
        description="Detect discovery schedules not run in 7+ days",
        severity="high",
        status=status,
        details=f"{len(stale)} active discovery schedules have not run since {cutoff_str}",
        affected_count=len(stale),
        affected_sys_ids=affected_ids[:50],
    )


def check_pattern_coverage(client: ServiceNowClient) -> AuditCheck:
    """Check the count of active discovery patterns."""
    patterns = client.get_records(
        "sa_pattern",
        fields=["sys_id", "name", "active"],
        query="active=true",
        limit=100,
    )

    count = len(patterns)
    # A healthy environment should have at least 5 active patterns
    threshold = 5
    status = "pass" if count >= threshold else "fail"
    severity = "medium" if count > 0 else "high"

    return AuditCheck(
        name="pattern_coverage",
        description="Check active discovery pattern count",
        severity=severity,
        status=status,
        details=f"{count} active discovery patterns found (threshold: {threshold})",
        affected_count=count,
    )


def check_ci_reconciliation(client: ServiceNowClient) -> AuditCheck:
    """Detect CIs with null discovery_source, indicating unreconciled records."""
    unreconciled = client.get_records(
        "cmdb_ci",
        fields=["sys_id", "name", "discovery_source"],
        query="discovery_sourceISEMPTY",
        limit=100,
    )

    affected_ids = [r.get("sys_id", "") for r in unreconciled if r.get("sys_id")]
    status = "fail" if unreconciled else "pass"
    return AuditCheck(
        name="ci_reconciliation",
        description="Detect CIs with no discovery source",
        severity="medium",
        status=status,
        details=f"{len(unreconciled)} CIs have no discovery_source set",
        affected_count=len(unreconciled),
        affected_sys_ids=affected_ids[:50],
    )


def run_discovery_audit(
    config: AuditConfig,
    client: ServiceNowClient,
    storage: AuditStorage,
) -> dict:
    """Execute all Discovery compliance checks and return the audit result.

    Args:
        config: Application configuration.
        client: ServiceNow REST client.
        storage: Audit storage for persisting results.

    Returns:
        Dict representation of the AuditResult.
    """
    check_fns = [
        lambda client=client: check_stale_schedules(client),
        lambda client=client: check_pattern_coverage(client),
        lambda client=client: check_ci_reconciliation(client),
    ]

    engine = AuditEngine(config, client)
    result = engine.run_audit("discovery", check_fns)
    storage.save_audit_result(result)
    return result.model_dump(mode="json")

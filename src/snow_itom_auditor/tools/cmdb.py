"""CMDB compliance audit tool for the ITOM Auditor.

This module performs governance-level CMDB compliance scoring.  It does
**not** re-implement CMDB data-quality operations (duplicate detection,
stale-CI management, orphan detection, IRE rules, etc.) — those are the
canonical domain of *snow-cmdb-agent*.

What this module **does**:
  * Scores the CMDB against policy thresholds (pass/fail per check).
  * Produces governance compliance reports and audit history entries.
  * Feeds the compliance score that the auditor tracks over time.

For raw data-quality details use snow-cmdb-agent's tools:
  get_cmdb_health_metrics, find_duplicate_configuration_items,
  find_stale_configuration_items, get_operational_dashboard.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from snow_itom_auditor.client import ServiceNowClient
from snow_itom_auditor.config import AuditConfig
from snow_itom_auditor.engine import AuditEngine
from snow_itom_auditor.models import AuditCheck
from snow_itom_auditor.storage import AuditStorage

# ---------------------------------------------------------------------------
# Governance policy thresholds
# ---------------------------------------------------------------------------
_ORPHAN_RATE_THRESHOLD = 0.20      # > 20% orphan CIs → compliance fail
_STALE_RATE_THRESHOLD = 0.10       # > 10% stale CIs → compliance fail
_DUPLICATE_RATE_THRESHOLD = 0.05   # > 5% duplicate groups → compliance fail
_MISSING_FIELD_THRESHOLD = 0.15    # > 15% servers missing IP → compliance fail


def check_orphan_compliance(client: ServiceNowClient) -> AuditCheck:
    """Governance check: orphan CI rate must not exceed the policy threshold.

    Samples up to 100 cmdb_ci records and cross-references cmdb_rel_ci.
    Reports pass/fail based on the policy threshold; the per-CI list is
    available via snow-cmdb-agent's find tools.
    """
    cis = client.get_records(
        "cmdb_ci",
        fields=["sys_id", "name", "sys_class_name"],
        limit=100,
    )
    if not cis:
        return AuditCheck(
            name="cmdb_orphan_compliance",
            description="Orphan CI rate below policy threshold",
            severity="medium",
            status="pass",
            details="No CIs found to evaluate",
        )

    orphan_ids: list[str] = []
    for ci in cis:
        sys_id = ci.get("sys_id", "")
        if not sys_id:
            continue
        rels = client.get_records(
            "cmdb_rel_ci",
            fields=["sys_id"],
            query=f"parent={sys_id}^ORchild={sys_id}",
            limit=1,
        )
        if not rels:
            orphan_ids.append(sys_id)

    orphan_rate = len(orphan_ids) / len(cis) if cis else 0.0
    status = "fail" if orphan_rate > _ORPHAN_RATE_THRESHOLD else "pass"
    return AuditCheck(
        name="cmdb_orphan_compliance",
        description="Orphan CI rate below policy threshold",
        severity="medium",
        status=status,
        details=(
            f"{len(orphan_ids)} of {len(cis)} sampled CIs have no relationships "
            f"({orphan_rate:.1%} — threshold {_ORPHAN_RATE_THRESHOLD:.0%})"
        ),
        affected_count=len(orphan_ids),
        affected_sys_ids=orphan_ids[:50],
    )


def check_stale_compliance(client: ServiceNowClient) -> AuditCheck:
    """Governance check: stale CI rate must not exceed the policy threshold.

    Uses a 90-day window consistent with the compliance policy.
    """
    cutoff = datetime.now(UTC) - timedelta(days=90)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    total_cis = client.get_records("cmdb_ci", fields=["sys_id"], limit=1000)
    stale_cis = client.get_records(
        "cmdb_ci",
        fields=["sys_id"],
        query=f"sys_updated_on<{cutoff_str}",
        limit=1000,
    )

    total = len(total_cis)
    stale = len(stale_cis)
    stale_rate = stale / total if total > 0 else 0.0
    status = "fail" if stale_rate > _STALE_RATE_THRESHOLD else "pass"

    return AuditCheck(
        name="cmdb_stale_compliance",
        description="Stale CI rate below policy threshold",
        severity="high",
        status=status,
        details=(
            f"{stale} of {total} CIs not updated since {cutoff_str} "
            f"({stale_rate:.1%} — threshold {_STALE_RATE_THRESHOLD:.0%})"
        ),
        affected_count=stale,
        affected_sys_ids=[r.get("sys_id", "") for r in stale_cis[:50]],
    )


def check_duplicate_compliance(client: ServiceNowClient) -> AuditCheck:
    """Governance check: duplicate CI group rate must not exceed the policy threshold."""
    cis = client.get_records(
        "cmdb_ci",
        fields=["sys_id", "name", "sys_class_name"],
        query="ORDERBYname",
        limit=200,
    )

    seen: dict[str, list[str]] = {}
    for ci in cis:
        key = f"{ci.get('name', '')}|{ci.get('sys_class_name', '')}"
        if key and key != "|":
            seen.setdefault(key, []).append(ci.get("sys_id", ""))

    duplicates = {k: v for k, v in seen.items() if len(v) > 1}
    total = len(cis)
    dup_rate = len(duplicates) / total if total > 0 else 0.0
    affected_ids = [sid for ids in duplicates.values() for sid in ids]
    status = "fail" if dup_rate > _DUPLICATE_RATE_THRESHOLD else "pass"

    return AuditCheck(
        name="cmdb_duplicate_compliance",
        description="Duplicate CI group rate below policy threshold",
        severity="high",
        status=status,
        details=(
            f"{len(duplicates)} duplicate groups across {len(affected_ids)} CIs "
            f"({dup_rate:.1%} — threshold {_DUPLICATE_RATE_THRESHOLD:.0%})"
        ),
        affected_count=len(affected_ids),
        affected_sys_ids=affected_ids[:50],
    )


def check_missing_field_compliance(client: ServiceNowClient) -> AuditCheck:
    """Governance check: server CIs missing IP address must not exceed threshold."""
    all_servers = client.get_records("cmdb_ci_server", fields=["sys_id"], limit=1000)
    missing_ip = client.get_records(
        "cmdb_ci_server",
        fields=["sys_id", "name", "ip_address"],
        query="ip_addressISEMPTY",
        limit=1000,
    )

    total = len(all_servers)
    missing = len(missing_ip)
    missing_rate = missing / total if total > 0 else 0.0
    status = "fail" if missing_rate > _MISSING_FIELD_THRESHOLD else "pass"
    affected_ids = [r.get("sys_id", "") for r in missing_ip if r.get("sys_id")]

    return AuditCheck(
        name="cmdb_missing_field_compliance",
        description="Server CI missing-IP rate below policy threshold",
        severity="critical",
        status=status,
        details=(
            f"{missing} of {total} server CIs have no IP address "
            f"({missing_rate:.1%} — threshold {_MISSING_FIELD_THRESHOLD:.0%})"
        ),
        affected_count=missing,
        affected_sys_ids=affected_ids[:50],
    )


def run_cmdb_audit(
    config: AuditConfig,
    client: ServiceNowClient,
    storage: AuditStorage,
    severity_filter: str | None = None,
) -> dict:
    """Execute CMDB governance compliance checks and return the audit result.

    Checks are governance-level (pass/fail against policy thresholds).
    Detailed data-quality operations are handled by snow-cmdb-agent.

    Args:
        config: Application configuration.
        client: ServiceNow REST client.
        storage: Audit storage for persisting results.
        severity_filter: Optional severity to filter checks (medium/high/critical).

    Returns:
        Dict representation of the AuditResult.
    """
    severity_map = {
        "cmdb_orphan_compliance": "medium",
        "cmdb_stale_compliance": "high",
        "cmdb_duplicate_compliance": "high",
        "cmdb_missing_field_compliance": "critical",
    }

    check_fns = [
        lambda client=client: check_orphan_compliance(client),
        lambda client=client: check_stale_compliance(client),
        lambda client=client: check_duplicate_compliance(client),
        lambda client=client: check_missing_field_compliance(client),
    ]

    if severity_filter:
        names = list(severity_map.keys())
        filtered_fns = [
            fn
            for fn, name in zip(check_fns, names, strict=True)
            if severity_map.get(name) == severity_filter
        ]
        check_fns = filtered_fns if filtered_fns else check_fns

    engine = AuditEngine(config, client)
    result = engine.run_audit("cmdb", check_fns)
    storage.save_audit_result(result)
    return result.model_dump(mode="json")

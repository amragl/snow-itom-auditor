"""CMDB audit checks and MCP tool.

Performs health checks against ServiceNow CMDB data including orphan CIs,
stale records, duplicate detection, and missing required fields.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from snow_itom_auditor.client import ServiceNowClient
from snow_itom_auditor.config import AuditConfig
from snow_itom_auditor.engine import AuditEngine
from snow_itom_auditor.models import AuditCheck
from snow_itom_auditor.storage import AuditStorage


def check_orphan_cis(client: ServiceNowClient) -> AuditCheck:
    """Detect CIs with no relationships (sample up to 100 records).

    Queries cmdb_ci for a sample of records and cross-references
    cmdb_rel_ci to find CIs that have zero relationships.
    """
    cis = client.get_records(
        "cmdb_ci",
        fields=["sys_id", "name", "sys_class_name"],
        limit=100,
    )
    if not cis:
        return AuditCheck(
            name="orphan_cis",
            description="Detect CIs with no relationships",
            severity="medium",
            status="pass",
            details="No CIs found to check",
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

    status = "fail" if orphan_ids else "pass"
    return AuditCheck(
        name="orphan_cis",
        description="Detect CIs with no relationships",
        severity="medium",
        status=status,
        details=f"{len(orphan_ids)} of {len(cis)} sampled CIs have no relationships",
        affected_count=len(orphan_ids),
        affected_sys_ids=orphan_ids[:50],
    )


def check_stale_records(client: ServiceNowClient) -> AuditCheck:
    """Detect CIs not updated in the last 90 days."""
    cutoff = datetime.now(UTC) - timedelta(days=90)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    stale = client.get_records(
        "cmdb_ci",
        fields=["sys_id", "name", "sys_updated_on"],
        query=f"sys_updated_on<{cutoff_str}",
        limit=100,
    )

    status = "fail" if stale else "pass"
    affected_ids = [r.get("sys_id", "") for r in stale if r.get("sys_id")]
    return AuditCheck(
        name="stale_records",
        description="Detect CIs not updated in 90+ days",
        severity="high",
        status=status,
        details=f"{len(stale)} CIs have not been updated since {cutoff_str}",
        affected_count=len(stale),
        affected_sys_ids=affected_ids[:50],
    )


def check_duplicate_cis(client: ServiceNowClient) -> AuditCheck:
    """Detect potential duplicate CIs with same name and class."""
    cis = client.get_records(
        "cmdb_ci",
        fields=["sys_id", "name", "sys_class_name"],
        query="ORDERBYname",
        limit=100,
    )

    seen: dict[str, list[str]] = {}
    for ci in cis:
        key = f"{ci.get('name', '')}|{ci.get('sys_class_name', '')}"
        if key and key != "|":
            seen.setdefault(key, []).append(ci.get("sys_id", ""))

    duplicates = {k: v for k, v in seen.items() if len(v) > 1}
    affected_ids = [sid for ids in duplicates.values() for sid in ids]

    status = "fail" if duplicates else "pass"
    return AuditCheck(
        name="duplicate_cis",
        description="Detect CIs with same name and class",
        severity="high",
        status=status,
        details=f"{len(duplicates)} potential duplicate groups found across {len(affected_ids)} CIs",
        affected_count=len(affected_ids),
        affected_sys_ids=affected_ids[:50],
    )


def check_missing_ip_address(client: ServiceNowClient) -> AuditCheck:
    """Detect server CIs missing IP address."""
    servers = client.get_records(
        "cmdb_ci_server",
        fields=["sys_id", "name", "ip_address"],
        query="ip_addressISEMPTY",
        limit=100,
    )

    affected_ids = [r.get("sys_id", "") for r in servers if r.get("sys_id")]
    status = "fail" if servers else "pass"
    return AuditCheck(
        name="missing_ip_address",
        description="Detect server CIs missing IP address",
        severity="critical",
        status=status,
        details=f"{len(servers)} server CIs have no IP address",
        affected_count=len(servers),
        affected_sys_ids=affected_ids[:50],
    )


def run_cmdb_audit(
    config: AuditConfig,
    client: ServiceNowClient,
    storage: AuditStorage,
    severity_filter: str | None = None,
) -> dict:
    """Execute all CMDB compliance checks and return the audit result.

    Args:
        config: Application configuration.
        client: ServiceNow REST client.
        storage: Audit storage for persisting results.
        severity_filter: Optional severity to filter checks.

    Returns:
        Dict representation of the AuditResult.
    """
    check_fns = [
        lambda client=client: check_orphan_cis(client),
        lambda client=client: check_stale_records(client),
        lambda client=client: check_duplicate_cis(client),
        lambda client=client: check_missing_ip_address(client),
    ]

    if severity_filter:
        severity_map = {
            "orphan_cis": "medium",
            "stale_records": "high",
            "duplicate_cis": "high",
            "missing_ip_address": "critical",
        }
        # Filter by matching severity
        filtered_fns = []
        names = ["orphan_cis", "stale_records", "duplicate_cis", "missing_ip_address"]
        for fn, name in zip(check_fns, names, strict=True):
            if severity_map.get(name) == severity_filter:
                filtered_fns.append(fn)
        check_fns = filtered_fns if filtered_fns else check_fns

    engine = AuditEngine(config, client)
    result = engine.run_audit("cmdb", check_fns)
    storage.save_audit_result(result)
    return result.model_dump(mode="json")

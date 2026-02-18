"""Asset audit checks and MCP tool.

Performs compliance checks against ServiceNow Asset Management data
including license over-allocation, expired hardware, and unassigned assets.
"""

from __future__ import annotations

from datetime import UTC, datetime

from snow_itom_auditor.client import ServiceNowClient
from snow_itom_auditor.config import AuditConfig
from snow_itom_auditor.engine import AuditEngine
from snow_itom_auditor.models import AuditCheck
from snow_itom_auditor.storage import AuditStorage


def check_license_overallocation(client: ServiceNowClient) -> AuditCheck:
    """Detect licenses where installed count exceeds license count."""
    licenses = client.get_records(
        "alm_license",
        fields=["sys_id", "display_name", "license_count", "installed_count"],
        limit=100,
    )

    overallocated: list[str] = []
    for lic in licenses:
        try:
            installed = int(lic.get("installed_count", 0) or 0)
            allowed = int(lic.get("license_count", 0) or 0)
            if allowed > 0 and installed > allowed:
                sys_id = lic.get("sys_id", "")
                if sys_id:
                    overallocated.append(sys_id)
        except (ValueError, TypeError):
            continue

    status = "fail" if overallocated else "pass"
    return AuditCheck(
        name="license_overallocation",
        description="Detect licenses exceeding allocated count",
        severity="critical",
        status=status,
        details=f"{len(overallocated)} licenses are over-allocated",
        affected_count=len(overallocated),
        affected_sys_ids=overallocated[:50],
    )


def check_expired_hardware(client: ServiceNowClient) -> AuditCheck:
    """Detect hardware assets past their end-of-life date."""
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")

    expired = client.get_records(
        "alm_hardware",
        fields=["sys_id", "display_name", "end_of_life"],
        query=f"end_of_life<{today_str}^end_of_lifeISNOTEMPTY",
        limit=100,
    )

    affected_ids = [r.get("sys_id", "") for r in expired if r.get("sys_id")]
    status = "fail" if expired else "pass"
    return AuditCheck(
        name="expired_hardware",
        description="Detect hardware past end-of-life",
        severity="high",
        status=status,
        details=f"{len(expired)} hardware assets have passed end-of-life",
        affected_count=len(expired),
        affected_sys_ids=affected_ids[:50],
    )


def check_unassigned_assets(client: ServiceNowClient) -> AuditCheck:
    """Detect active assets with no assigned user."""
    unassigned = client.get_records(
        "alm_asset",
        fields=["sys_id", "display_name", "install_status"],
        query="assigned_toISEMPTY^install_status=1",
        limit=100,
    )

    affected_ids = [r.get("sys_id", "") for r in unassigned if r.get("sys_id")]
    status = "fail" if unassigned else "pass"
    return AuditCheck(
        name="unassigned_assets",
        description="Detect active assets with no assigned user",
        severity="low",
        status=status,
        details=f"{len(unassigned)} active assets have no assigned user",
        affected_count=len(unassigned),
        affected_sys_ids=affected_ids[:50],
    )


def run_asset_audit(
    config: AuditConfig,
    client: ServiceNowClient,
    storage: AuditStorage,
) -> dict:
    """Execute all Asset compliance checks and return the audit result.

    Args:
        config: Application configuration.
        client: ServiceNow REST client.
        storage: Audit storage for persisting results.

    Returns:
        Dict representation of the AuditResult.
    """
    check_fns = [
        lambda client=client: check_license_overallocation(client),
        lambda client=client: check_expired_hardware(client),
        lambda client=client: check_unassigned_assets(client),
    ]

    engine = AuditEngine(config, client)
    result = engine.run_audit("asset", check_fns)
    storage.save_audit_result(result)
    return result.model_dump(mode="json")

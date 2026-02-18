"""FastMCP server entry point for the ITOM Compliance Auditor.

Registers all MCP tools and starts the server. The server connects to a
ServiceNow instance to perform CMDB, Discovery, and Asset compliance audits.
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from snow_itom_auditor.client import ServiceNowClient
from snow_itom_auditor.config import AuditConfig, get_config
from snow_itom_auditor.storage import AuditStorage
from snow_itom_auditor.tools.assets import run_asset_audit
from snow_itom_auditor.tools.cmdb import run_cmdb_audit
from snow_itom_auditor.tools.compliance import get_compliance_score, list_compliance_rules
from snow_itom_auditor.tools.discovery import run_discovery_audit
from snow_itom_auditor.tools.history import compare_audits, get_audit_history
from snow_itom_auditor.tools.orchestration import run_full_audit
from snow_itom_auditor.tools.remediation import (
    create_remediation_plan,
    track_remediation_progress,
    validate_compliance_fix,
)
from snow_itom_auditor.tools.reports import generate_compliance_report

logger = logging.getLogger(__name__)

mcp = FastMCP("snow-itom-auditor")

# Module-level singletons initialized on first tool call
_config: AuditConfig | None = None
_client: ServiceNowClient | None = None
_storage: AuditStorage | None = None


def _get_dependencies() -> tuple[AuditConfig, ServiceNowClient, AuditStorage]:
    """Lazily initialize and return the shared config, client, and storage."""
    global _config, _client, _storage  # noqa: PLW0603
    if _config is None:
        _config = get_config()
        _client = ServiceNowClient(_config)
        _storage = AuditStorage(_config.audit_storage_path)
    return _config, _client, _storage  # type: ignore[return-value]


@mcp.tool()
def audit_cmdb(severity_filter: str | None = None) -> dict:
    """Run CMDB compliance audit checking orphan CIs, stale records, duplicates, and missing fields."""
    config, client, storage = _get_dependencies()
    return run_cmdb_audit(config, client, storage, severity_filter=severity_filter)


@mcp.tool()
def audit_discovery() -> dict:
    """Run Discovery compliance audit checking schedule staleness, pattern coverage, and CI reconciliation."""
    config, client, storage = _get_dependencies()
    return run_discovery_audit(config, client, storage)


@mcp.tool()
def audit_assets() -> dict:
    """Run Asset compliance audit checking license over-allocation, expired hardware, and unassigned assets."""
    config, client, storage = _get_dependencies()
    return run_asset_audit(config, client, storage)


@mcp.tool()
def audit_full() -> dict:
    """Run a full compliance audit across CMDB, Discovery, and Asset domains."""
    config, client, storage = _get_dependencies()
    return run_full_audit(config, client, storage)


@mcp.tool()
def compliance_rules(category: str | None = None) -> dict:
    """List all defined compliance audit rules with optional category filter."""
    return list_compliance_rules(category=category)


@mcp.tool()
def compliance_score(audit_type: str | None = None) -> dict:
    """Get the latest compliance score, optionally filtered by audit type."""
    _, _, storage = _get_dependencies()
    return get_compliance_score(storage, audit_type=audit_type)


@mcp.tool()
def compliance_report(
    audit_id: str | None = None,
    audit_type: str = "full",
    report_format: str = "json",
) -> dict:
    """Generate a structured compliance report from an audit result or a fresh audit."""
    config, client, storage = _get_dependencies()
    return generate_compliance_report(
        config, client, storage,
        audit_id=audit_id, audit_type=audit_type, report_format=report_format,
    )


@mcp.tool()
def audit_history(audit_type: str | None = None, limit: int = 10) -> dict:
    """Retrieve past audit results for trend analysis."""
    _, _, storage = _get_dependencies()
    return get_audit_history(storage, audit_type=audit_type, limit=limit)


@mcp.tool()
def audit_compare(audit_id_1: str = "", audit_id_2: str = "") -> dict:
    """Compare two audit runs showing score deltas and finding changes."""
    if not audit_id_1 or not audit_id_2:
        return {"status": "error", "message": "Both audit_id_1 and audit_id_2 are required"}
    _, _, storage = _get_dependencies()
    return compare_audits(storage, audit_id_1, audit_id_2)


@mcp.tool()
def remediation_create(audit_id: str = "") -> dict:
    """Create a remediation plan from the failed checks in an audit result."""
    if not audit_id:
        return {"status": "error", "message": "audit_id is required"}
    _, _, storage = _get_dependencies()
    return create_remediation_plan(storage, audit_id)


@mcp.tool()
def remediation_progress(plan_id: str = "") -> dict:
    """Track progress of a remediation plan."""
    if not plan_id:
        return {"status": "error", "message": "plan_id is required"}
    _, _, storage = _get_dependencies()
    return track_remediation_progress(storage, plan_id)


@mcp.tool()
def remediation_validate(plan_id: str = "", item_id: str = "") -> dict:
    """Re-run the specific check for a remediation item to verify the fix."""
    if not plan_id or not item_id:
        return {"status": "error", "message": "Both plan_id and item_id are required"}
    config, client, storage = _get_dependencies()
    return validate_compliance_fix(config, client, storage, plan_id, item_id)


@mcp.tool()
def health_check() -> dict:
    """Verify the auditor server is running and can reach ServiceNow."""
    try:
        config, client, storage = _get_dependencies()
        # Quick connectivity test: query sys_properties with limit=1
        client.get_records("sys_properties", limit=1)
        return {"status": "healthy", "instance": config.servicenow_instance}
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}


def main() -> None:
    """Entry point for the snow-itom-auditor MCP server."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    logger.info("Starting snow-itom-auditor MCP server")
    mcp.run()

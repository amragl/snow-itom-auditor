"""Integration tests requiring a live ServiceNow instance.

These tests are skipped unless SERVICENOW_INSTANCE, SERVICENOW_USERNAME,
and SERVICENOW_PASSWORD environment variables are set.

Run with: pytest tests/integration -m integration
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration

SKIP_REASON = "ServiceNow credentials not configured"
HAS_CREDS = all(
    os.environ.get(v)
    for v in ["SERVICENOW_INSTANCE", "SERVICENOW_USERNAME", "SERVICENOW_PASSWORD"]
)


@pytest.fixture
def live_config():
    pytest.importorskip("snow_itom_auditor.config")
    from snow_itom_auditor.config import AuditConfig

    return AuditConfig()


@pytest.fixture
def live_client(live_config):
    from snow_itom_auditor.client import ServiceNowClient

    return ServiceNowClient(live_config)


@pytest.fixture
def live_storage(tmp_path, live_config):
    from snow_itom_auditor.storage import AuditStorage

    return AuditStorage(str(tmp_path / "integration-audit"))


@pytest.mark.skipunless(HAS_CREDS, SKIP_REASON)
def test_client_connectivity(live_client) -> None:
    """Verify the client can reach ServiceNow."""
    records = live_client.get_records("sys_properties", limit=1)
    assert isinstance(records, list)


@pytest.mark.skipunless(HAS_CREDS, SKIP_REASON)
def test_cmdb_audit_live(live_config, live_client, live_storage) -> None:
    """Run a CMDB audit against a live instance."""
    from snow_itom_auditor.tools.cmdb import run_cmdb_audit

    result = run_cmdb_audit(live_config, live_client, live_storage)
    assert result["audit_type"] == "cmdb"
    assert len(result["checks"]) >= 1


@pytest.mark.skipunless(HAS_CREDS, SKIP_REASON)
def test_full_audit_live(live_config, live_client, live_storage) -> None:
    """Run a full audit against a live instance."""
    from snow_itom_auditor.tools.orchestration import run_full_audit

    result = run_full_audit(live_config, live_client, live_storage)
    assert result["audit_type"] == "full"
    assert result["score"] is not None


@pytest.mark.skipunless(HAS_CREDS, SKIP_REASON)
def test_remediation_workflow_live(live_config, live_client, live_storage) -> None:
    """Test end-to-end remediation workflow against a live instance."""
    from snow_itom_auditor.tools.orchestration import run_full_audit
    from snow_itom_auditor.tools.remediation import create_remediation_plan, track_remediation_progress

    audit_result = run_full_audit(live_config, live_client, live_storage)
    plan = create_remediation_plan(live_storage, audit_result["id"])
    progress = track_remediation_progress(live_storage, plan["id"])
    assert "progress_pct" in progress

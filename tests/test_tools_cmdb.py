"""Tests for CMDB audit tools (mocked HTTP responses)."""

from __future__ import annotations

from unittest.mock import MagicMock

from snow_itom_auditor.client import ServiceNowClient
from snow_itom_auditor.config import AuditConfig
from snow_itom_auditor.storage import AuditStorage
from snow_itom_auditor.tools.cmdb import (
    check_duplicate_compliance,
    check_missing_field_compliance,
    check_orphan_compliance,
    check_stale_compliance,
    run_cmdb_audit,
)


def _make_client(records_by_call: list[list[dict]]) -> ServiceNowClient:
    """Create a ServiceNowClient with mocked get_records returning different results per call."""
    config = AuditConfig(
        SERVICENOW_INSTANCE="https://test.service-now.com",
        SERVICENOW_USERNAME="u",
        SERVICENOW_PASSWORD="p",
        SERVICENOW_MAX_RETRIES=1,
    )
    client = ServiceNowClient(config)
    mock_session = MagicMock()
    responses = []
    for records in records_by_call:
        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        resp.json.return_value = {"result": records}
        responses.append(resp)
    mock_session.request.side_effect = responses
    client.session = mock_session
    return client


class TestCheckOrphanCIs:
    def test_no_cis_returns_pass(self) -> None:
        client = _make_client([[]])
        result = check_orphan_compliance(client)
        assert result.status == "pass"
        assert result.name == "cmdb_orphan_compliance"

    def test_all_have_relationships(self) -> None:
        cis = [{"sys_id": "ci1", "name": "Server1", "sys_class_name": "cmdb_ci_server"}]
        rels = [{"sys_id": "rel1"}]
        client = _make_client([cis, rels])
        result = check_orphan_compliance(client)
        assert result.status == "pass"
        assert result.affected_count == 0

    def test_orphan_detected(self) -> None:
        cis = [{"sys_id": "ci1", "name": "Orphan", "sys_class_name": "cmdb_ci"}]
        no_rels: list[dict] = []
        client = _make_client([cis, no_rels])
        result = check_orphan_compliance(client)
        assert result.status == "fail"
        assert result.affected_count == 1
        assert "ci1" in result.affected_sys_ids

    def test_mixed_orphan_and_non(self) -> None:
        cis = [
            {"sys_id": "ci1", "name": "A", "sys_class_name": "x"},
            {"sys_id": "ci2", "name": "B", "sys_class_name": "x"},
        ]
        has_rel = [{"sys_id": "rel1"}]
        no_rel: list[dict] = []
        client = _make_client([cis, has_rel, no_rel])
        result = check_orphan_compliance(client)
        assert result.status == "fail"
        assert result.affected_count == 1


class TestCheckStaleRecords:
    def test_no_stale_records(self) -> None:
        # check_stale_compliance makes 2 calls: total CIs + stale CIs
        client = _make_client([[], []])
        result = check_stale_compliance(client)
        assert result.status == "pass"

    def test_stale_records_found(self) -> None:
        # 2 total CIs, both stale → 100% > 10% threshold → fail
        total_cis = [{"sys_id": "s1"}, {"sys_id": "s2"}]
        stale = [{"sys_id": "s1"}, {"sys_id": "s2"}]
        client = _make_client([total_cis, stale])
        result = check_stale_compliance(client)
        assert result.status == "fail"
        assert result.affected_count == 2
        assert result.severity == "high"


class TestCheckDuplicateCIs:
    def test_no_duplicates(self) -> None:
        cis = [
            {"sys_id": "c1", "name": "A", "sys_class_name": "server"},
            {"sys_id": "c2", "name": "B", "sys_class_name": "server"},
        ]
        client = _make_client([cis])
        result = check_duplicate_compliance(client)
        assert result.status == "pass"

    def test_duplicates_found(self) -> None:
        cis = [
            {"sys_id": "c1", "name": "Same", "sys_class_name": "server"},
            {"sys_id": "c2", "name": "Same", "sys_class_name": "server"},
        ]
        client = _make_client([cis])
        result = check_duplicate_compliance(client)
        assert result.status == "fail"
        assert result.affected_count == 2

    def test_different_class_not_duplicate(self) -> None:
        cis = [
            {"sys_id": "c1", "name": "Same", "sys_class_name": "server"},
            {"sys_id": "c2", "name": "Same", "sys_class_name": "router"},
        ]
        client = _make_client([cis])
        result = check_duplicate_compliance(client)
        assert result.status == "pass"


class TestCheckMissingIPAddress:
    def test_all_have_ip(self) -> None:
        # check_missing_field_compliance makes 2 calls: all servers + missing IP servers
        client = _make_client([[], []])
        result = check_missing_field_compliance(client)
        assert result.status == "pass"

    def test_missing_ips_found(self) -> None:
        # 1 total server, 1 missing IP → 100% > 15% threshold → fail
        all_servers = [{"sys_id": "s1"}]
        servers_missing = [{"sys_id": "s1", "name": "NoIP", "ip_address": ""}]
        client = _make_client([all_servers, servers_missing])
        result = check_missing_field_compliance(client)
        assert result.status == "fail"
        assert result.severity == "critical"


class TestRunCmdbAudit:
    def test_full_cmdb_audit(self, tmp_path) -> None:
        # Provide enough mock responses for all 4 checks
        # check_orphan_cis: 1 call for CIs (empty = pass)
        # check_stale_records: 1 call (empty = pass)
        # check_duplicate_cis: 1 call (empty = pass)
        # check_missing_ip_address: 1 call (empty = pass)
        config = AuditConfig(
            SERVICENOW_INSTANCE="https://test.service-now.com",
            SERVICENOW_USERNAME="u",
            SERVICENOW_PASSWORD="p",
            SERVICENOW_MAX_RETRIES=1,
        )
        client = _make_client([[], [], [], []])
        storage = AuditStorage(str(tmp_path / "audit"))
        result = run_cmdb_audit(config, client, storage)
        assert result["audit_type"] == "cmdb"
        assert result["score"] is not None
        assert len(result["checks"]) == 4

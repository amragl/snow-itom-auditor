"""Tests for Discovery audit tools (mocked HTTP responses)."""

from __future__ import annotations

from unittest.mock import MagicMock

from snow_itom_auditor.client import ServiceNowClient
from snow_itom_auditor.config import AuditConfig
from snow_itom_auditor.storage import AuditStorage
from snow_itom_auditor.tools.discovery import (
    check_ci_reconciliation,
    check_pattern_coverage,
    check_stale_schedules,
    run_discovery_audit,
)


def _make_client(records_by_call: list[list[dict]]) -> ServiceNowClient:
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


class TestCheckStaleSchedules:
    def test_no_stale(self) -> None:
        client = _make_client([[]])
        result = check_stale_schedules(client)
        assert result.status == "pass"
        assert result.name == "stale_discovery_schedules"

    def test_stale_found(self) -> None:
        schedules = [
            {"sys_id": "ds1", "name": "Sched1", "last_run_time": "2025-01-01"},
        ]
        client = _make_client([schedules])
        result = check_stale_schedules(client)
        assert result.status == "fail"
        assert result.affected_count == 1

    def test_multiple_stale(self) -> None:
        schedules = [
            {"sys_id": "ds1", "name": "S1", "last_run_time": "2025-01-01"},
            {"sys_id": "ds2", "name": "S2", "last_run_time": "2025-06-01"},
        ]
        client = _make_client([schedules])
        result = check_stale_schedules(client)
        assert result.status == "fail"
        assert result.affected_count == 2


class TestCheckPatternCoverage:
    def test_enough_patterns(self) -> None:
        patterns = [{"sys_id": f"p{i}", "name": f"Pat{i}", "active": "true"} for i in range(10)]
        client = _make_client([patterns])
        result = check_pattern_coverage(client)
        assert result.status == "pass"

    def test_too_few_patterns(self) -> None:
        patterns = [{"sys_id": "p1", "name": "Pat1", "active": "true"}]
        client = _make_client([patterns])
        result = check_pattern_coverage(client)
        assert result.status == "fail"

    def test_no_patterns(self) -> None:
        client = _make_client([[]])
        result = check_pattern_coverage(client)
        assert result.status == "fail"
        assert result.severity == "high"

    def test_exactly_threshold(self) -> None:
        patterns = [{"sys_id": f"p{i}", "name": f"P{i}", "active": "true"} for i in range(5)]
        client = _make_client([patterns])
        result = check_pattern_coverage(client)
        assert result.status == "pass"


class TestCheckCIReconciliation:
    def test_all_reconciled(self) -> None:
        client = _make_client([[]])
        result = check_ci_reconciliation(client)
        assert result.status == "pass"

    def test_unreconciled_found(self) -> None:
        cis = [{"sys_id": "c1", "name": "Unrec", "discovery_source": ""}]
        client = _make_client([cis])
        result = check_ci_reconciliation(client)
        assert result.status == "fail"
        assert result.affected_count == 1


class TestRunDiscoveryAudit:
    def test_full_discovery_audit(self, tmp_path) -> None:
        config = AuditConfig(
            SERVICENOW_INSTANCE="https://test.service-now.com",
            SERVICENOW_USERNAME="u",
            SERVICENOW_PASSWORD="p",
            SERVICENOW_MAX_RETRIES=1,
        )
        client = _make_client([[], [], []])
        storage = AuditStorage(str(tmp_path / "audit"))
        result = run_discovery_audit(config, client, storage)
        assert result["audit_type"] == "discovery"
        assert len(result["checks"]) == 3

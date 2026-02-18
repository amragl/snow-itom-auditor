"""Tests for Asset audit tools (mocked HTTP responses)."""

from __future__ import annotations

from unittest.mock import MagicMock

from snow_itom_auditor.client import ServiceNowClient
from snow_itom_auditor.config import AuditConfig
from snow_itom_auditor.storage import AuditStorage
from snow_itom_auditor.tools.assets import (
    check_expired_hardware,
    check_license_overallocation,
    check_unassigned_assets,
    run_asset_audit,
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


class TestCheckLicenseOverallocation:
    def test_no_overallocation(self) -> None:
        licenses = [
            {"sys_id": "l1", "display_name": "Lic1", "license_count": "100", "installed_count": "50"},
        ]
        client = _make_client([licenses])
        result = check_license_overallocation(client)
        assert result.status == "pass"

    def test_overallocation_detected(self) -> None:
        licenses = [
            {"sys_id": "l1", "display_name": "Lic1", "license_count": "10", "installed_count": "20"},
        ]
        client = _make_client([licenses])
        result = check_license_overallocation(client)
        assert result.status == "fail"
        assert result.severity == "critical"
        assert result.affected_count == 1

    def test_no_licenses(self) -> None:
        client = _make_client([[]])
        result = check_license_overallocation(client)
        assert result.status == "pass"

    def test_zero_license_count_not_overallocated(self) -> None:
        licenses = [
            {"sys_id": "l1", "display_name": "Free", "license_count": "0", "installed_count": "5"},
        ]
        client = _make_client([licenses])
        result = check_license_overallocation(client)
        assert result.status == "pass"  # allowed=0 means unlimited/free

    def test_invalid_count_skipped(self) -> None:
        licenses = [
            {"sys_id": "l1", "display_name": "Bad", "license_count": "abc", "installed_count": "5"},
        ]
        client = _make_client([licenses])
        result = check_license_overallocation(client)
        assert result.status == "pass"


class TestCheckExpiredHardware:
    def test_no_expired(self) -> None:
        client = _make_client([[]])
        result = check_expired_hardware(client)
        assert result.status == "pass"

    def test_expired_found(self) -> None:
        hardware = [
            {"sys_id": "h1", "display_name": "OldServer", "end_of_life": "2024-01-01"},
        ]
        client = _make_client([hardware])
        result = check_expired_hardware(client)
        assert result.status == "fail"
        assert result.severity == "high"

    def test_multiple_expired(self) -> None:
        hardware = [
            {"sys_id": "h1", "display_name": "A", "end_of_life": "2023-01-01"},
            {"sys_id": "h2", "display_name": "B", "end_of_life": "2024-06-01"},
        ]
        client = _make_client([hardware])
        result = check_expired_hardware(client)
        assert result.affected_count == 2


class TestCheckUnassignedAssets:
    def test_all_assigned(self) -> None:
        client = _make_client([[]])
        result = check_unassigned_assets(client)
        assert result.status == "pass"

    def test_unassigned_found(self) -> None:
        assets = [
            {"sys_id": "a1", "display_name": "Laptop", "install_status": "1"},
        ]
        client = _make_client([assets])
        result = check_unassigned_assets(client)
        assert result.status == "fail"
        assert result.severity == "low"


class TestRunAssetAudit:
    def test_full_asset_audit(self, tmp_path) -> None:
        config = AuditConfig(
            SERVICENOW_INSTANCE="https://test.service-now.com",
            SERVICENOW_USERNAME="u",
            SERVICENOW_PASSWORD="p",
            SERVICENOW_MAX_RETRIES=1,
        )
        client = _make_client([[], [], []])
        storage = AuditStorage(str(tmp_path / "audit"))
        result = run_asset_audit(config, client, storage)
        assert result["audit_type"] == "asset"
        assert len(result["checks"]) == 3
        assert result["score"] is not None

"""Tests for remediation plan creation, tracking, and validation tools."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from snow_itom_auditor.client import ServiceNowClient
from snow_itom_auditor.config import AuditConfig
from snow_itom_auditor.models import AuditCheck, AuditResult, ComplianceScore
from snow_itom_auditor.storage import AuditStorage
from snow_itom_auditor.tools.remediation import (
    create_remediation_plan,
    track_remediation_progress,
    validate_compliance_fix,
)


def _make_config() -> AuditConfig:
    return AuditConfig(
        SERVICENOW_INSTANCE="https://test.service-now.com",
        SERVICENOW_USERNAME="u",
        SERVICENOW_PASSWORD="p",
        SERVICENOW_MAX_RETRIES=1,
    )


def _make_passing_client() -> ServiceNowClient:
    config = _make_config()
    client = ServiceNowClient(config)
    mock_session = MagicMock()
    resp = MagicMock()
    resp.ok = True
    resp.status_code = 200
    resp.json.return_value = {"result": []}
    mock_session.request.return_value = resp
    client.session = mock_session
    return client


def _save_audit_with_failures(storage: AuditStorage) -> str:
    result = AuditResult(
        audit_type="cmdb",
        checks=[
            AuditCheck(
                name="stale_records",
                description="Stale CIs",
                severity="high",
                status="fail",
                affected_count=5,
                affected_sys_ids=["s1", "s2", "s3", "s4", "s5"],
            ),
            AuditCheck(
                name="missing_ip_address",
                description="Missing IPs",
                severity="critical",
                status="fail",
                affected_count=2,
                affected_sys_ids=["m1", "m2"],
            ),
            AuditCheck(name="orphan_cis", description="Orphans", severity="medium", status="pass"),
        ],
        score=ComplianceScore(
            overall_score=50.0, critical_score=0.0, high_score=0.0, medium_score=100.0, low_score=100.0
        ),
    )
    return storage.save_audit_result(result)


class TestCreateRemediationPlan:
    def test_creates_plan(self, audit_storage: AuditStorage) -> None:
        audit_id = _save_audit_with_failures(audit_storage)
        plan = create_remediation_plan(audit_storage, audit_id)
        assert plan["audit_result_id"] == audit_id
        assert plan["status"] == "active"
        assert len(plan["items"]) == 2

    def test_items_sorted_by_priority(self, audit_storage: AuditStorage) -> None:
        audit_id = _save_audit_with_failures(audit_storage)
        plan = create_remediation_plan(audit_storage, audit_id)
        priorities = [item["priority"] for item in plan["items"]]
        assert priorities[0] == "critical"
        assert priorities[1] == "high"

    def test_no_failures_creates_empty_plan(self, audit_storage: AuditStorage) -> None:
        result = AuditResult(
            audit_type="cmdb",
            checks=[AuditCheck(name="c", description="d", severity="low", status="pass")],
        )
        audit_id = audit_storage.save_audit_result(result)
        plan = create_remediation_plan(audit_storage, audit_id)
        assert plan["status"] == "empty"
        assert len(plan["items"]) == 0

    def test_plan_saved_to_storage(self, audit_storage: AuditStorage) -> None:
        audit_id = _save_audit_with_failures(audit_storage)
        plan = create_remediation_plan(audit_storage, audit_id)
        loaded = audit_storage.load_remediation_plan(plan["id"])
        assert loaded.id == plan["id"]

    def test_nonexistent_audit_raises(self, audit_storage: AuditStorage) -> None:
        with pytest.raises(FileNotFoundError):
            create_remediation_plan(audit_storage, "nonexistent")

    def test_items_have_actions(self, audit_storage: AuditStorage) -> None:
        audit_id = _save_audit_with_failures(audit_storage)
        plan = create_remediation_plan(audit_storage, audit_id)
        for item in plan["items"]:
            assert item["action"] != ""
            assert len(item["action"]) > 5


class TestTrackRemediationProgress:
    def test_initial_progress(self, audit_storage: AuditStorage) -> None:
        audit_id = _save_audit_with_failures(audit_storage)
        plan = create_remediation_plan(audit_storage, audit_id)
        progress = track_remediation_progress(audit_storage, plan["id"])
        assert progress["progress_pct"] == 0.0
        assert progress["pending"] == 2
        assert progress["done"] == 0

    def test_nonexistent_plan_raises(self, audit_storage: AuditStorage) -> None:
        with pytest.raises(FileNotFoundError):
            track_remediation_progress(audit_storage, "nonexistent")

    def test_progress_structure(self, audit_storage: AuditStorage) -> None:
        audit_id = _save_audit_with_failures(audit_storage)
        plan = create_remediation_plan(audit_storage, audit_id)
        progress = track_remediation_progress(audit_storage, plan["id"])
        assert "plan_id" in progress
        assert "status" in progress
        assert "total_items" in progress
        assert "items" in progress


class TestValidateComplianceFix:
    def test_item_not_found(self, audit_storage: AuditStorage) -> None:
        audit_id = _save_audit_with_failures(audit_storage)
        plan = create_remediation_plan(audit_storage, audit_id)
        config = _make_config()
        client = _make_passing_client()
        result = validate_compliance_fix(config, client, audit_storage, plan["id"], "nonexistent-item")
        assert result["status"] == "error"

    def test_validate_fix_passes(self, audit_storage: AuditStorage) -> None:
        audit_id = _save_audit_with_failures(audit_storage)
        plan_data = create_remediation_plan(audit_storage, audit_id)
        config = _make_config()
        client = _make_passing_client()

        # The stale_records check with empty results will pass
        item_id = plan_data["items"][1]["id"]  # high priority (stale_records)
        result = validate_compliance_fix(config, client, audit_storage, plan_data["id"], item_id)
        assert result["is_fixed"] is True
        assert result["new_status"] == "pass"

    def test_validate_updates_plan(self, audit_storage: AuditStorage) -> None:
        audit_id = _save_audit_with_failures(audit_storage)
        plan_data = create_remediation_plan(audit_storage, audit_id)
        config = _make_config()
        client = _make_passing_client()
        item_id = plan_data["items"][1]["id"]
        validate_compliance_fix(config, client, audit_storage, plan_data["id"], item_id)
        loaded = audit_storage.load_remediation_plan(plan_data["id"])
        found = [i for i in loaded.items if i.id == item_id][0]
        assert found.status == "done"

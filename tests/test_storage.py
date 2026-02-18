"""Tests for the JSON-based audit storage layer."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from snow_itom_auditor.models import (
    AuditCheck,
    AuditResult,
    ComplianceScore,
    RemediationItem,
    RemediationPlan,
)
from snow_itom_auditor.storage import AuditStorage


class TestAuditStorage:
    def test_creates_directories(self, tmp_path: Path) -> None:
        AuditStorage(str(tmp_path / "new-storage"))
        assert (tmp_path / "new-storage" / "history").is_dir()
        assert (tmp_path / "new-storage" / "remediation").is_dir()

    def test_save_and_load_audit_result(self, audit_storage: AuditStorage) -> None:
        result = AuditResult(
            audit_type="cmdb",
            checks=[AuditCheck(name="t", description="d", severity="low", status="pass")],
            summary="ok",
        )
        aid = audit_storage.save_audit_result(result)
        loaded = audit_storage.load_audit_result(aid)
        assert loaded.id == result.id
        assert loaded.audit_type == "cmdb"
        assert len(loaded.checks) == 1

    def test_load_nonexistent_raises(self, audit_storage: AuditStorage) -> None:
        with pytest.raises(FileNotFoundError):
            audit_storage.load_audit_result("nonexistent-id")

    def test_list_audit_results_empty(self, audit_storage: AuditStorage) -> None:
        results = audit_storage.list_audit_results()
        assert results == []

    def test_list_audit_results(self, audit_storage: AuditStorage) -> None:
        for at in ["cmdb", "discovery", "asset"]:
            r = AuditResult(audit_type=at, summary=f"{at} audit")
            audit_storage.save_audit_result(r)
        results = audit_storage.list_audit_results()
        assert len(results) == 3

    def test_list_audit_results_with_filter(self, audit_storage: AuditStorage) -> None:
        for at in ["cmdb", "cmdb", "discovery"]:
            r = AuditResult(audit_type=at)
            audit_storage.save_audit_result(r)
        cmdb = audit_storage.list_audit_results(audit_type="cmdb")
        assert len(cmdb) == 2
        disc = audit_storage.list_audit_results(audit_type="discovery")
        assert len(disc) == 1

    def test_list_audit_results_limit(self, audit_storage: AuditStorage) -> None:
        for _ in range(5):
            audit_storage.save_audit_result(AuditResult(audit_type="cmdb"))
        results = audit_storage.list_audit_results(limit=3)
        assert len(results) == 3

    def test_list_includes_score(self, audit_storage: AuditStorage) -> None:
        result = AuditResult(
            audit_type="cmdb",
            score=ComplianceScore(
                overall_score=85.0,
                critical_score=100.0,
                high_score=80.0,
                medium_score=70.0,
                low_score=90.0,
            ),
        )
        audit_storage.save_audit_result(result)
        items = audit_storage.list_audit_results()
        assert items[0]["overall_score"] == 85.0

    def test_save_and_load_remediation_plan(self, audit_storage: AuditStorage) -> None:
        plan = RemediationPlan(
            audit_result_id="test-audit",
            items=[RemediationItem(check_name="c", priority="high", action="fix")],
        )
        pid = audit_storage.save_remediation_plan(plan)
        loaded = audit_storage.load_remediation_plan(pid)
        assert loaded.id == plan.id
        assert len(loaded.items) == 1

    def test_load_nonexistent_plan_raises(self, audit_storage: AuditStorage) -> None:
        with pytest.raises(FileNotFoundError):
            audit_storage.load_remediation_plan("nonexistent-plan")

    def test_overwrite_existing_result(self, audit_storage: AuditStorage) -> None:
        result = AuditResult(audit_type="cmdb", summary="v1")
        audit_storage.save_audit_result(result)
        result.summary = "v2"
        audit_storage.save_audit_result(result)
        loaded = audit_storage.load_audit_result(result.id)
        assert loaded.summary == "v2"

    def test_corrupt_file_skipped_in_list(self, audit_storage: AuditStorage) -> None:
        # Write a corrupt JSON file
        bad_file = Path(audit_storage.history_path) / "bad.json"
        bad_file.write_text("{not valid json")
        results = audit_storage.list_audit_results()
        assert len(results) == 0

    def test_list_returns_summaries(self, audit_storage: AuditStorage) -> None:
        result = AuditResult(
            audit_type="full",
            completed_at=datetime.now(UTC),
            status="completed",
        )
        audit_storage.save_audit_result(result)
        items = audit_storage.list_audit_results()
        assert items[0]["id"] == result.id
        assert items[0]["audit_type"] == "full"
        assert items[0]["status"] == "completed"

    def test_overwrite_remediation_plan(self, audit_storage: AuditStorage) -> None:
        plan = RemediationPlan(audit_result_id="x", status="active")
        audit_storage.save_remediation_plan(plan)
        plan.status = "completed"
        audit_storage.save_remediation_plan(plan)
        loaded = audit_storage.load_remediation_plan(plan.id)
        assert loaded.status == "completed"

    def test_multiple_plans(self, audit_storage: AuditStorage) -> None:
        for i in range(3):
            plan = RemediationPlan(audit_result_id=f"audit-{i}")
            audit_storage.save_remediation_plan(plan)
        files = list(Path(audit_storage.remediation_path).glob("*.json"))
        assert len(files) == 3

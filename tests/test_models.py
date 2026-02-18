"""Tests for Pydantic data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from snow_itom_auditor.models import (
    AuditCheck,
    AuditResult,
    ComplianceScore,
    RemediationItem,
    RemediationPlan,
)


class TestAuditCheck:
    def test_create_minimal(self) -> None:
        check = AuditCheck(name="test", description="desc", severity="high", status="pass")
        assert check.name == "test"
        assert check.severity == "high"
        assert check.status == "pass"

    def test_default_details(self) -> None:
        check = AuditCheck(name="t", description="d", severity="low", status="fail")
        assert check.details == ""
        assert check.affected_count == 0
        assert check.affected_sys_ids == []

    def test_with_affected(self) -> None:
        check = AuditCheck(
            name="t",
            description="d",
            severity="critical",
            status="fail",
            affected_count=3,
            affected_sys_ids=["a", "b", "c"],
        )
        assert check.affected_count == 3
        assert len(check.affected_sys_ids) == 3

    def test_invalid_severity_raises(self) -> None:
        with pytest.raises(ValidationError):
            AuditCheck(name="t", description="d", severity="extreme", status="pass")

    def test_invalid_status_raises(self) -> None:
        with pytest.raises(ValidationError):
            AuditCheck(name="t", description="d", severity="high", status="unknown")

    def test_all_severity_levels(self) -> None:
        for sev in ["critical", "high", "medium", "low"]:
            check = AuditCheck(name="t", description="d", severity=sev, status="pass")
            assert check.severity == sev

    def test_all_status_values(self) -> None:
        for status in ["pass", "fail", "skip", "error"]:
            check = AuditCheck(name="t", description="d", severity="low", status=status)
            assert check.status == status

    def test_serialization(self) -> None:
        check = AuditCheck(name="t", description="d", severity="high", status="pass", details="ok")
        data = check.model_dump()
        assert data["name"] == "t"
        assert data["details"] == "ok"


class TestComplianceScore:
    def test_create_valid(self) -> None:
        score = ComplianceScore(
            overall_score=85.0,
            critical_score=100.0,
            high_score=80.0,
            medium_score=75.0,
            low_score=90.0,
        )
        assert score.overall_score == 85.0

    def test_score_min_max(self) -> None:
        score = ComplianceScore(
            overall_score=0.0, critical_score=0.0, high_score=0.0, medium_score=0.0, low_score=0.0
        )
        assert score.overall_score == 0.0

        score2 = ComplianceScore(
            overall_score=100.0, critical_score=100.0, high_score=100.0, medium_score=100.0, low_score=100.0
        )
        assert score2.overall_score == 100.0

    def test_score_below_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            ComplianceScore(
                overall_score=-1.0, critical_score=0.0, high_score=0.0, medium_score=0.0, low_score=0.0
            )

    def test_score_above_hundred_raises(self) -> None:
        with pytest.raises(ValidationError):
            ComplianceScore(
                overall_score=101.0, critical_score=0.0, high_score=0.0, medium_score=0.0, low_score=0.0
            )

    def test_counts_default(self) -> None:
        score = ComplianceScore(
            overall_score=50.0, critical_score=50.0, high_score=50.0, medium_score=50.0, low_score=50.0
        )
        assert score.passed_count == 0
        assert score.failed_count == 0
        assert score.total_count == 0


class TestAuditResult:
    def test_create_minimal(self) -> None:
        result = AuditResult(audit_type="cmdb")
        assert result.audit_type == "cmdb"
        assert result.status == "running"
        assert result.checks == []
        assert result.score is None

    def test_auto_id(self) -> None:
        r1 = AuditResult(audit_type="cmdb")
        r2 = AuditResult(audit_type="cmdb")
        assert r1.id != r2.id

    def test_auto_started_at(self) -> None:
        result = AuditResult(audit_type="discovery")
        assert result.started_at is not None
        assert result.started_at.tzinfo is not None

    def test_invalid_audit_type(self) -> None:
        with pytest.raises(ValidationError):
            AuditResult(audit_type="invalid")

    def test_all_audit_types(self) -> None:
        for at in ["cmdb", "discovery", "asset", "full"]:
            result = AuditResult(audit_type=at)
            assert result.audit_type == at

    def test_serialization_roundtrip(self) -> None:
        result = AuditResult(
            audit_type="full",
            checks=[AuditCheck(name="t", description="d", severity="low", status="pass")],
            summary="ok",
        )
        json_str = result.model_dump_json()
        loaded = AuditResult.model_validate_json(json_str)
        assert loaded.id == result.id
        assert len(loaded.checks) == 1


class TestRemediationItem:
    def test_create(self) -> None:
        item = RemediationItem(check_name="orphan_cis", priority="high", action="Fix it")
        assert item.check_name == "orphan_cis"
        assert item.status == "pending"

    def test_auto_id(self) -> None:
        i1 = RemediationItem(check_name="a", priority="low", action="do")
        i2 = RemediationItem(check_name="a", priority="low", action="do")
        assert i1.id != i2.id

    def test_invalid_priority(self) -> None:
        with pytest.raises(ValidationError):
            RemediationItem(check_name="a", priority="urgent", action="do")

    def test_invalid_status(self) -> None:
        with pytest.raises(ValidationError):
            RemediationItem(check_name="a", priority="low", action="do", status="complete")


class TestRemediationPlan:
    def test_create(self) -> None:
        plan = RemediationPlan(audit_result_id="abc-123")
        assert plan.audit_result_id == "abc-123"
        assert plan.status == "active"
        assert plan.progress_pct == 0.0
        assert plan.items == []

    def test_with_items(self) -> None:
        items = [
            RemediationItem(check_name="a", priority="high", action="do a"),
            RemediationItem(check_name="b", priority="low", action="do b"),
        ]
        plan = RemediationPlan(audit_result_id="xyz", items=items)
        assert len(plan.items) == 2

    def test_serialization_roundtrip(self) -> None:
        plan = RemediationPlan(
            audit_result_id="test-id",
            items=[RemediationItem(check_name="c", priority="medium", action="fix c")],
        )
        json_str = plan.model_dump_json()
        loaded = RemediationPlan.model_validate_json(json_str)
        assert loaded.id == plan.id
        assert len(loaded.items) == 1

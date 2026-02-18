"""Tests for compliance report generation."""

from __future__ import annotations

from datetime import UTC, datetime

from snow_itom_auditor.models import AuditCheck, AuditResult, ComplianceScore
from snow_itom_auditor.tools.reports import _build_report


class TestBuildReport:
    def test_report_structure(self) -> None:
        result = AuditResult(
            audit_type="cmdb",
            completed_at=datetime.now(UTC),
            checks=[
                AuditCheck(name="c1", description="d1", severity="high", status="pass"),
                AuditCheck(name="c2", description="d2", severity="critical", status="fail", details="bad"),
            ],
            score=ComplianceScore(
                overall_score=60.0,
                critical_score=0.0,
                high_score=100.0,
                medium_score=100.0,
                low_score=100.0,
                passed_count=1,
                failed_count=1,
                total_count=2,
            ),
        )
        report = _build_report(result)
        assert "executive_summary" in report
        assert "findings_by_severity" in report
        assert "recommendations" in report
        assert report["audit_type"] == "cmdb"

    def test_grade_a(self) -> None:
        result = AuditResult(
            audit_type="cmdb",
            completed_at=datetime.now(UTC),
            checks=[AuditCheck(name="c", description="d", severity="low", status="pass")],
            score=ComplianceScore(
                overall_score=95.0, critical_score=100.0, high_score=100.0, medium_score=100.0, low_score=100.0
            ),
        )
        report = _build_report(result)
        assert report["executive_summary"]["grade"] == "A"

    def test_grade_f(self) -> None:
        result = AuditResult(
            audit_type="cmdb",
            completed_at=datetime.now(UTC),
            checks=[AuditCheck(name="c", description="d", severity="critical", status="fail")],
            score=ComplianceScore(
                overall_score=20.0, critical_score=0.0, high_score=0.0, medium_score=0.0, low_score=0.0
            ),
        )
        report = _build_report(result)
        assert report["executive_summary"]["grade"] == "F"

    def test_findings_grouped_by_severity(self) -> None:
        result = AuditResult(
            audit_type="full",
            completed_at=datetime.now(UTC),
            checks=[
                AuditCheck(name="c1", description="d1", severity="critical", status="fail"),
                AuditCheck(name="c2", description="d2", severity="low", status="fail"),
                AuditCheck(name="c3", description="d3", severity="high", status="pass"),
            ],
            score=ComplianceScore(
                overall_score=50.0, critical_score=0.0, high_score=100.0, medium_score=100.0, low_score=0.0
            ),
        )
        report = _build_report(result)
        assert len(report["findings_by_severity"]["critical"]) == 1
        assert len(report["findings_by_severity"]["low"]) == 1
        assert len(report["findings_by_severity"]["high"]) == 0

    def test_recommendations_for_critical(self) -> None:
        result = AuditResult(
            audit_type="cmdb",
            completed_at=datetime.now(UTC),
            checks=[AuditCheck(name="c", description="d", severity="critical", status="fail")],
            score=ComplianceScore(
                overall_score=30.0, critical_score=0.0, high_score=100.0, medium_score=100.0, low_score=100.0
            ),
        )
        report = _build_report(result)
        assert any("critical" in r.lower() for r in report["recommendations"])

    def test_no_findings_recommendation(self) -> None:
        result = AuditResult(
            audit_type="cmdb",
            completed_at=datetime.now(UTC),
            checks=[AuditCheck(name="c", description="d", severity="low", status="pass")],
            score=ComplianceScore(
                overall_score=100.0, critical_score=100.0, high_score=100.0, medium_score=100.0, low_score=100.0
            ),
        )
        report = _build_report(result)
        assert any("maintain" in r.lower() for r in report["recommendations"])

    def test_report_includes_score(self) -> None:
        result = AuditResult(
            audit_type="cmdb",
            completed_at=datetime.now(UTC),
            checks=[],
            score=ComplianceScore(
                overall_score=75.0, critical_score=100.0, high_score=100.0, medium_score=0.0, low_score=100.0
            ),
        )
        report = _build_report(result)
        assert report["score"]["overall_score"] == 75.0

    def test_no_score(self) -> None:
        result = AuditResult(
            audit_type="cmdb",
            completed_at=datetime.now(UTC),
            checks=[],
        )
        report = _build_report(result)
        assert report["score"] is None
        assert report["executive_summary"]["overall_score"] == 0.0

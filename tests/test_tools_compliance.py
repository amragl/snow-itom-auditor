"""Tests for compliance rules listing and score retrieval tools."""

from __future__ import annotations

from snow_itom_auditor.models import AuditResult, ComplianceScore
from snow_itom_auditor.storage import AuditStorage
from snow_itom_auditor.tools.compliance import (
    COMPLIANCE_RULES,
    get_compliance_score,
    list_compliance_rules,
)


class TestListComplianceRules:
    def test_returns_all_rules(self) -> None:
        result = list_compliance_rules()
        assert result["total_count"] == len(COMPLIANCE_RULES)
        assert len(result["rules"]) == len(COMPLIANCE_RULES)

    def test_filter_by_category(self) -> None:
        cmdb = list_compliance_rules(category="cmdb")
        assert all(r["category"] == "cmdb" for r in cmdb["rules"])
        assert cmdb["total_count"] > 0

    def test_filter_discovery(self) -> None:
        disc = list_compliance_rules(category="discovery")
        assert all(r["category"] == "discovery" for r in disc["rules"])

    def test_filter_asset(self) -> None:
        asset = list_compliance_rules(category="asset")
        assert all(r["category"] == "asset" for r in asset["rules"])

    def test_filter_nonexistent_category(self) -> None:
        result = list_compliance_rules(category="nonexistent")
        assert result["total_count"] == 0

    def test_includes_categories_list(self) -> None:
        result = list_compliance_rules()
        assert "asset" in result["categories"]
        assert "cmdb" in result["categories"]
        assert "discovery" in result["categories"]

    def test_rule_has_required_fields(self) -> None:
        result = list_compliance_rules()
        for rule in result["rules"]:
            assert "name" in rule
            assert "category" in rule
            assert "severity" in rule
            assert "description" in rule


class TestGetComplianceScore:
    def test_no_data(self, audit_storage: AuditStorage) -> None:
        result = get_compliance_score(audit_storage)
        assert result["status"] == "no_data"

    def test_returns_latest(self, audit_storage: AuditStorage) -> None:
        ar = AuditResult(
            audit_type="cmdb",
            status="completed",
            score=ComplianceScore(
                overall_score=85.0,
                critical_score=100.0,
                high_score=80.0,
                medium_score=70.0,
                low_score=90.0,
                passed_count=3,
                failed_count=1,
                total_count=4,
            ),
        )
        audit_storage.save_audit_result(ar)
        result = get_compliance_score(audit_storage)
        assert result["status"] == "ok"
        assert result["overall_score"] == 85.0

    def test_filter_by_type(self, audit_storage: AuditStorage) -> None:
        for at in ["cmdb", "discovery"]:
            ar = AuditResult(audit_type=at, status="completed")
            audit_storage.save_audit_result(ar)
        result = get_compliance_score(audit_storage, audit_type="discovery")
        assert result["status"] == "ok"
        assert result["audit_type"] == "discovery"

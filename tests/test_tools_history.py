"""Tests for audit history and comparison tools."""

from __future__ import annotations

import pytest

from snow_itom_auditor.models import AuditCheck, AuditResult, ComplianceScore
from snow_itom_auditor.storage import AuditStorage
from snow_itom_auditor.tools.history import compare_audits, get_audit_history


class TestGetAuditHistory:
    def test_empty_history(self, audit_storage: AuditStorage) -> None:
        result = get_audit_history(audit_storage)
        assert result["total_returned"] == 0
        assert result["audits"] == []

    def test_returns_audits(self, audit_storage: AuditStorage) -> None:
        for _ in range(3):
            audit_storage.save_audit_result(AuditResult(audit_type="cmdb"))
        result = get_audit_history(audit_storage)
        assert result["total_returned"] == 3

    def test_limit(self, audit_storage: AuditStorage) -> None:
        for _ in range(5):
            audit_storage.save_audit_result(AuditResult(audit_type="cmdb"))
        result = get_audit_history(audit_storage, limit=2)
        assert result["total_returned"] == 2

    def test_filter_by_type(self, audit_storage: AuditStorage) -> None:
        audit_storage.save_audit_result(AuditResult(audit_type="cmdb"))
        audit_storage.save_audit_result(AuditResult(audit_type="discovery"))
        result = get_audit_history(audit_storage, audit_type="cmdb")
        assert result["total_returned"] == 1
        assert result["filter"] == "cmdb"

    def test_default_limit_is_ten(self, audit_storage: AuditStorage) -> None:
        for _ in range(15):
            audit_storage.save_audit_result(AuditResult(audit_type="cmdb"))
        result = get_audit_history(audit_storage)
        assert result["total_returned"] == 10

    def test_no_filter(self, audit_storage: AuditStorage) -> None:
        result = get_audit_history(audit_storage)
        assert result["filter"] is None


class TestCompareAudits:
    def _make_result(
        self, audit_storage: AuditStorage, score: float, failed_names: list[str]
    ) -> str:
        checks = []
        for name in failed_names:
            checks.append(AuditCheck(name=name, description="d", severity="high", status="fail"))
        checks.append(AuditCheck(name="always_pass", description="d", severity="low", status="pass"))

        result = AuditResult(
            audit_type="cmdb",
            checks=checks,
            score=ComplianceScore(
                overall_score=score,
                critical_score=100.0,
                high_score=score,
                medium_score=100.0,
                low_score=100.0,
            ),
        )
        return audit_storage.save_audit_result(result)

    def test_improving_trend(self, audit_storage: AuditStorage) -> None:
        id1 = self._make_result(audit_storage, 50.0, ["stale", "orphan"])
        id2 = self._make_result(audit_storage, 80.0, ["stale"])
        comp = compare_audits(audit_storage, id1, id2)
        assert comp["trend"] == "improving"
        assert comp["score_delta"] == 30.0
        assert "orphan" in comp["resolved_findings"]

    def test_declining_trend(self, audit_storage: AuditStorage) -> None:
        id1 = self._make_result(audit_storage, 80.0, [])
        id2 = self._make_result(audit_storage, 60.0, ["stale"])
        comp = compare_audits(audit_storage, id1, id2)
        assert comp["trend"] == "declining"
        assert comp["score_delta"] == -20.0
        assert "stale" in comp["new_findings"]

    def test_stable_trend(self, audit_storage: AuditStorage) -> None:
        id1 = self._make_result(audit_storage, 75.0, ["orphan"])
        id2 = self._make_result(audit_storage, 75.0, ["orphan"])
        comp = compare_audits(audit_storage, id1, id2)
        assert comp["trend"] == "stable"
        assert comp["score_delta"] == 0.0
        assert "orphan" in comp["persistent_findings"]

    def test_nonexistent_audit_raises(self, audit_storage: AuditStorage) -> None:
        id1 = self._make_result(audit_storage, 50.0, [])
        with pytest.raises(FileNotFoundError):
            compare_audits(audit_storage, id1, "nonexistent")

    def test_compare_returns_check_counts(self, audit_storage: AuditStorage) -> None:
        id1 = self._make_result(audit_storage, 90.0, [])
        id2 = self._make_result(audit_storage, 80.0, ["dup"])
        comp = compare_audits(audit_storage, id1, id2)
        assert comp["checks_count_1"] >= 1
        assert comp["checks_count_2"] >= 1

    def test_new_and_resolved(self, audit_storage: AuditStorage) -> None:
        id1 = self._make_result(audit_storage, 60.0, ["old_issue"])
        id2 = self._make_result(audit_storage, 70.0, ["new_issue"])
        comp = compare_audits(audit_storage, id1, id2)
        assert "old_issue" in comp["resolved_findings"]
        assert "new_issue" in comp["new_findings"]
        assert comp["persistent_findings"] == []

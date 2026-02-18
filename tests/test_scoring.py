"""Tests for the compliance scoring system."""

from __future__ import annotations

from snow_itom_auditor.models import AuditCheck
from snow_itom_auditor.scoring import ComplianceScorer


def _make_check(severity: str, status: str) -> AuditCheck:
    return AuditCheck(name=f"check_{severity}_{status}", description="test", severity=severity, status=status)


class TestComplianceScorer:
    def setup_method(self) -> None:
        self.scorer = ComplianceScorer()

    def test_all_passing(self) -> None:
        checks = [
            _make_check("critical", "pass"),
            _make_check("high", "pass"),
            _make_check("medium", "pass"),
            _make_check("low", "pass"),
        ]
        score = self.scorer.calculate_score(checks)
        assert score.overall_score == 100.0
        assert score.critical_score == 100.0
        assert score.passed_count == 4
        assert score.failed_count == 0

    def test_all_failing(self) -> None:
        checks = [
            _make_check("critical", "fail"),
            _make_check("high", "fail"),
            _make_check("medium", "fail"),
            _make_check("low", "fail"),
        ]
        score = self.scorer.calculate_score(checks)
        assert score.overall_score == 0.0
        assert score.failed_count == 4

    def test_empty_checks(self) -> None:
        score = self.scorer.calculate_score([])
        assert score.overall_score == 100.0
        assert score.total_count == 0

    def test_skip_and_error_excluded(self) -> None:
        checks = [
            _make_check("critical", "pass"),
            _make_check("high", "skip"),
            _make_check("medium", "error"),
        ]
        score = self.scorer.calculate_score(checks)
        assert score.total_count == 1
        assert score.passed_count == 1
        assert score.overall_score == 100.0

    def test_critical_failure_impacts_score(self) -> None:
        checks = [
            _make_check("critical", "fail"),
            _make_check("high", "pass"),
            _make_check("medium", "pass"),
            _make_check("low", "pass"),
        ]
        score = self.scorer.calculate_score(checks)
        assert score.critical_score == 0.0
        assert score.high_score == 100.0
        assert score.overall_score < 100.0

    def test_critical_weight_is_highest(self) -> None:
        # Fail critical only vs fail low only
        checks_crit_fail = [_make_check("critical", "fail"), _make_check("low", "pass")]
        checks_low_fail = [_make_check("critical", "pass"), _make_check("low", "fail")]
        score_crit = self.scorer.calculate_score(checks_crit_fail)
        score_low = self.scorer.calculate_score(checks_low_fail)
        assert score_crit.overall_score < score_low.overall_score

    def test_mixed_results(self) -> None:
        checks = [
            _make_check("critical", "pass"),
            _make_check("critical", "fail"),
            _make_check("high", "pass"),
            _make_check("medium", "fail"),
        ]
        score = self.scorer.calculate_score(checks)
        assert score.critical_score == 50.0
        assert score.high_score == 100.0
        assert score.medium_score == 0.0
        assert score.passed_count == 2
        assert score.failed_count == 2

    def test_severity_weights_sum(self) -> None:
        total = sum(self.scorer.SEVERITY_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9

    def test_total_count(self) -> None:
        checks = [
            _make_check("low", "pass"),
            _make_check("low", "fail"),
            _make_check("low", "skip"),
        ]
        score = self.scorer.calculate_score(checks)
        assert score.total_count == 2  # skip excluded

    def test_score_bounds(self) -> None:
        checks = [_make_check("high", "fail")]
        score = self.scorer.calculate_score(checks)
        assert 0.0 <= score.overall_score <= 100.0

    def test_only_one_severity_populated(self) -> None:
        checks = [_make_check("medium", "pass"), _make_check("medium", "fail")]
        score = self.scorer.calculate_score(checks)
        assert score.medium_score == 50.0
        assert score.critical_score == 100.0  # no checks, defaults to 100
        assert score.high_score == 100.0
        assert score.low_score == 100.0

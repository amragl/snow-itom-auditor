"""Compliance scoring system with severity-weighted calculations.

Computes an overall compliance score (0-100) based on the pass/fail ratio
of audit checks, weighted by severity tier.
"""

from __future__ import annotations

from snow_itom_auditor.models import AuditCheck, ComplianceScore


class ComplianceScorer:
    """Calculates compliance scores with configurable severity weights."""

    SEVERITY_WEIGHTS: dict[str, float] = {
        "critical": 0.4,
        "high": 0.3,
        "medium": 0.2,
        "low": 0.1,
    }

    def calculate_score(self, checks: list[AuditCheck]) -> ComplianceScore:
        """Calculate a weighted compliance score from a list of audit checks.

        Checks with status 'skip' or 'error' are excluded from scoring.
        The overall score is a weighted average of per-severity pass rates.
        If no scoreable checks exist for a severity tier, that tier scores 100.

        Args:
            checks: List of completed AuditCheck objects.

        Returns:
            ComplianceScore with overall and per-severity breakdowns.
        """
        scoreable_statuses = {"pass", "fail"}

        tier_scores: dict[str, float] = {}
        total_passed = 0
        total_failed = 0
        total_count = 0

        for severity in self.SEVERITY_WEIGHTS:
            tier_checks = [c for c in checks if c.severity == severity and c.status in scoreable_statuses]
            if not tier_checks:
                tier_scores[severity] = 100.0
                continue
            passed = sum(1 for c in tier_checks if c.status == "pass")
            failed = len(tier_checks) - passed
            tier_scores[severity] = (passed / len(tier_checks)) * 100.0
            total_passed += passed
            total_failed += failed
            total_count += len(tier_checks)

        # Weighted overall score
        overall = 0.0
        weight_sum = 0.0
        for severity, weight in self.SEVERITY_WEIGHTS.items():
            overall += tier_scores[severity] * weight
            weight_sum += weight

        if weight_sum > 0:
            overall = overall / weight_sum

        return ComplianceScore(
            overall_score=round(overall, 2),
            critical_score=round(tier_scores.get("critical", 100.0), 2),
            high_score=round(tier_scores.get("high", 100.0), 2),
            medium_score=round(tier_scores.get("medium", 100.0), 2),
            low_score=round(tier_scores.get("low", 100.0), 2),
            passed_count=total_passed,
            failed_count=total_failed,
            total_count=total_count,
        )

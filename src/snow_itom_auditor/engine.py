"""Core audit engine that orchestrates check execution and result aggregation.

The AuditEngine runs individual check functions, catches errors, calculates
compliance scores, and produces AuditResult objects.
"""

from __future__ import annotations

import logging
import traceback
from collections.abc import Callable
from datetime import UTC, datetime

from snow_itom_auditor.client import ServiceNowClient
from snow_itom_auditor.config import AuditConfig
from snow_itom_auditor.models import AuditCheck, AuditResult, AuditType
from snow_itom_auditor.scoring import ComplianceScorer

logger = logging.getLogger(__name__)


class AuditEngine:
    """Executes audit checks and aggregates results."""

    def __init__(self, config: AuditConfig, client: ServiceNowClient) -> None:
        self.config = config
        self.client = client
        self.scorer = ComplianceScorer()

    def run_check(self, check_fn: Callable[..., AuditCheck], **kwargs: object) -> AuditCheck:
        """Execute a single check function safely.

        If the check function raises, returns an AuditCheck with status='error'
        rather than propagating the exception.

        Args:
            check_fn: A callable that returns an AuditCheck.
            **kwargs: Arguments passed to the check function.

        Returns:
            The AuditCheck result, or an error check if the function failed.
        """
        try:
            return check_fn(**kwargs)
        except Exception as exc:
            logger.error("Check %s failed: %s", check_fn.__name__, exc)
            return AuditCheck(
                name=check_fn.__name__,
                description=f"Check failed with error: {exc}",
                severity="medium",
                status="error",
                details=traceback.format_exc(),
            )

    def run_audit(
        self,
        audit_type: AuditType,
        check_fns: list[Callable[..., AuditCheck]],
        **kwargs: object,
    ) -> AuditResult:
        """Run a full audit by executing all check functions.

        Args:
            audit_type: The type of audit being run.
            check_fns: List of check functions to execute.
            **kwargs: Arguments passed to each check function.

        Returns:
            AuditResult with all checks, score, and summary.
        """
        started = datetime.now(UTC)
        result = AuditResult(
            audit_type=audit_type,
            started_at=started,
            status="running",
        )

        checks: list[AuditCheck] = []
        for fn in check_fns:
            logger.info("Running check: %s", fn.__name__)
            check = self.run_check(fn, **kwargs)
            checks.append(check)

        result.checks = checks
        result.score = self.scorer.calculate_score(checks)
        result.completed_at = datetime.now(UTC)

        passed = sum(1 for c in checks if c.status == "pass")
        failed = sum(1 for c in checks if c.status == "fail")
        errors = sum(1 for c in checks if c.status == "error")
        result.summary = f"{passed} passed, {failed} failed, {errors} errors out of {len(checks)} checks"

        if any(c.status == "error" for c in checks):
            result.status = "completed_with_errors"
        elif failed > 0:
            result.status = "completed"
        else:
            result.status = "passed"

        return result

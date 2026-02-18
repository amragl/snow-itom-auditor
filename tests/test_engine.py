"""Tests for the audit engine."""

from __future__ import annotations

from unittest.mock import MagicMock

from snow_itom_auditor.config import AuditConfig
from snow_itom_auditor.engine import AuditEngine
from snow_itom_auditor.models import AuditCheck


def _make_config() -> AuditConfig:
    return AuditConfig(
        SERVICENOW_INSTANCE="https://test.service-now.com",
        SERVICENOW_USERNAME="u",
        SERVICENOW_PASSWORD="p",
        SERVICENOW_MAX_RETRIES=1,
    )


class TestAuditEngine:
    def setup_method(self) -> None:
        self.config = _make_config()
        self.client = MagicMock()
        self.engine = AuditEngine(self.config, self.client)

    def test_run_check_success(self) -> None:
        def good_check() -> AuditCheck:
            return AuditCheck(name="good", description="passes", severity="low", status="pass")

        result = self.engine.run_check(good_check)
        assert result.status == "pass"
        assert result.name == "good"

    def test_run_check_exception(self) -> None:
        def bad_check() -> AuditCheck:
            raise ValueError("something broke")

        result = self.engine.run_check(bad_check)
        assert result.status == "error"
        assert "something broke" in result.description

    def test_run_audit_all_pass(self) -> None:
        def check1() -> AuditCheck:
            return AuditCheck(name="c1", description="d1", severity="high", status="pass")

        def check2() -> AuditCheck:
            return AuditCheck(name="c2", description="d2", severity="low", status="pass")

        result = self.engine.run_audit("cmdb", [check1, check2])
        assert result.audit_type == "cmdb"
        assert len(result.checks) == 2
        assert result.status == "passed"
        assert result.score is not None
        assert result.score.overall_score == 100.0

    def test_run_audit_with_failure(self) -> None:
        def passing() -> AuditCheck:
            return AuditCheck(name="p", description="d", severity="high", status="pass")

        def failing() -> AuditCheck:
            return AuditCheck(name="f", description="d", severity="critical", status="fail")

        result = self.engine.run_audit("cmdb", [passing, failing])
        assert result.status == "completed"
        assert result.score is not None
        assert result.score.overall_score < 100.0

    def test_run_audit_with_error(self) -> None:
        def erroring() -> AuditCheck:
            raise RuntimeError("boom")

        result = self.engine.run_audit("discovery", [erroring])
        assert result.status == "completed_with_errors"
        assert len(result.checks) == 1
        assert result.checks[0].status == "error"

    def test_run_audit_summary(self) -> None:
        def p() -> AuditCheck:
            return AuditCheck(name="p", description="d", severity="low", status="pass")

        def f() -> AuditCheck:
            return AuditCheck(name="f", description="d", severity="low", status="fail")

        result = self.engine.run_audit("asset", [p, f])
        assert "1 passed" in result.summary
        assert "1 failed" in result.summary

    def test_run_audit_completed_at_set(self) -> None:
        def c() -> AuditCheck:
            return AuditCheck(name="c", description="d", severity="low", status="pass")

        result = self.engine.run_audit("cmdb", [c])
        assert result.completed_at is not None
        assert result.completed_at >= result.started_at

    def test_run_audit_empty_checks(self) -> None:
        result = self.engine.run_audit("cmdb", [])
        assert result.status == "passed"
        assert len(result.checks) == 0
        assert result.score is not None
        assert result.score.overall_score == 100.0

    def test_run_check_with_kwargs(self) -> None:
        def check_with_arg(client: object = None) -> AuditCheck:
            return AuditCheck(
                name="kwarg_check",
                description=f"client={client}",
                severity="low",
                status="pass",
            )

        result = self.engine.run_check(check_with_arg, client="test_client")
        assert result.status == "pass"
        assert "test_client" in result.description

    def test_run_audit_auto_id(self) -> None:
        result = self.engine.run_audit("full", [])
        assert result.id is not None
        assert len(result.id) > 0

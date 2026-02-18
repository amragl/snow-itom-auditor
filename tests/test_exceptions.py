"""Tests for the exception hierarchy."""

from __future__ import annotations

from snow_itom_auditor.exceptions import (
    AuditAPIError,
    AuditAuthError,
    AuditConnectionError,
    AuditError,
    AuditNotFoundError,
    AuditPermissionError,
    AuditRateLimitError,
)


class TestExceptionHierarchy:
    def test_base_error(self) -> None:
        exc = AuditError("base error")
        assert str(exc) == "base error"
        assert exc.details == {}

    def test_base_error_with_details(self) -> None:
        exc = AuditError("err", details={"key": "val"})
        assert exc.details == {"key": "val"}

    def test_connection_error_is_audit_error(self) -> None:
        exc = AuditConnectionError("conn failed")
        assert isinstance(exc, AuditError)
        assert str(exc) == "conn failed"

    def test_auth_error_is_audit_error(self) -> None:
        exc = AuditAuthError("bad creds")
        assert isinstance(exc, AuditError)

    def test_not_found_error_is_audit_error(self) -> None:
        exc = AuditNotFoundError("no such record")
        assert isinstance(exc, AuditError)

    def test_permission_error_is_audit_error(self) -> None:
        exc = AuditPermissionError("forbidden")
        assert isinstance(exc, AuditError)

    def test_rate_limit_error_with_retry_after(self) -> None:
        exc = AuditRateLimitError("slow down", retry_after=30)
        assert isinstance(exc, AuditError)
        assert exc.retry_after == 30

    def test_rate_limit_error_no_retry_after(self) -> None:
        exc = AuditRateLimitError("slow down")
        assert exc.retry_after is None

    def test_api_error_with_status_code(self) -> None:
        exc = AuditAPIError("server error", status_code=500)
        assert isinstance(exc, AuditError)
        assert exc.status_code == 500

    def test_api_error_no_status_code(self) -> None:
        exc = AuditAPIError("unknown")
        assert exc.status_code is None

    def test_all_inherit_from_base(self) -> None:
        subclasses = [
            AuditConnectionError,
            AuditAuthError,
            AuditNotFoundError,
            AuditPermissionError,
            AuditRateLimitError,
            AuditAPIError,
        ]
        for cls in subclasses:
            assert issubclass(cls, AuditError), f"{cls.__name__} should inherit from AuditError"

    def test_exception_details_propagation(self) -> None:
        details = {"error": {"message": "Not found", "detail": "Record not in table"}}
        exc = AuditNotFoundError("not found", details=details)
        assert exc.details["error"]["message"] == "Not found"

"""Custom exception hierarchy for the ITOM Compliance Auditor.

Maps ServiceNow REST API errors and internal failures to typed exceptions
for structured error handling throughout the audit pipeline.
"""

from __future__ import annotations


class AuditError(Exception):
    """Base exception for all audit-related errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class AuditConnectionError(AuditError):
    """Raised when the ServiceNow instance is unreachable."""


class AuditAuthError(AuditError):
    """Raised when authentication to ServiceNow fails (401)."""


class AuditNotFoundError(AuditError):
    """Raised when a requested resource does not exist (404)."""


class AuditPermissionError(AuditError):
    """Raised when the user lacks permission for the requested operation (403)."""


class AuditRateLimitError(AuditError):
    """Raised when ServiceNow returns a rate-limit response (429)."""

    def __init__(self, message: str, retry_after: int | None = None, details: dict | None = None) -> None:
        super().__init__(message, details)
        self.retry_after = retry_after


class AuditAPIError(AuditError):
    """Raised for unexpected ServiceNow API errors (5xx, malformed response, etc)."""

    def __init__(self, message: str, status_code: int | None = None, details: dict | None = None) -> None:
        super().__init__(message, details)
        self.status_code = status_code

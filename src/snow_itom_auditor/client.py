"""ServiceNow REST client with authentication, retry logic, and error mapping.

Provides a reusable client for querying ServiceNow Table API with
exponential backoff on transient failures and structured exception mapping.
"""

from __future__ import annotations

import logging
import time

import requests

from snow_itom_auditor.config import AuditConfig
from snow_itom_auditor.exceptions import (
    AuditAPIError,
    AuditAuthError,
    AuditConnectionError,
    AuditNotFoundError,
    AuditPermissionError,
    AuditRateLimitError,
)

logger = logging.getLogger(__name__)


class ServiceNowClient:
    """REST client for the ServiceNow Table API."""

    def __init__(self, config: AuditConfig) -> None:
        self.config = config
        self.base_url = config.servicenow_instance.rstrip("/")
        self.session = requests.Session()
        self.session.auth = (config.servicenow_username, config.servicenow_password)
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        self.timeout = config.servicenow_timeout
        self.max_retries = config.servicenow_max_retries

    def _request(self, method: str, url: str, **kwargs: object) -> requests.Response:
        """Execute an HTTP request with retry logic and error mapping.

        The initial attempt plus up to ``max_retries`` retries are made,
        giving a total of ``max_retries + 1`` attempts.
        """
        last_exception: Exception | None = None
        for attempt in range(1, self.max_retries + 2):
            try:
                response = self.session.request(
                    method,
                    url,
                    timeout=self.timeout,
                    **kwargs,  # type: ignore[arg-type]
                )
                self._raise_for_status(response)
                return response
            except AuditRateLimitError as exc:
                last_exception = exc
                wait = exc.retry_after or (2 ** (attempt - 1))
                logger.warning("Rate limited, retrying in %ds (attempt %d/%d)", wait, attempt, self.max_retries + 1)
                time.sleep(wait)
            except AuditConnectionError as exc:
                last_exception = exc
                wait = 2 ** (attempt - 1)
                logger.warning("Connection error, retrying in %ds (attempt %d/%d)", wait, attempt, self.max_retries + 1)
                time.sleep(wait)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exception = AuditConnectionError(
                    f"Connection failed: {exc}",
                    details={"url": url, "attempt": attempt},
                )
                wait = 2 ** (attempt - 1)
                logger.warning("Connection error, retrying in %ds (attempt %d/%d)", wait, attempt, self.max_retries + 1)
                time.sleep(wait)
        raise last_exception  # type: ignore[misc]

    def _raise_for_status(self, response: requests.Response) -> None:
        """Map HTTP status codes to typed audit exceptions."""
        if response.ok:
            return
        status = response.status_code
        try:
            body = response.json()
        except ValueError:
            body = {"raw": response.text[:500]}

        if status == 401:
            raise AuditAuthError("Authentication failed", details=body)
        if status == 403:
            raise AuditPermissionError("Permission denied", details=body)
        if status == 404:
            raise AuditNotFoundError("Resource not found", details=body)
        if status == 429:
            retry_after = response.headers.get("Retry-After")
            raise AuditRateLimitError(
                "Rate limit exceeded",
                retry_after=int(retry_after) if retry_after else None,
                details=body,
            )
        raise AuditAPIError(
            f"API error: HTTP {status}",
            status_code=status,
            details=body,
        )

    def get_records(
        self,
        table: str,
        fields: list[str] | None = None,
        query: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query records from a ServiceNow table.

        Args:
            table: ServiceNow table name (e.g. 'cmdb_ci').
            fields: Optional list of field names to return.
            query: Optional encoded query string.
            limit: Maximum number of records to return.

        Returns:
            List of record dictionaries.
        """
        url = f"{self.base_url}/api/now/table/{table}"
        params: dict[str, str | int] = {"sysparm_limit": limit}
        if fields:
            params["sysparm_fields"] = ",".join(fields)
        if query:
            params["sysparm_query"] = query

        response = self._request("GET", url, params=params)
        data = response.json()
        return data.get("result", [])

    def get_record(self, table: str, sys_id: str, fields: list[str] | None = None) -> dict:
        """Retrieve a single record by sys_id.

        Args:
            table: ServiceNow table name.
            sys_id: The sys_id of the record.
            fields: Optional list of field names to return.

        Returns:
            Record dictionary.

        Raises:
            AuditNotFoundError: If the record does not exist.
        """
        url = f"{self.base_url}/api/now/table/{table}/{sys_id}"
        params: dict[str, str] = {}
        if fields:
            params["sysparm_fields"] = ",".join(fields)

        response = self._request("GET", url, params=params)
        data = response.json()
        return data.get("result", {})

    def get_record_count(self, table: str, query: str | None = None) -> int:
        """Get the count of records matching a query using the Stats API.

        Args:
            table: ServiceNow table name.
            query: Optional encoded query string.

        Returns:
            Integer count of matching records.
        """
        url = f"{self.base_url}/api/now/stats/{table}"
        params: dict[str, str] = {"sysparm_count": "true"}
        if query:
            params["sysparm_query"] = query

        response = self._request("GET", url, params=params)
        data = response.json()
        stats = data.get("result", {}).get("stats", {})
        return int(stats.get("count", 0))

"""Shared test fixtures for the ITOM Compliance Auditor test suite.

Unit tests use MagicMock to simulate HTTP responses from requests.
Integration tests (tests/integration/) require a real ServiceNow instance.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from snow_itom_auditor.client import ServiceNowClient
from snow_itom_auditor.config import AuditConfig
from snow_itom_auditor.storage import AuditStorage


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def env_configured() -> bool:
    """Check whether ServiceNow environment variables are configured."""
    required_vars = ["SERVICENOW_INSTANCE", "SERVICENOW_USERNAME", "SERVICENOW_PASSWORD"]
    return all(os.environ.get(var) for var in required_vars)


@pytest.fixture
def audit_config() -> AuditConfig:
    """Return an AuditConfig with test values."""
    return AuditConfig(
        SERVICENOW_INSTANCE="https://test.service-now.com",
        SERVICENOW_USERNAME="admin",
        SERVICENOW_PASSWORD="password",
        SERVICENOW_TIMEOUT=10,
        SERVICENOW_MAX_RETRIES=1,
        AUDIT_STORAGE_PATH="/tmp/test-snow-audit",
        LOG_LEVEL="DEBUG",
    )


@pytest.fixture
def mock_session() -> MagicMock:
    """Return a MagicMock that simulates a requests.Session."""
    session = MagicMock()
    response = MagicMock()
    response.ok = True
    response.status_code = 200
    response.json.return_value = {"result": []}
    session.request.return_value = response
    return session


@pytest.fixture
def snow_client(audit_config: AuditConfig, mock_session: MagicMock) -> ServiceNowClient:
    """Return a ServiceNowClient with a mocked HTTP session."""
    client = ServiceNowClient(audit_config)
    client.session = mock_session
    return client


@pytest.fixture
def audit_storage(tmp_path: Path) -> AuditStorage:
    """Return an AuditStorage using a temp directory."""
    return AuditStorage(str(tmp_path / "audit-storage"))

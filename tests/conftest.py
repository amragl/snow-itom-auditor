"""Shared test fixtures for the ITOM Compliance Auditor test suite.

Provides fixtures for ServiceNow client configuration, test data paths,
and common test utilities. All tests use real ServiceNow API calls --
no mocks are permitted.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def env_configured() -> bool:
    """Check whether ServiceNow environment variables are configured.

    Returns True if all required environment variables are set.
    Tests that require a live ServiceNow connection should skip
    if this returns False.
    """
    required_vars = ["SNOW_INSTANCE", "SNOW_USER", "SNOW_PASSWORD"]
    return all(os.environ.get(var) for var in required_vars)

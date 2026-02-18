"""Tests for configuration management."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from snow_itom_auditor.config import AuditConfig, get_config


class TestAuditConfig:
    """Tests for the AuditConfig pydantic-settings model."""

    def test_create_with_required_fields(self) -> None:
        config = AuditConfig(
            SERVICENOW_INSTANCE="https://test.service-now.com",
            SERVICENOW_USERNAME="admin",
            SERVICENOW_PASSWORD="secret",
        )
        assert config.servicenow_instance == "https://test.service-now.com"
        assert config.servicenow_username == "admin"
        assert config.servicenow_password == "secret"

    def test_default_timeout(self) -> None:
        config = AuditConfig(
            SERVICENOW_INSTANCE="https://x.service-now.com",
            SERVICENOW_USERNAME="u",
            SERVICENOW_PASSWORD="p",
        )
        assert config.servicenow_timeout == 30

    def test_default_max_retries(self) -> None:
        config = AuditConfig(
            SERVICENOW_INSTANCE="https://x.service-now.com",
            SERVICENOW_USERNAME="u",
            SERVICENOW_PASSWORD="p",
        )
        assert config.servicenow_max_retries == 3

    def test_default_storage_path(self) -> None:
        config = AuditConfig(
            SERVICENOW_INSTANCE="https://x.service-now.com",
            SERVICENOW_USERNAME="u",
            SERVICENOW_PASSWORD="p",
        )
        assert config.audit_storage_path == ".snow-audit"

    def test_default_log_level(self) -> None:
        config = AuditConfig(
            SERVICENOW_INSTANCE="https://x.service-now.com",
            SERVICENOW_USERNAME="u",
            SERVICENOW_PASSWORD="p",
        )
        assert config.log_level == "INFO"

    def test_custom_timeout(self) -> None:
        config = AuditConfig(
            SERVICENOW_INSTANCE="https://x.service-now.com",
            SERVICENOW_USERNAME="u",
            SERVICENOW_PASSWORD="p",
            SERVICENOW_TIMEOUT=60,
        )
        assert config.servicenow_timeout == 60

    def test_custom_storage_path(self) -> None:
        config = AuditConfig(
            SERVICENOW_INSTANCE="https://x.service-now.com",
            SERVICENOW_USERNAME="u",
            SERVICENOW_PASSWORD="p",
            AUDIT_STORAGE_PATH="/custom/path",
        )
        assert config.audit_storage_path == "/custom/path"

    def test_missing_instance_raises(self) -> None:
        with pytest.raises(ValidationError):
            AuditConfig(
                SERVICENOW_USERNAME="u",
                SERVICENOW_PASSWORD="p",
            )

    def test_missing_username_raises(self) -> None:
        with pytest.raises(ValidationError):
            AuditConfig(
                SERVICENOW_INSTANCE="https://x.service-now.com",
                SERVICENOW_PASSWORD="p",
            )

    def test_missing_password_raises(self) -> None:
        with pytest.raises(ValidationError):
            AuditConfig(
                SERVICENOW_INSTANCE="https://x.service-now.com",
                SERVICENOW_USERNAME="u",
            )

    def test_from_environment_variables(self) -> None:
        env = {
            "SERVICENOW_INSTANCE": "https://env.service-now.com",
            "SERVICENOW_USERNAME": "env_user",
            "SERVICENOW_PASSWORD": "env_pass",
            "SERVICENOW_TIMEOUT": "45",
        }
        with patch.dict(os.environ, env, clear=False):
            config = AuditConfig()
            assert config.servicenow_instance == "https://env.service-now.com"
            assert config.servicenow_username == "env_user"
            assert config.servicenow_timeout == 45

    def test_extra_fields_ignored(self) -> None:
        config = AuditConfig(
            SERVICENOW_INSTANCE="https://x.service-now.com",
            SERVICENOW_USERNAME="u",
            SERVICENOW_PASSWORD="p",
            UNKNOWN_FIELD="should be ignored",
        )
        assert not hasattr(config, "unknown_field")


class TestGetConfig:
    """Tests for the get_config() cached factory."""

    def test_get_config_returns_config(self) -> None:
        env = {
            "SERVICENOW_INSTANCE": "https://cached.service-now.com",
            "SERVICENOW_USERNAME": "cached_user",
            "SERVICENOW_PASSWORD": "cached_pass",
        }
        get_config.cache_clear()
        with patch.dict(os.environ, env, clear=False):
            config = get_config()
            assert isinstance(config, AuditConfig)
            assert config.servicenow_instance == "https://cached.service-now.com"
        get_config.cache_clear()

    def test_get_config_is_cached(self) -> None:
        env = {
            "SERVICENOW_INSTANCE": "https://cached2.service-now.com",
            "SERVICENOW_USERNAME": "u",
            "SERVICENOW_PASSWORD": "p",
        }
        get_config.cache_clear()
        with patch.dict(os.environ, env, clear=False):
            c1 = get_config()
            c2 = get_config()
            assert c1 is c2
        get_config.cache_clear()

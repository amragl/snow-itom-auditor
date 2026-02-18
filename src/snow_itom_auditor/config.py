"""Configuration management for the ITOM Compliance Auditor.

Loads settings from environment variables and .env files using pydantic-settings.
Provides a cached singleton via get_config().
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuditConfig(BaseSettings):
    """Application configuration sourced from environment variables."""

    servicenow_instance: str = Field(..., alias="SERVICENOW_INSTANCE")
    servicenow_username: str = Field(..., alias="SERVICENOW_USERNAME")
    servicenow_password: str = Field(..., alias="SERVICENOW_PASSWORD")
    servicenow_timeout: int = Field(30, alias="SERVICENOW_TIMEOUT")
    servicenow_max_retries: int = Field(3, alias="SERVICENOW_MAX_RETRIES")
    audit_storage_path: str = Field(".snow-audit", alias="AUDIT_STORAGE_PATH")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache(maxsize=1)
def get_config() -> AuditConfig:
    """Return a cached singleton of AuditConfig."""
    return AuditConfig()

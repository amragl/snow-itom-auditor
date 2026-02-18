"""Pydantic v2 data models for audit findings, results, compliance scores, and remediation plans.

All core data structures used throughout the auditor live here.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

CheckSeverity = Literal["critical", "high", "medium", "low"]
CheckStatus = Literal["pass", "fail", "skip", "error"]
AuditType = Literal["cmdb", "discovery", "asset", "full"]
RemediationPriority = Literal["critical", "high", "medium", "low"]
RemediationItemStatus = Literal["pending", "in_progress", "done", "skipped"]


class AuditCheck(BaseModel):
    """A single compliance check result."""

    name: str
    description: str
    severity: CheckSeverity
    status: CheckStatus
    details: str = ""
    affected_count: int = 0
    affected_sys_ids: list[str] = Field(default_factory=list)


class ComplianceScore(BaseModel):
    """Calculated compliance score with severity-tier breakdowns."""

    overall_score: float = Field(ge=0, le=100)
    critical_score: float = Field(ge=0, le=100)
    high_score: float = Field(ge=0, le=100)
    medium_score: float = Field(ge=0, le=100)
    low_score: float = Field(ge=0, le=100)
    passed_count: int = 0
    failed_count: int = 0
    total_count: int = 0


class AuditResult(BaseModel):
    """Complete result of an audit run."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    audit_type: AuditType
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    checks: list[AuditCheck] = Field(default_factory=list)
    score: ComplianceScore | None = None
    status: str = "running"
    summary: str = ""


class RemediationItem(BaseModel):
    """A single actionable remediation task."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    check_name: str
    priority: RemediationPriority
    action: str
    target_sys_ids: list[str] = Field(default_factory=list)
    status: RemediationItemStatus = "pending"
    notes: str = ""


class RemediationPlan(BaseModel):
    """An actionable remediation plan generated from audit findings."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    audit_result_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    items: list[RemediationItem] = Field(default_factory=list)
    status: str = "active"
    progress_pct: float = 0.0

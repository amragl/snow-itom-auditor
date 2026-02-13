"""Pydantic data models for audit findings, results, compliance scores, and remediation plans.

Defines the core data structures used throughout the auditor:
- AuditFinding: individual compliance issue found during an audit
- AuditResult: complete result of an audit run including all findings
- ComplianceScore: calculated compliance score with category breakdowns
- RemediationPlan: actionable plan for addressing findings

Full implementation in AUDIT-005.
"""

from __future__ import annotations

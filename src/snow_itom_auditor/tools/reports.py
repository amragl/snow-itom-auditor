"""Compliance report generation MCP tool.

Generates structured compliance reports from audit results with executive
summary, score breakdown, findings by severity, and recommendations.
"""

from __future__ import annotations

from snow_itom_auditor.client import ServiceNowClient
from snow_itom_auditor.config import AuditConfig
from snow_itom_auditor.models import AuditResult
from snow_itom_auditor.storage import AuditStorage
from snow_itom_auditor.tools.orchestration import run_full_audit


def _build_report(result: AuditResult) -> dict:
    """Build a structured report dict from an AuditResult."""
    findings_by_severity: dict[str, list[dict]] = {
        "critical": [],
        "high": [],
        "medium": [],
        "low": [],
    }

    for check in result.checks:
        if check.status == "fail":
            findings_by_severity[check.severity].append({
                "name": check.name,
                "description": check.description,
                "details": check.details,
                "affected_count": check.affected_count,
            })

    total_findings = sum(len(v) for v in findings_by_severity.values())
    score_val = result.score.overall_score if result.score else 0.0

    if score_val >= 90:
        grade = "A"
        risk_level = "low"
    elif score_val >= 75:
        grade = "B"
        risk_level = "moderate"
    elif score_val >= 60:
        grade = "C"
        risk_level = "elevated"
    elif score_val >= 40:
        grade = "D"
        risk_level = "high"
    else:
        grade = "F"
        risk_level = "critical"

    recommendations: list[str] = []
    if findings_by_severity["critical"]:
        recommendations.append(
            f"Address {len(findings_by_severity['critical'])} critical finding(s) immediately"
        )
    if findings_by_severity["high"]:
        recommendations.append(
            f"Prioritize {len(findings_by_severity['high'])} high-severity finding(s) within this sprint"
        )
    if score_val < 75:
        recommendations.append("Schedule a comprehensive remediation review")
    if total_findings == 0:
        recommendations.append("Maintain current practices and consider expanding audit coverage")

    return {
        "audit_id": result.id,
        "audit_type": result.audit_type,
        "completed_at": result.completed_at.isoformat() if result.completed_at else None,
        "executive_summary": {
            "overall_score": score_val,
            "grade": grade,
            "risk_level": risk_level,
            "total_checks": len(result.checks),
            "total_findings": total_findings,
            "summary": result.summary,
        },
        "score": result.score.model_dump() if result.score else None,
        "findings_by_severity": findings_by_severity,
        "recommendations": recommendations,
    }


def generate_compliance_report(
    config: AuditConfig,
    client: ServiceNowClient,
    storage: AuditStorage,
    audit_id: str | None = None,
    audit_type: str = "full",
    report_format: str = "json",
) -> dict:
    """Generate a compliance report from an audit result.

    If audit_id is provided, loads that specific result. Otherwise runs a fresh
    audit of the specified type.

    Args:
        config: Application configuration.
        client: ServiceNow REST client.
        storage: Audit storage instance.
        audit_id: Optional specific audit result to report on.
        audit_type: Type of audit to run if no audit_id (default: full).
        report_format: Output format (currently only 'json' supported).

    Returns:
        Structured report dict.
    """
    if audit_id:
        result = storage.load_audit_result(audit_id)
    else:
        result_dict = run_full_audit(config, client, storage)
        result = AuditResult.model_validate(result_dict)

    report = _build_report(result)
    report["format"] = report_format
    return report

"""Audit history retrieval and comparison MCP tools.

Provides tools to browse past audit results and compare two audits
for trend analysis (score deltas, new/resolved findings).
"""

from __future__ import annotations

from snow_itom_auditor.storage import AuditStorage


def get_audit_history(storage: AuditStorage, audit_type: str | None = None, limit: int = 10) -> dict:
    """Retrieve a list of past audit results.

    Args:
        storage: Audit storage instance.
        audit_type: Optional filter by audit type.
        limit: Maximum number of results to return.

    Returns:
        Dict with list of audit summaries.
    """
    results = storage.list_audit_results(audit_type=audit_type, limit=limit)
    return {
        "audits": results,
        "total_returned": len(results),
        "filter": audit_type,
    }


def compare_audits(storage: AuditStorage, audit_id_1: str, audit_id_2: str) -> dict:
    """Compare two audit runs for trend analysis.

    Identifies score deltas, new findings, resolved findings, and persistent issues.

    Args:
        storage: Audit storage instance.
        audit_id_1: The older audit result ID.
        audit_id_2: The newer audit result ID.

    Returns:
        Dict with comparison data.
    """
    result_1 = storage.load_audit_result(audit_id_1)
    result_2 = storage.load_audit_result(audit_id_2)

    score_1 = result_1.score.overall_score if result_1.score else 0.0
    score_2 = result_2.score.overall_score if result_2.score else 0.0
    score_delta = round(score_2 - score_1, 2)

    # Build sets of failed check names for comparison
    failed_1 = {c.name for c in result_1.checks if c.status == "fail"}
    failed_2 = {c.name for c in result_2.checks if c.status == "fail"}

    new_findings = sorted(failed_2 - failed_1)
    resolved_findings = sorted(failed_1 - failed_2)
    persistent_findings = sorted(failed_1 & failed_2)

    trend = "improving" if score_delta > 0 else "declining" if score_delta < 0 else "stable"

    return {
        "audit_id_1": audit_id_1,
        "audit_id_2": audit_id_2,
        "score_1": score_1,
        "score_2": score_2,
        "score_delta": score_delta,
        "trend": trend,
        "new_findings": new_findings,
        "resolved_findings": resolved_findings,
        "persistent_findings": persistent_findings,
        "checks_count_1": len(result_1.checks),
        "checks_count_2": len(result_2.checks),
    }

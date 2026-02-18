"""Compliance rules listing and score retrieval MCP tools.

Provides tools to list all defined audit check names and descriptions,
and to retrieve the latest compliance score from storage.
"""

from __future__ import annotations

from snow_itom_auditor.storage import AuditStorage

# Registry of all defined audit checks with descriptions
COMPLIANCE_RULES: list[dict[str, str]] = [
    {"name": "orphan_cis", "category": "cmdb", "severity": "medium", "description": "Detect CIs with no relationships"},
    {"name": "stale_records", "category": "cmdb", "severity": "high", "description": "Detect CIs not updated in 90+ days"},
    {"name": "duplicate_cis", "category": "cmdb", "severity": "high", "description": "Detect CIs with same name and class"},
    {
        "name": "missing_ip_address",
        "category": "cmdb",
        "severity": "critical",
        "description": "Detect server CIs missing IP address",
    },
    {
        "name": "stale_discovery_schedules",
        "category": "discovery",
        "severity": "high",
        "description": "Detect discovery schedules not run in 7+ days",
    },
    {
        "name": "pattern_coverage",
        "category": "discovery",
        "severity": "medium",
        "description": "Check active discovery pattern count",
    },
    {
        "name": "ci_reconciliation",
        "category": "discovery",
        "severity": "medium",
        "description": "Detect CIs with no discovery source",
    },
    {
        "name": "license_overallocation",
        "category": "asset",
        "severity": "critical",
        "description": "Detect licenses exceeding allocated count",
    },
    {
        "name": "expired_hardware",
        "category": "asset",
        "severity": "high",
        "description": "Detect hardware past end-of-life",
    },
    {
        "name": "unassigned_assets",
        "category": "asset",
        "severity": "low",
        "description": "Detect active assets with no assigned user",
    },
]


def list_compliance_rules(category: str | None = None) -> dict:
    """List all defined audit compliance rules.

    Args:
        category: Optional filter by category (cmdb, discovery, asset).

    Returns:
        Dict with list of rules and total count.
    """
    rules = COMPLIANCE_RULES
    if category:
        rules = [r for r in rules if r["category"] == category]

    return {
        "rules": rules,
        "total_count": len(rules),
        "categories": sorted({r["category"] for r in COMPLIANCE_RULES}),
    }


def get_compliance_score(storage: AuditStorage, audit_type: str | None = None) -> dict:
    """Retrieve the latest compliance score from storage.

    Args:
        storage: Audit storage instance.
        audit_type: Optional filter by audit type.

    Returns:
        Dict with latest score, or a message if no audits exist.
    """
    results = storage.list_audit_results(audit_type=audit_type, limit=1)
    if not results:
        return {
            "status": "no_data",
            "message": "No audit results found. Run an audit first.",
        }

    latest = results[0]
    return {
        "status": "ok",
        "audit_id": latest["id"],
        "audit_type": latest["audit_type"],
        "completed_at": latest.get("completed_at"),
        "overall_score": latest.get("overall_score"),
    }

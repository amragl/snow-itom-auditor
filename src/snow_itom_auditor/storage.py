"""JSON-based file storage for audit results and remediation plans.

Persists audit history to the local filesystem under the configured
audit_storage_path, enabling history queries and trend comparison.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from snow_itom_auditor.models import AuditResult, RemediationPlan

logger = logging.getLogger(__name__)


class AuditStorage:
    """Manages persistence of audit results and remediation plans."""

    def __init__(self, base_path: str) -> None:
        self.base_path = Path(base_path)
        self.history_path = self.base_path / "history"
        self.remediation_path = self.base_path / "remediation"
        self.history_path.mkdir(parents=True, exist_ok=True)
        self.remediation_path.mkdir(parents=True, exist_ok=True)

    def save_audit_result(self, result: AuditResult) -> str:
        """Persist an audit result to disk.

        Args:
            result: The AuditResult to save.

        Returns:
            The audit result ID.
        """
        file_path = self.history_path / f"{result.id}.json"
        file_path.write_text(result.model_dump_json(indent=2))
        logger.info("Saved audit result %s to %s", result.id, file_path)
        return result.id

    def load_audit_result(self, audit_id: str) -> AuditResult:
        """Load an audit result by ID.

        Args:
            audit_id: The UUID of the audit result.

        Returns:
            The deserialized AuditResult.

        Raises:
            FileNotFoundError: If the audit result file does not exist.
        """
        file_path = self.history_path / f"{audit_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Audit result not found: {audit_id}")
        return AuditResult.model_validate_json(file_path.read_text())

    def list_audit_results(self, audit_type: str | None = None, limit: int = 50) -> list[dict]:
        """List stored audit results with optional type filtering.

        Args:
            audit_type: Filter by audit type (cmdb, discovery, asset, full).
            limit: Maximum number of results to return.

        Returns:
            List of summary dicts with id, audit_type, started_at, status, score.
        """
        results: list[dict] = []
        files = sorted(self.history_path.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

        for file_path in files:
            if len(results) >= limit:
                break
            try:
                data = json.loads(file_path.read_text())
                if audit_type and data.get("audit_type") != audit_type:
                    continue
                results.append({
                    "id": data["id"],
                    "audit_type": data["audit_type"],
                    "started_at": data.get("started_at"),
                    "completed_at": data.get("completed_at"),
                    "status": data.get("status"),
                    "overall_score": data.get("score", {}).get("overall_score") if data.get("score") else None,
                })
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning("Skipping corrupt audit file %s: %s", file_path, exc)
                continue

        return results

    def save_remediation_plan(self, plan: RemediationPlan) -> str:
        """Persist a remediation plan to disk.

        Args:
            plan: The RemediationPlan to save.

        Returns:
            The plan ID.
        """
        file_path = self.remediation_path / f"{plan.id}.json"
        file_path.write_text(plan.model_dump_json(indent=2))
        logger.info("Saved remediation plan %s to %s", plan.id, file_path)
        return plan.id

    def load_remediation_plan(self, plan_id: str) -> RemediationPlan:
        """Load a remediation plan by ID.

        Args:
            plan_id: The UUID of the remediation plan.

        Returns:
            The deserialized RemediationPlan.

        Raises:
            FileNotFoundError: If the plan file does not exist.
        """
        file_path = self.remediation_path / f"{plan_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Remediation plan not found: {plan_id}")
        return RemediationPlan.model_validate_json(file_path.read_text())

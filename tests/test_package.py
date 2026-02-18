"""Tests for package structure and importability."""

from __future__ import annotations


def test_package_imports() -> None:
    """Verify the snow_itom_auditor package can be imported."""
    import snow_itom_auditor

    assert snow_itom_auditor.__version__ == "0.1.0"


def test_submodule_imports() -> None:
    """Verify all submodules can be imported without error."""
    import snow_itom_auditor.client
    import snow_itom_auditor.config
    import snow_itom_auditor.engine
    import snow_itom_auditor.exceptions
    import snow_itom_auditor.models
    import snow_itom_auditor.scoring
    import snow_itom_auditor.server
    import snow_itom_auditor.storage
    import snow_itom_auditor.tools
    import snow_itom_auditor.tools.assets
    import snow_itom_auditor.tools.cmdb
    import snow_itom_auditor.tools.compliance
    import snow_itom_auditor.tools.discovery
    import snow_itom_auditor.tools.history
    import snow_itom_auditor.tools.orchestration
    import snow_itom_auditor.tools.remediation
    import snow_itom_auditor.tools.reports

    assert snow_itom_auditor.client is not None
    assert snow_itom_auditor.config is not None
    assert snow_itom_auditor.models is not None
    assert snow_itom_auditor.server is not None


def test_version_format() -> None:
    """Verify the version string follows semantic versioning."""
    from snow_itom_auditor import __version__

    parts = __version__.split(".")
    assert len(parts) == 3, f"Version {__version__} does not follow semver (expected X.Y.Z)"
    for part in parts:
        assert part.isdigit(), f"Version component '{part}' is not numeric"


def test_exports() -> None:
    """Verify key symbols are exported from __init__."""
    from snow_itom_auditor import (
        AuditCheck,
        AuditConfig,
        AuditError,
        AuditResult,
        AuditType,
        CheckSeverity,
        CheckStatus,
        ComplianceScore,
        RemediationItem,
        RemediationPlan,
        get_config,
    )

    assert AuditConfig is not None
    assert AuditCheck is not None
    assert AuditResult is not None
    assert ComplianceScore is not None
    assert RemediationItem is not None
    assert RemediationPlan is not None
    assert AuditError is not None
    assert get_config is not None
    # Type aliases
    assert CheckSeverity is not None
    assert CheckStatus is not None
    assert AuditType is not None

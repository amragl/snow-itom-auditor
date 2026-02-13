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
    import snow_itom_auditor.models
    import snow_itom_auditor.server

    # Verify modules are loaded (not None)
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

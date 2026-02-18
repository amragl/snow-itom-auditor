"""Tests for the FastMCP server module."""

from __future__ import annotations


def test_server_module_imports() -> None:
    """Verify the server module can be imported without starting the server."""
    from snow_itom_auditor.server import mcp

    assert mcp is not None
    assert mcp.name == "snow-itom-auditor"


def test_server_has_main() -> None:
    """Verify the main entry point function exists."""
    from snow_itom_auditor.server import main

    assert callable(main)


def test_mcp_tools_registered() -> None:
    """Verify MCP tools are registered on the server."""

    # FastMCP stores tools internally; check that key tool functions exist
    from snow_itom_auditor import server

    tool_functions = [
        "audit_cmdb",
        "audit_discovery",
        "audit_assets",
        "audit_full",
        "compliance_rules",
        "compliance_score",
        "compliance_report",
        "audit_history",
        "audit_compare",
        "remediation_create",
        "remediation_progress",
        "remediation_validate",
        "health_check",
    ]
    for name in tool_functions:
        assert hasattr(server, name), f"Tool function {name} not found on server module"


def test_get_dependencies_lazy() -> None:
    """Verify _get_dependencies is defined and callable."""
    from snow_itom_auditor.server import _get_dependencies

    assert callable(_get_dependencies)


def test_tool_functions_exist() -> None:
    """Verify each tool function exists on the server module.

    FastMCP's @mcp.tool() decorator wraps functions into FunctionTool objects,
    so we check existence via hasattr rather than callable().
    """
    from snow_itom_auditor import server

    tool_names = [
        "audit_cmdb",
        "audit_discovery",
        "audit_assets",
        "audit_full",
        "compliance_rules",
        "compliance_score",
        "compliance_report",
        "audit_history",
        "audit_compare",
        "remediation_create",
        "remediation_progress",
        "remediation_validate",
        "health_check",
    ]
    for name in tool_names:
        assert hasattr(server, name), f"{name} should exist on server module"
        fn = getattr(server, name)
        assert fn is not None, f"{name} should not be None"

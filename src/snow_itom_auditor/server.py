"""FastMCP server entry point for the ITOM Compliance Auditor.

This module initializes the FastMCP server instance and registers all MCP tools.
The server connects to a ServiceNow instance to perform CMDB, Discovery, and Asset
compliance audits.
"""

from __future__ import annotations


def main() -> None:
    """Entry point for the snow-itom-auditor MCP server.

    Initializes configuration, creates the ServiceNow client, registers MCP tools,
    and starts the FastMCP server. Full implementation in AUDIT-003.
    """
    raise NotImplementedError(
        "Server implementation pending AUDIT-003. "
        "This module provides the entry point that will be wired up once "
        "the FastMCP server setup and ServiceNow client are built."
    )

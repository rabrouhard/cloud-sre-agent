from __future__ import annotations
from typing import Any
from mcp.server.fastmcp import FastMCP
from src.services.runbook_registry import RunbookRegistry


def register_runbook_tools(mcp: FastMCP, registry: RunbookRegistry) -> None:
    """Register runbook-related tools on the provided FastMCP instance.

    Args:
        mcp (FastMCP): The FastMCP instance to register tools with.
        registry (RunbookRegistry): The registry to use for runbook context retrieval.
    """

    @mcp.tool()
    def runbook_get_context(domain: str, category: str) -> dict[str, Any]:
        """Retrieve the context for a given domain and category.

        Args:
            domain (str): The domain to get context for.
            category (str): The category within the domain.

        Returns:
            dict[str, Any]: The context information.
        """

        return registry.get_context(domain=domain, category=category)

    # function returns None as it registers the tool on the mcp instance
    return None
        registry (RunbookRegistry): The registry to use for runbook context retrieval.
    """
    @mcp.tool()
    def runbook_get_context(domain: str, category: str) -> dict[str, Any]:
        return registry.get_context(domain=domain, category=category)

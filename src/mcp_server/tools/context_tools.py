from __future__ import annotations
from typing import Any
from mcp.server.fastmcp import FastMCP
from src.services.application_error_service import ApplicationErrorService
from src.services.aurora_service import AuroraService
from src.services.infrastructure_service import InfrastructureService

def register_context_tools(mcp: FastMCP, aurora_service: AuroraService, infrastructure_service: InfrastructureService, application_error_service: ApplicationErrorService) -> None:
    @mcp.tool()
    def aurora_get_context(alarm_event: dict[str, Any]) -> dict[str, Any]:
        return aurora_service.get_context(alarm_event)

    @mcp.tool()
    def infrastructure_get_context(alarm_event: dict[str, Any]) -> dict[str, Any]:
        return infrastructure_service.get_context(alarm_event)

    @mcp.tool()
    def application_get_error_context(alarm_event: dict[str, Any]) -> dict[str, Any]:
        return application_error_service.get_context(alarm_event)

from __future__ import annotations
from typing import Any
from mcp.server.fastmcp import FastMCP
from src.services.audit_log_service import S3AuditLogService
from src.services.email_service import SmtpEmailService
from src.services.servicenow_service import ServiceNowService

def register_action_tools(mcp: FastMCP, email_service: SmtpEmailService, servicenow_service: ServiceNowService, audit_log_service: S3AuditLogService, default_email_recipients: list[str]) -> None:
    @mcp.tool()
    def email_send_advisory(subject: str, body: str, recipients: list[str] | None = None) -> dict[str, Any]:
        return email_service.send_advisory(recipients=recipients or default_email_recipients, subject=subject, body=body)

    @mcp.tool()
    def servicenow_create_incident(short_description: str, description: str, urgency: str = "2", impact: str = "2", category: str = "inquiry", subcategory: str | None = None) -> dict[str, Any]:
        return servicenow_service.create_incident(short_description=short_description, description=description, urgency=urgency, impact=impact, category=category, subcategory=subcategory)

    @mcp.tool()
    def audit_write_s3(record: dict[str, Any]) -> dict[str, str]:
        return audit_log_service.write(record)

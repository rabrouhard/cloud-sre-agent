from __future__ import annotations
import os
from .fastmcp import FastMCP
from src.mcp_server.tools.action_tools import register_action_tools
from src.mcp_server.tools.context_tools import register_context_tools
from src.mcp_server.tools.runbook_tools import register_runbook_tools
from src.services.application_error_service import ApplicationErrorService
from src.services.audit_log_service import S3AuditLogService
from src.services.aurora_service import AuroraService
from src.services.email_service import SmtpEmailService
from src.services.infrastructure_service import InfrastructureService
from src.services.runbook_registry import RunbookRegistry
from src.services.servicenow_service import ServiceNowService
from src.services.ssm_config_service import SsmConfigService

def build_server() -> FastMCP:
    region = os.environ["AWS_REGION"]
    parameter_prefix = os.environ.get("PARAMETER_PREFIX", "/aurora-sre-agent")
    ssm = SsmConfigService(region_name=region, parameter_prefix=parameter_prefix)
    mcp = FastMCP("aurora-sre-agent-mcp")
    runbook_registry = RunbookRegistry.from_ssm(region_name=region, ssm_config=ssm)

    email_service = SmtpEmailService(
        host=ssm.get_secure_string("smtp/host", True),
        port=int(ssm.get_secure_string("smtp/port", False) or "587"),
        sender=ssm.get_secure_string("smtp/sender", True),
        username=ssm.get_secure_string("smtp/username", False),
        password=ssm.get_secure_string("smtp/password", False),
        use_tls=(ssm.get_secure_string("smtp/use_tls", False) or "true").lower() == "true",
    )
    servicenow_service = ServiceNowService(
        instance_url=ssm.get_secure_string("servicenow/instance_url", True),
        username=ssm.get_secure_string("servicenow/username", False),
        password=ssm.get_secure_string("servicenow/password", False),
        bearer_token=ssm.get_secure_string("servicenow/bearer_token", False),
        default_assignment_group=ssm.get_secure_string("servicenow/assignment_group", False),
        default_cmdb_ci=ssm.get_secure_string("servicenow/cmdb_ci", False),
    )
    audit_log_service = S3AuditLogService(region, ssm.get_secure_string("audit/s3_bucket", True), ssm.get_secure_string("audit/s3_prefix", False) or "audit")
    recipients = [x.strip() for x in (ssm.get_secure_string("smtp/default_recipients", True) or "").split(",") if x.strip()]

    register_context_tools(mcp, AuroraService(region), InfrastructureService(region), ApplicationErrorService(region))
    register_runbook_tools(mcp, runbook_registry)
    register_action_tools(mcp, email_service, servicenow_service, audit_log_service, recipients)
    return mcp

mcp = build_server()

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=int(os.environ.get("MCP_PORT", "8000")))

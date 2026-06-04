from __future__ import annotations
import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any
import boto3
from src.agent.mcp_client import AgentMcpClient
from src.domain.alarm_classifier import AlarmClassifier
from src.domain.models import AlarmDomain
from src.services.bedrock_service import BedrockClaudeService
from src.services.event_validation_service import EventValidationService
from src.services.idempotency_service import IdempotencyService
from src.services.ssm_config_service import SsmConfigService


class DbaSreAgentWorker:
    @staticmethod
    def _safe_float(value: str | None, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def __init__(self) -> None:
        """
        Initialize the DbaSreAgentWorker by setting up AWS region, SSM, SQS, classifier, idempotency, MCP client, and Bedrock service.

        Raises:
            RuntimeError: If required environment variables or SSM parameters are missing.
        """
        self.region = os.environ.get("AWS_REGION")
        if not self.region:
            raise RuntimeError("Missing required environment variable: AWS_REGION")
        self.ssm = SsmConfigService(self.region)
        try:
            self.queue_url = self.ssm.get_secure_string("sqs/queue_url", True)
        except Exception as e:
            raise RuntimeError(
                "Missing required SSM parameter: 'sqs/queue_url'. Please ensure this parameter is set."
            ) from e
        self.sqs = boto3.client("sqs", region_name=self.region)
        self.classifier = AlarmClassifier()
        self.validator = EventValidationService()
        # services
        table_name = self.ssm.get_secure_string("dynamodb/table_name", True)
        self.idempotency = IdempotencyService(self.region, table_name)
        self.mcp = AgentMcpClient(
            self.ssm.get_secure_string("mcp/url", False) or "http://127.0.0.1:8000/mcp"
        )
        self.bedrock = BedrockClaudeService(
            temperature=self._safe_float(
                self.ssm.get_secure_string("bedrock/temperature", False), 0.1
            ),
            model_id=self.ssm.get_secure_string("bedrock/model_id", True),
        )

    async def run_forever(self) -> None:
        """Continuously poll SQS queue for messages and process them."""
        loop = asyncio.get_event_loop()
        while True:
            response = await loop.run_in_executor(
                None,
                self.sqs.receive_message,
                {
                    "QueueUrl": self.queue_url,
                    "MaxNumberOfMessages": 5,
                    "WaitTimeSeconds": 20,
                    "VisibilityTimeout": 900,
                },
            )
            for message in response.get("Messages", []):
                try:
                    await self.process_message(message)
                    await loop.run_in_executor(
                        None,
                        self.sqs.delete_message,
                        {
                            "QueueUrl": self.queue_url,
                            "ReceiptHandle": message["ReceiptHandle"],
                        },
                    )
                except Exception as exc:
                    print(
                        json.dumps({
                            "level": "error",
                            "message": "failed to process message",
                            "error": str(exc),
                        })
                    )

    async def process_message(self, message: dict[str, Any]) -> None:
        body = json.loads(message["Body"])
        event = (
            body if body.get("detail-type") else json.loads(body.get("Message", "{}"))
        )
        self.validator.validate(event)
        event_id = event.get("id") or message.get("MessageId") or str(uuid.uuid4())
        classified = self.classifier.classify(event)
        alarm_key = f"{classified.domain.value}#{classified.alarm_name or 'unknown'}#{classified.category}"
        if not self.idempotency.claim(event_id, alarm_key):
            print(
                json.dumps({
                    "level": "info",
                    "message": "duplicate event skipped",
                    "event_id": event_id,
                })
            )
            return
        operational_context = await self._collect_context(classified.domain, event)
        runbook_result = await self.mcp.call_tool(
            "runbook_get_context",
            {"domain": classified.domain.value, "category": classified.category},
        )
        runbook_context = (
            runbook_result.get("context", "")
            if isinstance(runbook_result, dict)
            else ""
        )
        analysis = self.bedrock.analyze_alarm(
            classified_alarm={
                "domain": classified.domain.value,
                "category": classified.category,
                "severity": classified.severity.value,
                "metric_name": classified.metric_name,
                "alarm_name": classified.alarm_name,
                "reason": classified.reason,
            },
            operational_context=operational_context,
            runbook_context=runbook_context,
        )
        correlation_id = str(uuid.uuid4())
        subject = f"[SRE Agent][{classified.severity.value}][{classified.domain.value}] {classified.alarm_name}"
        body_text = self._format_email_body(analysis, correlation_id, runbook_result)
        incident_result = await self._create_incident_if_needed(
            classified, analysis, body_text
        )
        email_result = await self.mcp.call_tool(
            "email_send_advisory", {"subject": subject, "body": body_text}
        )
        audit_record = {
            "correlation_id": correlation_id,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "classification": {
                "domain": classified.domain.value,
                "category": classified.category,
                "severity": classified.severity.value,
                "metric_name": classified.metric_name,
                "alarm_name": classified.alarm_name,
                "reason": classified.reason,
            },
            "raw_alarm_event": event,
            "operational_context": operational_context,
            "runbook": runbook_result.get("metadata", {})
            if isinstance(runbook_result, dict)
            else {},
            "analysis": analysis,
            "servicenow": incident_result,
            "email": email_result,
        }
        await self.mcp.call_tool("audit_write_s3", {"record": audit_record})

    async def _collect_context(
        self, domain: AlarmDomain, event: dict[str, Any]
    ) -> dict[str, Any]:
        if domain == AlarmDomain.DATABASE:
            return await self.mcp.call_tool(
                "aurora_get_context", {"alarm_event": event}
            )
        if domain == AlarmDomain.INFRASTRUCTURE:
            return await self.mcp.call_tool(
                "infrastructure_get_context", {"alarm_event": event}
            )
        if domain == AlarmDomain.APPLICATION:
            return await self.mcp.call_tool(
                "application_get_error_context", {"alarm_event": event}
            )
        return {"note": "No domain-specific context collector available"}

    async def _create_incident_if_needed(
        self, classified, analysis: dict[str, Any], body_text: str
    ) -> dict[str, Any]:
        enabled = (
            self.ssm.get_secure_string("servicenow/enabled", False) or "true"
        ).lower() == "true"
        if not enabled:
            return {"created": False, "reason": "ServiceNow disabled"}
        priority = analysis.get("servicenow_priority_guidance", {})
        result = await self.mcp.call_tool(
            "servicenow_create_incident",
            {
                "short_description": f"{classified.domain.value}: {classified.alarm_name}",
                "description": body_text,
                "impact": str(priority.get("impact", "2")),
                "urgency": str(priority.get("urgency", "2")),
                "category": classified.domain.value,
                "subcategory": classified.category,
            },
        )
        return result if isinstance(result, dict) else {"result": result}

    def _format_email_body(
        self, analysis: dict[str, Any], correlation_id: str, runbook_result: Any
    ) -> str:
        meta = (
            runbook_result.get("metadata", {})
            if isinstance(runbook_result, dict)
            else {}
        )
        sections = [
            f"Correlation ID: {correlation_id}",
            "",
            f"Summary: {analysis.get('summary')}",
            f"Likely Cause: {analysis.get('likely_cause')}",
            f"Confidence: {analysis.get('confidence')}",
            f"Business Impact: {analysis.get('business_impact')}",
            "",
            "Observed Evidence:",
            *[f"- {x}" for x in analysis.get("observed_evidence", [])],
            "",
            "Recommended Immediate Triage:",
            *[f"- {x}" for x in analysis.get("recommended_immediate_triage", [])],
            "",
            "Suggested Remediation:",
            *[f"- {x}" for x in analysis.get("suggested_remediation", [])],
            "",
            f"Human Approval Required: {analysis.get('human_approval_required', True)}",
            "",
            (
                f"Runbook Source: s3://{meta.get('bucket')}/{meta.get('key')}"
                if meta.get('bucket') and meta.get('key')
                else "Runbook Source: (not available)"
            ),
            f"Runbook ETag: {meta.get('etag') or '(not available)'}",
            f"Runbook Version: {meta.get('version_id') or '(not available)'}",
        ]
        return "\n".join(sections)


if __name__ == "__main__":
    asyncio.run(DbaSreAgentWorker().run_forever())

from __future__ import annotations
import json
import textwrap
from typing import Any


def build_analysis_prompt(
    classified_alarm: dict[str, Any],
    operational_context: dict[str, Any],
    runbook_context: str,
) -> str:
    prompt = textwrap.dedent(f"""
    You are a senior SRE and PostgreSQL DBA analyzing an AWS CloudWatch alarm.

    Use the company runbook context as authoritative guidance. The agent is advisory-only.
    Any availability-impacting, destructive, data-changing, cost-impacting, security-impacting,
    or topology-changing action requires human approval.

    Company Runbook Context:
    ---
    {runbook_context}
    ---

    Classified Alarm:
    # Using default=str to ensure all values are serializable; this will convert unsupported types to strings.
    # Be aware this may mask serialization issues by silently converting non-serializable types.
    {json.dumps(classified_alarm, indent=2, default=str)}

    Operational Context:
    # Using default=str to ensure all values are serializable; this will convert unsupported types to strings.
    # Be aware this may mask serialization issues by silently converting non-serializable types.
    {json.dumps(operational_context, indent=2, default=str)}

    Return valid JSON only with this shape:
    {{
      "summary": "string",
      "domain": "database|infrastructure|application|unknown",
      "category": "string",
      "likely_cause": "string",
      "confidence": "low|medium|high",
      "business_impact": "string",
      "observed_evidence": ["string"],
      "inferred_causes": ["string"],
      "recommended_immediate_triage": ["string"],
      "servicenow_priority_guidance": {{"severity": "Low|Medium|High|Critical", "impact": "1|2|3", "urgency": "1|2|3"}},
      "human_approval_required": true,
      "rollback_or_recovery": ["string"],
      "verification_steps": ["string"],
      "escalation": ["string"],
      "runbook_sections_used": ["string"],
      "missing_context": ["string"]
    }}

    Rules:
    - Separate observed facts from inferred causes.
    - If runbook guidance does not cover the alarm, say so.
    - If telemetry is insufficient, lower confidence and recommend additional diagnostics.
    - Do not include secrets, credentials, tokens, SSM values, or sensitive payloads.
    - For application log events, avoid repeating full stack traces; summarize patterns.
    - For infrastructure alarms, prefer safe diagnostics before disruptive actions.
    - For database alarms, do not recommend autonomous SQL, failover, scaling, restart, or parameter changes.
    """)
    return prompt

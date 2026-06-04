from __future__ import annotations
import json
from typing import Any
import boto3
from src.prompts.analysis_prompt import build_analysis_prompt

class BedrockClaudeService:
    def __init__(self, region_name: str, model_id: str, max_tokens: int = 2500, temperature: float = 0.1):
        self.client = boto3.client("bedrock-runtime", region_name=region_name)
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature

    def analyze_alarm(self, classified_alarm: dict[str, Any], operational_context: dict[str, Any], runbook_context: str) -> dict[str, Any]:
        prompt = build_analysis_prompt(classified_alarm, operational_context, runbook_context)
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        }
        response = self.client.invoke_model(modelId=self.model_id, body=json.dumps(body), accept="application/json", contentType="application/json")
        payload = json.loads(response["body"].read())
        text = payload["content"][0]["text"]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"summary":"Claude returned non-JSON analysis.","raw_response":text,"human_approval_required":True}

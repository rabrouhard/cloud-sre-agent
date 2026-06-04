from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any
import boto3

class S3AuditLogService:
    def __init__(self, region_name: str, bucket_name: str, prefix: str = "audit"):
        self.bucket_name = bucket_name
        self.prefix = prefix.strip("/")
        self.client = boto3.client("s3", region_name=region_name)

    def write(self, record: dict[str, Any]) -> dict[str, str]:
        now = datetime.now(timezone.utc)
        correlation_id = record.get("correlation_id", "unknown")
        classification = record.get("classification", {})
        domain = classification.get("domain", "unknown")
        alarm_name = classification.get("alarm_name", "unknown")
        safe_alarm = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in alarm_name)[:160]
        key = f"{self.prefix}/date={now.date().isoformat()}/domain={domain}/alarm={safe_alarm}/{correlation_id}.json"
        self.client.put_object(Bucket=self.bucket_name, Key=key, Body=json.dumps(record, indent=2, default=str).encode("utf-8"), ContentType="application/json")
        return {"bucket": self.bucket_name, "key": key}

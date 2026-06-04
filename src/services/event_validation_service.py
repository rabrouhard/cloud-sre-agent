from __future__ import annotations
import fnmatch
from typing import Any

class EventValidationService:
    def __init__(self, allowed_account_ids: list[str], allowed_regions: list[str], allowed_alarm_name_patterns: list[str]):
        self.allowed_account_ids = allowed_account_ids
        self.allowed_regions = allowed_regions
        self.allowed_alarm_name_patterns = allowed_alarm_name_patterns

    def validate(self, event: dict[str, Any]) -> None:
        account, region = event.get("account"), event.get("region")
        alarm_name = event.get("detail", {}).get("alarmName", "")
        if account not in self.allowed_account_ids: raise ValueError(f"Rejected event from unapproved account: {account}")
        if region not in self.allowed_regions: raise ValueError(f"Rejected event from unapproved region: {region}")
        if self.allowed_alarm_name_patterns and not any(fnmatch.fnmatch(alarm_name, p) for p in self.allowed_alarm_name_patterns):
            raise ValueError(f"Rejected event from unapproved alarm name: {alarm_name}")
        if event.get("source") != "aws.cloudwatch": raise ValueError(f"Rejected unsupported event source: {event.get('source')}")
        if event.get("detail-type") != "CloudWatch Alarm State Change": raise ValueError(f"Rejected unsupported detail-type: {event.get('detail-type')}")

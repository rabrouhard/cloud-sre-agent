from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any

class AlarmDomain(str, Enum):
    DATABASE = "database"
    INFRASTRUCTURE = "infrastructure"
    APPLICATION = "application"
    UNKNOWN = "unknown"

class AlarmSeverity(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

@dataclass(frozen=True)
class ClassifiedAlarm:
    domain: AlarmDomain
    category: str
    severity: AlarmSeverity
    metric_name: str | None
    alarm_name: str | None
    reason: str | None
    raw_event: dict[str, Any]

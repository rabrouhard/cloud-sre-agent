from __future__ import annotations
from typing import Any
from src.domain.models import AlarmDomain, AlarmSeverity, ClassifiedAlarm

DATABASE_KEYWORDS = {
    "cpuutilization": "aurora_high_cpu",
    "databaseconnections": "aurora_connection_exhaustion",
    "freeablememory": "aurora_low_memory",
    "swapusage": "aurora_low_memory",
    "aurorareplicalag": "aurora_replica_lag",
    "replicalagmaximum": "aurora_replica_lag",
    "readlatency": "aurora_latency",
    "writelatency": "aurora_latency",
    "commitlatency": "aurora_latency",
    "deadlocks": "aurora_deadlocks",
    "freelocalstorage": "aurora_local_storage",
    "volumebytesused": "aurora_storage_pressure",
    "auroravolumebyteslefttotal": "aurora_storage_pressure",
    "rds": "aurora_event",
    "aurora": "aurora_event",
    "postgres": "aurora_event",
    "postgresql": "aurora_event",
}
INFRASTRUCTURE_KEYWORDS = {
    "statuscheckfailed": "ec2_status_check",
    "cpucreditbalance": "ec2_cpu_credit",
    "networkin": "network_throughput",
    "networkout": "network_throughput",
    "diskspacelow": "disk_pressure",
    "diskusedpercent": "disk_pressure",
    "memoryutilization": "memory_pressure",
    "mem_used_percent": "memory_pressure",
    "targetresponsetime": "load_balancer_latency",
    "httpcode_target_5xx_count": "load_balancer_5xx",
    "httpcode_elb_5xx_count": "load_balancer_5xx",
    "unhealthyhostcount": "load_balancer_unhealthy_hosts",
    "healthyhostcount": "load_balancer_unhealthy_hosts",
    "ecs": "ecs_service_health",
    "runningtaskcount": "ecs_service_health",
    "pendingtaskcount": "ecs_service_health",
    "asg": "autoscaling_health",
    "autoscaling": "autoscaling_health",
    "lambdaerrors": "lambda_errors",
    "throttles": "throttling",
}
APPLICATION_KEYWORDS = {
    "error": "application_errors",
    "exception": "application_exceptions",
    "5xx": "application_5xx",
    "4xx": "application_4xx",
    "latency": "application_latency",
    "timeout": "application_timeouts",
    "failedrequest": "application_failed_requests",
    "logerror": "application_log_errors",
    "cloudwatchlogs": "application_log_errors",
    "metricfilter": "application_log_errors",
    "synthetics": "synthetic_canary_failure",
    "canary": "synthetic_canary_failure",
}


class AlarmClassifier:
    def classify(self, event: dict[str, Any]) -> ClassifiedAlarm:
        detail = event.get("detail", {})
        alarm_name = detail.get("alarmName")
        reason = detail.get("state", {}).get("reason")
        metric_name = self._metric(event)
        namespace = self._namespace(event)
        text = f"{alarm_name or ''} {reason or ''} {metric_name or ''} {namespace or ''}".lower()
        domain, category = self._by_namespace(namespace, text)
        if domain == AlarmDomain.UNKNOWN:
            domain, category = self._by_keywords(text)
        return ClassifiedAlarm(
            domain,
            category,
            self._severity(text, domain, category),
            metric_name,
            alarm_name,
            reason,
            event,
        )

    def _metric(self, event: dict[str, Any]):
        config = event.get("detail", {}).get("configuration", {})
        metrics = config.get("metrics", [])
        if metrics:
            return metrics[0].get("metricStat", {}).get("metric", {}).get("name")
        return config.get("metricName")

    def _namespace(self, event: dict[str, Any]):
        config = event.get("detail", {}).get("configuration", {})
        metrics = config.get("metrics", [])
        if metrics:
            return metrics[0].get("metricStat", {}).get("metric", {}).get("namespace")
        return config.get("namespace")

    def _by_namespace(self, namespace: str | None, text: str):
        ns = (namespace or "").lower()
        if ns == "aws/rds" or "aurora" in text or "postgres" in text:
            return AlarmDomain.DATABASE, self._match(
                text, DATABASE_KEYWORDS, "aurora_event"
            )
        if ns in {
            "aws/ec2",
            "aws/ecs",
            "aws/elasticloadbalancing",
            "aws/applicationelb",
            "aws/networkelb",
            "aws/autoscaling",
            "aws/lambda",
            "cwagent",
        }:
            return AlarmDomain.INFRASTRUCTURE, self._match(
                text, INFRASTRUCTURE_KEYWORDS, "generic_infrastructure"
            )
        if ns in {"aws/logs", "aws/synthetics", "application"}:
            return AlarmDomain.APPLICATION, self._match(
                text, APPLICATION_KEYWORDS, "application_errors"
            )
        return AlarmDomain.UNKNOWN, "unknown"

    def _by_keywords(self, text):
        for mapping, domain, default in [
            (DATABASE_KEYWORDS, AlarmDomain.DATABASE, "aurora_event"),
            (
                INFRASTRUCTURE_KEYWORDS,
                AlarmDomain.INFRASTRUCTURE,
                "generic_infrastructure",
            ),
            (APPLICATION_KEYWORDS, AlarmDomain.APPLICATION, "application_errors"),
        ]:
            cat = self._match(text, mapping, None)
            if cat:
                return domain, cat
        return AlarmDomain.UNKNOWN, "unknown"

    def _match(self, text, mapping, default):
        for k, v in mapping.items():
            if k in text:
                return v
        return default or "unknown"

    def _severity(self, text, domain, category):
        if any(
            w in text
            for w in ["critical", "sev1", "p1", "outage", "unavailable", "down"]
        ):
            return AlarmSeverity.CRITICAL
        if any(
            w in text
            for w in ["high", "sev2", "p2", "5xx", "error", "failed", "exhaustion"]
        ):
            return AlarmSeverity.HIGH
        if domain in {AlarmDomain.DATABASE, AlarmDomain.APPLICATION}:
            return AlarmSeverity.MEDIUM
        return AlarmSeverity.LOW

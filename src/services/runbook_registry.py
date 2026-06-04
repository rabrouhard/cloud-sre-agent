from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from src.services.runbook_service import RunbookService
from src.services.s3_runbook_loader import S3RunbookLoader, RunbookLoadResult

DATABASE_CATEGORY_MAP = {
    "aurora_high_cpu": ["High CPU Utilization"],
    "aurora_connection_exhaustion": ["Connection Exhaustion"],
    "aurora_low_memory": ["Low Freeable Memory"],
    "aurora_storage_pressure": [
        "Storage Pressure",
        "Freeable Local Storage Low on Instance",
    ],
    "aurora_replica_lag": ["Replica Lag / Replication Delay"],
    "aurora_latency": ["High Read or Write Latency"],
    "aurora_deadlocks": ["Deadlocks"],
    "aurora_local_storage": ["Freeable Local Storage Low on Instance"],
    "aurora_event": ["Failover, Restart, or Availability Degradation"],
}
INFRASTRUCTURE_CATEGORY_MAP = {
    "ec2_status_check": ["EC2 Status Check Failure"],
    "ec2_cpu_credit": ["EC2 CPU Credit Exhaustion"],
    "memory_pressure": ["Infrastructure Memory Pressure"],
    "disk_pressure": ["Disk or Filesystem Pressure"],
    "network_throughput": ["Network Saturation or Packet Loss"],
    "load_balancer_latency": ["Load Balancer High Latency"],
    "load_balancer_5xx": ["Load Balancer 5XX Errors"],
    "load_balancer_unhealthy_hosts": ["Load Balancer Unhealthy Targets"],
    "ecs_service_health": ["ECS Service Health"],
    "autoscaling_health": ["Auto Scaling Capacity or Health"],
    "lambda_errors": ["Lambda Errors or Throttles"],
    "throttling": ["AWS API or Service Throttling"],
    "generic_infrastructure": ["General Infrastructure Alarm"],
}
APPLICATION_CATEGORY_MAP = {
    "application_errors": ["Application Error Rate"],
    "application_exceptions": ["Application Exceptions"],
    "application_5xx": ["Application 5XX Errors"],
    "application_4xx": ["Application 4XX Errors"],
    "application_latency": ["Application Latency"],
    "application_timeouts": ["Application Timeouts"],
    "application_failed_requests": ["Failed Requests"],
    "application_log_errors": ["CloudWatch Log Error Pattern"],
    "synthetic_canary_failure": ["Synthetic Canary Failure"],
}


@dataclass
class RegisteredRunbook:
    domain: str
    loader: S3RunbookLoader
    service: RunbookService
    last_load: RunbookLoadResult


class RunbookRegistry:
    def __init__(self, runbooks: dict[str, RegisteredRunbook]):
        self.runbooks = runbooks

    @classmethod
    def from_ssm(
        cls,
        region_name: str,
        ssm_config: Any,
        refresh_interval_seconds: int = 300,
        max_chars: int = 18000,
    ) -> "RunbookRegistry":
        bucket = ssm_config.get_secure_string("runbooks/s3_bucket", required=True)
        refresh = int(
            ssm_config.get_secure_string(
                "runbooks/refresh_interval_seconds", required=False
            )
            or str(refresh_interval_seconds)
        )
        max_context = int(
            ssm_config.get_secure_string("runbooks/max_chars", required=False)
            or str(max_chars)
        )
        configs: dict[str, dict[str, Any]] = {
            "database": {
                "key_param": "runbooks/database/key",
                "cache_path": "/tmp/runbooks/database.md",
                "category_map": DATABASE_CATEGORY_MAP,
            },
            "infrastructure": {
                "key_param": "runbooks/infrastructure/key",
                "cache_path": "/tmp/runbooks/infrastructure.md",
                "category_map": INFRASTRUCTURE_CATEGORY_MAP,
            },
            "application": {
                "key_param": "runbooks/application/key",
                "cache_path": "/tmp/runbooks/application.md",
                "category_map": APPLICATION_CATEGORY_MAP,
            },
        }
        registered: dict[str, RegisteredRunbook] = {}
        for domain, config in configs.items():
            key = ssm_config.get_secure_string(config["key_param"], required=True)
            cache_path = (
                ssm_config.get_secure_string(
                    f"runbooks/{domain}/cache_path", required=False
                )
                or config["cache_path"]
            )
            loader = S3RunbookLoader(region_name, bucket, key, cache_path, refresh)
            load_result = loader.ensure_current()
            service = RunbookService(
                load_result.path, domain, max_context, config["category_map"]
            )
            registered[domain] = RegisteredRunbook(domain, loader, service, load_result)
        return cls(registered)

    def get_context(self, domain: str, category: str) -> dict[str, Any]:
        registered = self.runbooks.get(domain)
        if not registered:
            return {
                "domain": domain,
                "category": category,
                "context": "",
                "metadata": {"error": f"No runbook registered for {domain}"},
            }
        load_result = registered.loader.ensure_current()
        registered.last_load = load_result
        registered.service.reload()
        context = registered.service.get_context_for_category(
            category,
            f"No exact runbook section found for {category}; use general safety rules.",
        )
        return {
            "domain": domain,
            "category": category,
            "context": context,
            "metadata": {
                "source": "s3",
                "bucket": load_result.bucket,
                "key": load_result.key,
                "etag": load_result.etag,
                "version_id": load_result.version_id,
            },
        }

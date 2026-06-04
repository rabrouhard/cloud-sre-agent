from __future__ import annotations
import json
from functools import lru_cache
from typing import Any

# boto3 may not be available to static type checkers in some environments
try:
    import boto3  # type: ignore
except Exception:  # pragma: no cover - fallback for editors/static analysis
    boto3 = None  # type: ignore

class SsmConfigService:
    def __init__(self, region_name: str, parameter_prefix: str):
        self.region_name = region_name
        self.parameter_prefix = parameter_prefix.rstrip("/")
        if boto3 is None:
            raise ImportError("boto3 is required to use SsmConfigService")
        self.client = boto3.client("ssm", region_name=region_name)

    @lru_cache(maxsize=256)
    def get_secure_string(self, name: str, required: bool = True) -> str | None:
        parameter_name = self._full_name(name)
        try:
            response = self.client.get_parameter(Name=parameter_name, WithDecryption=True)
            value = response["Parameter"]["Value"]
            return value.strip() if value else None
        except self.client.exceptions.ParameterNotFound:
            if required:
                raise ValueError(f"Required SSM parameter not found: {parameter_name}")
            return None

    def get_json(self, name: str, required: bool = True) -> Any:
        value = self.get_secure_string(name=name, required=required)
        if value is None:
            return None
        return json.loads(value)

    def _full_name(self, name: str) -> str:
        if name.startswith("/"):
            return name
        return f"{self.parameter_prefix}/{name}"

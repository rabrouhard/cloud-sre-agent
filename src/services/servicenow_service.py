from __future__ import annotations
from typing import Any
import requests


class ServiceNowService:
    def __init__(
        self,
        instance_url: str,
        username: str | None = None,
        password: str | None = None,
        bearer_token: str | None = None,
        default_assignment_group: str | None = None,
        default_cmdb_ci: str | None = None,
        timeout_seconds: int = 20,
    ):
        self.instance_url = instance_url.rstrip("/")
        self.username, self.password, self.bearer_token = (
            username,
            password,
            bearer_token,
        )
        self.default_assignment_group, self.default_cmdb_ci = (
            default_assignment_group,
            default_cmdb_ci,
        )
        self.timeout_seconds = timeout_seconds

    def create_incident(
        self,
        short_description: str,
        description: str,
        urgency: str = "2",
        impact: str = "2",
        category: str = "inquiry",
        subcategory: str | None = None,
        assignment_group: str | None = None,
        cmdb_ci: str | None = None,
        caller_id: str | None = None,
        business_service: str | None = None,
    ) -> dict[str, Any]:
        """
        Creates a new incident in ServiceNow.

        Returns:
            dict[str, Any]: The JSON response from ServiceNow, typically containing
            the created incident record under the 'result' key, e.g.:
            {
                "result": {
                    "sys_id": "<incident_sys_id>",
                    "number": "<incident_number>",
                    ...
                }
            }

        Raises:
            ValueError: If neither bearer token nor username/password is provided for authentication.
            requests.HTTPError: If the HTTP request to ServiceNow fails.
            requests.JSONDecodeError: If the response body is not valid JSON.
        """
        payload: dict[str, Any] = {
            "short_description": short_description,
            "description": description,
            "urgency": urgency,
            "impact": impact,
            "category": category,
        }
        if subcategory:
            payload["subcategory"] = subcategory
        if assignment_group or self.default_assignment_group:
            payload["assignment_group"] = assignment_group or self.default_assignment_group
        if cmdb_ci or self.default_cmdb_ci:
            payload["cmdb_ci"] = cmdb_ci or self.default_cmdb_ci
        if caller_id:
            payload["caller_id"] = caller_id
        if business_service:
            payload["business_service"] = business_service

        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        auth: tuple[str, str] | None = None
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        elif self.username and self.password:
            auth = (self.username, self.password)
        else:
            raise ValueError(
                "Missing authentication: provide either 'bearer_token' or both 'username' and 'password' for ServiceNow authentication."
            )
        r = requests.post(
            f"{self.instance_url}/api/now/table/incident",
            json=payload,
            headers=headers,
            auth=auth,
            timeout=self.timeout_seconds,
        )
        r.raise_for_status()
        return r.json()

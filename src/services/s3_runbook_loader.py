from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
import boto3


@dataclass(frozen=True)
class RunbookLoadResult:
    path: str
    bucket: str
    key: str
    etag: str | None
    version_id: str | None


class S3RunbookLoader:
    def __init__(
        self,
        region_name: str,
        bucket_name: str,
        object_key: str,
        cache_path: str,
        refresh_interval_seconds: int = 300,
    ):
        self.bucket_name = bucket_name
        self.object_key = object_key.lstrip("/")
        self.cache_path = Path(cache_path)
        self.refresh_interval_seconds = refresh_interval_seconds
        self.s3_client = boto3.client("s3", region_name=region_name)
        self._last_checked_at = 0.0
        self._etag = None
        self._version_id = None

    def ensure_current(self) -> RunbookLoadResult:
        """
        Ensures the local cache of the runbook is up-to-date with the S3 object.
        If the cache is fresh (within the refresh interval) and matches the S3 object's ETag and VersionId,
        returns the cached result. Otherwise, fetches the latest object from S3, updates the cache,
        and returns the new result.
        """
        now = monotonic()
        if (
            self.cache_path.exists()
            and now - self._last_checked_at < self.refresh_interval_seconds
        ):
            return RunbookLoadResult(
                str(self.cache_path),
                self.bucket_name,
                self.object_key,
                self._etag,
                self._version_id,
            )
        self._last_checked_at = now
        head = self.s3_client.head_object(Bucket=self.bucket_name, Key=self.object_key)
        current_etag = head.get("ETag")
        if current_etag is not None and current_etag.startswith('"') and current_etag.endswith('"'):
            current_etag = current_etag[1:-1]
        current_version_id = head.get("VersionId")
        cached_etag = self._etag
        if cached_etag is not None and cached_etag.startswith('"') and cached_etag.endswith('"'):
            cached_etag = cached_etag[1:-1]
        if (
            self.cache_path.exists()
            and cached_etag == current_etag
            and self._version_id == current_version_id
        ):
            return RunbookLoadResult(
                str(self.cache_path),
                self.bucket_name,
                self.object_key,
                self._etag,
                self._version_id,
            )

        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=self.object_key)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        body = response["Body"].read().decode("utf-8")
        with self.cache_path.open("w", encoding="utf-8") as f:
            f.write(body)

        response_etag = response.get("ETag")
        if response_etag is not None and response_etag.startswith('"') and response_etag.endswith('"'):
            response_etag = response_etag[1:-1]
        # Fallback to head_object values if missing
        self._etag = response_etag if response_etag is not None else current_etag
        response_version_id = response.get("VersionId")
        self._version_id = response_version_id if response_version_id is not None else current_version_id
        return RunbookLoadResult(
            str(self.cache_path),
            self.bucket_name,
            self.object_key,
            self._etag,
            self._version_id,
        )

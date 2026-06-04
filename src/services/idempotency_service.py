from __future__ import annotations
from datetime import datetime, timedelta, timezone
import boto3
from botocore.exceptions import ClientError


class IdempotencyService:
    def __init__(
        self,
        region_name: str,
        table_name: str,
        ttl_days: int = 30,
        partition_key: str = "pk",
        sort_key: str = "sk"
    ):
        """
        Initialize the IdempotencyService.

        Args:
            region_name (str): AWS region name.
            table_name (str): Name of the DynamoDB table.
            ttl_days (int, optional): Number of days before the claim expires. Defaults to 30.
            partition_key (str, optional): Name of the partition key. Defaults to "pk".
            sort_key (str, optional): Name of the sort key. Defaults to "sk".
        """
        self.client = boto3.client("dynamodb", region_name=region_name)
        self.table_name = table_name
        self.ttl_days = ttl_days
        self.partition_key = partition_key
        self.sort_key = sort_key

    def claim(self, event_id: str, alarm_key: str) -> bool:
        """
        Attempts to claim an event by inserting a record into DynamoDB if it does not already exist.

        Args:
            event_id (str): The unique identifier for the event to claim.
            alarm_key (str): The alarm key associated with the event.

        Returns:
            bool: True if the claim was successful, False if the event was already claimed.
        """
        try:
            expires_at = int(
                (datetime.now(timezone.utc) + timedelta(days=self.ttl_days)).timestamp()
            )
            self.client.put_item(
                TableName=self.table_name,
                Item={
                    "pk": {"S": f"event#{event_id}"},
                    "sk": {"S": "claim"},
                    "alarm_key": {"S": alarm_key},
                    "expires_at": {"N": str(expires_at)},
                },
                ConditionExpression="attribute_not_exists(pk)",
            )
            return True
        except ClientError as error:
            if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise

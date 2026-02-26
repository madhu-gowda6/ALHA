"""DynamoDB helper utilities for ALHA agent."""
import os
from typing import Any, Optional

import boto3
import structlog

log = structlog.get_logger()


def get_table(table_name: str, region: Optional[str] = None):
    """Return a DynamoDB Table resource."""
    region = region or os.environ.get("AWS_REGION", "us-east-1")
    dynamodb = boto3.resource("dynamodb", region_name=region)
    return dynamodb.Table(table_name)


def put_item(table_name: str, item: dict[str, Any], session_id: str = "") -> bool:
    """Put an item into a DynamoDB table. Returns True on success."""
    table = get_table(table_name)
    table.put_item(Item=item)
    log.info("dynamo_put_item", session_id=session_id, table=table_name, pk=list(item.keys())[:1])
    return True


def get_item(table_name: str, key: dict[str, Any], session_id: str = "") -> Optional[dict]:
    """Get an item from a DynamoDB table. Returns None if not found."""
    table = get_table(table_name)
    response = table.get_item(Key=key)
    item = response.get("Item")
    log.info("dynamo_get_item", session_id=session_id, table=table_name, found=item is not None)
    return item


def scan_all(table_name: str, session_id: str = "") -> list[dict]:
    """Scan all items from a DynamoDB table (use sparingly — no pagination limit)."""
    table = get_table(table_name)
    response = table.scan()
    items = response.get("Items", [])
    log.info("dynamo_scan", session_id=session_id, table=table_name, count=len(items))
    return items

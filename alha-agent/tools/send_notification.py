"""Tool: send_notification — send SMS to vet via SNS."""
import os

import boto3
import structlog

log = structlog.get_logger()


async def send_notification(
    session_id: str, vet_phone: str, farmer_name: str, disease_name: str, severity: str
) -> dict:
    """
    Send SMS notification to assigned vet via AWS SNS.

    Returns:
        dict with message_id, success bool.
    """
    pass

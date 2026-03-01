"""Tool: send_notification — send dual SNS SMS to farmer and vet."""
import asyncio
import json
from datetime import datetime

import boto3
import structlog
from botocore.exceptions import ClientError
from claude_agent_sdk import tool

from config import config

log = structlog.get_logger()

# Module-level SNS client
_sns = boto3.client("sns", region_name=config.aws_region)

_SMS_ATTRS = {
    "AWS.SNS.SMS.SMSType": {
        "DataType": "String",
        "StringValue": "Transactional",
    }
}


@tool(
    "send_notification",
    "Send transactional SMS via AWS SNS to both the farmer and the assigned vet. "
    "Farmer receives a confirmation with vet name. Vet receives farmer GPS and case details. "
    "Soft-fails on SNS errors (sandbox restriction) — does not crash the session.",
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Active consultation session ID"},
            "farmer_phone": {"type": "string", "description": "Farmer E.164 phone number"},
            "vet_phone": {"type": "string", "description": "Vet E.164 phone number"},
            "vet_name": {"type": "string", "description": "Vet display name"},
            "disease_name": {"type": "string", "description": "Diagnosed disease name"},
            "severity": {"type": "string", "description": "Severity level: CRITICAL/HIGH/MEDIUM/LOW"},
            "lat": {"type": "number", "description": "Farmer latitude"},
            "lon": {"type": "number", "description": "Farmer longitude"},
            "confidence": {"type": "number", "description": "Disease confidence score (0-100)"},
            "animal_type": {
                "type": "string",
                "description": "Animal species for vet SMS context",
            },
        },
        "required": [
            "session_id",
            "farmer_phone",
            "vet_phone",
            "vet_name",
            "disease_name",
            "severity",
            "lat",
            "lon",
            "confidence",
        ],
    },
)
async def send_notification(args: dict) -> dict:
    """Publish dual SNS SMS — one to farmer, one to vet. Soft-fails on ClientError."""
    session_id = args.get("session_id", "")
    farmer_phone = args.get("farmer_phone", "")
    vet_phone = args.get("vet_phone", "")
    vet_name = args.get("vet_name", "")
    disease_name = args.get("disease_name", "")
    severity = args.get("severity", "")
    lat = float(args.get("lat", 0.0))
    lon = float(args.get("lon", 0.0))
    confidence = float(args.get("confidence", 0.0))
    animal_type = args.get("animal_type", "animal")

    farmer_msg = (
        f"ALHA Alert: {disease_name} detected ({confidence:.0f}% confidence, {severity}). "
        f"Nearest vet: {vet_name} is on their way. / "
        f"ALHA सूचना: {disease_name} ({confidence:.0f}% निश्चितता, {severity}). "
        f"सबसे नजदीकी पशु चिकित्सक: {vet_name}."
    )

    maps_link = f"https://maps.google.com/?q={lat:.6f},{lon:.6f}"

    vet_msg = (
        f"ALHA Emergency: Farmer has reported {disease_name} ({severity}) "
        f"in their {animal_type}. Confidence: {confidence:.0f}%. "
        f"Location: {maps_link}. Please respond immediately."
    )

    try:
        _sns.publish(
            PhoneNumber=farmer_phone,
            Message=farmer_msg,
            MessageAttributes=_SMS_ATTRS,
        )
        _sns.publish(
            PhoneNumber=vet_phone,
            Message=vet_msg,
            MessageAttributes=_SMS_ATTRS,
        )

        log.info(
            "tool_executed",
            tool_name="send_notification",
            session_id=session_id,
            vet_name=vet_name,
            sms_type="Transactional",
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

        # Send notification_sent WS to Flutter
        from ws_map import _active_ws_map

        ws = _active_ws_map.get(session_id)
        if ws:
            asyncio.create_task(
                ws.send_json(
                    {
                        "type": "notification_sent",
                        "vet_name": vet_name,
                        "session_id": session_id,
                    }
                )
            )

        result = {
            "notification_sent": True,
            "vet_name": vet_name,
            "session_id": session_id,
        }
        return {"content": [{"type": "text", "text": json.dumps(result)}]}

    except ClientError as exc:
        log.error(
            "sns_publish_error",
            tool_name="send_notification",
            session_id=session_id,
            error=str(exc),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        result = {
            "notification_sent": False,
            "error": True,
            "code": "SNS_ERROR",
            "message": f"SMS could not be delivered. Please call {vet_name} directly.",
            "message_hi": f"SMS नहीं भेजा जा सका। कृपया {vet_name} को सीधे कॉल करें।",
            "session_id": session_id,
        }
        return {"content": [{"type": "text", "text": json.dumps(result)}]}

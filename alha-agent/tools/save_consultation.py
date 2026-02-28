"""Tool: save_consultation — persist completed consultation to DynamoDB."""
import asyncio
import json
from datetime import datetime

import boto3
import structlog
from botocore.exceptions import ClientError
from claude_agent_sdk import tool

from config import config
from hooks.pii_filter_hook import redact_phone

log = structlog.get_logger()

# Module-level DynamoDB client
_dynamodb = boto3.client("dynamodb", region_name=config.aws_region)


@tool(
    "save_consultation",
    "Persist the completed consultation record to the alha-consultations DynamoDB table. "
    "Stores a flat JSON item (no nested DynamoDB types) for console readability. "
    "kb_citations are serialised as a JSON string. ALWAYS call at the end of every consultation.",
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Active consultation session ID"},
            "farmer_phone": {"type": "string", "description": "Farmer E.164 phone (pii_filter_hook redacts)"},
            "animal_type": {"type": "string", "description": "Animal species"},
            "disease_name": {"type": "string", "description": "Diagnosed disease name"},
            "confidence_score": {"type": "number", "description": "Confidence score (0-100)"},
            "severity": {"type": "string", "description": "Severity level: CRITICAL/HIGH/MEDIUM/LOW/NONE"},
            "vet_assigned": {"type": "string", "description": "Name of vet assigned, or 'none'"},
            "vet_phone": {"type": "string", "description": "Vet phone number, or 'none' (pii_filter_hook redacts)"},
            "treatment_summary": {"type": "string", "description": "KB treatment guidance summary"},
            "kb_citations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of KB source citations",
            },
        },
        "required": [
            "session_id",
            "farmer_phone",
            "animal_type",
            "disease_name",
            "confidence_score",
            "severity",
            "vet_assigned",
            "vet_phone",
            "treatment_summary",
            "kb_citations",
        ],
    },
)
async def save_consultation(args: dict) -> dict:
    """Write flat consultation record to DynamoDB. Soft-fails on ClientError."""
    session_id = args.get("session_id", "")
    farmer_phone = args.get("farmer_phone", "")
    animal_type = args.get("animal_type", "")
    disease_name = args.get("disease_name", "")
    confidence_score = float(args.get("confidence_score", 0.0))
    severity = args.get("severity", "")
    vet_assigned = args.get("vet_assigned", "none") or "none"
    vet_phone = args.get("vet_phone", "none") or "none"
    treatment_summary = str(args.get("treatment_summary", ""))
    kb_citations = args.get("kb_citations", [])
    if not isinstance(kb_citations, list):
        kb_citations = []

    # Flat DynamoDB item — no List or Map types, all string/number primitives
    # AC #10: PII-redact phone numbers before writing to DynamoDB
    item = {
        "session_id": {"S": session_id},
        "farmer_phone": {"S": redact_phone(farmer_phone)},
        "animal_type": {"S": animal_type},
        "disease_name": {"S": disease_name},
        "confidence_score": {"N": str(round(confidence_score, 2))},
        "severity": {"S": severity},
        "vet_assigned": {"S": vet_assigned},
        "vet_phone": {"S": redact_phone(vet_phone)},
        "treatment_summary": {"S": treatment_summary[:2000]},
        "kb_citations": {"S": json.dumps(kb_citations)},  # list → flat JSON string
        "timestamp": {"S": datetime.utcnow().isoformat() + "Z"},
    }

    try:
        _dynamodb.put_item(TableName=config.consultations_table, Item=item)

        log.info(
            "tool_executed",
            tool_name="save_consultation",
            session_id=session_id,
            severity=severity,
            disease_name=disease_name,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

        # Send session_complete WS to Flutter
        from ws_map import _active_ws_map

        ws = _active_ws_map.get(session_id)
        if ws:
            asyncio.create_task(
                ws.send_json(
                    {
                        "type": "session_complete",
                        "consultation_id": session_id,
                        "session_id": session_id,
                    }
                )
            )

        result = {
            "saved": True,
            "consultation_id": session_id,
            "session_id": session_id,
        }
        return {"content": [{"type": "text", "text": json.dumps(result)}]}

    except ClientError as exc:
        log.error(
            "dynamo_put_error",
            tool_name="save_consultation",
            session_id=session_id,
            error=str(exc),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        result = {
            "saved": False,
            "error": True,
            "code": "DYNAMO_ERROR",
            "message": "Consultation could not be saved. Please try again.",
            "message_hi": "परामर्श सहेजा नहीं जा सका। कृपया पुनः प्रयास करें।",
            "session_id": session_id,
        }
        return {"content": [{"type": "text", "text": json.dumps(result)}]}

"""Tool: assess_severity — determine case severity from disease and symptom context."""
import asyncio
import json
from datetime import datetime

import structlog
from claude_agent_sdk import tool

log = structlog.get_logger()

# Severity heuristic table — disease_name → base severity
_CRITICAL_DISEASES = frozenset(
    {"lumpy_skin_disease", "newcastle_disease", "anthrax"}
)
_HIGH_DISEASES = frozenset(
    {"foot_and_mouth_disease", "brucellosis", "blackleg", "foot_and_mouth"}
)
_ROUTINE_KEYWORDS = frozenset(
    {"preventive", "routine", "vaccine", "vaccination", "deworming", "general"}
)


def _compute_severity(disease_name: str, symptom_context: str) -> str:
    """Heuristic severity classification — Claude drives the call, tool validates."""
    name = disease_name.lower().strip()
    context = symptom_context.lower()

    if not name:
        return "NONE"

    if name in _CRITICAL_DISEASES:
        return "CRITICAL"

    if name in _HIGH_DISEASES:
        return "HIGH"

    # Routine / preventive query → LOW
    if any(kw in context for kw in _ROUTINE_KEYWORDS):
        return "LOW"

    # Known disease but not in the explicit tables → MEDIUM
    if name:
        return "MEDIUM"

    return "NONE"


@tool(
    "assess_severity",
    "Assess the severity of a diagnosed livestock disease and emit a severity badge to the farmer's UI. "
    "Returns one of: CRITICAL, HIGH, MEDIUM, LOW, NONE. "
    "CRITICAL diseases trigger immediate GPS-based vet dispatch. "
    "HIGH/MEDIUM show a vet-preference card. LOW/NONE provide KB guidance only.",
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Active consultation session ID"},
            "disease_name": {
                "type": "string",
                "description": "Disease name as returned by classify_disease (e.g. lumpy_skin_disease)",
            },
            "animal_type": {
                "type": "string",
                "description": "Animal species: cattle, poultry, buffalo, goat, sheep",
            },
            "symptom_context": {
                "type": "string",
                "description": "Brief summary of observed symptoms used for severity calibration",
            },
        },
        "required": ["session_id", "disease_name", "animal_type", "symptom_context"],
    },
)
async def assess_severity(args: dict) -> dict:
    """Compute severity level and broadcast it to the Flutter client via WebSocket."""
    session_id = args.get("session_id", "")
    disease_name = args.get("disease_name", "")
    animal_type = args.get("animal_type", "")
    symptom_context = args.get("symptom_context", "")

    severity = _compute_severity(disease_name, symptom_context)

    log.info(
        "tool_executed",
        tool_name="assess_severity",
        session_id=session_id,
        severity=severity,
        animal_type=animal_type,
        disease_name=disease_name,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )

    # Dispatch severity badge to Flutter via WebSocket
    from ws_map import _active_ws_map

    ws = _active_ws_map.get(session_id)
    if ws:
        asyncio.create_task(
            ws.send_json(
                {
                    "type": "severity",
                    "level": severity,
                    "session_id": session_id,
                }
            )
        )

    result = {
        "severity": severity,
        "session_id": session_id,
        "disease_name": disease_name,
    }
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

"""Tool: symptom_interview — structured symptom collection from farmer via overlay."""
import asyncio
import json
from datetime import datetime

import structlog
from claude_agent_sdk import tool

log = structlog.get_logger()


@tool(
    "symptom_interview",
    "Display a structured symptom interview overlay to the farmer. "
    "Call after generating targeted follow-up questions. "
    "Waits for farmer answers before proceeding.",
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Active session ID"},
            "questions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Up to 3 targeted questions in English",
            },
            "questions_hi": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Same questions translated to Hindi",
            },
        },
        "required": ["session_id", "questions", "questions_hi"],
    },
)
async def symptom_interview(args: dict) -> dict:
    """Signal the frontend to show the symptom interview overlay."""
    session_id = args.get("session_id", "")
    questions = args.get("questions", [])
    questions_hi = args.get("questions_hi", [])

    if not questions:
        result = {
            "error": True,
            "code": "NO_QUESTIONS",
            "message": "At least one question is required",
        }
        return {"content": [{"type": "text", "text": json.dumps(result)}]}

    # Truncate to max 3 questions
    questions = questions[:3]
    questions_hi = questions_hi[: len(questions)]

    log.info(
        "tool_executed",
        tool_name="symptom_interview",
        session_id=session_id,
        question_count=len(questions),
        timestamp=datetime.utcnow().isoformat() + "Z",
    )

    # Dispatch frontend_action to Flutter via active WebSocket
    from ws_map import _active_ws_map

    async def _send(ws_ref, payload: dict) -> None:
        try:
            await ws_ref.send_json(payload)
        except Exception as exc:
            log.warning(
                "ws_send_failed",
                tool_name="symptom_interview",
                session_id=session_id,
                error=str(exc),
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

    ws = _active_ws_map.get(session_id)
    if ws:
        asyncio.create_task(
            _send(
                ws,
                {
                    "type": "frontend_action",
                    "action": "symptom_interview",
                    "questions": questions,
                    "questions_hi": questions_hi,
                    "session_id": session_id,
                },
            )
        )

    result = {
        "frontend_action": "symptom_interview",
        "questions": questions,
        "questions_hi": questions_hi,
        "question_count": len(questions),
        "status": "overlay_shown",
        "next": "Wait for symptom_answers WebSocket message before proceeding.",
    }
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

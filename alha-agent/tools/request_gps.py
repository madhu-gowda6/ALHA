"""Tool: request_gps — ask farmer to share GPS coordinates via Flutter Geolocation API."""
import asyncio
import json
from datetime import datetime

import structlog
from claude_agent_sdk import tool

log = structlog.get_logger()


@tool(
    "request_gps",
    "Send a GPS coordinate request to the farmer's Flutter client. "
    "The client will prompt the farmer for browser geolocation permission. "
    "After the farmer grants access, Flutter sends back a gps_data WebSocket message.",
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Active consultation session ID"},
            "prompt_text": {
                "type": "string",
                "description": "English prompt shown to farmer before GPS request",
            },
            "prompt_text_hi": {
                "type": "string",
                "description": "Hindi prompt shown to farmer before GPS request",
            },
        },
        "required": ["session_id", "prompt_text", "prompt_text_hi"],
    },
)
async def request_gps(args: dict) -> dict:
    """Dispatch a frontend_action request_gps to Flutter via WebSocket."""
    session_id = args.get("session_id", "")
    prompt_text = args.get("prompt_text", "Please share your location to find the nearest vet.")
    prompt_text_hi = args.get(
        "prompt_text_hi", "निकटतम पशु चिकित्सक खोजने के लिए कृपया अपना स्थान साझा करें।"
    )

    log.info(
        "tool_executed",
        tool_name="request_gps",
        session_id=session_id,
        timestamp=datetime.utcnow().isoformat() + "Z",
    )

    # Dispatch GPS request action to Flutter via WebSocket
    from ws_map import _active_ws_map

    ws = _active_ws_map.get(session_id)
    if ws:
        asyncio.create_task(
            ws.send_json(
                {
                    "type": "frontend_action",
                    "action": "request_gps",
                    "session_id": session_id,
                    "prompt_text": prompt_text,
                    "prompt_text_hi": prompt_text_hi,
                }
            )
        )

    result = {
        "frontend_action": "request_gps",
        "session_id": session_id,
    }
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

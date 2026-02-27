"""Tool: request_image — prompt farmer to upload an image via camera overlay."""
import asyncio
import json
from datetime import datetime

import structlog
from claude_agent_sdk import tool

log = structlog.get_logger()


@tool(
    "request_image",
    "Request the farmer to take or upload a photo of the affected animal. "
    "Triggers the camera overlay in the Flutter app. "
    "Call when visual diagnosis is required.",
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Active session ID"},
            "prompt_text": {
                "type": "string",
                "description": "English prompt shown to farmer",
            },
            "prompt_text_hi": {
                "type": "string",
                "description": "Hindi prompt shown to farmer",
            },
        },
        "required": ["session_id", "prompt_text", "prompt_text_hi"],
    },
)
async def request_image(args: dict) -> dict:
    """Signal the frontend to open the camera/gallery overlay."""
    session_id = args.get("session_id", "")
    prompt_text = args.get("prompt_text", "Please take a photo of the animal")
    prompt_text_hi = args.get("prompt_text_hi", "कृपया जानवर की फोटो लें")

    log.info(
        "tool_executed",
        tool_name="request_image",
        session_id=session_id,
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
                tool_name="request_image",
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
                    "action": "request_image",
                    "session_id": session_id,
                    "prompt": prompt_text,
                    "prompt_hi": prompt_text_hi,
                },
            )
        )

    result = {
        "frontend_action": "request_image",
        "prompt": prompt_text,
        "prompt_hi": prompt_text_hi,
        "status": "camera_overlay_shown",
        "next": "Wait for image_data WebSocket message before proceeding.",
    }
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

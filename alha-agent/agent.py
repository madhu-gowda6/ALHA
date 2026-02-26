"""ALHA Agent — Claude Agent SDK configuration for veterinary AI assistant."""
import os
from datetime import datetime

import structlog
from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import StreamEvent

from hooks.logging_hook import LoggingHook

log = structlog.get_logger()
_hook = LoggingHook()

SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.txt")

_system_prompt: str | None = None


def load_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        with open(SYSTEM_PROMPT_PATH, encoding="utf-8") as f:
            _system_prompt = f.read()
    return _system_prompt


async def process_message(session_id: str, message: str, language: str, ws) -> None:
    """Stream agent response tokens back to the WebSocket client."""
    system_prompt = load_system_prompt()
    user_prompt = f"[language: {language}]\n{message}"

    log.info(
        "agent_query_started",
        session_id=session_id,
        language=language,
        message_length=len(message),
        timestamp=datetime.utcnow().isoformat() + "Z",
    )

    try:
        async for event in query(
            prompt=user_prompt,
            options=ClaudeAgentOptions(
                system_prompt=system_prompt,
                allowed_tools=[],
                max_turns=1,
                include_partial_messages=True,
            ),
        ):
            if isinstance(event, StreamEvent):
                raw = event.event
                if raw.get("type") == "content_block_delta":
                    delta = raw.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text_chunk = delta.get("text", "")
                        if text_chunk:
                            _hook.log_token_streamed(session_id, len(text_chunk))
                            try:
                                await ws.send_json(
                                    {
                                        "type": "token",
                                        "session_id": session_id,
                                        "text": text_chunk,
                                    }
                                )
                            except Exception:
                                log.warning(
                                    "ws_client_disconnected_during_stream",
                                    session_id=session_id,
                                    timestamp=datetime.utcnow().isoformat() + "Z",
                                )
                                return

        _hook.log_response_complete(session_id)
        try:
            await ws.send_json({"type": "response_complete", "session_id": session_id})
        except Exception:
            log.warning(
                "ws_client_disconnected_at_complete",
                session_id=session_id,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

    except Exception as exc:
        exc_str = str(exc).lower()
        is_blocked = any(kw in exc_str for kw in ("guardrail", "blocked", "content policy"))

        log.warning(
            "agent_error",
            session_id=session_id,
            error=str(exc),
            is_guardrail_block=is_blocked,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

        try:
            await ws.send_json(
                {
                    "type": "error",
                    "session_id": session_id,
                    "message": (
                        "I can't help with that."
                        if is_blocked
                        else "An error occurred processing your request."
                    ),
                    "message_hi": (
                        "मैं इसमें मदद नहीं कर सकता।"
                        if is_blocked
                        else "आपका अनुरोध प्रसंस्करण करते समय एक त्रुटि हुई।"
                    ),
                }
            )
        except Exception:
            log.warning(
                "ws_client_disconnected_during_error",
                session_id=session_id,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

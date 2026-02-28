"""ALHA Agent — Claude Agent SDK configuration for veterinary AI assistant."""
import os
from datetime import datetime

# The SDK always merges {**os.environ, **user_env} so CLAUDECODE must be removed
# from os.environ itself — not just from the user_env dict passed to the SDK.
os.environ.pop("CLAUDECODE", None)

import structlog
from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, query
from claude_agent_sdk.types import StreamEvent

from config import config
from hooks.logging_hook import LoggingHook
from hooks.pii_filter_hook import PIIFilterHook
from tools.assess_severity import assess_severity
from tools.classify_disease import classify_disease
from tools.find_nearest_vet import find_nearest_vet
from tools.query_knowledge_base import query_knowledge_base
from tools.request_gps import request_gps
from tools.request_image import request_image
from tools.save_consultation import save_consultation
from tools.send_notification import send_notification
from tools.symptom_interview import symptom_interview
from ws_map import _active_ws_map

log = structlog.get_logger()
_hook = LoggingHook()
_pii_hook = PIIFilterHook()

# In-process MCP server exposing all 9 tools (Epic 3 + Epic 4) to Claude
_alha_mcp_server = create_sdk_mcp_server(
    name="alha",
    version="1.0.0",
    tools=[
        symptom_interview,
        request_image,
        classify_disease,
        query_knowledge_base,
        assess_severity,
        request_gps,
        find_nearest_vet,
        send_notification,
        save_consultation,
    ],
)

_ALLOWED_TOOLS = [
    "mcp__alha__symptom_interview",
    "mcp__alha__request_image",
    "mcp__alha__classify_disease",
    "mcp__alha__query_knowledge_base",
    "mcp__alha__assess_severity",
    "mcp__alha__request_gps",
    "mcp__alha__find_nearest_vet",
    "mcp__alha__send_notification",
    "mcp__alha__save_consultation",
]


def _log_claude_stderr(line: str) -> None:
    """Forward claude subprocess stderr to structured logs for debugging."""
    log.warning("claude_subprocess_stderr", line=line.rstrip())


SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.txt")

_system_prompt: str | None = None


def load_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        with open(SYSTEM_PROMPT_PATH, encoding="utf-8") as f:
            _system_prompt = f.read()
    return _system_prompt


def _build_prompt(
    history: list[dict], message: str, language: str, session_id: str, farmer_phone: str = ""
) -> str:
    """Build a conversation-aware prompt by prepending prior exchanges."""
    parts = []
    for entry in history:
        role = "Farmer" if entry["role"] == "user" else "Assistant"
        parts.append(f"{role}: {entry['content']}")
    parts.append(
        f"[session_id: {session_id}]\n[language: {language}]\n[farmer_phone: {farmer_phone}]\nFarmer: {message}"
    )
    return "\n\n".join(parts)


async def process_message(
    session_id: str,
    message: str,
    language: str,
    ws,
    history: list[dict] | None = None,
    farmer_phone: str = "",
) -> str:
    """Stream agent response tokens back to the WebSocket client.

    Returns the full assistant response text so the caller can store it in
    conversation history.
    """
    system_prompt = load_system_prompt()
    user_prompt = _build_prompt(history or [], message, language, session_id, farmer_phone)

    # Register this WebSocket so tool handlers can dispatch frontend_actions
    _active_ws_map[session_id] = ws

    log.info(
        "agent_query_started",
        session_id=session_id,
        language=language,
        message_length=len(message),
        timestamp=datetime.utcnow().isoformat() + "Z",
    )

    full_response = ""

    try:
        # Merge current process env so the claude subprocess inherits AWS
        # credential env vars (AWS_CONTAINER_CREDENTIALS_RELATIVE_URI, AWS_REGION,
        # etc.) that ECS injects, then layer any overrides on top.
        subprocess_env = {
            **os.environ,
            "CLAUDE_CODE_ACCEPT_TOS": "1",
            # Clear placeholder guardrail headers — an invalid guardrail ID causes
            # Bedrock to reject every request with a 400 error.
            "ANTHROPIC_CUSTOM_HEADERS": "",
        }

        # Build an async-iterable prompt instead of a plain string.
        # The SDK's string-prompt path calls end_input() immediately after
        # writing the user message, which closes the subprocess stdin.
        # With MCP servers, the subprocess sends control requests (tools/list,
        # tools/call) back to the SDK that require writing responses to stdin.
        # The async-iterable path uses stream_input() which keeps stdin open
        # until the first result arrives, allowing MCP bidirectional I/O.
        async def _prompt_iter():
            yield {
                "type": "user",
                "session_id": "",
                "message": {"role": "user", "content": user_prompt},
                "parent_tool_use_id": None,
            }

        async for event in query(
            prompt=_prompt_iter(),
            options=ClaudeAgentOptions(
                system_prompt=system_prompt,
                allowed_tools=_ALLOWED_TOOLS,
                mcp_servers={"alha": _alha_mcp_server},
                max_turns=10,
                include_partial_messages=True,
                model=config.bedrock_model_id if config.claude_use_bedrock else None,
                env=subprocess_env,
                stderr=_log_claude_stderr,
            ),
        ):
            if isinstance(event, StreamEvent):
                raw = event.event
                if raw.get("type") == "content_block_delta":
                    delta = raw.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text_chunk = delta.get("text", "")
                        if text_chunk:
                            full_response += text_chunk
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
                                return full_response

        _hook.log_response_complete(session_id)
        try:
            await ws.send_json({"type": "response_complete", "session_id": session_id})
        except Exception:
            log.warning(
                "ws_client_disconnected_at_complete",
                session_id=session_id,
                timestamp=datetime.utcnow().isoformat() + "Z",
            )

        return full_response

    except Exception as exc:
        # Unwrap ExceptionGroup (raised by asyncio TaskGroup / anyio) to surface
        # the actual root cause sub-exception in logs.
        root_exc = exc
        root_cause = str(exc)
        if hasattr(exc, "exceptions") and exc.exceptions:
            root_exc = exc.exceptions[0]
            root_cause = f"sub[0]: {type(root_exc).__name__}: {root_exc}"

        exc_str = (str(exc) + root_cause).lower()
        is_blocked = any(kw in exc_str for kw in ("guardrail", "blocked", "content policy"))

        log.warning(
            "agent_error",
            session_id=session_id,
            error=str(exc),
            root_cause=root_cause,
            exc_type=type(root_exc).__name__,
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
        return ""

    finally:
        # Deregister WebSocket — session may re-register on next call
        _active_ws_map.pop(session_id, None)

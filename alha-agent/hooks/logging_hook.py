"""PreToolUse / PostToolUse hook: structured logging for all tool calls and WS events."""
from datetime import datetime

import structlog

log = structlog.get_logger()


class LoggingHook:
    """Logs every tool invocation, WS message, and agent interaction with session_id."""

    async def pre_tool_use(self, session_id: str, tool_name: str, tool_input: dict) -> None:
        log.info(
            "tool_invoked",
            session_id=session_id,
            tool=tool_name,
            input_keys=list(tool_input.keys()),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    async def post_tool_use(
        self, session_id: str, tool_name: str, tool_output: dict, duration_ms: float
    ) -> None:
        log.info(
            "tool_completed",
            session_id=session_id,
            tool=tool_name,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    def log_ws_message(self, session_id: str, msg_type: str, extra: dict | None = None) -> None:
        log.info(
            "ws_message",
            session_id=session_id,
            msg_type=msg_type,
            timestamp=datetime.utcnow().isoformat() + "Z",
            **(extra or {}),
        )

    def log_token_streamed(self, session_id: str, chunk_length: int) -> None:
        log.debug(
            "token_streamed",
            session_id=session_id,
            chunk_length=chunk_length,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    def log_response_complete(self, session_id: str) -> None:
        log.info(
            "response_complete",
            session_id=session_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

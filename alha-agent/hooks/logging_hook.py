"""PreToolUse / PostToolUse hook: structured logging for all tool calls."""
import structlog

log = structlog.get_logger()


class LoggingHook:
    """Logs every tool invocation with session_id and timing."""

    async def pre_tool_use(self, session_id: str, tool_name: str, tool_input: dict) -> None:
        log.info(
            "tool_invoked",
            session_id=session_id,
            tool=tool_name,
            input_keys=list(tool_input.keys()),
        )

    async def post_tool_use(
        self, session_id: str, tool_name: str, tool_output: dict, duration_ms: float
    ) -> None:
        log.info(
            "tool_completed",
            session_id=session_id,
            tool=tool_name,
            duration_ms=duration_ms,
        )

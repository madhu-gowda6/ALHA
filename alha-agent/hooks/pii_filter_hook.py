"""PreToolUse hook: redact PII (phone numbers) before logging."""
import re

import structlog

log = structlog.get_logger()

# Matches: +919XXXXXXXXX, 919XXXXXXXXX, or local 10-digit 9XXXXXXXXX
PHONE_PATTERN = re.compile(r"(?:\+?91)?[6-9]\d{9}")


def redact_phone(value: str) -> str:
    """Replace phone numbers with [REDACTED]."""
    return PHONE_PATTERN.sub("[REDACTED]", value)


class PIIFilterHook:
    """Redacts Indian phone numbers from tool inputs before logging."""

    async def pre_tool_use(self, session_id: str, tool_name: str, tool_input: dict) -> dict:
        sanitised = {
            k: redact_phone(str(v)) if "phone" in k else v
            for k, v in tool_input.items()
        }
        log.debug("pii_filter_applied", session_id=session_id, tool=tool_name)
        return sanitised

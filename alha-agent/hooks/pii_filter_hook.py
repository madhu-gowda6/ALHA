"""PreToolUse / PostToolUse hook: redact PII (phone numbers) from tool I/O."""
import re

import structlog

log = structlog.get_logger()

# Matches: +919XXXXXXXXX, 919XXXXXXXXX, or local 10-digit 9XXXXXXXXX
PHONE_PATTERN = re.compile(r"(\+?91)?([6-9]\d{5})(\d{4})")


def redact_phone(value: str) -> str:
    """Mask phone numbers as +91XXXXX1234 (last 4 digits visible for vet callback).

    AC #10: farmer_phone and vet_phone are PII-redacted in the DynamoDB record
    with format +91XXXXX1234.
    """
    def _mask(m: re.Match) -> str:
        last4 = m.group(3)
        return f"+91XXXXX{last4}"

    return PHONE_PATTERN.sub(_mask, value)


class PIIFilterHook:
    """Redacts Indian phone numbers from tool inputs and outputs."""

    async def pre_tool_use(self, session_id: str, tool_name: str, tool_input: dict) -> dict:
        sanitised = {
            k: redact_phone(str(v)) if "phone" in k else v
            for k, v in tool_input.items()
        }
        log.debug("pii_filter_applied", session_id=session_id, tool=tool_name)
        return sanitised

    async def post_tool_use(
        self, session_id: str, tool_name: str, tool_output: dict, duration_ms: float
    ) -> dict:
        """Redact phone numbers from tool output before it reaches CloudWatch logs."""
        if tool_name == "save_consultation":
            redacted = {}
            for k, v in tool_output.items():
                if "phone" in k and isinstance(v, str):
                    redacted[k] = redact_phone(v)
                else:
                    redacted[k] = v
            log.debug("pii_filter_output_applied", session_id=session_id, tool=tool_name)
            return redacted
        return tool_output

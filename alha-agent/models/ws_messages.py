from typing import Any, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Client → Agent (inbound)
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """Farmer sends a chat message. type="chat"."""

    type: str = "chat"
    session_id: str
    message: str
    language: str = "en"  # "hi" or "en"


# ---------------------------------------------------------------------------
# Agent → Client (outbound)
# ---------------------------------------------------------------------------


class WSMessage(BaseModel):
    type: str
    session_id: str


class TokenMessage(WSMessage):
    """Streaming token chunk. type="token"."""

    type: str = "token"
    text: str


class ResponseCompleteMessage(WSMessage):
    """Signals end of streaming response. type="response_complete"."""

    type: str = "response_complete"


class ErrorMessage(WSMessage):
    """Bilingual error message. type="error"."""

    type: str = "error"
    message: str
    message_hi: str


# ---------------------------------------------------------------------------
# Future epic message types (stubs — do not invoke yet)
# ---------------------------------------------------------------------------


class ImageRequestMessage(WSMessage):
    """Request farmer to upload an image. type="image_request". Epic 3."""

    type: str = "image_request"
    upload_url: str
    prompt: str
    prompt_hi: str


class GPSRequestMessage(WSMessage):
    """Request farmer's GPS location. type="gps_request". Epic 4."""

    type: str = "gps_request"
    prompt: str
    prompt_hi: str


class ToolCallMessage(WSMessage):
    """Notify client of a tool invocation. type="tool_call". Epic 3-4."""

    type: str = "tool_call"
    tool_name: str
    tool_input: dict[str, Any]

from typing import Any, Optional
from pydantic import BaseModel


class WSMessage(BaseModel):
    type: str
    session_id: str
    payload: Optional[dict[str, Any]] = None


class TokenMessage(WSMessage):
    type: str = "token"
    token: str


class ToolCallMessage(WSMessage):
    type: str = "tool_call"
    tool_name: str
    tool_input: dict[str, Any]


class ImageRequestMessage(WSMessage):
    type: str = "image_request"
    upload_url: str
    prompt: str
    prompt_hi: str


class GPSRequestMessage(WSMessage):
    type: str = "gps_request"
    prompt: str
    prompt_hi: str


class ErrorMessage(WSMessage):
    type: str = "error"
    message: str
    message_hi: str

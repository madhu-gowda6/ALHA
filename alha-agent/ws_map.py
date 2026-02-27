"""Shared WebSocket session map for tool handlers to dispatch frontend actions."""
from typing import Any

# Maps session_id → active WebSocket connection.
# Populated by app.py before calling process_message(); cleared on disconnect.
_active_ws_map: dict[str, Any] = {}

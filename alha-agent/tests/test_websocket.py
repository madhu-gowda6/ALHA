"""Tests for WebSocket endpoint message parsing and dispatch."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import app as app_module
from app import app

client = TestClient(app)


class TestWebSocketNoToken:
    def test_ws_rejects_connection_without_token(self):
        with client.websocket_connect("/ws") as ws:
            msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "message" in msg
        assert "message_hi" in msg

    def test_ws_sends_bilingual_error_without_token(self):
        with client.websocket_connect("/ws") as ws:
            msg = ws.receive_json()
        assert msg["message_hi"] is not None


class TestWebSocketInvalidToken:
    def test_ws_rejects_invalid_jwt(self):
        with patch.object(
            app_module,
            "_validate_jwt",
            new=AsyncMock(side_effect=__import__("jose").JWTError("bad token")),
        ):
            with client.websocket_connect("/ws?token=bad-token") as ws:
                msg = ws.receive_json()
        assert msg["type"] == "error"


class TestWebSocketMessageParsing:
    def _make_valid_session(self):
        return AsyncMock(return_value={"cognito:username": "raju", "sub": "user-123"})

    def test_ws_accepts_valid_token(self):
        with patch.object(
            app_module, "_validate_jwt", new=self._make_valid_session()
        ), patch.object(
            app_module, "process_message", new=AsyncMock()
        ):
            with client.websocket_connect("/ws?token=valid") as ws:
                # Send a chat message
                ws.send_json({
                    "type": "chat",
                    "session_id": "sess-1",
                    "message": "Hello",
                    "language": "en",
                })
                # process_message is mocked so WS stays open; close cleanly
            # No error raised = accepted

    def test_ws_dispatches_chat_type_to_process_message(self):
        mock_process = AsyncMock()
        with patch.object(
            app_module, "_validate_jwt", new=self._make_valid_session()
        ), patch.object(app_module, "process_message", new=mock_process):
            with client.websocket_connect("/ws?token=valid") as ws:
                ws.send_json({
                    "type": "chat",
                    "session_id": "sess-1",
                    "message": "Meri gaay beemar hai",
                    "language": "hi",
                })
        mock_process.assert_called_once()
        args = mock_process.call_args[0]
        assert args[0] == "sess-1"   # session_id
        assert args[1] == "Meri gaay beemar hai"  # message
        assert args[2] == "hi"       # language

    def test_ws_handles_invalid_json(self):
        with patch.object(
            app_module, "_validate_jwt", new=self._make_valid_session()
        ), patch.object(app_module, "process_message", new=AsyncMock()):
            with client.websocket_connect("/ws?token=valid") as ws:
                ws.send_text("not json at all")
                err = ws.receive_json()
            assert err["type"] == "error"
            assert "message_hi" in err

    def test_ws_message_envelope_always_has_session_id(self):
        mock_process = AsyncMock()
        with patch.object(
            app_module, "_validate_jwt", new=self._make_valid_session()
        ), patch.object(app_module, "process_message", new=mock_process):
            with client.websocket_connect("/ws?token=valid") as ws:
                ws.send_text("not json at all")
                err = ws.receive_json()
            assert "session_id" in err

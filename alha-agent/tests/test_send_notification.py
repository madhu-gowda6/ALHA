"""Tests for tools.send_notification — dual SNS SMS and soft failure handling."""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from botocore.exceptions import ClientError

from tools.send_notification import send_notification


def _make_client_error(code: str = "InvalidParameterException") -> ClientError:
    return ClientError(
        error_response={"Error": {"Code": code, "Message": "SNS sandbox restriction"}},
        operation_name="Publish",
    )


_VALID_ARGS = {
    "session_id": "s1",
    "farmer_phone": "+919000000001",
    "vet_phone": "+919876543210",
    "vet_name": "Dr. Ramesh Patel",
    "disease_name": "lumpy_skin_disease",
    "severity": "CRITICAL",
    "lat": 18.5204,
    "lon": 73.8567,
    "confidence": 87.5,
    "animal_type": "cattle",
}


class TestSendNotificationToolMeta:
    def test_tool_has_name(self):
        assert send_notification.name == "send_notification"

    def test_tool_has_description(self):
        assert len(send_notification.description) > 0

    def test_tool_schema_has_required_fields(self):
        schema = send_notification.input_schema
        required = schema.get("required", [])
        for field in ("session_id", "farmer_phone", "vet_phone", "vet_name", "disease_name",
                      "severity", "lat", "lon", "confidence"):
            assert field in required, f"Missing required field: {field}"


class TestSendNotificationHappyPath:
    @pytest.mark.asyncio
    async def test_both_farmer_and_vet_sms_called(self):
        with (
            patch("tools.send_notification._sns") as mock_sns,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_sns.publish.return_value = {"MessageId": "msg-001"}
            result = await send_notification.handler(_VALID_ARGS)

        assert mock_sns.publish.call_count == 2
        content = json.loads(result["content"][0]["text"])
        assert content["notification_sent"] is True
        assert content["vet_name"] == "Dr. Ramesh Patel"

    @pytest.mark.asyncio
    async def test_transactional_sms_type_used_for_both_calls(self):
        with (
            patch("tools.send_notification._sns") as mock_sns,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_sns.publish.return_value = {"MessageId": "msg-001"}
            await send_notification.handler(_VALID_ARGS)

        for call_kwargs in mock_sns.publish.call_args_list:
            attrs = call_kwargs[1].get("MessageAttributes", call_kwargs.kwargs.get("MessageAttributes", {}))
            if not attrs:
                # positional call
                attrs = call_kwargs[0][2] if len(call_kwargs[0]) > 2 else {}
            # MessageAttributes is passed as keyword arg
            kwargs = call_kwargs.kwargs
            msg_attrs = kwargs.get("MessageAttributes", {})
            sms_type = msg_attrs.get("AWS.SNS.SMS.SMSType", {}).get("StringValue", "")
            assert sms_type == "Transactional"

    @pytest.mark.asyncio
    async def test_farmer_phone_used_for_first_publish(self):
        captured_calls = []
        with (
            patch("tools.send_notification._sns") as mock_sns,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_sns.publish.side_effect = lambda **kw: captured_calls.append(kw) or {"MessageId": "m"}
            await send_notification.handler(_VALID_ARGS)

        phones = [c.get("PhoneNumber") for c in captured_calls]
        assert "+919000000001" in phones  # farmer
        assert "+919876543210" in phones  # vet

    @pytest.mark.asyncio
    async def test_notification_sent_ws_dispatched(self):
        mock_ws = AsyncMock()
        with (
            patch("tools.send_notification._sns") as mock_sns,
            patch.dict("ws_map._active_ws_map", {"s1": mock_ws}, clear=True),
            patch("asyncio.create_task", side_effect=lambda coro: asyncio.ensure_future(coro)),
        ):
            mock_sns.publish.return_value = {"MessageId": "m"}
            await send_notification.handler(_VALID_ARGS)
            await asyncio.sleep(0)

        mock_ws.send_json.assert_called_once()
        payload = mock_ws.send_json.call_args[0][0]
        assert payload["type"] == "notification_sent"
        assert payload["vet_name"] == "Dr. Ramesh Patel"

    @pytest.mark.asyncio
    async def test_result_has_content_wrapper(self):
        with (
            patch("tools.send_notification._sns") as mock_sns,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_sns.publish.return_value = {"MessageId": "m"}
            result = await send_notification.handler(_VALID_ARGS)

        assert "content" in result
        assert result["content"][0]["type"] == "text"


class TestSendNotificationSoftFailure:
    @pytest.mark.asyncio
    async def test_client_error_returns_soft_failure_not_exception(self):
        with (
            patch("tools.send_notification._sns") as mock_sns,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_sns.publish.side_effect = _make_client_error()
            result = await send_notification.handler(_VALID_ARGS)

        content = json.loads(result["content"][0]["text"])
        assert content["notification_sent"] is False
        assert content["error"] is True
        assert content["code"] == "SNS_ERROR"
        assert "message" in content
        assert "message_hi" in content

    @pytest.mark.asyncio
    async def test_soft_failure_includes_vet_name_in_message(self):
        with (
            patch("tools.send_notification._sns") as mock_sns,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_sns.publish.side_effect = _make_client_error()
            result = await send_notification.handler(_VALID_ARGS)

        content = json.loads(result["content"][0]["text"])
        assert "Dr. Ramesh Patel" in content["message"]

    @pytest.mark.asyncio
    async def test_client_error_does_not_raise(self):
        with (
            patch("tools.send_notification._sns") as mock_sns,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_sns.publish.side_effect = _make_client_error()
            # Should not raise any exception
            result = await send_notification.handler(_VALID_ARGS)

        assert "content" in result

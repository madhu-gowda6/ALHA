"""Tests for tools.save_consultation — flat DynamoDB item, kb_citations, and soft failures."""
import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from botocore.exceptions import ClientError

from tools.save_consultation import save_consultation


_VALID_ARGS = {
    "session_id": "sess-abc-123",
    "farmer_phone": "+919000000001",
    "animal_type": "cattle",
    "disease_name": "lumpy_skin_disease",
    "confidence_score": 87.5,
    "severity": "CRITICAL",
    "vet_assigned": "Dr. Ramesh Patel",
    "vet_phone": "+919876543210",
    "treatment_summary": "Isolate animal. Apply topical antiseptic. Supportive care.",
    "kb_citations": ["ICAR Livestock Guide 2023", "NVS Protocol 2021"],
}


class TestSaveConsultationToolMeta:
    def test_tool_has_name(self):
        assert save_consultation.name == "save_consultation"

    def test_tool_has_description(self):
        assert len(save_consultation.description) > 0

    def test_tool_schema_has_required_fields(self):
        schema = save_consultation.input_schema
        required = schema.get("required", [])
        for field in ("session_id", "farmer_phone", "animal_type", "disease_name",
                      "confidence_score", "severity", "vet_assigned", "vet_phone",
                      "treatment_summary", "kb_citations"):
            assert field in required, f"Missing required field: {field}"

    def test_tool_module_importable(self):
        from tools import save_consultation as mod
        assert mod is not None


class TestSaveConsultationHappyPath:
    @pytest.mark.asyncio
    async def test_dynamo_put_item_called_with_flat_item(self):
        with (
            patch("tools.save_consultation._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.put_item.return_value = {}
            await save_consultation.handler(_VALID_ARGS)

        mock_ddb.put_item.assert_called_once()
        call_kwargs = mock_ddb.put_item.call_args.kwargs
        item = call_kwargs["Item"]

        # Verify flat item structure — all S or N types, no L or M
        for key, val in item.items():
            assert len(val) == 1, f"Field {key} has more than one DynamoDB type"
            dynamo_type = list(val.keys())[0]
            assert dynamo_type in ("S", "N"), f"Field {key} uses non-primitive type {dynamo_type}"

    @pytest.mark.asyncio
    async def test_kb_citations_stored_as_json_string(self):
        with (
            patch("tools.save_consultation._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.put_item.return_value = {}
            await save_consultation.handler(_VALID_ARGS)

        item = mock_ddb.put_item.call_args.kwargs["Item"]
        # kb_citations must be S (string), never L (list)
        assert "S" in item["kb_citations"]
        citations_str = item["kb_citations"]["S"]
        # Must be valid JSON
        parsed = json.loads(citations_str)
        assert isinstance(parsed, list)
        assert "ICAR Livestock Guide 2023" in parsed

    @pytest.mark.asyncio
    async def test_consultation_id_equals_session_id(self):
        with (
            patch("tools.save_consultation._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.put_item.return_value = {}
            result = await save_consultation.handler(_VALID_ARGS)

        content = json.loads(result["content"][0]["text"])
        assert content["saved"] is True
        assert content["consultation_id"] == "sess-abc-123"
        assert content["session_id"] == "sess-abc-123"

    @pytest.mark.asyncio
    async def test_treatment_summary_truncated_at_2000_chars(self):
        long_summary = "x" * 3000
        args = {**_VALID_ARGS, "treatment_summary": long_summary}
        with (
            patch("tools.save_consultation._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.put_item.return_value = {}
            await save_consultation.handler(args)

        item = mock_ddb.put_item.call_args.kwargs["Item"]
        stored = item["treatment_summary"]["S"]
        assert len(stored) == 2000

    @pytest.mark.asyncio
    async def test_session_complete_ws_dispatched(self):
        mock_ws = AsyncMock()
        with (
            patch("tools.save_consultation._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {"sess-abc-123": mock_ws}, clear=True),
            patch("asyncio.create_task", side_effect=lambda coro: asyncio.ensure_future(coro)),
        ):
            mock_ddb.put_item.return_value = {}
            await save_consultation.handler(_VALID_ARGS)
            await asyncio.sleep(0)

        mock_ws.send_json.assert_called_once()
        payload = mock_ws.send_json.call_args[0][0]
        assert payload["type"] == "session_complete"
        assert payload["consultation_id"] == "sess-abc-123"

    @pytest.mark.asyncio
    async def test_result_has_content_wrapper(self):
        with (
            patch("tools.save_consultation._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.put_item.return_value = {}
            result = await save_consultation.handler(_VALID_ARGS)

        assert "content" in result
        assert result["content"][0]["type"] == "text"


class TestSaveConsultationSoftFailure:
    @pytest.mark.asyncio
    async def test_client_error_returns_error_dict(self):
        with (
            patch("tools.save_consultation._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.put_item.side_effect = ClientError(
                error_response={"Error": {"Code": "ProvisionedThroughputExceededException",
                                          "Message": "Throughput exceeded"}},
                operation_name="PutItem",
            )
            result = await save_consultation.handler(_VALID_ARGS)

        content = json.loads(result["content"][0]["text"])
        assert content["saved"] is False
        assert content["error"] is True
        assert content["code"] == "DYNAMO_ERROR"
        assert "message" in content

    @pytest.mark.asyncio
    async def test_client_error_does_not_raise(self):
        with (
            patch("tools.save_consultation._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.put_item.side_effect = ClientError(
                error_response={"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}},
                operation_name="PutItem",
            )
            result = await save_consultation.handler(_VALID_ARGS)

        assert "content" in result

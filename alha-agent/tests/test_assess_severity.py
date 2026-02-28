"""Tests for tools.assess_severity — severity classification and WS dispatch."""
import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from tools.assess_severity import assess_severity, _compute_severity


class TestComputeSeverity:
    """Unit tests for the pure heuristic function."""

    def test_critical_lumpy_skin_disease(self):
        assert _compute_severity("lumpy_skin_disease", "") == "CRITICAL"

    def test_critical_newcastle_disease(self):
        assert _compute_severity("newcastle_disease", "") == "CRITICAL"

    def test_critical_anthrax(self):
        assert _compute_severity("anthrax", "") == "CRITICAL"

    def test_high_foot_and_mouth(self):
        assert _compute_severity("foot_and_mouth_disease", "") == "HIGH"

    def test_high_brucellosis(self):
        assert _compute_severity("brucellosis", "") == "HIGH"

    def test_high_blackleg(self):
        assert _compute_severity("blackleg", "") == "HIGH"

    def test_low_from_routine_context(self):
        assert _compute_severity("general_checkup", "routine vaccination checkup") == "LOW"

    def test_low_preventive_keyword(self):
        assert _compute_severity("deworming", "preventive deworming schedule") == "LOW"

    def test_none_for_empty_disease_name(self):
        assert _compute_severity("", "some context") == "NONE"

    def test_medium_for_unknown_disease(self):
        result = _compute_severity("some_other_disease", "mild symptoms")
        assert result == "MEDIUM"


class TestAssessSeverityTool:
    """Integration tests for the @tool-decorated assess_severity function."""

    def test_tool_has_name(self):
        assert assess_severity.name == "assess_severity"

    def test_tool_has_description(self):
        assert len(assess_severity.description) > 0

    def test_tool_schema_has_required_fields(self):
        schema = assess_severity.input_schema
        required = schema.get("required", [])
        assert "session_id" in required
        assert "disease_name" in required
        assert "animal_type" in required
        assert "symptom_context" in required

    @pytest.mark.asyncio
    async def test_returns_critical_for_lumpy_skin(self):
        with patch.dict("ws_map._active_ws_map", {}, clear=True):
            result = await assess_severity.handler({
                "session_id": "s1",
                "disease_name": "lumpy_skin_disease",
                "animal_type": "cattle",
                "symptom_context": "skin lesions, high fever",
            })
        content = json.loads(result["content"][0]["text"])
        assert content["severity"] == "CRITICAL"
        assert content["session_id"] == "s1"
        assert content["disease_name"] == "lumpy_skin_disease"

    @pytest.mark.asyncio
    async def test_returns_low_with_correct_structure(self):
        with patch.dict("ws_map._active_ws_map", {}, clear=True):
            result = await assess_severity.handler({
                "session_id": "s2",
                "disease_name": "general_checkup",
                "animal_type": "cattle",
                "symptom_context": "routine vaccination checkup",
            })
        content = json.loads(result["content"][0]["text"])
        assert content["severity"] == "LOW"
        assert "session_id" in content

    @pytest.mark.asyncio
    async def test_missing_disease_name_returns_none(self):
        with patch.dict("ws_map._active_ws_map", {}, clear=True):
            result = await assess_severity.handler({
                "session_id": "s3",
                "disease_name": "",
                "animal_type": "cattle",
                "symptom_context": "",
            })
        content = json.loads(result["content"][0]["text"])
        assert content["severity"] == "NONE"

    @pytest.mark.asyncio
    async def test_result_has_content_wrapper(self):
        with patch.dict("ws_map._active_ws_map", {}, clear=True):
            result = await assess_severity.handler({
                "session_id": "s4",
                "disease_name": "lumpy_skin_disease",
                "animal_type": "cattle",
                "symptom_context": "critical lesions",
            })
        assert "content" in result
        assert isinstance(result["content"], list)
        assert result["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_ws_severity_message_sent(self):
        """WS message with type=severity and correct level must be dispatched."""
        mock_ws = AsyncMock()
        with (
            patch.dict("ws_map._active_ws_map", {"s5": mock_ws}, clear=True),
            patch("asyncio.create_task", side_effect=lambda coro: asyncio.ensure_future(coro)),
        ):
            await assess_severity.handler({
                "session_id": "s5",
                "disease_name": "newcastle_disease",
                "animal_type": "poultry",
                "symptom_context": "mass mortality",
            })
            await asyncio.sleep(0)  # allow coroutine to run

        mock_ws.send_json.assert_called_once()
        payload = mock_ws.send_json.call_args[0][0]
        assert payload["type"] == "severity"
        assert payload["level"] == "CRITICAL"
        assert payload["session_id"] == "s5"

    @pytest.mark.asyncio
    async def test_no_ws_send_when_no_session_in_map(self):
        """No exception raised when session_id not in ws_map."""
        with patch.dict("ws_map._active_ws_map", {}, clear=True):
            result = await assess_severity.handler({
                "session_id": "nonexistent",
                "disease_name": "lumpy_skin_disease",
                "animal_type": "cattle",
                "symptom_context": "critical",
            })
        # Should complete without error
        assert "content" in result

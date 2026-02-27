"""Tests for tools.symptom_interview — full implementation tests."""
import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from tools.symptom_interview import symptom_interview


class TestSymptomInterviewToolMeta:
    """Verify the tool is properly decorated."""

    def test_tool_has_name(self):
        assert symptom_interview.name == "symptom_interview"

    def test_tool_handler_is_async(self):
        import inspect

        assert inspect.iscoroutinefunction(symptom_interview.handler)

    def test_tool_schema_has_required_fields(self):
        schema = symptom_interview.input_schema
        required = schema.get("required", [])
        assert "session_id" in required
        assert "questions" in required
        assert "questions_hi" in required


class TestSymptomInterviewHappyPath:
    """Test normal question flow."""

    @pytest.mark.asyncio
    async def test_returns_frontend_action(self):
        with patch.dict("ws_map._active_ws_map", {}, clear=True):
            result = await symptom_interview.handler(
                {
                    "session_id": "s1",
                    "questions": ["How many days?", "Any fever?"],
                    "questions_hi": ["कितने दिन से?", "बुखार है?"],
                }
            )

        content = json.loads(result["content"][0]["text"])
        assert content["frontend_action"] == "symptom_interview"

    @pytest.mark.asyncio
    async def test_returns_correct_questions(self):
        with patch.dict("ws_map._active_ws_map", {}, clear=True):
            result = await symptom_interview.handler(
                {
                    "session_id": "s1",
                    "questions": ["How many days?", "Any fever?"],
                    "questions_hi": ["कितने दिन से?", "बुखार है?"],
                }
            )

        content = json.loads(result["content"][0]["text"])
        assert content["questions"] == ["How many days?", "Any fever?"]
        assert content["questions_hi"] == ["कितने दिन से?", "बुखार है?"]
        assert content["question_count"] == 2

    @pytest.mark.asyncio
    async def test_ws_frontend_action_dispatched(self):
        mock_ws = AsyncMock()

        with (
            patch.dict("ws_map._active_ws_map", {"s1": mock_ws}, clear=True),
            patch(
                "asyncio.create_task",
                side_effect=lambda coro: asyncio.ensure_future(coro),
            ),
        ):
            await symptom_interview.handler(
                {
                    "session_id": "s1",
                    "questions": ["How many days?"],
                    "questions_hi": ["कितने दिन से?"],
                }
            )
            await asyncio.sleep(0)  # allow tasks to run

        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "frontend_action"
        assert call_args["action"] == "symptom_interview"
        assert call_args["session_id"] == "s1"
        assert "questions" in call_args
        assert "questions_hi" in call_args


class TestSymptomInterviewTruncation:
    """Test that questions are truncated to max 3."""

    @pytest.mark.asyncio
    async def test_more_than_three_questions_truncated(self):
        four_questions = ["Q1", "Q2", "Q3", "Q4"]
        four_hi = ["H1", "H2", "H3", "H4"]

        with patch.dict("ws_map._active_ws_map", {}, clear=True):
            result = await symptom_interview.handler(
                {
                    "session_id": "s2",
                    "questions": four_questions,
                    "questions_hi": four_hi,
                }
            )

        content = json.loads(result["content"][0]["text"])
        assert len(content["questions"]) == 3
        assert content["question_count"] == 3

    @pytest.mark.asyncio
    async def test_exactly_three_questions_not_truncated(self):
        with patch.dict("ws_map._active_ws_map", {}, clear=True):
            result = await symptom_interview.handler(
                {
                    "session_id": "s2",
                    "questions": ["Q1", "Q2", "Q3"],
                    "questions_hi": ["H1", "H2", "H3"],
                }
            )

        content = json.loads(result["content"][0]["text"])
        assert len(content["questions"]) == 3


class TestSymptomInterviewValidation:
    """Test input validation — empty questions."""

    @pytest.mark.asyncio
    async def test_empty_questions_returns_error(self):
        with patch.dict("ws_map._active_ws_map", {}, clear=True):
            result = await symptom_interview.handler(
                {
                    "session_id": "s3",
                    "questions": [],
                    "questions_hi": [],
                }
            )

        content = json.loads(result["content"][0]["text"])
        assert content["error"] is True
        assert content["code"] == "NO_QUESTIONS"

    @pytest.mark.asyncio
    async def test_empty_questions_no_ws_dispatch(self):
        mock_ws = AsyncMock()

        with patch.dict("ws_map._active_ws_map", {"s3": mock_ws}, clear=True):
            await symptom_interview.handler(
                {
                    "session_id": "s3",
                    "questions": [],
                    "questions_hi": [],
                }
            )

        mock_ws.send_json.assert_not_called()


class TestSymptomInterviewNoWs:
    """Test tool works gracefully when no WebSocket is registered."""

    @pytest.mark.asyncio
    async def test_no_ws_does_not_raise(self):
        with patch.dict("ws_map._active_ws_map", {}, clear=True):
            # Should not raise even when no WS registered
            result = await symptom_interview.handler(
                {
                    "session_id": "unknown-session",
                    "questions": ["Any fever?"],
                    "questions_hi": ["बुखार है?"],
                }
            )

        content = json.loads(result["content"][0]["text"])
        assert content["frontend_action"] == "symptom_interview"

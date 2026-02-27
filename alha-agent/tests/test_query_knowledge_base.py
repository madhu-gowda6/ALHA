"""Tests for tools.query_knowledge_base — full implementation tests."""
import json
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError

from tools.query_knowledge_base import query_knowledge_base


class TestQueryKnowledgeBaseToolMeta:
    """Verify the tool is properly decorated."""

    def test_tool_has_name(self):
        assert query_knowledge_base.name == "query_knowledge_base"

    def test_tool_handler_is_async(self):
        import inspect

        assert inspect.iscoroutinefunction(query_knowledge_base.handler)

    def test_tool_schema_has_required_fields(self):
        schema = query_knowledge_base.input_schema
        required = schema.get("required", [])
        assert "session_id" in required
        assert "disease_name" in required
        assert "animal_type" in required
        assert "language" in required


class TestQueryKnowledgeBaseResults:
    """Test citation extraction when results are returned."""

    @pytest.fixture
    def mock_bedrock_response(self):
        return {
            "retrievalResults": [
                {
                    "content": {"text": "Lumpy skin disease treatment: Administer anti-viral..."},
                    "location": {"s3Location": {"uri": "s3://alha-kb/icar-guide.pdf"}},
                },
                {
                    "content": {"text": "Vaccination protocol for LSD: Use attenuated strain vaccine..."},
                    "location": {"s3Location": {"uri": "s3://alha-kb/nddb-protocol.pdf"}},
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_found_true_when_results_returned(self, mock_bedrock_response):
        with (
            patch("tools.query_knowledge_base._bedrock_agent_runtime") as mock_brt,
            patch("tools.query_knowledge_base.config.bedrock_kb_id", "test-kb-id"),
        ):
            mock_brt.retrieve.return_value = mock_bedrock_response

            result = await query_knowledge_base.handler(
                {
                    "session_id": "s1",
                    "disease_name": "lumpy_skin_disease",
                    "animal_type": "cattle",
                    "language": "en",
                }
            )

        content = json.loads(result["content"][0]["text"])
        assert content["found"] is True

    @pytest.mark.asyncio
    async def test_citations_extracted_correctly(self, mock_bedrock_response):
        with (
            patch("tools.query_knowledge_base._bedrock_agent_runtime") as mock_brt,
            patch("tools.query_knowledge_base.config.bedrock_kb_id", "test-kb-id"),
        ):
            mock_brt.retrieve.return_value = mock_bedrock_response

            result = await query_knowledge_base.handler(
                {
                    "session_id": "s1",
                    "disease_name": "lumpy_skin_disease",
                    "animal_type": "cattle",
                    "language": "en",
                }
            )

        content = json.loads(result["content"][0]["text"])
        assert len(content["citations"]) == 2
        assert content["citations"][0]["source"] == "s3://alha-kb/icar-guide.pdf"

    @pytest.mark.asyncio
    async def test_treatment_summary_combined(self, mock_bedrock_response):
        with (
            patch("tools.query_knowledge_base._bedrock_agent_runtime") as mock_brt,
            patch("tools.query_knowledge_base.config.bedrock_kb_id", "test-kb-id"),
        ):
            mock_brt.retrieve.return_value = mock_bedrock_response

            result = await query_knowledge_base.handler(
                {
                    "session_id": "s1",
                    "disease_name": "lumpy_skin_disease",
                    "animal_type": "cattle",
                    "language": "hi",
                }
            )

        content = json.loads(result["content"][0]["text"])
        assert "Lumpy skin disease" in content["treatment_summary"]

    @pytest.mark.asyncio
    async def test_limits_to_five_citations(self):
        six_results = {
            "retrievalResults": [
                {
                    "content": {"text": f"Result {i}"},
                    "location": {"s3Location": {"uri": f"s3://alha-kb/doc{i}.pdf"}},
                }
                for i in range(6)
            ]
        }
        with (
            patch("tools.query_knowledge_base._bedrock_agent_runtime") as mock_brt,
            patch("tools.query_knowledge_base.config.bedrock_kb_id", "test-kb-id"),
        ):
            mock_brt.retrieve.return_value = six_results

            result = await query_knowledge_base.handler(
                {
                    "session_id": "s1",
                    "disease_name": "lumpy_skin_disease",
                    "animal_type": "cattle",
                    "language": "en",
                }
            )

        content = json.loads(result["content"][0]["text"])
        assert len(content["citations"]) == 5


class TestQueryKnowledgeBaseNoResults:
    """Test graceful handling of 0-result KB response."""

    @pytest.mark.asyncio
    async def test_zero_results_returns_found_false(self):
        with (
            patch("tools.query_knowledge_base._bedrock_agent_runtime") as mock_brt,
            patch("tools.query_knowledge_base.config.bedrock_kb_id", "test-kb-id"),
        ):
            mock_brt.retrieve.return_value = {"retrievalResults": []}

            result = await query_knowledge_base.handler(
                {
                    "session_id": "s2",
                    "disease_name": "unknown_disease",
                    "animal_type": "cattle",
                    "language": "en",
                }
            )

        content = json.loads(result["content"][0]["text"])
        assert content["found"] is False
        assert content["citations"] == []
        assert content["treatment_summary"] == ""

    @pytest.mark.asyncio
    async def test_zero_results_no_exception(self):
        with (
            patch("tools.query_knowledge_base._bedrock_agent_runtime") as mock_brt,
            patch("tools.query_knowledge_base.config.bedrock_kb_id", "test-kb-id"),
        ):
            mock_brt.retrieve.return_value = {"retrievalResults": []}

            # Should not raise
            result = await query_knowledge_base.handler(
                {
                    "session_id": "s2",
                    "disease_name": "unknown_disease",
                    "animal_type": "cattle",
                    "language": "en",
                }
            )
        assert "content" in result


class TestQueryKnowledgeBaseClientError:
    """Test ClientError handling — structured error dict, no raw exception."""

    @pytest.mark.asyncio
    async def test_client_error_returns_error_dict(self):
        with (
            patch("tools.query_knowledge_base._bedrock_agent_runtime") as mock_brt,
            patch("tools.query_knowledge_base.config.bedrock_kb_id", "test-kb-id"),
        ):
            mock_brt.retrieve.side_effect = ClientError(
                error_response={"Error": {"Code": "AccessDeniedException", "Message": "Denied"}},
                operation_name="retrieve",
            )

            result = await query_knowledge_base.handler(
                {
                    "session_id": "s3",
                    "disease_name": "lumpy_skin_disease",
                    "animal_type": "cattle",
                    "language": "en",
                }
            )

        content = json.loads(result["content"][0]["text"])
        assert content["error"] is True
        assert content["code"] == "KB_ERROR"
        assert "message" in content
        assert "message_hi" in content

    @pytest.mark.asyncio
    async def test_client_error_no_raw_exception_leaked(self):
        with (
            patch("tools.query_knowledge_base._bedrock_agent_runtime") as mock_brt,
            patch("tools.query_knowledge_base.config.bedrock_kb_id", "test-kb-id"),
        ):
            mock_brt.retrieve.side_effect = ClientError(
                error_response={"Error": {"Code": "ServiceUnavailableException", "Message": "Down"}},
                operation_name="retrieve",
            )

            result = await query_knowledge_base.handler(
                {
                    "session_id": "s3",
                    "disease_name": "lumpy_skin_disease",
                    "animal_type": "cattle",
                    "language": "hi",
                }
            )

        content = json.loads(result["content"][0]["text"])
        # Should NOT contain raw boto3 error messages
        assert "ServiceUnavailableException" not in str(content)


class TestQueryKnowledgeBaseNoKbId:
    """Test graceful handling when BEDROCK_KB_ID is not configured."""

    @pytest.mark.asyncio
    async def test_no_kb_id_returns_not_configured(self):
        with patch("tools.query_knowledge_base.config.bedrock_kb_id", ""):
            result = await query_knowledge_base.handler(
                {
                    "session_id": "s4",
                    "disease_name": "lumpy_skin_disease",
                    "animal_type": "cattle",
                    "language": "en",
                }
            )

        content = json.loads(result["content"][0]["text"])
        assert content["found"] is False

"""Tests for tools.classify_disease — full implementation tests."""
import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest
from botocore.exceptions import ClientError

from tools.classify_disease import classify_disease


class TestClassifyDiseaseToolMeta:
    """Verify the tool is properly decorated as an SdkMcpTool."""

    def test_tool_has_name(self):
        assert classify_disease.name == "classify_disease"

    def test_tool_handler_is_async(self):
        import inspect

        assert inspect.iscoroutinefunction(classify_disease.handler)

    def test_tool_has_description(self):
        assert len(classify_disease.description) > 0

    def test_tool_schema_has_required_fields(self):
        schema = classify_disease.input_schema
        required = schema.get("required", [])
        assert "session_id" in required
        assert "s3_image_key" in required
        assert "animal_type" in required


class TestClassifyDiseaseLabelsFound:
    """Test happy-path label detection with bounding box."""

    @pytest.fixture
    def mock_rekognition_response(self):
        return {
            "CustomLabels": [
                {
                    "Name": "lumpy_skin_disease",
                    "Confidence": 89.0,
                    "Geometry": {
                        "BoundingBox": {
                            "Left": 0.12,
                            "Top": 0.35,
                            "Width": 0.45,
                            "Height": 0.28,
                        }
                    },
                },
                {
                    "Name": "dermatitis",
                    "Confidence": 55.0,
                    "Geometry": {
                        "BoundingBox": {
                            "Left": 0.5,
                            "Top": 0.5,
                            "Width": 0.2,
                            "Height": 0.2,
                        }
                    },
                },
            ]
        }

    @pytest.mark.asyncio
    async def test_returns_top_label_by_confidence(self, mock_rekognition_response):
        with (
            patch("tools.classify_disease._rekognition") as mock_rek,
            patch("tools.classify_disease._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.get_item.return_value = {
                "Item": {"model_arn": {"S": "arn:aws:rekognition:us-east-1:123:project/test/version/1"}}
            }
            mock_rek.detect_custom_labels.return_value = mock_rekognition_response

            result = await classify_disease.handler(
                {"session_id": "s1", "s3_image_key": "uploads/s1/img.jpg", "animal_type": "cattle"}
            )

        content = json.loads(result["content"][0]["text"])
        assert content["disease"] == "lumpy_skin_disease"
        assert content["confidence"] == 89.0

    @pytest.mark.asyncio
    async def test_returns_normalised_bbox(self, mock_rekognition_response):
        with (
            patch("tools.classify_disease._rekognition") as mock_rek,
            patch("tools.classify_disease._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.get_item.return_value = {
                "Item": {"model_arn": {"S": "arn:aws:rekognition:us-east-1:123:project/test/version/1"}}
            }
            mock_rek.detect_custom_labels.return_value = mock_rekognition_response

            result = await classify_disease.handler(
                {"session_id": "s1", "s3_image_key": "uploads/s1/img.jpg", "animal_type": "cattle"}
            )

        content = json.loads(result["content"][0]["text"])
        bbox = content["bbox"]
        assert bbox is not None
        assert bbox["left"] == pytest.approx(0.12)
        assert bbox["top"] == pytest.approx(0.35)
        assert bbox["width"] == pytest.approx(0.45)
        assert bbox["height"] == pytest.approx(0.28)

    @pytest.mark.asyncio
    async def test_diagnosis_ws_message_sent(self, mock_rekognition_response):
        mock_ws = AsyncMock()
        with (
            patch("tools.classify_disease._rekognition") as mock_rek,
            patch("tools.classify_disease._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {"s1": mock_ws}, clear=True),
            patch("asyncio.create_task", side_effect=lambda coro: asyncio.ensure_future(coro)),
        ):
            mock_ddb.get_item.return_value = {
                "Item": {"model_arn": {"S": "arn:aws:rekognition:us-east-1:123:project/test/version/1"}}
            }
            mock_rek.detect_custom_labels.return_value = mock_rekognition_response

            result = await classify_disease.handler(
                {"session_id": "s1", "s3_image_key": "uploads/s1/img.jpg", "animal_type": "cattle"}
            )
            await asyncio.sleep(0)  # allow tasks to run

        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "diagnosis"
        assert call_args["disease"] == "lumpy_skin_disease"


class TestClassifyDiseaseSoftFailure:
    """Test 0-label soft failure path — no exception raised."""

    @pytest.mark.asyncio
    async def test_zero_labels_returns_soft_failure(self):
        with (
            patch("tools.classify_disease._rekognition") as mock_rek,
            patch("tools.classify_disease._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.get_item.return_value = {
                "Item": {"model_arn": {"S": "arn:aws:rekognition:us-east-1:123:project/test/version/1"}}
            }
            mock_rek.detect_custom_labels.return_value = {"CustomLabels": []}

            result = await classify_disease.handler(
                {"session_id": "s2", "s3_image_key": "uploads/s2/blur.jpg", "animal_type": "cattle"}
            )

        content = json.loads(result["content"][0]["text"])
        assert content["soft_failure"] is True
        assert content["disease"] is None
        assert content["confidence"] == 0.0
        assert "message" in content
        assert "message_hi" in content

    @pytest.mark.asyncio
    async def test_zero_labels_no_exception(self):
        with (
            patch("tools.classify_disease._rekognition") as mock_rek,
            patch("tools.classify_disease._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.get_item.return_value = {
                "Item": {"model_arn": {"S": "arn:aws:rekognition:us-east-1:123:project/test/version/1"}}
            }
            mock_rek.detect_custom_labels.return_value = {"CustomLabels": []}

            # Should not raise
            result = await classify_disease.handler(
                {"session_id": "s2", "s3_image_key": "uploads/s2/blur.jpg", "animal_type": "cattle"}
            )
        assert "content" in result


class TestClassifyDiseaseClientError:
    """Test ClientError handling — structured error dict, no raw exception."""

    def _make_client_error(self, code: str) -> ClientError:
        return ClientError(
            error_response={"Error": {"Code": code, "Message": "Test error"}},
            operation_name="detect_custom_labels",
        )

    @pytest.mark.asyncio
    async def test_rekognition_error_returns_error_dict(self):
        with (
            patch("tools.classify_disease._rekognition") as mock_rek,
            patch("tools.classify_disease._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.get_item.return_value = {
                "Item": {"model_arn": {"S": "arn:aws:rekognition:us-east-1:123:project/test/version/1"}}
            }
            mock_rek.detect_custom_labels.side_effect = self._make_client_error(
                "AccessDeniedException"
            )

            result = await classify_disease.handler(
                {"session_id": "s3", "s3_image_key": "uploads/s3/img.jpg", "animal_type": "cattle"}
            )

        content = json.loads(result["content"][0]["text"])
        assert content["error"] is True
        assert content["code"] == "REKOGNITION_ERROR"
        assert "message" in content
        assert "message_hi" in content

    @pytest.mark.asyncio
    async def test_model_stopped_returns_model_stopped_code(self):
        with (
            patch("tools.classify_disease._rekognition") as mock_rek,
            patch("tools.classify_disease._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.get_item.return_value = {
                "Item": {"model_arn": {"S": "arn:aws:rekognition:us-east-1:123:project/test/version/1"}}
            }
            mock_rek.detect_custom_labels.side_effect = self._make_client_error(
                "InvalidParameterException"
            )

            result = await classify_disease.handler(
                {"session_id": "s3", "s3_image_key": "uploads/s3/img.jpg", "animal_type": "cattle"}
            )

        content = json.loads(result["content"][0]["text"])
        assert content["code"] == "REKOGNITION_MODEL_STOPPED"


class TestClassifyDiseaseDynamoFallback:
    """Test DynamoDB ARN fallback to env var when lookup fails."""

    @pytest.mark.asyncio
    async def test_dynamodb_error_falls_back_to_env_var(self):
        with (
            patch("tools.classify_disease._rekognition") as mock_rek,
            patch("tools.classify_disease._dynamodb") as mock_ddb,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
            patch(
                "tools.classify_disease.config.rekognition_cattle_arn",
                "arn:aws:rekognition:us-east-1:123:project/fallback/version/1",
            ),
        ):
            mock_ddb.get_item.side_effect = ClientError(
                error_response={"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}},
                operation_name="get_item",
            )
            mock_rek.detect_custom_labels.return_value = {
                "CustomLabels": [
                    {
                        "Name": "anthrax",
                        "Confidence": 72.0,
                        "Geometry": {"BoundingBox": {"Left": 0.1, "Top": 0.1, "Width": 0.3, "Height": 0.3}},
                    }
                ]
            }

            result = await classify_disease.handler(
                {"session_id": "s4", "s3_image_key": "uploads/s4/img.jpg", "animal_type": "cattle"}
            )

        content = json.loads(result["content"][0]["text"])
        assert content["disease"] == "anthrax"
        # Verify fallback ARN was used (no error)
        assert "error" not in content

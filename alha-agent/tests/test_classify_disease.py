"""Tests for tools.classify_disease — full implementation tests."""
import asyncio
import io
import json
from unittest.mock import AsyncMock, patch

import pytest
from botocore.exceptions import ClientError

from tools.classify_disease import classify_disease


def _make_bedrock_response(disease, confidence, bbox=None):
    """Build a mock bedrock invoke_model response with the given classification."""
    body = json.dumps({
        "content": [{"text": json.dumps({
            "disease": disease,
            "confidence": confidence,
            "bbox": bbox,
        })}]
    }).encode()
    return {"body": io.BytesIO(body)}


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
            patch("tools.classify_disease._s3") as mock_s3,
            patch("tools.classify_disease._bedrock_runtime") as mock_br,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.get_item.return_value = {
                "Item": {"model_arn": {"S": "arn:aws:rekognition:us-east-1:123:project/test/version/1"}}
            }
            mock_rek.detect_custom_labels.return_value = mock_rekognition_response
            mock_s3.get_object.return_value = {"Body": io.BytesIO(b"fake_image_bytes")}
            mock_br.invoke_model.return_value = _make_bedrock_response(
                "lumpy_skin_disease", 85.0,
                {"left": 0.12, "top": 0.35, "width": 0.45, "height": 0.28}
            )

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
            patch("tools.classify_disease._s3") as mock_s3,
            patch("tools.classify_disease._bedrock_runtime") as mock_br,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.get_item.return_value = {
                "Item": {"model_arn": {"S": "arn:aws:rekognition:us-east-1:123:project/test/version/1"}}
            }
            mock_rek.detect_custom_labels.return_value = mock_rekognition_response
            mock_s3.get_object.return_value = {"Body": io.BytesIO(b"fake_image_bytes")}
            mock_br.invoke_model.return_value = _make_bedrock_response(
                "lumpy_skin_disease", 85.0,
                {"left": 0.12, "top": 0.35, "width": 0.45, "height": 0.28}
            )

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
            patch("tools.classify_disease._s3") as mock_s3,
            patch("tools.classify_disease._bedrock_runtime") as mock_br,
            patch.dict("ws_map._active_ws_map", {"s1": mock_ws}, clear=True),
            patch("asyncio.create_task", side_effect=lambda coro: asyncio.ensure_future(coro)),
        ):
            mock_ddb.get_item.return_value = {
                "Item": {"model_arn": {"S": "arn:aws:rekognition:us-east-1:123:project/test/version/1"}}
            }
            mock_rek.detect_custom_labels.return_value = mock_rekognition_response
            mock_s3.get_object.return_value = {"Body": io.BytesIO(b"fake_image_bytes")}
            mock_br.invoke_model.return_value = _make_bedrock_response(
                "lumpy_skin_disease", 85.0,
                {"left": 0.12, "top": 0.35, "width": 0.45, "height": 0.28}
            )

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
    """Test ClientError handling — now falls through to Claude (claude_fallback)."""

    def _make_client_error(self, code: str) -> ClientError:
        return ClientError(
            error_response={"Error": {"Code": code, "Message": "Test error"}},
            operation_name="detect_custom_labels",
        )

    @pytest.mark.asyncio
    async def test_rekognition_error_falls_back_to_claude(self):
        with (
            patch("tools.classify_disease._rekognition") as mock_rek,
            patch("tools.classify_disease._dynamodb") as mock_ddb,
            patch("tools.classify_disease._s3") as mock_s3,
            patch("tools.classify_disease._bedrock_runtime") as mock_br,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.get_item.return_value = {
                "Item": {"model_arn": {"S": "arn:aws:rekognition:us-east-1:123:project/test/version/1"}}
            }
            mock_rek.detect_custom_labels.side_effect = self._make_client_error(
                "AccessDeniedException"
            )
            mock_s3.get_object.return_value = {"Body": io.BytesIO(b"fake_image_bytes")}
            mock_br.invoke_model.return_value = _make_bedrock_response(
                "lumpy_skin_disease", 80.0,
                {"left": 0.1, "top": 0.2, "width": 0.3, "height": 0.4}
            )

            result = await classify_disease.handler(
                {"session_id": "s3", "s3_image_key": "uploads/s3/img.jpg", "animal_type": "cattle"}
            )

        content = json.loads(result["content"][0]["text"])
        assert content["source"] == "claude_fallback"
        assert content["disease"] == "lumpy_skin_disease"
        assert "error" not in content

    @pytest.mark.asyncio
    async def test_model_stopped_also_falls_back_to_claude(self):
        with (
            patch("tools.classify_disease._rekognition") as mock_rek,
            patch("tools.classify_disease._dynamodb") as mock_ddb,
            patch("tools.classify_disease._s3") as mock_s3,
            patch("tools.classify_disease._bedrock_runtime") as mock_br,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.get_item.return_value = {
                "Item": {"model_arn": {"S": "arn:aws:rekognition:us-east-1:123:project/test/version/1"}}
            }
            mock_rek.detect_custom_labels.side_effect = self._make_client_error(
                "InvalidParameterException"
            )
            mock_s3.get_object.return_value = {"Body": io.BytesIO(b"fake_image_bytes")}
            mock_br.invoke_model.return_value = _make_bedrock_response(
                "foot_and_mouth", 75.0,
                {"left": 0.2, "top": 0.1, "width": 0.4, "height": 0.3}
            )

            result = await classify_disease.handler(
                {"session_id": "s3", "s3_image_key": "uploads/s3/img.jpg", "animal_type": "cattle"}
            )

        content = json.loads(result["content"][0]["text"])
        assert content["source"] == "claude_fallback"
        assert content["disease"] is not None
        assert "error" not in content


class TestClassifyDiseaseDynamoFallback:
    """Test DynamoDB ARN fallback to env var when lookup fails."""

    @pytest.mark.asyncio
    async def test_dynamodb_error_falls_back_to_env_var(self):
        with (
            patch("tools.classify_disease._rekognition") as mock_rek,
            patch("tools.classify_disease._dynamodb") as mock_ddb,
            patch("tools.classify_disease._s3") as mock_s3,
            patch("tools.classify_disease._bedrock_runtime") as mock_br,
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
            mock_s3.get_object.return_value = {"Body": io.BytesIO(b"fake_image_bytes")}
            mock_br.invoke_model.return_value = _make_bedrock_response(
                "anthrax", 70.0,
                {"left": 0.1, "top": 0.1, "width": 0.3, "height": 0.3}
            )

            result = await classify_disease.handler(
                {"session_id": "s4", "s3_image_key": "uploads/s4/img.jpg", "animal_type": "cattle"}
            )

        content = json.loads(result["content"][0]["text"])
        assert content["disease"] == "anthrax"
        # Verify fallback ARN was used (no error)
        assert "error" not in content


class TestClaudeOnlyPath:
    """REKOGNITION_MOCK=true — all classification goes to Claude."""

    @pytest.fixture
    def bedrock_response(self):
        return _make_bedrock_response(
            "lumpy_skin_disease", 83.0,
            {"left": 0.1, "top": 0.2, "width": 0.3, "height": 0.4},
        )

    @pytest.mark.asyncio
    async def test_claude_only_returns_disease(self, bedrock_response):
        with (
            patch("tools.classify_disease.config.rekognition_mock", True),
            patch("tools.classify_disease._s3") as mock_s3,
            patch("tools.classify_disease._bedrock_runtime") as mock_br,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_s3.get_object.return_value = {"Body": io.BytesIO(b"fake_image_bytes")}
            mock_br.invoke_model.return_value = bedrock_response

            result = await classify_disease.handler(
                {"session_id": "s1", "s3_image_key": "uploads/s1/img.jpg", "animal_type": "cattle"}
            )

        content = json.loads(result["content"][0]["text"])
        assert content["disease"] == "lumpy_skin_disease"
        assert content["source"] == "claude"

    @pytest.mark.asyncio
    async def test_claude_null_disease_returns_soft_failure(self):
        with (
            patch("tools.classify_disease.config.rekognition_mock", True),
            patch("tools.classify_disease._s3") as mock_s3,
            patch("tools.classify_disease._bedrock_runtime") as mock_br,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_s3.get_object.return_value = {"Body": io.BytesIO(b"fake_image_bytes")}
            mock_br.invoke_model.return_value = _make_bedrock_response(None, 0.0, None)

            result = await classify_disease.handler(
                {"session_id": "s1", "s3_image_key": "uploads/s1/img.jpg", "animal_type": "cattle"}
            )

        content = json.loads(result["content"][0]["text"])
        assert content["soft_failure"] is True
        assert content["disease"] is None


class TestRekognitionClaudeAgree:
    """Rekognition and Claude agree on disease — Rekognition result used."""

    @pytest.mark.asyncio
    async def test_agreement_uses_rekognition_result(self):
        rek_bbox = {"Left": 0.1, "Top": 0.2, "Width": 0.5, "Height": 0.4}
        with (
            patch("tools.classify_disease._rekognition") as mock_rek,
            patch("tools.classify_disease._dynamodb") as mock_ddb,
            patch("tools.classify_disease._s3") as mock_s3,
            patch("tools.classify_disease._bedrock_runtime") as mock_br,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.get_item.return_value = {
                "Item": {"model_arn": {"S": "arn:aws:rekognition:us-east-1:123:project/test/version/1"}}
            }
            mock_rek.detect_custom_labels.return_value = {
                "CustomLabels": [{
                    "Name": "lumpy_skin_disease",
                    "Confidence": 91.0,
                    "Geometry": {"BoundingBox": rek_bbox},
                }]
            }
            mock_s3.get_object.return_value = {"Body": io.BytesIO(b"fake_image_bytes")}
            # Claude agrees (same disease name)
            mock_br.invoke_model.return_value = _make_bedrock_response(
                "lumpy_skin_disease", 78.0,
                {"left": 0.2, "top": 0.3, "width": 0.4, "height": 0.3}
            )

            result = await classify_disease.handler(
                {"session_id": "s1", "s3_image_key": "uploads/s1/img.jpg", "animal_type": "cattle"}
            )

        content = json.loads(result["content"][0]["text"])
        assert content["source"] == "rekognition"
        # Rekognition confidence and bbox used
        assert content["confidence"] == 91.0
        assert content["bbox"]["left"] == pytest.approx(0.1)
        assert content["bbox"]["top"] == pytest.approx(0.2)


class TestRekognitionClaudeDisagree:
    """Rekognition and Claude disagree — Claude wins."""

    @pytest.mark.asyncio
    async def test_disagreement_claude_wins(self):
        with (
            patch("tools.classify_disease._rekognition") as mock_rek,
            patch("tools.classify_disease._dynamodb") as mock_ddb,
            patch("tools.classify_disease._s3") as mock_s3,
            patch("tools.classify_disease._bedrock_runtime") as mock_br,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.get_item.return_value = {
                "Item": {"model_arn": {"S": "arn:aws:rekognition:us-east-1:123:project/test/version/1"}}
            }
            mock_rek.detect_custom_labels.return_value = {
                "CustomLabels": [{
                    "Name": "lumpy_skin_disease",
                    "Confidence": 88.0,
                    "Geometry": {"BoundingBox": {"Left": 0.1, "Top": 0.1, "Width": 0.5, "Height": 0.4}},
                }]
            }
            mock_s3.get_object.return_value = {"Body": io.BytesIO(b"fake_image_bytes")}
            # Claude disagrees
            mock_br.invoke_model.return_value = _make_bedrock_response(
                "dermatitis", 82.0,
                {"left": 0.15, "top": 0.2, "width": 0.4, "height": 0.35}
            )

            result = await classify_disease.handler(
                {"session_id": "s1", "s3_image_key": "uploads/s1/img.jpg", "animal_type": "cattle"}
            )

        content = json.loads(result["content"][0]["text"])
        assert content["disease"] == "dermatitis"
        assert content["source"] == "claude"


class TestRekognitionErrorFallback:
    """Rekognition throws ClientError — falls back to Claude with source=claude_fallback."""

    def _make_client_error(self, code: str = "AccessDeniedException") -> ClientError:
        return ClientError(
            error_response={"Error": {"Code": code, "Message": "Test error"}},
            operation_name="detect_custom_labels",
        )

    @pytest.mark.asyncio
    async def test_rekognition_error_returns_claude_fallback(self):
        with (
            patch("tools.classify_disease._rekognition") as mock_rek,
            patch("tools.classify_disease._dynamodb") as mock_ddb,
            patch("tools.classify_disease._s3") as mock_s3,
            patch("tools.classify_disease._bedrock_runtime") as mock_br,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.get_item.return_value = {
                "Item": {"model_arn": {"S": "arn:aws:rekognition:us-east-1:123:project/test/version/1"}}
            }
            mock_rek.detect_custom_labels.side_effect = self._make_client_error()
            mock_s3.get_object.return_value = {"Body": io.BytesIO(b"fake_image_bytes")}
            mock_br.invoke_model.return_value = _make_bedrock_response(
                "newcastle_disease", 77.0,
                {"left": 0.1, "top": 0.1, "width": 0.3, "height": 0.3}
            )

            result = await classify_disease.handler(
                {"session_id": "s5", "s3_image_key": "uploads/s5/img.jpg", "animal_type": "poultry"}
            )

        content = json.loads(result["content"][0]["text"])
        assert content["source"] == "claude_fallback"
        assert content["disease"] == "newcastle_disease"
        assert "error" not in content


class TestClaudeVisionError:
    """Both Rekognition and Claude fail — last-resort error dict returned."""

    def _make_client_error(self) -> ClientError:
        return ClientError(
            error_response={"Error": {"Code": "AccessDeniedException", "Message": "Denied"}},
            operation_name="detect_custom_labels",
        )

    @pytest.mark.asyncio
    async def test_both_fail_returns_error_dict(self):
        with (
            patch("tools.classify_disease._rekognition") as mock_rek,
            patch("tools.classify_disease._dynamodb") as mock_ddb,
            patch("tools.classify_disease._s3") as mock_s3,
            patch("tools.classify_disease._bedrock_runtime") as mock_br,
            patch.dict("ws_map._active_ws_map", {}, clear=True),
        ):
            mock_ddb.get_item.return_value = {
                "Item": {"model_arn": {"S": "arn:aws:rekognition:us-east-1:123:project/test/version/1"}}
            }
            mock_rek.detect_custom_labels.side_effect = self._make_client_error()
            mock_s3.get_object.return_value = {"Body": io.BytesIO(b"fake_image_bytes")}
            mock_br.invoke_model.side_effect = Exception("Bedrock unavailable")

            result = await classify_disease.handler(
                {"session_id": "s6", "s3_image_key": "uploads/s6/img.jpg", "animal_type": "cattle"}
            )

        content = json.loads(result["content"][0]["text"])
        assert content["error"] is True
        assert content["code"] == "REKOGNITION_ERROR"
        assert "message" in content
        assert "message_hi" in content

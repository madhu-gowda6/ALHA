"""Tests for notification_handler Lambda — history endpoint."""
import importlib.util
import json
import os
from unittest.mock import MagicMock, patch

import pytest

# Load notification_handler/app.py by path with a unique module name so it does
# not pollute sys.modules['app'] and break other Lambda test files.
_NH_APP_PATH = os.path.join(os.path.dirname(__file__), '..', 'functions', 'notification_handler', 'app.py')
import sys
_spec = importlib.util.spec_from_file_location("notification_handler_app", _NH_APP_PATH)
_nh_module = importlib.util.module_from_spec(_spec)
sys.modules["notification_handler_app"] = _nh_module  # register so patch() can find it
_spec.loader.exec_module(_nh_module)
handler = _nh_module.handler


def _make_event(phone_number=""):
    """Build a mock API Gateway HTTP API v2 event with JWT claims."""
    return {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "phone_number": phone_number,
                        "sub": "user-123",
                    }
                }
            }
        }
    }


_SAMPLE_ITEMS = [
    {
        "session_id": {"S": "sess-001"},
        "animal_type": {"S": "cattle"},
        "disease_name": {"S": "lumpy_skin_disease"},
        "confidence_score": {"N": "89.5"},
        "severity": {"S": "CRITICAL"},
        "vet_assigned": {"S": "Dr. Ramesh"},
        "treatment_summary": {"S": "Isolate animal."},
        "kb_citations": {"S": '["ICAR 2023"]'},
        "timestamp": {"S": "2026-02-26T06:15:00Z"},
        "farmer_phone": {"S": "+919000000001"},
    },
    {
        "session_id": {"S": "sess-002"},
        "animal_type": {"S": "cattle"},
        "disease_name": {"S": "foot_and_mouth"},
        "confidence_score": {"N": "75.0"},
        "severity": {"S": "HIGH"},
        "vet_assigned": {"S": "none"},
        "treatment_summary": {"S": "Supportive care."},
        "kb_citations": {"S": "[]"},
        "timestamp": {"S": "2026-02-25T10:00:00Z"},
        "farmer_phone": {"S": "+919000000001"},
    },
]


class TestHandlerHappyPath:
    def test_returns_200_with_valid_phone(self):
        with patch("notification_handler_app._dynamodb") as mock_ddb:
            mock_ddb.query.return_value = {"Items": _SAMPLE_ITEMS}
            result = handler(_make_event("+919000000001"), None)

        assert result["statusCode"] == 200

    def test_returns_consultation_list(self):
        with patch("notification_handler_app._dynamodb") as mock_ddb:
            mock_ddb.query.return_value = {"Items": _SAMPLE_ITEMS}
            result = handler(_make_event("+919000000001"), None)

        body = json.loads(result["body"])
        assert body["success"] is True
        assert isinstance(body["data"], list)
        assert len(body["data"]) == 2

    def test_consultation_fields_mapped_correctly(self):
        with patch("notification_handler_app._dynamodb") as mock_ddb:
            mock_ddb.query.return_value = {"Items": [_SAMPLE_ITEMS[0]]}
            result = handler(_make_event("+919000000001"), None)

        body = json.loads(result["body"])
        c = body["data"][0]
        assert c["consultation_id"] == "sess-001"
        assert c["animal_type"] == "cattle"
        assert c["disease_name"] == "lumpy_skin_disease"
        assert c["confidence_score"] == 89.5
        assert c["severity"] == "CRITICAL"

    def test_consultations_sorted_newest_first(self):
        with patch("notification_handler_app._dynamodb") as mock_ddb:
            mock_ddb.query.return_value = {"Items": _SAMPLE_ITEMS}
            result = handler(_make_event("+919000000001"), None)

        body = json.loads(result["body"])
        timestamps = [c["timestamp"] for c in body["data"]]
        assert timestamps == sorted(timestamps, reverse=True), "Consultations must be newest first"

    def test_uses_gsi_query_not_scan(self):
        with patch("notification_handler_app._dynamodb") as mock_ddb:
            mock_ddb.query.return_value = {"Items": []}
            handler(_make_event("+919000000001"), None)

        mock_ddb.query.assert_called_once()
        mock_ddb.scan.assert_not_called() if hasattr(mock_ddb, 'scan') else None
        call_kwargs = mock_ddb.query.call_args.kwargs
        assert call_kwargs["IndexName"] == "gsi-farmer-phone"
        assert call_kwargs["KeyConditionExpression"] == "farmer_phone = :phone"
        assert call_kwargs["ExpressionAttributeValues"] == {":phone": {"S": "+919000000001"}}

    def test_empty_result_returns_empty_list(self):
        with patch("notification_handler_app._dynamodb") as mock_ddb:
            mock_ddb.query.return_value = {"Items": []}
            result = handler(_make_event("+919000000001"), None)

        body = json.loads(result["body"])
        assert body["success"] is True
        assert body["data"] == []


class TestHandlerMissingPhone:
    def test_missing_phone_returns_400(self):
        result = handler(_make_event(""), None)
        assert result["statusCode"] == 400

    def test_missing_phone_returns_bilingual_error(self):
        result = handler(_make_event(""), None)
        body = json.loads(result["body"])
        assert body["success"] is False
        assert "message" in body["error"]
        assert "message_hi" in body["error"]

    def test_no_requestcontext_returns_400(self):
        result = handler({}, None)
        assert result["statusCode"] == 400


class TestHandlerDynamoError:
    def test_dynamodb_exception_returns_500(self):
        with patch("notification_handler_app._dynamodb") as mock_ddb:
            mock_ddb.query.side_effect = Exception("DynamoDB unavailable")
            result = handler(_make_event("+919000000001"), None)

        assert result["statusCode"] == 500

    def test_dynamodb_exception_returns_bilingual_error(self):
        with patch("notification_handler_app._dynamodb") as mock_ddb:
            mock_ddb.query.side_effect = Exception("Throughput exceeded")
            result = handler(_make_event("+919000000001"), None)

        body = json.loads(result["body"])
        assert body["success"] is False
        assert "message_hi" in body["error"]

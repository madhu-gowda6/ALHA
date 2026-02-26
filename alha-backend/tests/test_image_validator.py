import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'functions', 'image_validator'))

from app import handler


def test_handler_returns_200():
    event = {"httpMethod": "POST", "path": "/api/upload-url", "body": "{}"}
    result = handler(event, {})
    assert result["statusCode"] == 200


def test_handler_returns_success_envelope():
    event = {"httpMethod": "POST", "path": "/api/upload-url", "body": "{}"}
    result = handler(event, {})
    body = json.loads(result["body"])
    assert body["success"] is True
    assert "data" in body
    assert body["error"] is None


def test_handler_content_type_json():
    event = {}
    result = handler(event, {})
    assert result["headers"]["Content-Type"] == "application/json"

import json
import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'functions', 'notification_handler'))

from app import auth_handler


def _event(username="raju", password="Demo@1234"):
    return {"body": json.dumps({"username": username, "password": password})}


def test_auth_handler_returns_token_on_success():
    mock_client = MagicMock()
    mock_client.initiate_auth.return_value = {
        "AuthenticationResult": {"IdToken": "test-jwt-token"}
    }
    with patch("boto3.client", return_value=mock_client):
        result = auth_handler(_event(), {})

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["success"] is True
    assert body["data"]["token"] == "test-jwt-token"
    assert body["error"] is None


def test_auth_handler_returns_401_on_bad_credentials():
    mock_client = MagicMock()
    mock_client.exceptions.NotAuthorizedException = Exception
    mock_client.initiate_auth.side_effect = Exception("NotAuthorizedException")

    with patch("boto3.client", return_value=mock_client):
        result = auth_handler(_event(password="wrong"), {})

    assert result["statusCode"] == 401
    body = json.loads(result["body"])
    assert body["success"] is False
    assert "message" in body["error"]
    assert "message_hi" in body["error"]


def test_auth_handler_empty_body_does_not_crash():
    mock_client = MagicMock()
    mock_client.exceptions.NotAuthorizedException = Exception
    mock_client.initiate_auth.side_effect = Exception("NotAuthorizedException")

    with patch("boto3.client", return_value=mock_client):
        result = auth_handler({"body": None}, {})

    assert result["statusCode"] in (200, 401)


def test_auth_handler_content_type_json():
    mock_client = MagicMock()
    mock_client.initiate_auth.return_value = {
        "AuthenticationResult": {"IdToken": "tok"}
    }
    with patch("boto3.client", return_value=mock_client):
        result = auth_handler(_event(), {})

    assert result["headers"]["Content-Type"] == "application/json"


def test_auth_handler_uses_cognito_client_id_from_env(monkeypatch):
    monkeypatch.setenv("COGNITO_CLIENT_ID", "my-client-id")
    captured = {}

    def fake_initiate_auth(**kwargs):
        captured["client_id"] = kwargs.get("ClientId")
        return {"AuthenticationResult": {"IdToken": "tok"}}

    mock_client = MagicMock()
    mock_client.initiate_auth.side_effect = fake_initiate_auth

    with patch("boto3.client", return_value=mock_client):
        auth_handler(_event(), {})

    assert captured["client_id"] == "my-client-id"

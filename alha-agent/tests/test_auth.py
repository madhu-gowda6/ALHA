"""Tests for /api/auth/login endpoint."""
import json
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

import app as app_module
from app import app

client = TestClient(app)


def _cognito_error(code: str):
    error_response = {"Error": {"Code": code, "Message": "test"}}
    return ClientError(error_response, "InitiateAuth")


class TestAuthLoginSuccess:
    def test_returns_200_on_success(self):
        mock_cognito = MagicMock()
        mock_cognito.initiate_auth.return_value = {
            "AuthenticationResult": {
                "IdToken": "test-jwt-token",
                "AccessToken": "access",
                "RefreshToken": "refresh",
            }
        }
        with patch.object(app_module, "_cognito", mock_cognito):
            response = client.post(
                "/api/auth/login",
                json={"username": "raju", "password": "secret"},
            )
        assert response.status_code == 200

    def test_returns_success_envelope(self):
        mock_cognito = MagicMock()
        mock_cognito.initiate_auth.return_value = {
            "AuthenticationResult": {"IdToken": "test-jwt-token"}
        }
        with patch.object(app_module, "_cognito", mock_cognito):
            body = client.post(
                "/api/auth/login",
                json={"username": "raju", "password": "secret"},
            ).json()
        assert body["success"] is True
        assert body["error"] is None
        assert body["data"]["token"] == "test-jwt-token"
        assert body["data"]["username"] == "raju"

    def test_calls_cognito_with_correct_params(self):
        mock_cognito = MagicMock()
        mock_cognito.initiate_auth.return_value = {
            "AuthenticationResult": {"IdToken": "tok"}
        }
        with patch.object(app_module, "_cognito", mock_cognito):
            client.post(
                "/api/auth/login",
                json={"username": "raju", "password": "pw123"},
            )
        mock_cognito.initiate_auth.assert_called_once_with(
            ClientId="test-client-id",
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": "raju", "PASSWORD": "pw123"},
        )


class TestAuthLoginFailure:
    def test_invalid_credentials_returns_401(self):
        mock_cognito = MagicMock()
        mock_cognito.initiate_auth.side_effect = _cognito_error("NotAuthorizedException")
        with patch.object(app_module, "_cognito", mock_cognito):
            response = client.post(
                "/api/auth/login",
                json={"username": "raju", "password": "wrong"},
            )
        assert response.status_code == 401

    def test_user_not_found_returns_401(self):
        mock_cognito = MagicMock()
        mock_cognito.initiate_auth.side_effect = _cognito_error("UserNotFoundException")
        with patch.object(app_module, "_cognito", mock_cognito):
            response = client.post(
                "/api/auth/login",
                json={"username": "nobody", "password": "pw"},
            )
        assert response.status_code == 401

    def test_failure_returns_bilingual_error(self):
        mock_cognito = MagicMock()
        mock_cognito.initiate_auth.side_effect = _cognito_error("NotAuthorizedException")
        with patch.object(app_module, "_cognito", mock_cognito):
            body = client.post(
                "/api/auth/login",
                json={"username": "raju", "password": "wrong"},
            ).json()
        assert body["success"] is False
        assert body["data"] is None
        assert body["error"]["code"] == "AUTH_FAILED"
        assert "message" in body["error"]
        assert "message_hi" in body["error"]

    def test_missing_body_returns_422(self):
        response = client.post("/api/auth/login")
        assert response.status_code == 422

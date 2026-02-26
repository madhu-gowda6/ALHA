"""Tests for alha-agent FastAPI endpoints."""
import pytest
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_status_ok(self):
        response = client.get("/health")
        assert response.json() == {"status": "ok"}

    def test_health_content_type_json(self):
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]


class TestStubEndpoints:
    def test_upload_url_returns_200(self):
        response = client.post("/api/upload-url")
        assert response.status_code == 200

    def test_upload_url_success_envelope(self):
        body = client.post("/api/upload-url").json()
        assert body["success"] is True
        assert body["error"] is None

    def test_history_returns_200(self):
        response = client.get("/api/history")
        assert response.status_code == 200

    def test_history_returns_list(self):
        body = client.get("/api/history").json()
        assert isinstance(body["data"], list)

    def test_auth_login_requires_body(self):
        # Now requires username/password body — no body → 422 Unprocessable Entity
        response = client.post("/api/auth/login")
        assert response.status_code == 422

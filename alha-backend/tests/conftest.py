import os

import pytest


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("COGNITO_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("CONSULTATIONS_TABLE", "alha-consultations")
    monkeypatch.setenv("VETS_TABLE", "alha-vets")
    monkeypatch.setenv("FARMERS_TABLE", "alha-farmers")
    monkeypatch.setenv("DISEASE_MODELS_TABLE", "alha-disease-models")
    monkeypatch.setenv("S3_IMAGE_BUCKET", "alha-images")

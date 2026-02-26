import os
import sys

import pytest

# Add alha-agent root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(autouse=True)
def agent_env(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("CONSULTATIONS_TABLE", "alha-consultations")
    monkeypatch.setenv("VETS_TABLE", "alha-vets")
    monkeypatch.setenv("FARMERS_TABLE", "alha-farmers")
    monkeypatch.setenv("DISEASE_MODELS_TABLE", "alha-disease-models")
    monkeypatch.setenv("S3_IMAGE_BUCKET", "alha-images")
    monkeypatch.setenv("CLAUDE_CODE_USE_BEDROCK", "1")

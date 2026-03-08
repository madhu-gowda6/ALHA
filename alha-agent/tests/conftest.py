import os
import sys
from unittest.mock import MagicMock

import pytest

# Stub amazon_transcribe before any module import — it's not installed in the test venv.
_amazon_transcribe_stub = MagicMock()
sys.modules.setdefault("amazon_transcribe", _amazon_transcribe_stub)
sys.modules.setdefault("amazon_transcribe.client", _amazon_transcribe_stub)
sys.modules.setdefault("amazon_transcribe.handlers", _amazon_transcribe_stub)
sys.modules.setdefault("amazon_transcribe.model", _amazon_transcribe_stub)

# Set required env vars at module level so Config() succeeds at import time
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("CONSULTATIONS_TABLE", "alha-consultations")
os.environ.setdefault("VETS_TABLE", "alha-vets")
os.environ.setdefault("FARMERS_TABLE", "alha-farmers")
os.environ.setdefault("DISEASE_MODELS_TABLE", "alha-disease-models")
os.environ.setdefault("S3_IMAGE_BUCKET", "alha-images")
os.environ.setdefault("CLAUDE_CODE_USE_BEDROCK", "1")
os.environ.setdefault("COGNITO_CLIENT_ID", "test-client-id")
os.environ.setdefault("COGNITO_USER_POOL_ID", "us-east-1_testPool")

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
    monkeypatch.setenv("COGNITO_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_testPool")

"""Pytest fixtures for AI Agent tests."""

import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_k8s_unavailable():
    """Mock Kubernetes as unavailable for most tests to avoid kubeconfig dependency."""
    with patch("k8s_collector._k8s_available", False):
        yield


@pytest.fixture
def mock_google_api_key():
    """Disable Google API key so RAG uses mock responses."""
    with patch.dict("os.environ", {"GOOGLE_API_KEY": ""}):
        yield


@pytest.fixture
def client(mock_k8s_unavailable, mock_google_api_key):
    """FastAPI test client with mocked K8s and LLM."""
    from main import app
    return TestClient(app)

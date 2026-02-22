"""API tests for main FastAPI application."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client(mock_google_api_key):
    """Client with K8s and LLM mocked (via conftest)."""
    from main import app
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_ok(self, api_client: TestClient):
        r = api_client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["service"] == "ai-devops-assistant"
        assert "k8s_connected" in data
        assert "llm_configured" in data


class TestDiagnoseEndpoint:
    """Tests for POST /diagnose."""

    def test_diagnose_success(self, api_client: TestClient):
        r = api_client.post(
            "/diagnose",
            json={
                "error_message": "Pod OOMKilled in namespace default",
                "namespace": "default",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "request_id" in data
        assert "severity" in data
        assert "error_category" in data
        assert "root_cause" in data
        assert "fix_commands" in data
        assert "explanation" in data

    def test_diagnose_requires_error_message(self, api_client: TestClient):
        r = api_client.post("/diagnose", json={})
        assert r.status_code == 422  # validation error

    def test_diagnose_with_pod_name(self, api_client: TestClient):
        r = api_client.post(
            "/diagnose",
            json={
                "error_message": "CrashLoopBackOff",
                "pod_name": "my-pod",
                "namespace": "default",
            },
        )
        # K8s mocked as unavailable, so no pod data, but diagnose still works
        assert r.status_code == 200


class TestSuggestRunbookEndpoint:
    """Tests for POST /suggest-runbook."""

    def test_suggest_runbook_success(self, api_client: TestClient):
        r = api_client.post(
            "/suggest-runbook",
            json={"error_message": "OOMKilled memory", "top_k": 2},
        )
        assert r.status_code == 200
        data = r.json()
        assert "query" in data
        assert "results" in data
        assert "total_matched" in data


class TestClusterHealthEndpoint:
    """Tests for GET /cluster-health."""

    def test_cluster_health_without_k8s(self, api_client: TestClient):
        r = api_client.get("/cluster-health")
        assert r.status_code == 200
        data = r.json()
        assert data["cluster_status"] == "UNKNOWN"
        assert "Kubernetes is not configured" in str(data.get("warnings", []))


class TestLegacyEndpoint:
    """Tests for legacy /analyze-error."""

    def test_legacy_redirects_to_diagnose(self, api_client: TestClient):
        r = api_client.post(
            "/analyze-error",
            json={"error_message": "ImagePullBackOff", "namespace": "default"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "root_cause" in data

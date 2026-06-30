"""Tests for /health, /ready, and /metrics endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert "version" in body

    def test_health_has_request_id_header(self, client: TestClient) -> None:
        response = client.get("/health")
        assert "X-Request-ID" in response.headers


class TestReadyEndpoint:
    def test_ready_ok_when_db_and_redis_healthy(self, client: TestClient) -> None:
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.aclose = AsyncMock()

        with (
            patch("app.db.session.AsyncSessionLocal", return_value=mock_session),
            patch("app.main.get_client", return_value=mock_redis),
        ):
            response = client.get("/ready")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert body["db"] == "ok"
        assert body["redis"] == "ok"

    def test_ready_503_when_db_unavailable(self, client: TestClient) -> None:
        mock_session = MagicMock()
        mock_session.__aenter__ = AsyncMock(side_effect=ConnectionError("DB down"))
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.aclose = AsyncMock()

        with (
            patch("app.db.session.AsyncSessionLocal", return_value=mock_session),
            patch("app.main.get_client", return_value=mock_redis),
        ):
            response = client.get("/ready")

        assert response.status_code == 503
        assert response.json()["db"] == "error"


class TestMetricsEndpoint:
    def test_metrics_returns_prometheus_format(self, client: TestClient) -> None:
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        # Prometheus text format always contains the HELP lines
        assert b"# HELP" in response.content or b"# TYPE" in response.content

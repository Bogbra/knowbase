import pytest
from starlette.requests import Request

from app.core import limiter as limiter_module
from app.core.limiter import _get_client_ip


def _make_request(headers: dict[str, str], client_host: str | None = "10.0.0.1") -> Request:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    scope = {
        "type": "http",
        "headers": raw_headers,
        "client": (client_host, 12345) if client_host else None,
    }
    return Request(scope)


class TestGetClientIp:
    def test_trust_disabled_ignores_headers_uses_socket_peer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(limiter_module.settings, "TRUST_PROXY_HEADERS", False)  # type: ignore[attr-defined]
        request = _make_request(
            {"X-Real-IP": "9.9.9.9", "X-Forwarded-For": "9.9.9.9, 1.1.1.1"},
            client_host="10.0.0.1",
        )
        assert _get_client_ip(request) == "10.0.0.1"

    def test_trust_disabled_no_socket_peer_returns_unknown(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(limiter_module.settings, "TRUST_PROXY_HEADERS", False)  # type: ignore[attr-defined]
        request = _make_request({}, client_host=None)
        assert _get_client_ip(request) == "unknown"

    def test_trust_enabled_prefers_x_real_ip(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(limiter_module.settings, "TRUST_PROXY_HEADERS", True)  # type: ignore[attr-defined]
        request = _make_request(
            {"X-Real-IP": "203.0.113.7", "X-Forwarded-For": "203.0.113.7, 10.0.0.1"}
        )
        assert _get_client_ip(request) == "203.0.113.7"

    def test_trust_enabled_spoofed_xff_uses_rightmost_hop(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A client can set X-Forwarded-For to anything; only the last hop,
        appended by the trusted proxy itself, is safe to key rate limits on."""
        monkeypatch.setattr(limiter_module.settings, "TRUST_PROXY_HEADERS", True)  # type: ignore[attr-defined]
        request = _make_request(
            {"X-Forwarded-For": "1.2.3.4, 5.6.7.8, 10.0.0.1"},
        )
        # 10.0.0.1 is the rightmost entry — the hop appended by the trusted proxy.
        # 1.2.3.4 is attacker-controlled and must never be selected.
        assert _get_client_ip(request) == "10.0.0.1"

    def test_trust_enabled_no_headers_falls_back_to_socket_peer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(limiter_module.settings, "TRUST_PROXY_HEADERS", True)  # type: ignore[attr-defined]
        request = _make_request({}, client_host="10.0.0.1")
        assert _get_client_ip(request) == "10.0.0.1"

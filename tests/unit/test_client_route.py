"""Unit tests for HonchoClient SSH-tunnel route selection."""

from usr.plugins.honcho_shared_memory.backend.client import HonchoClient
from usr.plugins.honcho_shared_memory.backend import client as client_module


class FakeSecretsManager:
    def __init__(self, secrets):
        self._secrets = secrets

    def load_secrets(self):
        return self._secrets


class FakeTunnel:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.started = False

    def start(self):
        self.started = True
        return "http://127.0.0.1:12345"


class TestHonchoClientRoute:
    def test_direct_route_when_endpoint_reachable(self, monkeypatch):
        monkeypatch.setattr(
            client_module, "endpoint_reachable", lambda host, port, timeout=1.5: True
        )
        client = HonchoClient(
            base_url="http://example.com:8000",
            api_key="secret",
            workspace_id="default",
        )
        client._ensure_route()
        assert client.effective_base_url == "http://example.com:8000"
        assert client._tunnel is None

    def test_tunnel_route_when_endpoint_unreachable(self, monkeypatch):
        monkeypatch.setattr(
            client_module, "endpoint_reachable", lambda host, port, timeout=1.5: False
        )
        fake_tunnel = FakeTunnel()
        monkeypatch.setattr(client_module, "SshTunnel", lambda **kwargs: fake_tunnel)
        monkeypatch.setattr(
            client_module,
            "get_secrets_manager",
            lambda: FakeSecretsManager({"AUTH_LOGIN": "user", "AUTH_PASSWORD": "pass"}),
        )
        client = HonchoClient(
            base_url="http://example.com:8000",
            api_key="secret",
            workspace_id="default",
        )
        client._ensure_route()
        assert client.effective_base_url == "http://127.0.0.1:12345"
        assert client._tunnel is fake_tunnel
        assert fake_tunnel.started is True

    def test_no_tunnel_for_loopback(self, monkeypatch):
        fake_tunnel = FakeTunnel()
        monkeypatch.setattr(client_module, "SshTunnel", lambda **kwargs: fake_tunnel)
        client = HonchoClient(
            base_url="http://127.0.0.1:8000",
            api_key="secret",
            workspace_id="default",
        )
        client._ensure_route()
        assert client.effective_base_url == "http://127.0.0.1:8000"
        assert client._tunnel is None
        assert fake_tunnel.started is False

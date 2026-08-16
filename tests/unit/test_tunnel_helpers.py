"""Unit tests for Honcho SSH tunnel helpers."""

import socket

from usr.plugins.honcho_shared_memory.backend.tunnel import (
    endpoint_reachable,
    split_base_url,
)


class TestSplitBaseUrl:
    def test_url_with_scheme(self):
        host, port, loopback = split_base_url("http://example.com:8000")
        assert host == "example.com"
        assert port == 8000
        assert loopback is False

    def test_url_without_scheme_default_port(self):
        host, port, loopback = split_base_url("192.168.1.10")
        assert host == "192.168.1.10"
        assert port == 80
        assert loopback is False

    def test_https_default_port(self):
        host, port, loopback = split_base_url("https://example.com")
        assert host == "example.com"
        assert port == 443
        assert loopback is False

    def test_localhost_loopback(self):
        host, port, loopback = split_base_url("http://127.0.0.1:8000")
        assert host == "127.0.0.1"
        assert port == 8000
        assert loopback is True


class TestEndpointReachable:
    def test_matches_endpoint_reachable_true(self, monkeypatch):
        calls = []

        def fake_create_connection(address, timeout=None):
            calls.append((address, timeout))

            class Dummy:
                def __enter__(self):
                    return self

                def __exit__(self, *exc):
                    return False

            return Dummy()

        monkeypatch.setattr(socket, "create_connection", fake_create_connection)

        assert endpoint_reachable("127.0.0.1", 8000) is True
        assert calls == [(("127.0.0.1", 8000), 1.5)]

    def test_matches_endpoint_reachable_true_unreachable(self, monkeypatch):
        def fake_create_connection(address, timeout=None):
            raise OSError("connection timed out")

        monkeypatch.setattr(socket, "create_connection", fake_create_connection)

        assert endpoint_reachable("192.168.1.10", 8000) is False

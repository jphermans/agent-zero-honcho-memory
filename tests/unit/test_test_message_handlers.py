"""Unit tests for the settings test-message API handlers."""

import asyncio
from unittest.mock import patch

from usr.plugins.honcho_shared_memory.api.write_test_message import (
    WriteTestMessageHandler,
)
from usr.plugins.honcho_shared_memory.api.read_test_message import (
    ReadTestMessageHandler,
)


class FakeSecretsManager:
    def __init__(self, secrets):
        self._secrets = secrets

    def load_secrets(self):
        return self._secrets


class FakeMessage:
    def __init__(self, id, content):
        self.id = id
        self.content = content


class FakeSession:
    def __init__(self, messages):
        self._messages = messages
        self.deleted = False

    def messages(self, **kwargs):
        page = type("Page", (), {"items": self._messages})()
        return page

    def delete(self):
        self.deleted = True


class FakeHonchoApi:
    def __init__(self, session):
        self._session = session

    def session(self, id):
        return self._session


class FakeHonchoClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.client = FakeHonchoApi(None)
        self.written = []

    def add_messages(self, session_id, peer_id, messages, skip_metadata=False):
        self.written.append(
            {
                "session_id": session_id,
                "peer_id": peer_id,
                "messages": messages,
                "skip_metadata": skip_metadata,
            }
        )
        return [FakeMessage("msg-1", messages[0]["content"])]


CONFIG = {
    "honcho_base_url": "http://example.com:8000",
    "honcho_workspace_id": "hermes",
    "honcho_peer_id": "hermes",
    "agent_id": "agent-zero-0",
    "request_timeout": 30,
    "max_retries": 3,
    "tls_verify": True,
    "agent_compatibility": "hermes-agent",
    "redact_secrets_before_store": True,
}


def patch_environment(monkeypatch, config=None):
    monkeypatch.setattr(
        "usr.plugins.honcho_shared_memory.api.write_test_message.get_plugin_config",
        lambda plugin: config or CONFIG,
    )
    monkeypatch.setattr(
        "usr.plugins.honcho_shared_memory.api.write_test_message.get_secrets_manager",
        lambda: FakeSecretsManager({"HONCHO_DB_PASSWORD": "secret"}),
    )
    monkeypatch.setattr(
        "usr.plugins.honcho_shared_memory.api.read_test_message.get_plugin_config",
        lambda plugin: config or CONFIG,
    )
    monkeypatch.setattr(
        "usr.plugins.honcho_shared_memory.api.read_test_message.get_secrets_manager",
        lambda: FakeSecretsManager({"HONCHO_DB_PASSWORD": "secret"}),
    )


class TestWriteTestMessageHandler:
    def test_write_uses_dedicated_session_and_fixed_prefix(self, monkeypatch):
        patch_environment(monkeypatch)
        fake_client = FakeHonchoClient()
        monkeypatch.setattr(
            "usr.plugins.honcho_shared_memory.api.write_test_message.HonchoClient",
            lambda **kwargs: fake_client,
        )

        handler = WriteTestMessageHandler(None, None)
        result = asyncio.run(handler.process({}, None))

        assert result["success"] is True
        assert result["test_id"] == "msg-1"
        assert len(fake_client.written) == 1
        item = fake_client.written[0]
        assert item["session_id"] == "a0-plugin-test"
        assert item["messages"][0]["content"].startswith("Honcho test from A0")
        assert item["skip_metadata"] is True

    def test_missing_password_fails_safely(self, monkeypatch):
        monkeypatch.setattr(
            "usr.plugins.honcho_shared_memory.api.write_test_message.get_plugin_config",
            lambda plugin: CONFIG,
        )
        monkeypatch.setattr(
            "usr.plugins.honcho_shared_memory.api.write_test_message.get_secrets_manager",
            lambda: FakeSecretsManager({}),
        )

        handler = WriteTestMessageHandler(None, None)
        result = asyncio.run(handler.process({}, None))

        assert result["success"] is False
        assert "not configured" in result["message"].lower()


class TestReadTestMessageHandler:
    def test_read_latest_test_message_and_cleanup(self, monkeypatch):
        patch_environment(monkeypatch)
        session = FakeSession(
            [
                FakeMessage("old", "Honcho test from A0 — 2026-08-15T10:00:00+00:00"),
                FakeMessage("new", "Honcho test from A0 — 2026-08-16T03:17:00+00:00"),
            ]
        )
        fake_client = FakeHonchoClient()
        fake_client.client = FakeHonchoApi(session)
        monkeypatch.setattr(
            "usr.plugins.honcho_shared_memory.api.read_test_message.HonchoClient",
            lambda **kwargs: fake_client,
        )

        handler = ReadTestMessageHandler(None, None)
        result = asyncio.run(handler.process({}, None))

        assert result["success"] is True
        assert result["content"] == "Honcho test from A0 — 2026-08-16T03:17:00+00:00"
        assert result["cleaned_up"] is True
        assert session.deleted is True

    def test_no_test_message_returns_safe_error(self, monkeypatch):
        patch_environment(monkeypatch)
        session = FakeSession([FakeMessage("x", "regular message")])
        fake_client = FakeHonchoClient()
        fake_client.client = FakeHonchoApi(session)
        monkeypatch.setattr(
            "usr.plugins.honcho_shared_memory.api.read_test_message.HonchoClient",
            lambda **kwargs: fake_client,
        )

        handler = ReadTestMessageHandler(None, None)
        result = asyncio.run(handler.process({}, None))

        assert result["success"] is False
        assert "no test message" in result["message"].lower()

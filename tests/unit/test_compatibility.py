"""Unit tests for agent compatibility mode (Hermes-Agent and OpenClaw)."""

import pytest
from usr.plugins.honcho_shared_memory.backend.memory import _is_delegated_mode, generate_metadata


class TestIsDelegatedMode:
    def test_agent_zero(self):
        assert _is_delegated_mode({"agent_compatibility": "agent-zero"}) is False

    def test_hermes_agent(self):
        assert _is_delegated_mode({"agent_compatibility": "hermes-agent"}) is True

    def test_openclaw(self):
        assert _is_delegated_mode({"agent_compatibility": "openclaw"}) is True

    def test_missing_key_means_agent_zero(self):
        assert _is_delegated_mode({}) is False

    def test_unknown_value_means_agent_zero(self):
        assert _is_delegated_mode({"agent_compatibility": "unknown"}) is False


class TestGenerateMetadata:
    def test_agent_zero_full_metadata(self):
        meta = generate_metadata(
            agent_id="a0",
            workspace_id="ws",
            peer_id="p",
            session_id="s",
            role="user",
            tags=["tag1"],
            source_message_id="msg-1",
            compatibility="agent-zero",
        )
        assert "plugin_version" in meta
        assert "agent_id" in meta
        assert "workspace_id" in meta
        assert "peer_id" in meta
        assert "session_id" in meta
        assert "tags" in meta
        assert "source_message_id" in meta
        assert meta["agent_id"] == "a0"

    def test_hermes_minimal_metadata(self):
        meta = generate_metadata(
            agent_id="a0",
            workspace_id="ws",
            peer_id="p",
            session_id="s",
            role="user",
            tags=["tag1"],
            source_message_id="msg-1",
            compatibility="hermes-agent",
        )
        assert "plugin_version" not in meta
        assert "agent_id" not in meta
        assert "workspace_id" not in meta
        assert "peer_id" not in meta
        assert "session_id" not in meta
        assert "tags" not in meta
        assert "source_message_id" not in meta
        assert "role" in meta
        assert "stored_at" in meta
        assert meta["role"] == "user"

    def test_openclaw_minimal_metadata(self):
        meta = generate_metadata(
            agent_id="a0",
            workspace_id="ws",
            peer_id="p",
            session_id="s",
            role="assistant",
            compatibility="openclaw",
        )
        assert "plugin_version" not in meta
        assert "agent_id" not in meta
        assert "role" in meta
        assert "stored_at" in meta
        assert meta["role"] == "assistant"

    def test_default_compatibility_is_agent_zero(self):
        meta = generate_metadata(
            agent_id="a0",
            workspace_id="ws",
            peer_id="p",
            session_id="s",
            role="user",
        )
        assert "agent_id" in meta
        assert meta["agent_id"] == "a0"

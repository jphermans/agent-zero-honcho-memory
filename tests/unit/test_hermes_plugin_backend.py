"""Unit tests for the Hermes plugin backend (hermes-plugin/backend.py).

The Hermes plugin folder name contains a hyphen, so it is loaded with
importlib (not `import`).
"""

import importlib.util
from pathlib import Path

import pytest

HERMES_PLUGIN_DIR = Path(__file__).resolve().parents[2] / "hermes-plugin"

spec = importlib.util.spec_from_file_location(
    "hermes_backend", HERMES_PLUGIN_DIR / "backend.py"
)
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


class TestRedactText:
    def test_redact_authorization(self):
        result = backend.redact_text("Authorization: Bearer abc123")
        assert "abc123" not in result
        assert "***" in result

    def test_redact_token(self):
        result = backend.redact_text("api_key=sk-12345xyz")
        assert "sk-12345xyz" not in result

    def test_redact_password(self):
        result = backend.redact_text("password: super-secret")
        assert "super-secret" not in result

    def test_no_change_plain_text(self):
        text = "Hello world, plain text stays as-is."
        assert backend.redact_text(text) == text


class TestValidateURL:
    def test_simple_url(self):
        assert backend.validate_url("http://example.com:8000") == "http://example.com:8000"

    def test_adds_scheme(self):
        assert backend.validate_url("localhost:8000") == "http://localhost:8000"

    def test_rejects_file_scheme(self):
        with pytest.raises(ValueError):
            backend.validate_url("file:///etc/passwd")

    def test_trailing_slash_stripped(self):
        assert backend.validate_url("http://example.com:8000/") == "http://example.com:8000"


class TestValidateIdentifier:
    def test_valid(self):
        assert backend.validate_identifier("hermes-0", "agent") == "hermes-0"

    def test_rejects_space(self):
        with pytest.raises(ValueError):
            backend.validate_identifier("bad id", "agent")


class TestGenerateMetadata:
    def test_hermes_mode_minimal(self):
        meta = backend.generate_metadata(
            agent_id="hermes",
            workspace_id="hermes",
            peer_id="hermes",
            session_id="default",
            role="assistant",
            compatibility="hermes-agent",
        )
        assert meta["role"] == "assistant"
        assert "stored_at" in meta
        assert "plugin_version" not in meta

    def test_agent_zero_mode_full(self):
        meta = backend.generate_metadata(
            agent_id="agent-zero-0",
            workspace_id="hermes",
            peer_id="hermes",
            session_id="default",
            role="user",
            content_type="memory",
            tags=["a", "b"],
            compatibility="agent-zero",
        )
        assert meta["agent_id"] == "agent-zero-0"
        assert meta["tags"] == "a,b"
        assert meta["content_type"] == "memory"


class TestIsStoreableContent:
    def test_empty_rejected(self):
        assert backend.is_storeable_content("", {}) is False

    def test_too_long_rejected(self):
        config = {"max_stored_content_length": 10}
        assert backend.is_storeable_content("x" * 100, config) is False

    def test_credential_like_rejected(self):
        config = {"max_stored_content_length": 10000}
        assert backend.is_storeable_content("api_key=abc123", config) is False

    def test_normal_accepted(self):
        config = {"max_stored_content_length": 10000}
        assert backend.is_storeable_content("De klant prefereert maandag.", config) is True


class TestFormatMemoryContext:
    def test_empty(self):
        assert backend.format_memory_context([]) == ""

    def test_renders_agent_and_content(self):
        class FakeMem:
            content = "hello memory"
            metadata = {"agent_id": "agent-zero-0", "stored_at": "2026-08-16T00:00:00"}

        out = backend.format_memory_context([FakeMem()])
        assert "Memory from agent-zero-0" in out
        assert "hello memory" in out

    def test_truncates_to_max_chars(self):
        class FakeMem:
            content = "y" * 5000
            metadata = {}

        out = backend.format_memory_context([FakeMem()], max_chars=200)
        assert len(out) <= 250

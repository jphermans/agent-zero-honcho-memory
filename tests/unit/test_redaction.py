"""Unit tests for redaction utilities."""

import pytest
from usr.plugins.honcho_shared_memory.backend.redaction import (
    redact_text, redact_headers, contains_likely_secret,
)


class TestRedactText:

    def test_redact_authorization(self):
        text = "Authorization: Bearer abc123"
        result = redact_text(text)
        assert "abc123" not in result
        assert "REDACTED" in result

    def test_redact_password(self):
        text = "password: super-secret"
        result = redact_text(text)
        assert "super-secret" not in result
        assert "REDACTED" in result

    def test_redact_postgres_uri(self):
        text = "postgresql://user:password@host/db"
        result = redact_text(text)
        assert "password" not in result or "REDACTED" in result

    def test_no_change_plain_text(self):
        text = "Hello world"
        assert redact_text(text) == "Hello world"

    def test_redact_private_key(self):
        text = "-----BEGIN RSA PRIVATE KEY-----\nkeydata\n-----END RSA PRIVATE KEY-----"
        result = redact_text(text)
        assert "-----BEGIN RSA PRIVATE KEY-----" not in result
        assert "REDACTED" in result


class TestRedactHeaders:

    def test_redact_authorization(self):
        headers = {"Authorization": "Bearer abc123", "Content-Type": "application/json"}
        result = redact_headers(headers)
        assert result["Authorization"] == "[REDACTED]"
        assert result["Content-Type"] == "application/json"

    def test_empty(self):
        assert redact_headers({}) == {}


class TestContainsLikelySecret:

    def test_api_key(self):
        assert contains_likely_secret("api_key=abc123") is True

    def test_bearer_token(self):
        assert contains_likely_secret("Authorization: bearer token") is True

    def test_plain_text(self):
        assert contains_likely_secret("Hello world") is False

    def test_private_key(self):
        assert contains_likely_secret("-----BEGIN PRIVATE KEY-----") is True

"""Unit tests for validation utilities."""

import pytest
from usr.plugins.honcho_shared_memory.backend.validation import (
    validate_url,
    validate_identifier,
    validate_int_range,
    validate_agent_ids,
)
from usr.plugins.honcho_shared_memory.backend.exceptions import ValidationError


class TestValidateURL:
    def test_simple_url(self):
        assert validate_url("http://example.com:8000") == "http://example.com:8000"

    def test_adds_scheme(self):
        assert validate_url("localhost:8000") == "http://localhost:8000"

    def test_rejects_file_scheme(self):
        with pytest.raises(ValidationError):
            validate_url("file:///etc/passwd")

    def test_rejects_ftp(self):
        with pytest.raises(ValidationError):
            validate_url("ftp://example.com")

    def test_rejects_empty(self):
        with pytest.raises(ValidationError):
            validate_url("")

    def test_rejects_control_chars(self):
        with pytest.raises(ValidationError):
            validate_url("http://test.com\x00")

    def test_accepts_https(self):
        assert validate_url("https://example.com") == "https://example.com"


class TestValidateIdentifier:
    def test_simple_id(self):
        assert validate_identifier("my-workspace", "name") == "my-workspace"

    def test_strips_whitespace(self):
        assert validate_identifier("  foo  ", "name") == "foo"

    def test_rejects_empty_after_strip(self):
        with pytest.raises(ValidationError):
            validate_identifier("   ", "name")

    def test_rejects_whitespace_inside(self):
        with pytest.raises(ValidationError):
            validate_identifier("my id", "name")

    def test_rejects_control_chars(self):
        with pytest.raises(ValidationError):
            validate_identifier("id\x01", "name")

    def test_allows_dots(self):
        assert validate_identifier("agent.v1", "name") == "agent.v1"


class TestValidateIntRange:
    def test_valid(self):
        assert validate_int_range(5, 1, 10, "timeout") == 5

    def test_below_min(self):
        with pytest.raises(ValidationError):
            validate_int_range(0, 1, 10, "timeout")

    def test_above_max(self):
        with pytest.raises(ValidationError):
            validate_int_range(11, 1, 10, "timeout")

    def test_non_int(self):
        with pytest.raises(ValidationError):
            validate_int_range("abc", 1, 10, "timeout")


class TestValidateAgentIDs:
    def test_empty_list(self):
        validate_agent_ids([], "agent-zero-0")  # should not raise

    def test_valid(self):
        validate_agent_ids(["agent-zero-0", "agent-zero-1"], "agent-zero-0")

    def test_duplicate(self):
        with pytest.raises(ValidationError):
            validate_agent_ids(["agent-zero-0", "agent-zero-0"], "agent-zero-0")

    def test_empty_entry(self):
        with pytest.raises(ValidationError):
            validate_agent_ids(["agent-zero-0", ""], "agent-zero-0")

    def test_whitespace_entry(self):
        with pytest.raises(ValidationError):
            validate_agent_ids(["agent-zero-0", "   "], "agent-zero-0")

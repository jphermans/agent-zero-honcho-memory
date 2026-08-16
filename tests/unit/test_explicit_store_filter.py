"""Unit tests for explicit store content filtering."""

from usr.plugins.honcho_shared_memory.backend.memory import (
    is_storeable_content,
)


class TestIsStoreableContent:
    def test_allows_short_explicit_memory(self):
        config = {
            "redact_secrets_before_store": True,
            "max_stored_content_length": 10000,
        }
        assert is_storeable_content("remember this", config) is True

    def test_rejects_empty_content(self):
        config = {
            "redact_secrets_before_store": True,
            "max_stored_content_length": 10000,
        }
        assert is_storeable_content("   ", config) is False

    def test_rejects_likely_secret(self):
        config = {
            "redact_secrets_before_store": True,
            "max_stored_content_length": 10000,
        }
        assert (
            is_storeable_content("my api_key=super-secret-value for service", config)
            is False
        )

    def test_respects_max_length(self):
        config = {
            "redact_secrets_before_store": True,
            "max_stored_content_length": 10,
        }
        assert is_storeable_content("abcdefghij", config) is True
        assert is_storeable_content("abcdefghijk", config) is False

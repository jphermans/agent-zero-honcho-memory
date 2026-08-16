"""Unit tests for automatic memory storage selection."""

from usr.plugins.honcho_shared_memory.backend.memory import (
    select_auto_store_messages,
)


class TestSelectAutoStoreMessages:
    def test_disabled_returns_empty_list(self):
        config = {
            "auto_store": False,
            "store_user_messages": True,
            "store_assistant_messages": True,
            "redact_secrets_before_store": True,
            "max_stored_content_length": 10000,
        }
        result = select_auto_store_messages(
            "Please remember the project architecture decision", "Done", config
        )
        assert result == []

    def test_stores_worthy_user_message(self):
        config = {
            "auto_store": True,
            "store_user_messages": True,
            "store_assistant_messages": False,
            "redact_secrets_before_store": True,
            "max_stored_content_length": 10000,
        }
        result = select_auto_store_messages(
            "Please remember that the database must use PostgreSQL",
            "Understood",
            config,
        )
        assert result == [
            {
                "role": "user",
                "content": "Please remember that the database must use PostgreSQL",
            }
        ]

    def test_skips_trivial_user_message(self):
        config = {
            "auto_store": True,
            "store_user_messages": True,
            "store_assistant_messages": True,
            "redact_secrets_before_store": True,
            "max_stored_content_length": 10000,
        }
        result = select_auto_store_messages("hi", "hello", config)
        assert result == []

    def test_stores_assistant_when_enabled(self):
        config = {
            "auto_store": True,
            "store_user_messages": False,
            "store_assistant_messages": True,
            "redact_secrets_before_store": True,
            "max_stored_content_length": 10000,
        }
        result = select_auto_store_messages(
            "hello", "The authentication module lives in backend/auth.py", config
        )
        assert result == [
            {
                "role": "assistant",
                "content": "The authentication module lives in backend/auth.py",
            }
        ]

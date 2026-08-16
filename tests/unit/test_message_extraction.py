"""Unit tests for extracting clean text from framework message content."""

from usr.plugins.honcho_shared_memory.backend.memory import (
    extract_user_message_text,
)


class TestExtractUserMessageText:
    def test_handles_plain_string_content(self):
        assert extract_user_message_text("  hello world  ") == "hello world"

    def test_extracts_nested_user_message_key(self):
        content = {"user_message": "  remember this  ", "attachments": []}
        assert extract_user_message_text(content) == "remember this"

    def test_extracts_message_key_fallback(self):
        content = {"message": "just an intervention", "system_message": ""}
        assert extract_user_message_text(content) == "just an intervention"

    def test_handles_list_of_strings(self):
        content = ["part one", "part two"]
        assert extract_user_message_text(content) == "part one\npart two"

    def test_handles_empty_and_unknown_content(self):
        assert extract_user_message_text(None) == ""
        assert extract_user_message_text({"data": 1}) == ""

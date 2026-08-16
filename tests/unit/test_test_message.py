"""Unit tests for test-message write/read helpers."""

from datetime import datetime, timezone

from usr.plugins.honcho_shared_memory.backend.test_message import (
    TEST_SESSION_ID,
    build_test_message_content,
    extract_latest_test_content,
    is_test_message,
)


class TestBuildTestMessageContent:
    def test_contains_fixed_plugin_prefix(self):
        content = build_test_message_content(datetime(2026, 8, 16, tzinfo=timezone.utc))
        assert content.startswith("Honcho test from A0")

    def test_includes_timestamp(self):
        stamp = datetime(2026, 8, 16, 3, 17, 0, tzinfo=timezone.utc)
        content = build_test_message_content(stamp)
        assert "2026-08-16T03:17:00" in content

    def test_can_use_current_time_without_argument(self):
        content = build_test_message_content()
        assert content.startswith("Honcho test from A0")


class TestIsTestMessage:
    def test_true_for_test_message(self):
        assert (
            is_test_message("Honcho test from A0 — 2026-08-16T03:17:00+00:00") is True
        )

    def test_true_ignores_leading_whitespace(self):
        assert is_test_message("   Honcho test from A0 — timestamp") is True

    def test_false_for_other_content(self):
        assert is_test_message("Please remember this preference") is False

    def test_false_for_non_string(self):
        assert is_test_message(None) is False


class TestExtractLatestTestContent:
    class FakeMessage:
        def __init__(self, content, created_at):
            self.content = content
            self.created_at = created_at

    def test_extracts_latest_by_created_at(self):
        older = self.FakeMessage(
            "Honcho test from A0 — 2026-08-15T10:00:00+00:00",
            "2026-08-15T10:00:00+00:00",
        )
        newer = self.FakeMessage(
            "Honcho test from A0 — 2026-08-16T03:17:00+00:00",
            "2026-08-16T03:17:00+00:00",
        )
        assert extract_latest_test_content([older, newer]) == newer.content

    def test_ignores_non_test_messages(self):
        normal = self.FakeMessage("hello", "2026-08-16T05:00:00+00:00")
        test = self.FakeMessage(
            "Honcho test from A0 — 2026-08-15T10:00:00+00:00",
            "2026-08-15T10:00:00+00:00",
        )
        assert extract_latest_test_content([normal, test]) == test.content

    def test_returns_none_when_no_test_message(self):
        normal = self.FakeMessage("hello", "2026-08-16T05:00:00+00:00")
        assert extract_latest_test_content([normal]) is None

    def test_handles_dict_messages(self):
        messages = [
            {
                "content": "Honcho test from A0 — 2026-08-15T10:00:00+00:00",
                "created_at": "2026-08-15T10:00:00+00:00",
            },
            {"content": "other", "created_at": "2026-08-16T05:00:00+00:00"},
        ]
        assert (
            extract_latest_test_content(messages)
            == "Honcho test from A0 — 2026-08-15T10:00:00+00:00"
        )


class TestTestSessionId:
    def test_stable_dedicated_session_id(self):
        assert TEST_SESSION_ID == "a0-plugin-test"

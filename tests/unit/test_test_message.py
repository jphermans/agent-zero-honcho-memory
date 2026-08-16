"""Unit tests for test-message write/read helpers."""

from datetime import datetime, timezone

from usr.plugins.honcho_shared_memory.backend.test_message import (
    TEST_SESSION_PREFIX,
    build_test_message_content,
    build_test_session_id,
    extract_latest_test_content,
    find_latest_test_session,
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


class TestBuildTestSessionId:
    def test_session_id_uses_dedicated_prefix(self):
        stamp = datetime(2026, 8, 16, 13, 30, 38, tzinfo=timezone.utc)
        session_id = build_test_session_id(stamp)
        assert session_id.startswith(TEST_SESSION_PREFIX)
        assert session_id == "a0-plugin-test-20260816133038000000"

    def test_different_timestamps_produce_different_ids(self):
        first = build_test_session_id(
            datetime(2026, 8, 16, 13, 30, 38, tzinfo=timezone.utc)
        )
        second = build_test_session_id(
            datetime(2026, 8, 16, 13, 30, 39, tzinfo=timezone.utc)
        )
        assert first != second

    def test_prefix_never_equals_legacy_fixed_session(self):
        assert TEST_SESSION_PREFIX != "a0-plugin-test"


class TestFindLatestTestSession:
    class FakeSession:
        def __init__(self, id, created_at):
            self.id = id
            self.created_at = created_at

    def test_returns_newest_test_session_only(self):
        older = self.FakeSession(
            "a0-plugin-test-20260816130000000000",
            "2026-08-16T13:00:00+00:00",
        )
        newer = self.FakeSession(
            "a0-plugin-test-20260816130100000000",
            datetime(2026, 8, 16, 13, 1, 0, tzinfo=timezone.utc),
        )
        assert find_latest_test_session([older, newer]) is newer

    def test_ignores_production_and_hermes_sessions(self):
        normal = self.FakeSession(
            "default",
            "2026-08-16T14:00:00+00:00",
        )
        hermes = self.FakeSession(
            "agent-main-discord-thread-1234",
            "2026-08-16T15:00:00+00:00",
        )
        assert find_latest_test_session([normal, hermes]) is None

    def test_ignores_legacy_fixed_test_session(self):
        legacy = self.FakeSession("a0-plugin-test", "2026-08-16T15:00:00+00:00")
        assert find_latest_test_session([legacy]) is None

    def test_handles_dict_sessions(self):
        sessions = [
            {
                "id": "a0-plugin-test-20260816130000000000",
                "created_at": "2026-08-16T13:00:00+00:00",
            },
            {
                "id": "a0-plugin-test-20260816130100000000",
                "created_at": "2026-08-16T13:01:00+00:00",
            },
        ]
        result = find_latest_test_session(sessions)
        assert result["id"] == "a0-plugin-test-20260816130100000000"

"""Helpers for the settings-page write/read test message.

The test message uses a dedicated, timestamped Honcho session so it does not
pollute normal conversation data. Each write gets a fresh session ID because
Honcho does not allow reusing a deleted session ID. The read endpoint selects
the newest dedicated test session and removes only that session, never
production sessions such as ``default`` or sessions owned by Hermes Agent.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

TEST_PREFIX = "Honcho test from A0"
TEST_SESSION_PREFIX = "a0-plugin-test-"


def build_test_session_id(now: Optional[datetime] = None) -> str:
    """Build a sortable, timestamped dedicated test-session ID."""
    if now is None:
        now = datetime.now(timezone.utc)
    return f"{TEST_SESSION_PREFIX}{now.strftime('%Y%m%d%H%M%S%f')}"


def build_test_message_content(now: Optional[datetime] = None) -> str:
    """Build a deterministic, timestamped test message."""
    if now is None:
        now = datetime.now(timezone.utc)
    stamp = now.isoformat(timespec="seconds")
    return f"{TEST_PREFIX} — {stamp}"


def is_test_message(content: Any) -> bool:
    """Return True when content is a settings test message."""
    return isinstance(content, str) and content.strip().startswith(TEST_PREFIX)


def extract_latest_test_content(messages: list) -> Optional[str]:
    """Return the content of the newest test message among messages."""
    candidates: list[tuple[str, str]] = []
    for message in messages:
        if isinstance(message, dict):
            content = message.get("content")
            created_at_raw = message.get("created_at")
        else:
            content = getattr(message, "content", None)
            created_at_raw = getattr(message, "created_at", None)
        if not isinstance(content, str) or not is_test_message(content):
            continue
        if isinstance(created_at_raw, datetime):
            created_at = created_at_raw.isoformat()
        else:
            created_at = str(created_at_raw or "")
        candidates.append((created_at, content))

    if not candidates:
        return None

    # ISO 8601 timestamps sort correctly as strings; oldest first.
    candidates.sort(key=lambda item: item[0])
    return candidates[-1][1]


def _session_id(session: Any) -> str:
    """Return the session ID from a dict or SDK session object."""
    if isinstance(session, dict):
        return str(session.get("id") or "")
    return str(getattr(session, "id", "") or "")


def find_latest_test_session(sessions: list) -> Optional[Any]:
    """Return the newest dedicated test session.

    Only sessions with the ``a0-plugin-test-`` prefix are considered. The
    legacy fixed ID ``a0-plugin-test`` and all production/Hermes sessions are
    ignored.
    """
    candidates: list[Any] = []
    for session in sessions:
        session_id = _session_id(session)
        if session_id.startswith(TEST_SESSION_PREFIX):
            candidates.append(session)

    if not candidates:
        return None

    # The timestamped portion of the ID is lexicographically sortable.
    candidates.sort(key=_session_id)
    return candidates[-1]

"""Helpers for the settings-page write/read test message.

The test message uses a dedicated Honcho session so it does not pollute
normal conversation data. The read endpoint removes the test message after
showing it to the user.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

TEST_SESSION_ID = "a0-plugin-test"
TEST_PREFIX = "Honcho test from A0"


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
            created_at = str(message.get("created_at") or "")
        else:
            content = getattr(message, "content", None)
            created_at = str(getattr(message, "created_at", None) or "")
        if not isinstance(content, str) or not is_test_message(content):
            continue
        candidates.append((created_at, content))

    if not candidates:
        return None

    # ISO 8601 timestamps sort correctly as strings; oldest first.
    candidates.sort(key=lambda item: item[0])
    return candidates[-1][1]

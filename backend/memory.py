"""Memory filtering, deduplication, context limiting, and metadata generation."""

from typing import Optional, Dict, Any, List
import hashlib
import datetime

from usr.plugins.honcho_shared_memory.backend.redaction import (
    contains_likely_secret, redact_text
)

PLUGIN_VERSION = "0.0.1"


def is_memory_worthy(content: str, role: str, config: dict) -> bool:
    """Decide whether a message content should be persisted.

    Returns False for:
    - Empty or very short content
    - Messages containing likely secrets (when redaction enabled)
    - Greetings, trivial messages
    - Tool output unless explicitly enabled
    """
    if not content or not isinstance(content, str):
        return False
    content = content.strip()
    if len(content) < 20:
        return False

    # Check length limit
    max_len = config.get("max_stored_content_length", 10000)
    if len(content) > max_len:
        return False

    # Redact secrets check
    if config.get("redact_secrets_before_store", True):
        if contains_likely_secret(content):
            return False

    # Role-based filtering
    if role == "user" and not config.get("store_user_messages", False):
        return False
    if role == "assistant" and not config.get("store_assistant_messages", False):
        return False
    if role == "tool" and not config.get("store_tool_output", False):
        return False

    # Skip trivial greetings
    trivial_patterns = ["hello", "hi", "hey", "good morning", "good afternoon", "ok", "thanks", "thank you"]
    lower = content.lower().strip()
    if lower in trivial_patterns:
        return False

    return True


def generate_metadata(
    agent_id: str,
    workspace_id: str,
    peer_id: str,
    session_id: str,
    role: str,
    content_type: str = "memory",
    tags: Optional[List[str]] = None,
    sharing_scope: str = "single",
    source_message_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate deterministic metadata for a stored memory."""
    now = datetime.datetime.utcnow().isoformat()
    meta = {
        "plugin_version": PLUGIN_VERSION,
        "agent_id": agent_id,
        "workspace_id": workspace_id,
        "peer_id": peer_id,
        "session_id": session_id,
        "role": role,
        "content_type": content_type,
        "sharing_scope": sharing_scope,
        "stored_at": now,
    }
    if tags:
        meta["tags"] = ",".join(tags)
    if source_message_id:
        meta["source_message_id"] = source_message_id
    return meta


def deduplicate_messages(messages: list, content: str, threshold: float = 0.9) -> bool:
    """Check if the given content closely matches any existing message.

    Uses a simple hash-based approach for speed. Returns True if duplicate.
    """
    if not messages:
        return False
    new_hash = _content_hash(content)
    for msg in messages:
        existing = getattr(msg, 'content', '') or str(msg)
        if _content_similarity(new_hash, _content_hash(existing)) >= threshold:
            return True
    return False


def _content_hash(content: str) -> str:
    """Stable content hash for dedup."""
    normalized = content.strip().lower()[:1000]
    return hashlib.sha256(normalized.encode()).hexdigest()


def _content_similarity(h1: str, h2: str) -> float:
    """Simple hex-char overlap ratio as a fast similarity proxy."""
    if h1 == h2:
        return 1.0
    overlap = sum(a == b for a, b in zip(h1, h2))
    return overlap / len(h1)


def format_memory_context(
    memories: list,
    max_chars: int = 8000,
) -> str:
    """Format retrieved memories into a concise markdown block for context injection.

    Respects character limit and prioritizes more relevant (earlier) results.
    """
    if not memories:
        return ""

    lines = []
    total = 0
    for mem in memories:
        content = getattr(mem, 'content', str(mem))
        meta = getattr(mem, 'metadata', {})
        agent = meta.get("agent_id", "unknown") if isinstance(meta, dict) else "unknown"
        ts = meta.get("stored_at", "") if isinstance(meta, dict) else ""

        header = f"### Memory from {agent}"
        if ts:
            header += f" ({ts[:10]})"
        body = redact_text(content[:2000])

        entry = f"{header}\n{body}\n"
        if total + len(entry) > max_chars:
            remaining = max_chars - total - 30
            if remaining > 100:
                entry = f"{header}\n{body[:remaining]}...\n"
                lines.append(entry)
            break
        lines.append(entry)
        total += len(entry)

    return "\n".join(lines)


def sanitize_for_storage(content: str, config: dict) -> str:
    """Prepare content for storage: truncate and optionally redact."""
    max_len = config.get("max_stored_content_length", 10000)
    if len(content) > max_len:
        content = content[:max_len]
    if config.get("redact_secrets_before_store", True):
        content = redact_text(content)
    return content

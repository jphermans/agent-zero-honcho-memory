"""Memory filtering, deduplication, context limiting, and metadata generation."""

from typing import Optional, Dict, Any, List
import hashlib
import datetime

from usr.plugins.honcho_shared_memory.backend.redaction import (
    contains_likely_secret,
    redact_text,
)

PLUGIN_VERSION = "0.0.7"


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
    trivial_patterns = [
        "hello",
        "hi",
        "hey",
        "good morning",
        "good afternoon",
        "ok",
        "thanks",
        "thank you",
    ]
    lower = content.lower().strip()
    if lower in trivial_patterns:
        return False

    return True


# Represents the current compatibility mode
def _is_delegated_mode(config: dict) -> bool:
    """Check if we're delegating metadata to the other agent's conventions."""
    comp = config.get("agent_compatibility", "agent-zero")
    return comp in ("hermes-agent", "openclaw")


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
    compatibility: str = "agent-zero",
) -> Dict[str, Any]:
    """Generate deterministic metadata for a stored memory.

    In delegated modes (hermes-agent, openclaw), returns minimal metadata
    to match the conventions of those agents (no custom metadata fields).
    """
    now = datetime.datetime.utcnow().isoformat()
    if compatibility in ("hermes-agent", "openclaw"):
        # Minimal metadata matching native Honcho conventions
        meta = {
            "role": role,
            "stored_at": now,
        }
        return meta

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
        existing = getattr(msg, "content", "") or str(msg)
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


def extract_user_message_text(content) -> str:
    """Extract clean user text from A0 message content structures."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [extract_user_message_text(item) for item in content]
        return "\n".join(part for part in parts if part).strip()
    if isinstance(content, dict):
        for key in ("user_message", "message", "text", "content"):
            value = content.get(key)
            if value is not None and value != "":
                extracted = extract_user_message_text(value)
                if extracted:
                    return extracted
        return ""
    return ""


def is_storeable_content(content: str, config: dict) -> bool:
    """Return True when explicit memory content is safe to store.

    Explicit storage does not depend on role-based auto-store flags, but it
    still respects length limits and secret redaction.
    """
    if not content or not isinstance(content, str):
        return False
    content = content.strip()
    if not content:
        return False

    max_len = config.get("max_stored_content_length", 10000)
    if len(content) > max_len:
        return False

    if config.get("redact_secrets_before_store", True):
        if contains_likely_secret(content):
            return False

    return True


def select_auto_store_messages(
    user_content: str,
    assistant_content: str,
    config: dict,
) -> list:
    """Select the user/assistant messages that should be auto-stored.

    Respects auto_store plus the role-specific storage flags. Content is
    sanitized before being returned.
    """
    if not config.get("auto_store", False):
        return []

    selected = []
    role_content = {
        "user": (user_content, "store_user_messages"),
        "assistant": (assistant_content, "store_assistant_messages"),
    }
    for role, (content, flag_key) in role_content.items():
        if not config.get(flag_key, False):
            continue
        if is_memory_worthy(content, role, config):
            selected.append(
                {
                    "role": role,
                    "content": sanitize_for_storage(content, config),
                }
            )
    return selected


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
        content = getattr(mem, "content", str(mem))
        meta = getattr(mem, "metadata", {})
        agent = meta.get("agent_id", "memory") if isinstance(meta, dict) else "memory"
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

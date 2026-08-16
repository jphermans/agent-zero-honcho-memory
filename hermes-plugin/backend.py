"""Shared backend for the Hermes Honcho Shared Memory plugin.

Ported from the Agent Zero plugin (``agent-zero-honcho-memory``) so that
both agents use identical conventions (workspace, peer, session, metadata)
and therefore share the same memory namespace.

Differences from the Agent Zero version:
- No Agent Zero secret store: configuration comes from environment variables.
- No SSH tunnel fallback: direct connection only (LAN/remote via base URL).
- Same SDK (honcho-ai), same storage/search semantics, same redaction.
"""

from __future__ import annotations

import datetime
import hashlib
import logging
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

PLUGIN_VERSION = "0.0.7"


# ---------------------------------------------------------------------------
# Configuration (environment variables with sensible defaults)
# ---------------------------------------------------------------------------

def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default).strip() or default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


def load_config() -> Dict[str, Any]:
    """Load plugin configuration from environment variables."""
    return {
        "honcho_base_url": _env_str("HONCHO_BASE_URL", "http://localhost:8000"),
        "honcho_workspace_id": _env_str("HONCHO_WORKSPACE_ID", "hermes"),
        "honcho_peer_id": _env_str("HONCHO_PEER_ID", "hermes"),
        "agent_id": _env_str("HONCHO_AGENT_ID", "hermes"),
        "api_key": _env_str("HONCHO_API_KEY", ""),
        "request_timeout": _env_int("HONCHO_TIMEOUT", 30),
        "max_retries": _env_int("HONCHO_MAX_RETRIES", 3),
        "retrieval_limit": _env_int("HONCHO_RETRIEVAL_LIMIT", 10),
        "retrieval_max_chars": _env_int("HONCHO_RETRIEVAL_MAX_CHARS", 8000),
        "max_stored_content_length": _env_int("HONCHO_MAX_STORED_LENGTH", 10000),
        "redact_secrets_before_store": _env_bool("HONCHO_REDACT", True),
        "tls_verify": _env_bool("HONCHO_TLS_VERIFY", True),
    }


def validate_url(url: str) -> str:
    """Validate and normalize a base URL (http/https only)."""
    url = (url or "").strip()
    if not url:
        raise ValueError("URL is required")
    if "://" not in url:
        url = "http://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")
    if re.search(r"[\x00-\x1f\x7f]", url):
        raise ValueError("URL contains control characters")
    if not parsed.path or parsed.path == "/":
        return f"{parsed.scheme}://{parsed.netloc}"
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


def validate_identifier(value: str, field_name: str) -> str:
    """Validate workspace/peer/agent identifiers (ASCII alnum, _ - .)."""
    if not value or not isinstance(value, str):
        raise ValueError(f"{field_name} is required")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise ValueError(
            f"{field_name} may only contain letters, digits, underscore, hyphen, dot"
        )
    return value


# ---------------------------------------------------------------------------
# Redaction (ported from the Agent Zero plugin)
# ---------------------------------------------------------------------------

REDACT_PATTERNS: List[tuple] = [
    (re.compile(r"(?i)authorization\s*[:=]\s*.+$"), "Authorization: ***"),
    (
        re.compile(r"(?:bearer|token|api[-_]?key)\s*[:=]?\s*[^\s,;]+", re.IGNORECASE),
        "token: [REDACTED]",
    ),
    (
        re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*[^\s,;]+", re.IGNORECASE),
        "password: [REDACTED]",
    ),
    (
        re.compile(r"postgres(?:ql)?://[^@]*:([^@]+)@", re.IGNORECASE),
        lambda m: m.group(0).replace(m.group(1), "[REDACTED]"),
    ),
    (
        re.compile(r"mongodb(?:\+srv)?://[^@]*:([^@]+)@", re.IGNORECASE),
        lambda m: m.group(0).replace(m.group(1), "[REDACTED]"),
    ),
    (
        re.compile(r"redis://[^@]*:([^@]+)@", re.IGNORECASE),
        lambda m: m.group(0).replace(m.group(1), "[REDACTED]"),
    ),
]


def redact_text(text: str) -> str:
    """Redact likely secrets from arbitrary text."""
    if not text:
        return text or ""
    result = text
    for pattern, replacement in REDACT_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


# ---------------------------------------------------------------------------
# Memory helpers (ported from the Agent Zero plugin)
# ---------------------------------------------------------------------------

def _content_hash(content: str) -> str:
    normalized = content.strip().lower()[:1000]
    return hashlib.sha256(normalized.encode()).hexdigest()


def _content_similarity(h1: str, h2: str) -> float:
    if h1 == h2:
        return 1.0
    if not h1 or not h2:
        return 0.0
    longer, shorter = (h1, h2) if len(h1) >= len(h2) else (h2, h1)
    if not shorter:
        return 0.0
    return len(longer) - sum(1 for a, b in zip(longer, shorter) if a != b) / len(shorter)


def deduplicate_messages(messages: list, content: str, threshold: float = 0.9) -> bool:
    """Check if content closely matches any existing message."""
    if not messages:
        return False
    new_hash = _content_hash(content)
    for msg in messages:
        existing = getattr(msg, "content", "") or str(msg)
        if _content_similarity(new_hash, _content_hash(existing)) >= threshold:
            return True
    return False


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
    compatibility: str = "hermes-agent",
) -> Dict[str, Any]:
    """Generate deterministic metadata for a stored memory.

    In delegated mode (``hermes-agent``), metadata is minimal so it matches
    native Honcho conventions and stays readable by the Agent Zero plugin
    in its Hermes-compatibility mode.
    """
    now = datetime.datetime.utcnow().isoformat()
    if compatibility in ("hermes-agent", "openclaw"):
        meta: Dict[str, Any] = {"role": role, "stored_at": now}
        if agent_id:
            meta["agent_id"] = agent_id
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


def is_storeable_content(content: str, config: dict) -> bool:
    """Basic safety filter: non-empty, within length, no obvious secrets."""
    if not content or not content.strip():
        return False
    max_len = config.get("max_stored_content_length", 10000)
    if len(content) > max_len:
        return False
    # Refuse storing what looks like a credential dump
    lower = content.lower()
    if re.search(r"(?m)^(api[_-]?key|password|secret|token)\s*[=:]", lower):
        return False
    return True


def sanitize_for_storage(content: str, config: dict) -> str:
    """Prepare content for storage: truncate and optionally redact."""
    max_len = config.get("max_stored_content_length", 10000)
    if len(content) > max_len:
        content = content[:max_len]
    if config.get("redact_secrets_before_store", True):
        content = redact_text(content)
    return content


def format_memory_context(memories: list, max_chars: int = 8000) -> str:
    """Format retrieved memories into a concise markdown block."""
    if not memories:
        return ""
    lines: List[str] = []
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


def extract_user_message_text(content) -> str:
    """Extract plain text from a message object (dict or string)."""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        for key in ("text", "content", "message"):
            val = content.get(key)
            if isinstance(val, str):
                return val
        return str(content)
    return str(content)


# ---------------------------------------------------------------------------
# Honcho client (ported from the Agent Zero plugin, no SSH tunnel)
# ---------------------------------------------------------------------------

class HonchoClient:
    """Wraps the Honcho SDK with consistent error handling."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        workspace_id: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        tls_verify: bool = True,
    ):
        self.base_url = validate_url(base_url)
        self.workspace_id = validate_identifier(workspace_id, "workspace")
        self.timeout = timeout
        self.max_retries = max_retries
        self._api_key = api_key
        self._tls_verify = tls_verify
        self._client = None

    def _build(self):
        try:
            from honcho import Honcho
        except ImportError as exc:
            raise RuntimeError(
                "honcho-ai is not installed in the Hermes environment. "
                "Run: <hermes-venv>/bin/pip install 'honcho-ai>=2.0.0'"
            ) from exc

        kwargs = {}
        if not self._tls_verify:
            import httpx

            kwargs["http_client"] = httpx.Client(verify=False)
        return Honcho(
            api_key=self._api_key or None,
            base_url=self.base_url,
            workspace_id=self.workspace_id,
            timeout=self.timeout,
            max_retries=self.max_retries,
            **kwargs,
        )

    @property
    def client(self):
        if self._client is None:
            self._client = self._build()
        return self._client

    def test_connection(self) -> Dict[str, Any]:
        """Test connectivity without modifying production data."""
        diag: Dict[str, Any] = {}
        try:
            client = self.client
            diag["reachability"] = "ok"
            diag["workspace"] = self.workspace_id
            peer = client.peer(id="__test_peer__")
            diag["peer"] = "ok"
            # Unique session per run: avoids stale-cache conflicts with
            # previously deleted test sessions.
            session_id = f"__test_session__{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
            session = client.session(id=session_id, peers=[peer])
            msgs = session.add_messages(
                messages=[{"peer_id": "__test_peer__", "content": "plugin connection test"}]
            )
            diag["write"] = "ok"
            session.messages(size=1)
            diag["read"] = "ok"
            return {"success": True, "message": "Connection successful", "diagnostics": diag}
        except Exception as exc:
            return {"success": False, "message": redact_text(str(exc)), "diagnostics": diag}

    def get_or_create_session(self, session_id: str, peer_id: str):
        client = self.client
        peer = client.peer(id=peer_id)
        return client.session(id=session_id, peers=[peer])

    def add_messages(
        self,
        session_id: str,
        peer_id: str,
        messages: List[Dict[str, Any]],
        skip_metadata: bool = False,
    ):
        session = self.get_or_create_session(session_id, peer_id)
        formatted = []
        for m in messages:
            entry: Dict[str, Any] = {"peer_id": peer_id, "content": m.get("content", "")}
            if not skip_metadata and m.get("metadata"):
                entry["metadata"] = m["metadata"]
            formatted.append(entry)
        return session.add_messages(messages=formatted)

    def search_messages(
        self,
        session_id: str,
        query: str,
        peer_id: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        skip_filters: bool = False,
    ):
        session = self.get_or_create_session(session_id, peer_id)
        effective_filters = filters if not skip_filters else None
        try:
            return session.search(query=query, filters=effective_filters, limit=limit)
        except Exception as exc:
            err_msg = str(exc)
            if "not allowed to be filtered" in err_msg or "does not exist" in err_msg:
                logger.warning("Honcho filter rejected, retrying without filters: %s", err_msg)
                return session.search(query=query, filters=None, limit=limit)
            raise

    def get_session_messages(
        self,
        session_id: str,
        peer_id: str,
        page: int = 1,
        size: int = 50,
        reverse: bool = True,
        filters: Optional[Dict[str, Any]] = None,
    ):
        session = self.get_or_create_session(session_id, peer_id)
        try:
            return session.messages(filters=filters, page=page, size=size, reverse=reverse)
        except Exception as exc:
            err_msg = str(exc)
            if "not allowed to be filtered" in err_msg or "does not exist" in err_msg:
                logger.warning("Honcho filter rejected on messages(), retrying without filters: %s", err_msg)
                return session.messages(filters=None, page=page, size=size, reverse=reverse)
            raise

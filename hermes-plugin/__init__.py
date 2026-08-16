"""Hermes plugin: Honcho Shared Memory.

Shared persistent memory for Hermes through a self-hosted Honcho database.
Compatible with the Agent Zero plugin of the same name (same workspace,
peer, session and metadata conventions), so both agents read and write the
same memory namespace.

Configuration is read from environment variables (defaults in parentheses):

- HONCHO_BASE_URL        (http://localhost:8000)
- HONCHO_WORKSPACE_ID    (hermes)
- HONCHO_PEER_ID         (hermes)
- HONCHO_AGENT_ID        (hermes)
- HONCHO_API_KEY         (empty; only needed if your Honcho uses auth)
- HONCHO_TIMEOUT         (30)
- HONCHO_MAX_RETRIES     (3)
- HONCHO_RETRIEVAL_LIMIT (10)
- HONCHO_RETRIEVAL_MAX_CHARS (8000)
- HONCHO_MAX_STORED_LENGTH   (10000)
- HONCHO_REDACT          (true)
- HONCHO_TLS_VERIFY      (true)

Every tool returns a JSON string.
"""

from __future__ import annotations

import datetime
import json
from typing import List, Optional

from . import backend
from .backend import (
    HonchoClient,
    deduplicate_messages,
    extract_user_message_text,
    format_memory_context,
    generate_metadata,
    is_storeable_content,
    load_config,
    redact_text,
    sanitize_for_storage,
)

PLUGIN_VERSION = backend.PLUGIN_VERSION


def _ok(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _err(message: str, icon: str = "❌") -> str:
    return json.dumps({"success": False, "icon": icon, "error": redact_text(message)}, ensure_ascii=False)


def honcho_memory_test() -> str:
    """Test the connection to the Honcho server. Returns diagnostics.

    Checks reachability, workspace access, and a temporary write/read cycle
    using a throwaway test session. Safe to run; never touches real data.

    Returns a JSON string.
    """
    config = load_config()
    client = HonchoClient(
        base_url=config["honcho_base_url"],
        api_key=config["api_key"],
        workspace_id=config["honcho_workspace_id"],
        timeout=config["request_timeout"],
        max_retries=config["max_retries"],
        tls_verify=config["tls_verify"],
    )
    try:
        result = client.test_connection()
        if result.get("success"):
            return _ok({
                "success": True,
                "icon": "✅",
                "message": "Connection successful",
                "workspace": config["honcho_workspace_id"],
                "peer": config["honcho_peer_id"],
                "diagnostics": result.get("diagnostics", {}),
            })
        return _err(result.get("message", "Connection failed"))
    except Exception as exc:
        return _err(str(exc))


def honcho_memory_store(
    content: str,
    memory_type: str = "memory",
    tags: Optional[str] = None,
    session_id: str = "default",
    sharing_scope: str = "single",
    source_message_id: Optional[str] = None,
) -> str:
    """Explicitly store a memory in the shared Honcho database.

    Use this when the user asks to remember something, or when you learn a
    durable fact (preference, decision, project detail) worth persisting.

    Args:
        content: The text to store.
        memory_type: Type of memory (memory, preference, decision, project, fact).
        tags: Comma-separated tags for later filtering (optional).
        session_id: Honcho session to write to (default 'default').
        sharing_scope: 'single' (this agent) or 'shared' (all agents).
        source_message_id: Optional source message id for provenance.

    Returns a JSON string.
    """
    config = load_config()
    if not content or not content.strip():
        return _err("No content to store.")
    if not is_storeable_content(content, config):
        return _err("Content was filtered: empty, too long, or contains a likely secret.")

    content = sanitize_for_storage(content, config)

    client = HonchoClient(
        base_url=config["honcho_base_url"],
        api_key=config["api_key"],
        workspace_id=config["honcho_workspace_id"],
        timeout=config["request_timeout"],
        max_retries=config["max_retries"],
        tls_verify=config["tls_verify"],
    )
    try:
        metadata = generate_metadata(
            agent_id=config["agent_id"],
            workspace_id=config["honcho_workspace_id"],
            peer_id=config["honcho_peer_id"],
            session_id=session_id,
            role="assistant",
            content_type=memory_type,
            tags=tags.split(",") if tags else None,
            sharing_scope=sharing_scope,
            source_message_id=source_message_id,
            compatibility="hermes-agent",
        )
        msgs = client.add_messages(
            session_id=session_id,
            peer_id=config["honcho_peer_id"],
            messages=[{"content": content, "metadata": metadata}],
        )
        msg_id = msgs[0].id if msgs else "unknown"
        return _ok({
            "success": True,
            "icon": "💾",
            "message": "Memory stored successfully.",
            "record_id": msg_id,
            "workspace": config["honcho_workspace_id"],
            "peer": config["honcho_peer_id"],
            "agent": config["agent_id"],
            "session": session_id,
            "content_type": memory_type,
        })
    except Exception as exc:
        return _err(f"Failed to store memory: {exc}")


def honcho_memory_search(
    query: str,
    limit: Optional[int] = None,
    agent_filter: Optional[str] = None,
    session_filter: Optional[str] = None,
    tags: Optional[str] = None,
) -> str:
    """Search shared memories in Honcho for a query.

    Use this to recall what you or another agent (e.g. Agent Zero) stored
    earlier — preferences, decisions, project context.

    Args:
        query: Natural-language or keyword search text.
        limit: Max results (default from config, max 50).
        agent_filter: Restrict to a specific agent_id (optional).
        session_filter: Restrict to a specific session (default 'default').
        tags: Comma-separated tags to filter on (optional).

    Returns a JSON string with matching memories.
    """
    config = load_config()
    if not query or not query.strip():
        return _err("No search query provided.")

    client = HonchoClient(
        base_url=config["honcho_base_url"],
        api_key=config["api_key"],
        workspace_id=config["honcho_workspace_id"],
        timeout=config["request_timeout"],
        max_retries=config["max_retries"],
        tls_verify=config["tls_verify"],
    )
    try:
        filters = {}
        if tags:
            filters["tags"] = tags
        if agent_filter:
            filters["agent_id"] = agent_filter
        if session_filter:
            filters["session_id"] = session_filter

        use_limit = int(limit) if limit else config["retrieval_limit"]
        results = client.search_messages(
            session_id=session_filter or "default",
            query=query,
            peer_id=config["honcho_peer_id"],
            limit=min(use_limit, 50),
            filters=filters if filters else None,
            skip_filters=True,
        )
        if not results:
            return _ok({
                "success": True,
                "icon": "🔍",
                "message": "No matching memories found.",
                "count": 0,
                "memories": [],
            })

        max_chars = config["retrieval_max_chars"]
        formatted = format_memory_context(results, max_chars=max_chars)
        return _ok({
            "success": True,
            "icon": "🔍",
            "message": f"Found {len(results)} matching memories:",
            "count": len(results),
            "memories": formatted,
        })
    except Exception as exc:
        return _err(f"Failed to search memories: {exc}")


def honcho_memory_context(
    query: str,
    limit: Optional[int] = None,
    agent_filter: Optional[str] = None,
    session_filter: Optional[str] = None,
) -> str:
    """Retrieve shared context from Honcho relevant to a topic.

    Like honcho_memory_search, but returns a context block designed to be injected
    into your working context before answering a question.

    Args:
        query: The topic or question to retrieve context for.
        limit: Max results (default from config, max 50).
        agent_filter: Restrict to a specific agent_id (optional).
        session_filter: Restrict to a specific session (default 'default').

    Returns a JSON string.
    """
    config = load_config()
    if not query or not query.strip():
        return _err("No query provided for context retrieval.")

    client = HonchoClient(
        base_url=config["honcho_base_url"],
        api_key=config["api_key"],
        workspace_id=config["honcho_workspace_id"],
        timeout=config["request_timeout"],
        max_retries=config["max_retries"],
        tls_verify=config["tls_verify"],
    )
    try:
        filters = {}
        if agent_filter:
            filters["agent_id"] = agent_filter
        if session_filter:
            filters["session_id"] = session_filter

        use_limit = int(limit) if limit else config["retrieval_limit"]
        results = client.search_messages(
            session_id=session_filter or "default",
            query=query,
            peer_id=config["honcho_peer_id"],
            limit=min(use_limit, 50),
            filters=filters if filters else None,
            skip_filters=True,
        )
        if not results:
            return _ok({
                "success": True,
                "icon": "🧠",
                "message": "No relevant context found.",
                "count": 0,
                "context": "",
            })

        max_chars = config["retrieval_max_chars"]
        context_text = format_memory_context(results, max_chars=max_chars)
        return _ok({
            "success": True,
            "icon": "🧠",
            "message": "Retrieved shared context:",
            "count": len(results),
            "context": f"## Honcho Shared Context\n\n{context_text}",
        })
    except Exception as exc:
        return _err(f"Failed to retrieve context: {exc}")


def honcho_memory_latest(limit: int = 5, session_filter: Optional[str] = None) -> str:
    """List the most recent messages stored in the shared Honcho session.

    Useful to see what has been stored recently (by any compatible agent).

    Args:
        limit: Max messages to return (default 5, max 50).
        session_filter: Session to read (default 'default').

    Returns a JSON string.
    """
    config = load_config()
    client = HonchoClient(
        base_url=config["honcho_base_url"],
        api_key=config["api_key"],
        workspace_id=config["honcho_workspace_id"],
        timeout=config["request_timeout"],
        max_retries=config["max_retries"],
        tls_verify=config["tls_verify"],
    )
    try:
        msgs = client.get_session_messages(
            session_id=session_filter or "default",
            peer_id=config["honcho_peer_id"],
            page=1,
            size=max(1, min(int(limit) if limit else 5, 50)),
            reverse=True,
        )
        items = []
        for m in msgs:
            meta = getattr(m, "metadata", {}) or {}
            created = getattr(m, "created_at", "") or meta.get("stored_at", "")
            if isinstance(created, datetime.datetime):
                created = created.isoformat()
            items.append({
                "id": getattr(m, "id", "?"),
                "role": meta.get("role", "?"),
                "agent": meta.get("agent_id", "?"),
                "created_at": str(created)[:19],
                "content": redact_text((getattr(m, "content", "") or "")[:300]),
            })
        return _ok({
            "success": True,
            "icon": "📜",
            "message": f"Latest {len(items)} messages:",
            "count": len(items),
            "messages": items,
        })
    except Exception as exc:
        return _err(f"Failed to list messages: {exc}")

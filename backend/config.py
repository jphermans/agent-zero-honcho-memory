"""Configuration model for Honcho Shared Memory plugin."""

import re
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator

from usr.plugins.honcho_shared_memory.backend.validation import (
    validate_url,
    validate_identifier,
    validate_int_range,
)


class HonchoConfig(BaseModel):
    """Validated plugin configuration."""

    honcho_base_url: str = Field(
        default="http://localhost:8000", description="Base URL for the Honcho API"
    )
    honcho_workspace_id: str = Field(
        default="default", description="Honcho workspace ID or name"
    )
    honcho_peer_id: str = Field(default="agent-zero", description="Honcho peer ID")
    agent_id: str = Field(default="agent-zero-0", description="Current agent ID")
    request_timeout: int = Field(
        default=30, ge=1, le=300, description="Request timeout in seconds"
    )
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry count")
    retrieval_limit: int = Field(
        default=10, ge=1, le=100, description="Max results per retrieval"
    )
    retrieval_max_chars: int = Field(
        default=8000,
        ge=100,
        le=50000,
        description="Max characters of memory content to inject",
    )
    agent_compatibility: Literal["agent-zero", "hermes-agent", "openclaw"] = Field(
        default="agent-zero",
        description="Agent compatibility mode for cross-agent memory sharing",
    )
    minimum_relevance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum relevance threshold (Honcho semantic distance; 0 means disabled)",
    )
    connection_mode: Literal["local", "lan", "remote"] = Field(
        default="local",
        description="Connection mode: local, lan, or remote/private server",
    )
    tls_verify: bool = Field(
        default=True, description="Enable TLS certificate verification"
    )
    multi_agent_mode: bool = Field(
        default=False, description="Enable multi-agent shared memory"
    )
    allowed_agent_ids: List[str] = Field(
        default_factory=list,
        description="Allowed agent IDs when multi-agent mode is enabled",
    )

    # Memory automation flags
    auto_retrieval: bool = Field(
        default=True, description="Automatically retrieve memories before each response"
    )
    auto_store: bool = Field(
        default=False, description="Automatically store memories after each response"
    )
    store_user_messages: bool = Field(default=False, description="Store user messages")
    store_assistant_messages: bool = Field(
        default=False, description="Store assistant messages"
    )
    store_tool_output: bool = Field(
        default=False, description="Store tool output messages"
    )
    redact_secrets_before_store: bool = Field(
        default=True, description="Redact likely secrets before storing"
    )
    max_stored_content_length: int = Field(
        default=10000,
        ge=100,
        le=100000,
        description="Maximum stored content length in characters",
    )
    include_shared_agent_memories: bool = Field(
        default=False,
        description="Include memories from other agents in multi-agent mode",
    )

    @field_validator("honcho_base_url")
    @classmethod
    def validate_base_url(cls, v):
        return validate_url(v)

    @field_validator("honcho_workspace_id", "honcho_peer_id", "agent_id")
    @classmethod
    def validate_ids(cls, v):
        return validate_identifier(v, "identifier")

    @field_validator("allowed_agent_ids")
    @classmethod
    def validate_allowed_agents(cls, v):
        from usr.plugins.honcho_shared_memory.backend.validation import (
            validate_agent_ids,
        )

        validate_agent_ids(v, "")
        return v


def resolve_secret_aliases(config: dict, secrets: dict) -> dict:
    """Resolve Agent Zero secret aliases in string config values.

    Example:
        config = {"honcho_base_url": "§§secret(HONCHO_BASE_URL)"}
        secrets = {"HONCHO_BASE_URL": "http://example.com:8000"}
        -> {"honcho_base_url": "http://example.com:8000"}
    """
    pattern = re.compile(r"§§secret\(([A-Za-z_][A-Za-z0-9_]*)\)")
    resolved = dict(config)
    for key, value in resolved.items():
        if not isinstance(value, str):
            continue

        def replacer(match: re.Match) -> str:
            secret_key = match.group(1).upper()
            return secrets.get(secret_key, match.group(0))

        resolved[key] = pattern.sub(replacer, value)
    return resolved


def normalize_shared_config(config: dict) -> dict:
    """Normalize plugin config before it is consumed."""
    normalized = dict(config)
    if normalized.get("multi_agent_mode"):
        current = normalized.get("agent_id", "agent-zero-0")
        allowed = list(normalized.get("allowed_agent_ids") or [])
        if not allowed and normalized.get("allowed_agent_ids_string"):
            raw_ids = normalized["allowed_agent_ids_string"]
            if isinstance(raw_ids, str):
                allowed = [
                    item.strip() for item in raw_ids.split(",") if item and item.strip()
                ]
        # deduplicate while preserving order
        seen = []
        for agent_id in allowed:
            if agent_id and agent_id not in seen:
                seen.append(agent_id)
        if current and current not in seen:
            seen.append(current)
        normalized["allowed_agent_ids"] = seen
        normalized["allowed_agent_ids_string"] = ",".join(seen)
    return normalized


def default_config_dict() -> dict:
    """Return default config as dict for default_config.yaml."""
    c = HonchoConfig()
    return c.model_dump()

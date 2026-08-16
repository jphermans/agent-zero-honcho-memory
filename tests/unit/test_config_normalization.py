"""Unit tests for config normalization and secret alias resolution."""

from usr.plugins.honcho_shared_memory.backend.config import (
    normalize_shared_config,
    resolve_secret_aliases,
)


class TestResolveSecretAliases:
    def test_resolves_existing_secret_placeholder(self):
        config = {"honcho_base_url": "§§secret(HONCHO_BASE_URL)"}
        result = resolve_secret_aliases(
            config, {"HONCHO_BASE_URL": "http://example.com:8000"}
        )
        assert result["honcho_base_url"] == "http://example.com:8000"

    def test_preserves_values_without_placeholders(self):
        config = {"agent_id": "agent-zero-0", "tls_verify": True}
        result = resolve_secret_aliases(config, {})
        assert result == config

    def test_leaves_unresolved_placeholder_in_tact(self):
        config = {"honcho_base_url": "§§secret(MISSING_SECRET)"}
        result = resolve_secret_aliases(config, {})
        assert result["honcho_base_url"] == "§§secret(MISSING_SECRET)"


class TestNormalizeSharedConfig:
    def test_uses_string_list_when_json_list_is_empty(self):
        config = {
            "honcho_base_url": "http://example.com:8000",
            "multi_agent_mode": True,
            "allowed_agent_ids": [],
            "allowed_agent_ids_string": "hermes, agent-zero-0",
            "agent_id": "agent-zero-0",
        }
        result = normalize_shared_config(config)
        assert result["allowed_agent_ids"] == ["hermes", "agent-zero-0"]

    def test_deduplicates_agent_ids(self):
        config = {
            "honcho_base_url": "http://example.com:8000",
            "multi_agent_mode": True,
            "allowed_agent_ids": ["hermes", "hermes"],
            "allowed_agent_ids_string": "",
            "agent_id": "agent-zero-0",
        }
        result = normalize_shared_config(config)
        assert result["allowed_agent_ids"] == ["hermes", "agent-zero-0"]

    def test_does_not_change_single_agent_mode(self):
        config = {
            "honcho_base_url": "http://example.com:8000",
            "multi_agent_mode": False,
            "allowed_agent_ids": [],
            "allowed_agent_ids_string": "unused",
            "agent_id": "agent-zero-0",
        }
        result = normalize_shared_config(config)
        assert result["allowed_agent_ids"] == []

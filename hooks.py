"""Plugin configuration lifecycle hooks.

- `get_plugin_config` resolves Agent Zero secret aliases before use.
- `save_plugin_config` normalizes settings before they are persisted.

Passwords are never handled here: HONCHO_DB_PASSWORD is read only from the
Agent Zero secret store by runtime code.
"""

from __future__ import annotations

from helpers.secrets import get_secrets_manager
from usr.plugins.honcho_shared_memory.backend.config import (
    normalize_shared_config,
    resolve_secret_aliases,
)


def get_plugin_config(default=None, **kwargs):
    """Return the effective config with secret aliases resolved."""
    config = dict(default or {}) if isinstance(default, dict) else {}
    try:
        secrets = get_secrets_manager().load_secrets()
        config = resolve_secret_aliases(config, secrets)
    except Exception:
        # Secret resolution is best-effort; never break plugin config loading.
        pass
    return normalize_shared_config(config)


def save_plugin_config(default=None, settings=None, **kwargs):
    """Normalize settings on save without resolving secret aliases.

    Secret aliases are deliberately preserved so no secret value is ever
    written into plugin configuration.
    """
    raw = settings if isinstance(settings, dict) else default or {}
    config = dict(raw) if isinstance(raw, dict) else {}
    return normalize_shared_config(config)

import asyncio
from unittest.mock import patch

from usr.plugins.honcho_shared_memory.api.reload_backend import ReloadBackendHandler


def test_reload_backend_triggers_framework_plugin_refresh():
    """In-process reload must use after_plugin_change with python_change."""
    handler = ReloadBackendHandler(None, None)

    with patch(
        "usr.plugins.honcho_shared_memory.api.reload_backend.plugins.after_plugin_change"
    ) as refresh:
        result = asyncio.run(handler.process({}, None))

    assert result["ok"] is True
    assert result["plugin"] == "honcho_shared_memory"
    refresh.assert_called_once_with(["honcho_shared_memory"], python_change=True)

"""Loopback-only endpoint to refresh this plugin's backend modules in-process.

Changes under ``backend/`` are not watched by the Agent Zero plugin file
watcher. This handler gives the operator a safe way to force the running
server to drop cached ``usr.plugins`` modules and reload the plugin without
restarting the whole Agent Zero process.
"""

from helpers.api import ApiHandler, Request, Response
from helpers import plugins


class ReloadBackendHandler(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def requires_api_key(cls) -> bool:
        return False

    @classmethod
    def requires_loopback(cls) -> bool:
        return True

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["POST", "GET"]

    async def process(self, input: dict, request: Request) -> dict:
        plugins.after_plugin_change(["honcho_shared_memory"], python_change=True)
        return {
            "ok": True,
            "plugin": "honcho_shared_memory",
            "python_change": True,
        }

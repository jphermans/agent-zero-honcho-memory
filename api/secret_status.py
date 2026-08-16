"""API handler to check HONCHO_DB_PASSWORD secret status."""

from helpers.api import ApiHandler
from helpers.secrets import get_secrets_manager


class SecretStatusHandler(ApiHandler):
    @classmethod
    def get_methods(cls):
        return ["GET"]

    async def process(self, input: dict, request) -> dict:
        """Check whether the HONCHO_DB_PASSWORD secret is configured."""
        secrets = get_secrets_manager()
        all_secrets = secrets.load_secrets()
        password = all_secrets.get("HONCHO_DB_PASSWORD", "")
        if password:
            return {"configured": True, "message": "Secret is configured."}
        else:
            return {
                "configured": False,
                "message": "Secret HONCHO_DB_PASSWORD is not set.",
            }

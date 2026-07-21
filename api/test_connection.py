"""API handler to test Honcho connection."""

from helpers.api import ApiHandler
from helpers.plugins import get_plugin_config
from helpers.secrets import get_secrets_manager
from usr.plugins.honcho_shared_memory.backend.client import HonchoClient
from usr.plugins.honcho_shared_memory.backend.redaction import redact_text


class TestConnectionHandler(ApiHandler):

    async def process(self, input: dict, request) -> dict:
        """Test connectivity to the configured Honcho server."""
        config = get_plugin_config("honcho_shared_memory")
        if not config:
            return {"success": False, "message": "Plugin is not configured."}

        # Get password from secrets
        secrets = get_secrets_manager()
        all_secrets = secrets.load_secrets()
        password = all_secrets.get("HONCHO_DB_PASSWORD", "")
        if not password:
            return {
                "success": False,
                "message": "Secret HONCHO_DB_PASSWORD is not configured. Please set it in Agent Zero secrets."
            }

        try:
            client = HonchoClient(
                base_url=config.get("honcho_base_url", "http://localhost:8000"),
                api_key=password,
                workspace_id=config.get("honcho_workspace_id", "default"),
                timeout=config.get("request_timeout", 30),
                max_retries=config.get("max_retries", 3),
                tls_verify=config.get("tls_verify", True),
            )

            result = client.test_connection()
            # Sanitize error messages
            if not result.get("success"):
                result["message"] = redact_text(result["message"])

            return result

        except Exception as e:
            err_msg = redact_text(str(e))
            return {"success": False, "message": f"Connection test failed: {err_msg}"}

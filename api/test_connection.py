"""API handler to test Honcho connection."""

from flask import jsonify
from helpers.api import ApiHandler
from helpers.plugins import get_plugin_config
from helpers.secrets import get_secrets_manager
from usr.plugins.honcho_shared_memory.backend.client import HonchoClient
from usr.plugins.honcho_shared_memory.backend.redaction import redact_text


class TestConnectionHandler(ApiHandler):

    def post(self):
        """Test connectivity to the configured Honcho server."""
        config = get_plugin_config("honcho_shared_memory")
        if not config:
            return jsonify({"success": False, "message": "Plugin is not configured."}), 400

        # Get password from secrets
        secrets = get_secrets_manager()
        all_secrets = secrets.load_secrets()
        password = all_secrets.get("HONCHO_DB_PASSWORD", "")
        if not password:
            return jsonify({
                "success": False,
                "message": "Secret HONCHO_DB_PASSWORD is not configured. Please set it in Agent Zero secrets."
            }), 400

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

            return jsonify(result)

        except Exception as e:
            err_msg = redact_text(str(e))
            return jsonify({"success": False, "message": f"Connection test failed: {err_msg}"}), 500


class SecretStatusHandler(ApiHandler):

    @classmethod
    def get_methods(cls):
        return ["GET"]

    def get(self):
        """Check whether the HONCHO_DB_PASSWORD secret is configured."""
        secrets = get_secrets_manager()
        all_secrets = secrets.load_secrets()
        password = all_secrets.get("HONCHO_DB_PASSWORD", "")
        if password:
            return jsonify({"configured": True, "message": "Secret is configured."})
        else:
            return jsonify({"configured": False, "message": "Secret HONCHO_DB_PASSWORD is not set."})

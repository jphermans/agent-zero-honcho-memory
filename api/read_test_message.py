"""API handler: read and clean up the dedicated Honcho test message."""

from helpers.api import ApiHandler
from helpers.plugins import get_plugin_config
from helpers.secrets import get_secrets_manager
from usr.plugins.honcho_shared_memory.backend.client import HonchoClient
from usr.plugins.honcho_shared_memory.backend.redaction import redact_text
from usr.plugins.honcho_shared_memory.backend.test_message import (
    TEST_SESSION_ID,
    extract_latest_test_content,
)


class ReadTestMessageHandler(ApiHandler):
    @classmethod
    def get_methods(cls):
        return ["POST"]

    async def process(self, input: dict, request) -> dict:
        config = get_plugin_config("honcho_shared_memory")
        if not config:
            return {"success": False, "message": "Plugin is not configured."}

        password = get_secrets_manager().load_secrets().get("HONCHO_DB_PASSWORD", "")
        if not password:
            return {
                "success": False,
                "message": "Secret HONCHO_DB_PASSWORD is not configured.",
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
            session = client.client.session(id=TEST_SESSION_ID)
            page = session.messages(reverse=True, size=50)
            messages = list(getattr(page, "items", page) or [])
            content = extract_latest_test_content(messages)

            if content is None:
                return {
                    "success": False,
                    "message": "No test message found. Use Write Test Message first.",
                    "cleaned_up": False,
                }

            # Honcho SDK has no single-message delete; removing the dedicated
            # test session is the safest cleanup and cannot touch production data.
            cleaned_up = False
            try:
                session.delete()
                cleaned_up = True
            except Exception:
                # Cleanup failure must not fail the user-facing read action.
                cleaned_up = False

            return {
                "success": True,
                "message": "Test message retrieved.",
                "session_id": TEST_SESSION_ID,
                "content": content,
                "cleaned_up": cleaned_up,
            }
        except Exception as exc:
            return {
                "success": False,
                "message": redact_text(str(exc)),
                "cleaned_up": False,
            }

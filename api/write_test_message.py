"""API handler: write a dedicated Honcho settings test message."""

from helpers.api import ApiHandler
from helpers.plugins import get_plugin_config
from helpers.secrets import get_secrets_manager
from usr.plugins.honcho_shared_memory.backend.client import HonchoClient
from usr.plugins.honcho_shared_memory.backend.redaction import redact_text
from usr.plugins.honcho_shared_memory.backend.test_message import (
    build_test_message_content,
    build_test_session_id,
)


class WriteTestMessageHandler(ApiHandler):
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
            session_id = build_test_session_id()
            content = build_test_message_content()
            created = client.add_messages(
                session_id=session_id,
                peer_id=config.get("honcho_peer_id", "default"),
                messages=[{"content": content}],
                skip_metadata=True,
            )
            test_id = ""
            if created:
                first = created[0]
                test_id = getattr(first, "id", "") or ""

            return {
                "success": True,
                "message": "Test message written.",
                "session_id": session_id,
                "test_id": test_id,
                "content": content,
            }
        except Exception as exc:
            return {
                "success": False,
                "message": redact_text(str(exc)),
            }

"""Auto-store extension: persist memory-worthy messages after a monologue."""

from helpers.extension import Extension
from agent import LoopData
from helpers import plugins
from helpers.secrets import get_secrets_manager
from usr.plugins.honcho_shared_memory.backend.client import HonchoClient
from usr.plugins.honcho_shared_memory.backend.memory import (
    _is_delegated_mode,
    extract_user_message_text,
    generate_metadata,
    select_auto_store_messages,
)
from usr.plugins.honcho_shared_memory.backend.redaction import redact_text


class HonchoAutoStore(Extension):
    """Automatically store memory-worthy user messages in Honcho.

    The plugin is intentionally conservative: only user messages are stored
    by default. Assistant/tool storage is controlled by explicit settings and
    evaluated by `select_auto_store_messages`.
    """

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if not self.agent:
            return

        config = plugins.get_plugin_config("honcho_shared_memory", self.agent)
        if not config or not config.get("auto_store", False):
            return

        user_content = ""
        if loop_data.user_message is not None:
            user_content = extract_user_message_text(loop_data.user_message.content)

        assistant_content = loop_data.last_response or ""
        selected = select_auto_store_messages(user_content, assistant_content, config)
        if not selected:
            return

        secrets = get_secrets_manager().load_secrets()
        password = secrets.get("HONCHO_DB_PASSWORD", "")
        if not password:
            self.agent.context.log.log(
                type="warning",
                heading="Honcho auto-store skipped",
                content="HONCHO_DB_PASSWORD secret is not configured.",
            )
            return

        try:
            client = HonchoClient(
                base_url=config["honcho_base_url"],
                api_key=password,
                workspace_id=config["honcho_workspace_id"],
                timeout=config.get("request_timeout", 30),
                max_retries=config.get("max_retries", 3),
                tls_verify=config.get("tls_verify", True),
            )

            is_delegated = _is_delegated_mode(config)
            stored = 0
            for item in selected:
                metadata = generate_metadata(
                    agent_id=config.get("agent_id", "agent-zero-0"),
                    workspace_id=config["honcho_workspace_id"],
                    peer_id=config["honcho_peer_id"],
                    session_id="default",
                    role=item["role"],
                    content_type="memory",
                    compatibility=config.get("agent_compatibility", "agent-zero"),
                )
                client.add_messages(
                    session_id="default",
                    peer_id=config["honcho_peer_id"],
                    messages=[{"content": item["content"], "metadata": metadata}],
                    skip_metadata=is_delegated,
                )
                stored += 1

            if stored:
                self.agent.context.log.log(
                    type="util",
                    heading=f"Stored {stored} Honcho memories",
                )

        # HonchoClient kiest de route (direct of SSH-fallback) pas bij eerste gebruik.
        except Exception as e:
            err = redact_text(str(e))
            self.agent.context.log.log(
                type="warning",
                heading="Honcho auto-store error",
                content=err,
            )

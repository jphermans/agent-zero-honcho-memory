"""Tool to explicitly store information as a shared memory in Honcho."""

from helpers.tool import Tool, Response
from helpers import plugins
from helpers.secrets import get_secrets_manager
from usr.plugins.honcho_shared_memory.backend.client import HonchoClient
from usr.plugins.honcho_shared_memory.backend.memory import (
    is_storeable_content,
    generate_metadata,
    sanitize_for_storage,
)
from usr.plugins.honcho_shared_memory.backend.redaction import redact_text


class HonchoMemoryStore(Tool):
    async def execute(
        self,
        content="",
        memory_type="memory",
        tags=None,
        session_id=None,
        source_message_id=None,
        sharing_scope="single",
        **kwargs,
    ):
        if not self.agent:
            return Response(message="No agent context available.", break_loop=False)

        set = plugins.get_plugin_config("honcho_shared_memory", self.agent)
        if not set:
            return Response(
                message="Honcho Shared Memory plugin is not configured. Please configure it in the settings.",
                break_loop=False,
            )

        if not content or not content.strip():
            return Response(message="No content to store.", break_loop=False)

        # Check whether explicit content is safe to store. Do not apply
        # role-based auto-store flags to an explicit save request.
        if not is_storeable_content(content, set):
            return Response(
                message="Content was filtered: it is empty, too long, or contains a likely secret.",
                break_loop=False,
            )

        # Sanitize
        content = sanitize_for_storage(content, set)

        # Resolve password
        secrets = get_secrets_manager()
        all_secrets = secrets.load_secrets()
        password = all_secrets.get("HONCHO_DB_PASSWORD", "")

        if not password:
            return Response(
                message="Honcho DB password secret (HONCHO_DB_PASSWORD) is not configured.",
                break_loop=False,
            )

        # Build client
        try:
            client = HonchoClient(
                base_url=set["honcho_base_url"],
                api_key=password,
                workspace_id=set["honcho_workspace_id"],
                timeout=set.get("request_timeout", 30),
                max_retries=set.get("max_retries", 3),
                tls_verify=set.get("tls_verify", True),
            )

            metadata = generate_metadata(
                agent_id=set.get("agent_id", "agent-zero-0"),
                workspace_id=set["honcho_workspace_id"],
                peer_id=set["honcho_peer_id"],
                session_id=session_id or "default",
                role="assistant",
                content_type=memory_type,
                tags=tags.split(",") if isinstance(tags, str) else tags,
                sharing_scope=sharing_scope,
                source_message_id=source_message_id,
            )

            msgs = client.add_messages(
                session_id=session_id or "default",
                peer_id=set["honcho_peer_id"],
                messages=[{"content": content, "metadata": metadata}],
            )

            msg_id = msgs[0].id if msgs else "unknown"
            result = (
                f"Memory stored successfully.\n"
                f"- Record ID: {msg_id}\n"
                f"- Workspace: {set['honcho_workspace_id']}\n"
                f"- Peer: {set['honcho_peer_id']}\n"
                f"- Agent: {set.get('agent_id', 'agent-zero-0')}\n"
                f"- Status: new"
            )
            return Response(message=result, break_loop=False)

        except Exception as e:
            err_msg = redact_text(str(e))
            return Response(
                message=f"Failed to store memory: {err_msg}",
                break_loop=False,
            )

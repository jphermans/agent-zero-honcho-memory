"""Auto-retrieval extension: inject Honcho shared memories before the agent monologue."""

from helpers.extension import Extension
from agent import LoopData
from helpers import plugins
from helpers.secrets import get_secrets_manager
from usr.plugins.honcho_shared_memory.backend.client import HonchoClient
from usr.plugins.honcho_shared_memory.backend.memory import format_memory_context
from usr.plugins.honcho_shared_memory.backend.redaction import redact_text


class HonchoAutoRetrieval(Extension):
    """Automatically search Honcho for relevant memories and inject them as context."""

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if not self.agent:
            return

        set = plugins.get_plugin_config("honcho_shared_memory", self.agent)
        if not set:
            return

        # Only run if auto-retrieval is enabled
        if not set.get("auto_retrieval", True):
            return

        # Only run on the first iteration to avoid repeated injections
        if loop_data.iteration > 0:
            return

        # Build a query from the user message
        user_instruction = (
            loop_data.user_message.output_text() if loop_data.user_message else ""
        )
        if not user_instruction or len(user_instruction.strip()) < 5:
            return

        # Resolve password
        secrets = get_secrets_manager()
        all_secrets = secrets.load_secrets()
        password = all_secrets.get("HONCHO_DB_PASSWORD", "")
        if not password:
            self.agent.context.log.log(
                type="warning",
                heading="Honcho auto-retrieval skipped",
                content="HONCHO_DB_PASSWORD secret is not configured.",
            )
            return

        try:
            client = HonchoClient(
                base_url=set["honcho_base_url"],
                api_key=password,
                workspace_id=set["honcho_workspace_id"],
                timeout=set.get("request_timeout", 30),
                max_retries=set.get("max_retries", 3),
                tls_verify=set.get("tls_verify", True),
            )

            # Build filters based on multi-agent mode and compatibility
            from usr.plugins.honcho_shared_memory.backend.memory import (
                _is_delegated_mode,
            )

            filters = {}
            is_delegated = _is_delegated_mode(set)
            if not is_delegated:
                if set.get("multi_agent_mode") and set.get(
                    "include_shared_agent_memories"
                ):
                    allowed = set.get("allowed_agent_ids", [])
                    current = set.get("agent_id", "agent-zero-0")
                    if current not in allowed:
                        allowed.append(current)
                    if allowed:
                        filters["agent_id"] = ",".join(allowed)
                else:
                    filters["agent_id"] = set.get("agent_id", "agent-zero-0")

            # Search
            results = client.search_messages(
                session_id="default",
                query=user_instruction,
                peer_id=set["honcho_peer_id"],
                limit=set.get("retrieval_limit", 10),
                filters=filters if filters else None,
                skip_filters=is_delegated,
            )

            if not results:
                return

            max_chars = set.get("retrieval_max_chars", 8000)
            context_text = format_memory_context(results, max_chars=max_chars)

            # Inject into extras
            extras = loop_data.extras_persistent
            if "honcho_memories" not in extras:
                extras["honcho_memories"] = ""
            extras["honcho_memories"] += f"\n\n## Shared Memory Context\n{context_text}"

            self.agent.context.log.log(
                type="util",
                heading=f"Retrieved {len(results)} Honcho memories",
            )

        except Exception as e:
            err = redact_text(str(e))
            self.agent.context.log.log(
                type="warning",
                heading="Honcho auto-retrieval error",
                content=err,
            )

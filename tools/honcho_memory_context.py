"""Tool to retrieve shared context from Honcho for injection before a model call."""

from helpers.tool import Tool, Response
from helpers import plugins
from helpers.secrets import get_secrets_manager
from usr.plugins.honcho_shared_memory.backend.client import HonchoClient
from usr.plugins.honcho_shared_memory.backend.memory import format_memory_context
from usr.plugins.honcho_shared_memory.backend.redaction import redact_text


class HonchoMemoryContext(Tool):

    async def execute(
        self,
        query="",
        limit=None,
        agent_filter=None,
        session_filter=None,
        **kwargs,
    ):
        if not self.agent:
            return Response(message="No agent context available.", break_loop=False)

        set = plugins.get_plugin_config("honcho_shared_memory", self.agent)
        if not set:
            return Response(
                message="Honcho Shared Memory plugin is not configured.",
                break_loop=False,
            )

        if not query or not query.strip():
            return Response(message="No query provided for context retrieval.", break_loop=False)

        secrets = get_secrets_manager()
        all_secrets = secrets.load_secrets()
        password = all_secrets.get("HONCHO_DB_PASSWORD", "")
        if not password:
            return Response(
                message="Honcho DB password secret (HONCHO_DB_PASSWORD) is not configured.",
                break_loop=False,
            )

        try:
            client = HonchoClient(
                base_url=set["honcho_base_url"],
                api_key=password,
                workspace_id=set["honcho_workspace_id"],
                timeout=set.get("request_timeout", 30),
                max_retries=set.get("max_retries", 3),
                tls_verify=set.get("tls_verify", True),
            )

            filters = {}
            if agent_filter:
                filters["agent_id"] = agent_filter
            if session_filter:
                filters["session_id"] = session_filter

            use_limit = int(limit) if limit else set.get("retrieval_limit", 10)

            results = client.search_messages(
                session_id=session_filter or "default",
                query=query,
                peer_id=set["honcho_peer_id"],
                limit=min(use_limit, 50),
                filters=filters if filters else None,
            )

            if not results:
                return Response(
                    message="No relevant context found.",
                    break_loop=False,
                )

            max_chars = set.get("retrieval_max_chars", 8000)
            context_text = format_memory_context(results, max_chars=max_chars)

            result = (
                "## Honcho Shared Context\n\n"
                f"The following shared memories may be relevant:\n\n{context_text}"
            )
            return Response(message=result, break_loop=False)

        except Exception as e:
            err_msg = redact_text(str(e))
            return Response(
                message=f"Failed to retrieve context: {err_msg}",
                break_loop=False,
            )

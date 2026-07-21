"""Honcho SDK wrapper for the plugin."""

import logging
from typing import Optional, Dict, Any, List
from honcho import Honcho
from honcho import (
    APIError,
    AuthenticationError as HonchoAuthError,
    ConnectionError as HonchoConnError,
    TimeoutError as HonchoTimeoutError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError as HonchoRateLimitError,
    ConflictError,
    ServerError,
)

from usr.plugins.honcho_shared_memory.backend.exceptions import (
    AuthenticationError, ConnectionError, TimeoutError,
    WorkspaceNotFoundError, PeerNotFoundError, APICompatibilityError,
    RateLimitError, ConfigurationError,
)

logger = logging.getLogger(__name__)


class HonchoClient:
    """Wraps the Honcho SDK for consistent error mapping and connection testing."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        workspace_id: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        tls_verify: bool = True,
    ):
        self.base_url = base_url
        self.workspace_id = workspace_id
        self.timeout = timeout
        self.max_retries = max_retries
        self._api_key = api_key
        self._client: Optional[Honcho] = None
        self._tls_verify = tls_verify

    def _get_client(self) -> Honcho:
        if self._client is None:
            self._client = Honcho(
                api_key=self._api_key,
                base_url=self.base_url,
                workspace_id=self.workspace_id,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )
            # Disable TLS verification if requested
            if not self._tls_verify:
                import httpx
                http_client = httpx.Client(verify=False)
                self._client = Honcho(
                    api_key=self._api_key,
                    base_url=self.base_url,
                    workspace_id=self.workspace_id,
                    timeout=self.timeout,
                    max_retries=self.max_retries,
                    http_client=http_client,
                )
        return self._client

    @property
    def client(self) -> Honcho:
        return self._get_client()

    def _map_error(self, err: Exception) -> Exception:
        """Map Honcho SDK exceptions to plugin exceptions."""
        if isinstance(err, HonchoAuthError):
            return AuthenticationError(str(err))
        if isinstance(err, HonchoConnError):
            return ConnectionError(str(err))
        if isinstance(err, HonchoTimeoutError):
            return TimeoutError(str(err))
        if isinstance(err, HonchoRateLimitError):
            return RateLimitError(str(err))
        if isinstance(err, NotFoundError):
            msg = str(err).lower()
            if "workspace" in msg:
                return WorkspaceNotFoundError(str(err))
            if "peer" in msg:
                return PeerNotFoundError(str(err))
            return APICompatibilityError(str(err))
        return ConnectionError(str(err))

    def test_connection(self) -> Dict[str, Any]:
        """Test connectivity without modifying production data.

        Returns a dict with keys: success, message, diagnostics.
        """
        diag = {}
        try:
            client = self.client
            # 1. Check reachability by listing workspaces (a light call)
            diag["reachability"] = "ok"
            # 2. Check workspace access
            ws = client.workspace_id
            diag["workspace"] = ws
            # 3. Try to get-or-create peer (idempotent)
            peer = client.peer(id="__test_peer__")
            diag["peer"] = "ok"
            # 4. Try basic write (temporary)
            session = client.session(id="__test_session__")
            msgs = session.add_messages(
                messages=[{"peer_id": "__test_peer__", "content": "plugin connection test"}]
            )
            diag["write"] = "ok"
            # 5. Try read
            msgs_list = session.messages(size=1)
            diag["read"] = "ok"
            return {
                "success": True,
                "message": "Connection successful",
                "diagnostics": diag,
            }
        except ConflictError:
            # __test_session__ already exists — just check it can be read
            try:
                session = client.session(id="__test_session__")
                session.messages(size=1)
                return {
                    "success": True,
                    "message": "Connection successful (test session already existed)",
                    "diagnostics": diag,
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Test read failed: {e}",
                    "diagnostics": diag,
                }
        except Exception as e:
            return {
                "success": False,
                "message": str(self._map_error(e)),
                "diagnostics": diag,
            }

    def get_or_create_session(self, session_id: str, peer_id: str):
        """Get or create a session with the given peer."""
        client = self.client
        peer = client.peer(id=peer_id)
        session = client.session(id=session_id, peers=[peer])
        return session

    def add_messages(
        self,
        session_id: str,
        peer_id: str,
        messages: List[Dict[str, Any]],
        skip_metadata: bool = False,
    ):
        """Add messages to a session. Creates session and peer if needed.

        Args:
            skip_metadata: If True, omit metadata from messages (Hermes/OpenClaw compatibility).
        """
        session = self.get_or_create_session(session_id, peer_id)
        formatted = []
        for m in messages:
            entry = {
                "peer_id": peer_id,
                "content": m.get("content", ""),
            }
            if not skip_metadata and m.get("metadata"):
                entry["metadata"] = m["metadata"]
            formatted.append(entry)
        return session.add_messages(messages=formatted)

    def search_messages(
        self,
        session_id: str,
        query: str,
        peer_id: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        skip_filters: bool = False,
    ):
        """Search messages in a session.

        Args:
            skip_filters: If True, ignore metadata filters (Hermes/OpenClaw compatibility).

        Falls back to unfiltered search when Honcho rejects unknown filter columns
        (e.g., agent_id on messages stored by Hermes or OpenClaw).
        """
        session = self.get_or_create_session(session_id, peer_id)
        effective_filters = filters if not skip_filters else None
        try:
            return session.search(query=query, filters=effective_filters, limit=limit)
        except Exception as e:
            err_msg = str(e)
            # If Honcho rejects a filter column, retry without filters
            if "not allowed to be filtered" in err_msg or "does not exist" in err_msg:
                logger.warning(
                    f"Honcho filter rejected, retrying without filters: {err_msg}"
                )
                return session.search(query=query, filters=None, limit=limit)
            raise

    def get_session_messages(
        self,
        session_id: str,
        peer_id: str,
        page: int = 1,
        size: int = 50,
        reverse: bool = True,
        filters: Optional[Dict[str, Any]] = None,
    ):
        """Retrieve messages from a session."""
        session = self.get_or_create_session(session_id, peer_id)
        return session.messages(filters=filters, page=page, size=size, reverse=reverse)

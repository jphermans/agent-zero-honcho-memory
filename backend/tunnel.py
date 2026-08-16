"""Internal SSH local-forward used when the Honcho API is not routable.

The original `honcho_base_url` stays intact in plugin configuration. At
runtime, when direct TCP to that endpoint fails and SSH credentials are
available, `HonchoClient` transparently switches to an SSH-tunneled local
endpoint. Secrets are read from the Agent Zero secret store only.
"""

from __future__ import annotations

import logging
import socket
import threading
import urllib.parse
from typing import Optional

import paramiko

logger = logging.getLogger(__name__)


class SshTunnel:
    """Own a local TCP listener and forward traffic over SSH."""

    def __init__(
        self,
        target_host: str,
        target_port: int,
        ssh_host: str,
        ssh_port: int,
        ssh_user: str,
        ssh_password: str,
        local_host: str = "127.0.0.1",
        local_port: int = 0,
    ) -> None:
        self.target_host = target_host
        self.target_port = target_port
        self.ssh_host = ssh_host
        self.ssh_port = ssh_port
        self.ssh_user = ssh_user
        self.ssh_password = ssh_password
        self.local_host = local_host
        self.local_port = local_port
        self.listener: Optional[socket.socket] = None
        self.transport: Optional[paramiko.Transport] = None
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None

    @property
    def local_url(self) -> str:
        if self.listener is None:
            return ""
        actual_port = self.listener.getsockname()[1]
        return f"http://{self.local_host}:{actual_port}"

    def start(self) -> str:
        """Start the local listener and SSH session; return local base URL."""
        if self.thread and self.thread.is_alive():
            return self.local_url

        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self.local_host, self.local_port))
        listener.listen(32)
        listener.settimeout(0.5)
        self.listener = listener

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            self.ssh_host,
            port=self.ssh_port,
            username=self.ssh_user,
            password=self.ssh_password,
            timeout=15,
            look_for_keys=False,
            allow_agent=False,
        )
        self.transport = client.get_transport()
        if not self.transport:
            client.close()
            self._close_listener()
            raise RuntimeError("SSH transport failed to initialize")

        self.thread = threading.Thread(
            target=self._accept_loop, name="honcho-ssh-tunnel", daemon=True
        )
        self.thread.start()
        return self.local_url

    def _accept_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                listener = self.listener
                if listener is None:
                    continue
                source, _ = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                if self.stop_event.is_set():
                    return
                continue
            threading.Thread(target=self._handle, args=(source,), daemon=True).start()

    def _handle(self, source: socket.socket) -> None:
        channel = None
        try:
            if not self.transport or not self.transport.is_active():
                raise RuntimeError("SSH tunnel is no longer active")
            channel = self.transport.open_channel(
                "direct-tcpip",
                (self.target_host, self.target_port),
                (self.local_host, 0),
            )
        except Exception as exc:
            logger.debug("Tunnel channel open failed: %s", exc)
            try:
                source.close()
            except OSError:
                pass
            return

        thread_a = threading.Thread(
            target=self._pump, args=(source, channel), daemon=True
        )
        thread_b = threading.Thread(
            target=self._pump, args=(channel, source), daemon=True
        )
        thread_a.start()
        thread_b.start()

    @staticmethod
    def _pump(src, dst) -> None:
        try:
            while True:
                data = src.recv(65536)
                if not data:
                    break
                dst.sendall(data)
        except OSError:
            pass
        finally:
            try:
                dst.close()
            except OSError:
                pass

    def _close_listener(self) -> None:
        if self.listener:
            try:
                self.listener.close()
            except OSError:
                pass
            self.listener = None

    def stop(self) -> None:
        self.stop_event.set()
        self._close_listener()
        if self.transport:
            try:
                self.transport.close()
            except Exception:
                pass
            self.transport = None


def endpoint_reachable(host: str, port: int, timeout: float = 1.5) -> bool:
    """Return True when a TCP connect to host:port succeeds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def split_base_url(base_url: str) -> tuple[str, int, bool]:
    """Return (host, port, is_loopback) for a base URL."""
    raw = base_url if "://" in base_url else f"http://{base_url}"
    parsed = urllib.parse.urlparse(raw)
    scheme = parsed.scheme.lower()
    port = parsed.port or (443 if scheme == "https" else 80)
    host = parsed.hostname or ""
    loopback = host in {"127.0.0.1", "localhost", "::1"}
    return host, port, loopback

"""SSH transport for FortiGate collector."""

# pyright: reportMissingModuleSource=false

import logging
import socket
from typing import Optional

import paramiko  # type: ignore[import-untyped]


logger = logging.getLogger(__name__)


class FortiGateSSHClient:
    """Small wrapper around Paramiko for FortiGate CLI access."""

    def __init__(self, host: str, port: int, username: str, password: str, timeout: int):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self._client: Optional[paramiko.SSHClient] = None

    def connect(self) -> bool:
        """Establish the SSH connection."""
        try:
            self._client = paramiko.SSHClient()
            self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False,
            )
            return True
        except paramiko.AuthenticationException as exc:
            logger.error(f"❌ SSH authentication failed for {self.host}: {exc}")
        except paramiko.SSHException as exc:
            logger.error(f"❌ SSH connection error for {self.host}: {exc}")
        except socket.timeout:
            logger.error(f"❌ SSH connection timeout for {self.host}")
        except Exception as exc:
            logger.error(f"❌ SSH error for {self.host}: {exc}")

        self._client = None
        return False

    def execute_command(self, command: str) -> Optional[str]:
        """Execute a FortiGate CLI command."""
        if not self._client:
            logger.error("SSH client not connected")
            return None

        try:
            _, stdout, stderr = self._client.exec_command(command, timeout=self.timeout)
            output = stdout.read().decode("utf-8", errors="ignore")
            error = stderr.read().decode("utf-8", errors="ignore")

            if error:
                logger.warning(f"SSH command stderr: {error}")

            return output
        except Exception as exc:
            logger.error(f"SSH command execution failed: {exc}")
            return None

    def close(self) -> None:
        """Close the SSH connection."""
        if not self._client:
            return

        try:
            self._client.close()
            logger.info(f"SSH connection closed for {self.host}")
        except Exception as exc:
            logger.warning(f"Error closing SSH connection: {exc}")
        finally:
            self._client = None

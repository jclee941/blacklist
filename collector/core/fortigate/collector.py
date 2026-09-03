"""FortiGate Collector Module.

Collects active session data from FortiGate devices via SSH or API.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from .parsers import parse_device_info, parse_policy_output, parse_session_output
from .ssh_client import FortiGateSSHClient


logger = logging.getLogger(__name__)


class FortiGateCollector:
    """
    FortiGate device collector for active session monitoring.

    Supports two collection methods:
    1. SSH CLI - Direct SSH connection to FortiGate CLI
    2. REST API - FortiGate REST API (requires API token)
    """

    DEFAULT_SSH_PORT = 22
    DEFAULT_API_PORT = 443
    SSH_TIMEOUT = 30
    API_TIMEOUT = 30

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: Optional[int] = None,
        api_token: Optional[str] = None,
        use_api: bool = False,
        vdom: str = "root",
    ):
        self.host = host
        self.username = username
        self.password = password
        self.api_token = api_token
        self.use_api = use_api
        self.vdom = vdom
        self.port = port or (self.DEFAULT_API_PORT if use_api else self.DEFAULT_SSH_PORT)
        self._ca_cert = os.getenv("FORTIGATE_CA_CERT", "")

        self._ssh_client: Optional[FortiGateSSHClient] = None
        self._authenticated = False
        self._device_info: Dict[str, Any] = {}

        logger.info(
            f"FortiGateCollector initialized for {self.host}:{self.port} (method: {'API' if use_api else 'SSH'})"
        )

    def authenticate(self) -> bool:
        """Authenticate with the FortiGate device."""
        if self.use_api:
            return self._authenticate_api()
        return self._authenticate_ssh()

    def _authenticate_ssh(self) -> bool:
        """Authenticate via SSH."""
        logger.info(f"Connecting to FortiGate {self.host} via SSH...")

        ssh_client = FortiGateSSHClient(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            timeout=self.SSH_TIMEOUT,
        )
        if not ssh_client.connect():
            return False

        self._ssh_client = ssh_client
        output = self._execute_ssh_command("get system status")
        if output and "FortiGate" in output:
            self._authenticated = True
            self._device_info = parse_device_info(output)
            logger.info(f"✅ SSH authentication successful for {self.host}")
            return True

        logger.error("❌ SSH authentication failed: unexpected response")
        return False

    def _authenticate_api(self) -> bool:
        """Authenticate via REST API."""
        if not self._ca_cert or not os.path.isfile(self._ca_cert):
            logger.error("FortiGate API trust is not configured; set FORTIGATE_CA_CERT to a readable CA bundle")
            return False
        try:
            logger.info(f"Connecting to FortiGate {self.host} via API...")
            response = requests.get(
                f"{self._base_url}/monitor/system/status",
                headers=self._api_headers(include_content_type=True),
                auth=(self.username, self.password) if not self.api_token else None,
                verify=self._ca_cert,
                timeout=self.API_TIMEOUT,
            )

            if response.status_code == 200:
                data = response.json()
                self._authenticated = True
                self._device_info = data.get("results", {})
                logger.info(f"✅ API authentication successful for {self.host}")
                return True

            logger.error(f"❌ API authentication failed: {response.status_code} - {response.text}")
            return False
        except requests.exceptions.SSLError as exc:
            logger.error(f"❌ API SSL error for {self.host}: {exc}")
            return False
        except requests.exceptions.Timeout:
            logger.error(f"❌ API connection timeout for {self.host}")
            return False
        except Exception as exc:
            logger.error(f"❌ API error for {self.host}: {exc}")
            return False

    def collect_sessions(self, filter_blocked: bool = False) -> List[Dict[str, Any]]:
        """Collect active sessions from FortiGate."""
        if not self._authenticated:
            logger.error("Not authenticated. Call authenticate() first.")
            return []

        if self.use_api:
            return self._collect_sessions_api(filter_blocked)
        return self._collect_sessions_ssh(filter_blocked)

    def _collect_sessions_ssh(self, filter_blocked: bool = False) -> List[Dict[str, Any]]:
        """Collect sessions via SSH CLI."""
        try:
            logger.info(f"Collecting sessions from {self.host} via SSH...")

            command = (
                ("diagnose sys session filter clear\ndiagnose sys session filter policy 0\ndiagnose sys session list")
                if filter_blocked
                else "diagnose sys session list"
            )

            output = self._execute_ssh_command(command)
            if not output:
                logger.warning("No session data received")
                return []

            sessions = parse_session_output(output)
            logger.info(f"Collected {len(sessions)} sessions from {self.host}")
            return sessions
        except Exception as exc:
            logger.error(f"Failed to collect sessions: {exc}")
            return []

    def _collect_sessions_api(self, filter_blocked: bool = False) -> List[Dict[str, Any]]:
        """Collect sessions via REST API."""
        try:
            logger.info(f"Collecting sessions from {self.host} via API...")
            response = requests.get(
                f"{self._base_url}/monitor/firewall/session",
                headers=self._api_headers(include_content_type=True),
                auth=(self.username, self.password) if not self.api_token else None,
                params={"vdom": self.vdom},
                verify=self._ca_cert,
                timeout=self.API_TIMEOUT,
            )

            if response.status_code != 200:
                logger.error(f"API request failed: {response.status_code}")
                return []

            sessions = response.json().get("results", [])
            normalized = []
            for session in sessions:
                normalized.append(
                    {
                        "session_id": session.get("session_id"),
                        "src_ip": session.get("src"),
                        "dst_ip": session.get("dst"),
                        "src_port": session.get("sport"),
                        "dst_port": session.get("dport"),
                        "protocol": session.get("proto_str", session.get("proto")),
                        "policy_id": session.get("policy_id"),
                        "policy_name": session.get("policy_name"),
                        "action": session.get("action", "allow"),
                        "bytes_sent": session.get("bytes_sent", 0),
                        "bytes_received": session.get("bytes_received", 0),
                        "duration": session.get("duration", 0),
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            logger.info(f"Collected {len(normalized)} sessions from {self.host}")
            return normalized
        except Exception as exc:
            logger.error(f"Failed to collect sessions via API: {exc}")
            return []

    def get_blocked_sessions(self, blacklist_ips: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get sessions involving blocked IPs."""
        if not blacklist_ips:
            logger.warning("No blacklist IPs provided")
            return []

        all_sessions = self.collect_sessions()
        blocked_sessions = []
        blacklist_set = set(blacklist_ips)

        for session in all_sessions:
            src_ip = session.get("src_ip")
            dst_ip = session.get("dst_ip")
            if src_ip in blacklist_set or dst_ip in blacklist_set:
                session["blocked_ip"] = src_ip if src_ip in blacklist_set else dst_ip
                session["direction"] = "inbound" if src_ip in blacklist_set else "outbound"
                blocked_sessions.append(session)

        logger.info(
            f"Found {len(blocked_sessions)} sessions involving blocked IPs out of {len(all_sessions)} total sessions"
        )
        return blocked_sessions

    def get_firewall_policies(self) -> List[Dict[str, Any]]:
        """Get firewall policies from FortiGate."""
        if not self._authenticated:
            logger.error("Not authenticated")
            return []

        if self.use_api:
            return self._get_policies_api()
        return self._get_policies_ssh()

    def _get_policies_ssh(self) -> List[Dict[str, Any]]:
        """Get policies via SSH."""
        try:
            output = self._execute_ssh_command("show firewall policy")
            if not output:
                return []
            return parse_policy_output(output)
        except Exception as exc:
            logger.error(f"Failed to get policies: {exc}")
            return []

    def _get_policies_api(self) -> List[Dict[str, Any]]:
        """Get policies via API."""
        try:
            response = requests.get(
                f"{self._base_url}/cmdb/firewall/policy",
                headers=self._api_headers(),
                auth=(self.username, self.password) if not self.api_token else None,
                params={"vdom": self.vdom},
                verify=self._ca_cert,
                timeout=self.API_TIMEOUT,
            )
            if response.status_code == 200:
                return response.json().get("results", [])
            return []
        except Exception as exc:
            logger.error(f"Failed to get policies via API: {exc}")
            return []

    def get_device_info(self) -> Dict[str, Any]:
        """Get device information."""
        return {
            "host": self.host,
            "port": self.port,
            "authenticated": self._authenticated,
            "connection_method": "API" if self.use_api else "SSH",
            **self._device_info,
        }

    def close(self) -> None:
        """Close the FortiGate connection."""
        if self._ssh_client:
            self._ssh_client.close()

        self._authenticated = False
        self._ssh_client = None

    def __enter__(self):
        self.authenticate()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    @property
    def _base_url(self) -> str:
        return f"https://{self.host}:{self.port}/api/v2"

    def _api_headers(self, include_content_type: bool = False) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if include_content_type:
            headers["Content-Type"] = "application/json"
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def _execute_ssh_command(self, command: str) -> Optional[str]:
        if not self._ssh_client:
            logger.error("SSH client not connected")
            return None
        return self._ssh_client.execute_command(command)


def collect_fortigate_sessions(
    devices: List[Dict[str, Any]], blacklist_ips: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Collect sessions from multiple FortiGate devices."""
    results: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "devices_checked": 0,
        "devices_success": 0,
        "devices_failed": 0,
        "total_sessions": 0,
        "blocked_sessions": 0,
        "sessions": [],
        "errors": [],
    }

    for device_config in devices:
        try:
            results["devices_checked"] += 1
            with FortiGateCollector(
                host=device_config["host"],
                username=device_config["username"],
                password=device_config["password"],
                port=device_config.get("port"),
                api_token=device_config.get("api_token"),
                use_api=device_config.get("use_api", False),
            ) as collector:
                if blacklist_ips:
                    sessions = collector.get_blocked_sessions(blacklist_ips)
                    results["blocked_sessions"] += len(sessions)
                else:
                    sessions = collector.collect_sessions()

                results["total_sessions"] += len(sessions)
                results["sessions"].extend(sessions)
                results["devices_success"] += 1
        except Exception as exc:
            results["devices_failed"] += 1
            results["errors"].append({"device": device_config.get("host", "unknown"), "error": str(exc)})
            logger.error(f"Failed to collect from {device_config.get('host')}: {exc}")

    logger.info(
        f"FortiGate collection complete: {results['devices_success']}/{results['devices_checked']} devices, "
        f"{results['total_sessions']} sessions"
    )
    return results

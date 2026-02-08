"""
FortiGate Collector Module
Collects active session data from FortiGate devices via SSH or API

Author: Blacklist System Team
Date: 2025-12-22
Version: 1.0.0
"""

import logging
import re
import socket
from datetime import datetime
from typing import List, Dict, Any, Optional
import paramiko
import requests

logger = logging.getLogger(__name__)


class FortiGateCollector:
    """
    FortiGate device collector for active session monitoring.

    Supports two collection methods:
    1. SSH CLI - Direct SSH connection to FortiGate CLI
    2. REST API - FortiGate REST API (requires API token)

    Usage:
        >>> collector = FortiGateCollector(
        ...     host="192.168.1.1",
        ...     username="admin",
        ...     password="password"
        ... )
        >>> if collector.authenticate():
        ...     sessions = collector.collect_sessions()
        ...     blocked = collector.get_blocked_sessions()
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
        """
        Initialize FortiGate collector.

        Args:
            host: FortiGate device IP or hostname
            username: Admin username
            password: Admin password
            port: SSH or API port (auto-detected based on use_api)
            api_token: API token for REST API authentication
            use_api: Use REST API instead of SSH
            vdom: Virtual domain (default: root)
        """
        self.host = host
        self.username = username
        self.password = password
        self.api_token = api_token
        self.use_api = use_api
        self.vdom = vdom

        # Set port based on connection method
        if port:
            self.port = port
        else:
            self.port = self.DEFAULT_API_PORT if use_api else self.DEFAULT_SSH_PORT

        # Connection state
        self._ssh_client: Optional[paramiko.SSHClient] = None
        self._authenticated = False
        self._device_info: Dict[str, Any] = {}

        logger.info(
            f"FortiGateCollector initialized for {self.host}:{self.port} (method: {'API' if use_api else 'SSH'})"
        )

    def authenticate(self) -> bool:
        """
        Authenticate with FortiGate device.

        Returns:
            bool: True if authentication successful
        """
        if self.use_api:
            return self._authenticate_api()
        else:
            return self._authenticate_ssh()

    def _authenticate_ssh(self) -> bool:
        """
        Authenticate via SSH.

        Returns:
            bool: True if SSH authentication successful
        """
        try:
            logger.info(f"Connecting to FortiGate {self.host} via SSH...")

            self._ssh_client = paramiko.SSHClient()
            self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            self._ssh_client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.SSH_TIMEOUT,
                allow_agent=False,
                look_for_keys=False,
            )

            # Verify connection by getting system status
            output = self._execute_ssh_command("get system status")
            if output and "FortiGate" in output:
                self._authenticated = True
                self._parse_device_info(output)
                logger.info(f"✅ SSH authentication successful for {self.host}")
                return True
            else:
                logger.error("❌ SSH authentication failed: unexpected response")
                return False

        except paramiko.AuthenticationException as e:
            logger.error(f"❌ SSH authentication failed for {self.host}: {e}")
            return False
        except paramiko.SSHException as e:
            logger.error(f"❌ SSH connection error for {self.host}: {e}")
            return False
        except socket.timeout:
            logger.error(f"❌ SSH connection timeout for {self.host}")
            return False
        except Exception as e:
            logger.error(f"❌ SSH error for {self.host}: {e}")
            return False

    def _authenticate_api(self) -> bool:
        """
        Authenticate via REST API.

        Returns:
            bool: True if API authentication successful
        """
        try:
            logger.info(f"Connecting to FortiGate {self.host} via API...")

            # Build API URL
            base_url = f"https://{self.host}:{self.port}/api/v2"

            # Set headers
            headers = {"Content-Type": "application/json", "Accept": "application/json"}

            # Use API token if available, otherwise use session auth
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"

            # Test connection with system status
            response = requests.get(
                f"{base_url}/monitor/system/status",
                headers=headers,
                auth=(self.username, self.password) if not self.api_token else None,
                verify=False,  # FortiGate often uses self-signed certs
                timeout=self.API_TIMEOUT,
            )

            if response.status_code == 200:
                data = response.json()
                self._authenticated = True
                self._device_info = data.get("results", {})
                logger.info(f"✅ API authentication successful for {self.host}")
                return True
            else:
                logger.error(f"❌ API authentication failed: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.SSLError as e:
            logger.error(f"❌ API SSL error for {self.host}: {e}")
            return False
        except requests.exceptions.Timeout:
            logger.error(f"❌ API connection timeout for {self.host}")
            return False
        except Exception as e:
            logger.error(f"❌ API error for {self.host}: {e}")
            return False

    def _execute_ssh_command(self, command: str) -> Optional[str]:
        """
        Execute SSH command on FortiGate.

        Args:
            command: CLI command to execute

        Returns:
            Command output or None if failed
        """
        if not self._ssh_client:
            logger.error("SSH client not connected")
            return None

        try:
            # Execute command
            stdin, stdout, stderr = self._ssh_client.exec_command(command, timeout=self.SSH_TIMEOUT)

            output = stdout.read().decode("utf-8", errors="ignore")
            error = stderr.read().decode("utf-8", errors="ignore")

            if error:
                logger.warning(f"SSH command stderr: {error}")

            return output

        except Exception as e:
            logger.error(f"SSH command execution failed: {e}")
            return None

    def _parse_device_info(self, status_output: str) -> None:
        """
        Parse device info from 'get system status' output.

        Args:
            status_output: Output from 'get system status' command
        """
        try:
            info = {}

            # Parse key-value pairs
            for line in status_output.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    info[key.strip().lower().replace(" ", "_")] = value.strip()

            self._device_info = {
                "hostname": info.get("hostname", "unknown"),
                "serial_number": info.get("serial-number", "unknown"),
                "firmware": info.get("version", "unknown"),
                "model": info.get("platform_type", "FortiGate"),
                "uptime": info.get("system_time", "unknown"),
            }

            logger.debug(f"Device info: {self._device_info}")

        except Exception as e:
            logger.warning(f"Failed to parse device info: {e}")

    def collect_sessions(self, filter_blocked: bool = False) -> List[Dict[str, Any]]:
        """
        Collect active sessions from FortiGate.

        Args:
            filter_blocked: Only return blocked sessions

        Returns:
            List of session dictionaries
        """
        if not self._authenticated:
            logger.error("Not authenticated. Call authenticate() first.")
            return []

        if self.use_api:
            return self._collect_sessions_api(filter_blocked)
        else:
            return self._collect_sessions_ssh(filter_blocked)

    def _collect_sessions_ssh(self, filter_blocked: bool = False) -> List[Dict[str, Any]]:
        """
        Collect sessions via SSH CLI.

        Args:
            filter_blocked: Only return blocked sessions

        Returns:
            List of session dictionaries
        """
        try:
            logger.info(f"Collecting sessions from {self.host} via SSH...")

            # Get session list
            if filter_blocked:
                # Get sessions that match blocked IPs
                command = (
                    "diagnose sys session filter clear\ndiagnose sys session filter policy 0\ndiagnose sys session list"
                )
            else:
                command = "diagnose sys session list"

            output = self._execute_ssh_command(command)

            if not output:
                logger.warning("No session data received")
                return []

            # Parse session output
            sessions = self._parse_session_output(output)

            logger.info(f"Collected {len(sessions)} sessions from {self.host}")
            return sessions

        except Exception as e:
            logger.error(f"Failed to collect sessions: {e}")
            return []

    def _collect_sessions_api(self, filter_blocked: bool = False) -> List[Dict[str, Any]]:
        """
        Collect sessions via REST API.

        Args:
            filter_blocked: Only return blocked sessions

        Returns:
            List of session dictionaries
        """
        try:
            logger.info(f"Collecting sessions from {self.host} via API...")

            base_url = f"https://{self.host}:{self.port}/api/v2"

            headers = {"Content-Type": "application/json", "Accept": "application/json"}

            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"

            # Get session list
            response = requests.get(
                f"{base_url}/monitor/firewall/session",
                headers=headers,
                auth=(self.username, self.password) if not self.api_token else None,
                params={"vdom": self.vdom},
                verify=False,
                timeout=self.API_TIMEOUT,
            )

            if response.status_code != 200:
                logger.error(f"API request failed: {response.status_code}")
                return []

            data = response.json()
            sessions = data.get("results", [])

            # Normalize session format
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

        except Exception as e:
            logger.error(f"Failed to collect sessions via API: {e}")
            return []

    def _parse_session_output(self, output: str) -> List[Dict[str, Any]]:
        """
        Parse SSH session list output.

        FortiGate session output format:
        session info: proto=6 proto_state=01 duration=123 expire=3600 ...

        Args:
            output: Raw session list output

        Returns:
            List of parsed session dictionaries
        """
        sessions = []

        try:
            # Split by session blocks
            session_blocks = re.split(r"session info:", output)

            for block in session_blocks[1:]:  # Skip first empty block
                session = self._parse_session_block(block)
                if session:
                    sessions.append(session)

        except Exception as e:
            logger.error(f"Failed to parse session output: {e}")

        return sessions

    def _parse_session_block(self, block: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single session block.

        Args:
            block: Single session block text

        Returns:
            Parsed session dictionary or None
        """
        try:
            session: Dict[str, Any] = {"timestamp": datetime.now().isoformat()}

            # Extract key=value pairs
            patterns = {
                "proto": r"proto=(\d+)",
                "proto_state": r"proto_state=(\w+)",
                "duration": r"duration=(\d+)",
                "expire": r"expire=(\d+)",
                "policy_id": r"policy=(\d+)",
                "src_ip": r"src=(\d+\.\d+\.\d+\.\d+)",
                "dst_ip": r"dst=(\d+\.\d+\.\d+\.\d+)",
                "src_port": r"sport=(\d+)",
                "dst_port": r"dport=(\d+)",
                "bytes_sent": r"sent=(\d+)",
                "bytes_received": r"rcvd=(\d+)",
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, block)
                if match:
                    raw_value = match.group(1)
                    # Convert numeric values
                    if key in [
                        "proto",
                        "duration",
                        "expire",
                        "policy_id",
                        "src_port",
                        "dst_port",
                        "bytes_sent",
                        "bytes_received",
                    ]:
                        session[key] = int(raw_value)
                    else:
                        session[key] = raw_value

            # Map protocol number to name
            proto_map: Dict[int, str] = {6: "TCP", 17: "UDP", 1: "ICMP"}
            if "proto" in session:
                proto_num = session["proto"]
                session["protocol"] = proto_map.get(proto_num, str(proto_num))

            # Only return if we have essential fields
            if "src_ip" in session and "dst_ip" in session:
                return session

            return None

        except Exception as e:
            logger.warning(f"Failed to parse session block: {e}")
            return None

    def get_blocked_sessions(self, blacklist_ips: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get sessions involving blocked IPs.

        Args:
            blacklist_ips: List of blacklisted IPs to check against

        Returns:
            List of sessions involving blocked IPs
        """
        if not blacklist_ips:
            logger.warning("No blacklist IPs provided")
            return []

        # Collect all sessions
        all_sessions = self.collect_sessions()

        # Filter sessions involving blacklisted IPs
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
        """
        Get firewall policies from FortiGate.

        Returns:
            List of firewall policy dictionaries
        """
        if not self._authenticated:
            logger.error("Not authenticated")
            return []

        if self.use_api:
            return self._get_policies_api()
        else:
            return self._get_policies_ssh()

    def _get_policies_ssh(self) -> List[Dict[str, Any]]:
        """Get policies via SSH."""
        try:
            output = self._execute_ssh_command("show firewall policy")
            if not output:
                return []

            # Parse policy output (simplified)
            policies: List[Dict[str, Any]] = []
            current_policy: Dict[str, Any] = {}

            for line in output.split("\n"):
                line = line.strip()
                if line.startswith("edit "):
                    if current_policy:
                        policies.append(current_policy)
                    policy_id = re.search(r"edit (\d+)", line)
                    current_policy = {"id": int(policy_id.group(1)) if policy_id else 0}
                elif line.startswith("set "):
                    parts = line.split(" ", 2)
                    if len(parts) >= 3:
                        key = parts[1]
                        value = parts[2].strip('"')
                        current_policy[key] = value

            if current_policy:
                policies.append(current_policy)

            return policies

        except Exception as e:
            logger.error(f"Failed to get policies: {e}")
            return []

    def _get_policies_api(self) -> List[Dict[str, Any]]:
        """Get policies via API."""
        try:
            base_url = f"https://{self.host}:{self.port}/api/v2"

            headers = {"Accept": "application/json"}
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"

            response = requests.get(
                f"{base_url}/cmdb/firewall/policy",
                headers=headers,
                auth=(self.username, self.password) if not self.api_token else None,
                params={"vdom": self.vdom},
                verify=False,
                timeout=self.API_TIMEOUT,
            )

            if response.status_code == 200:
                return response.json().get("results", [])

            return []

        except Exception as e:
            logger.error(f"Failed to get policies via API: {e}")
            return []

    def get_device_info(self) -> Dict[str, Any]:
        """
        Get device information.

        Returns:
            Device info dictionary
        """
        return {
            "host": self.host,
            "port": self.port,
            "authenticated": self._authenticated,
            "connection_method": "API" if self.use_api else "SSH",
            **self._device_info,
        }

    def close(self) -> None:
        """
        Close connection to FortiGate.
        """
        if self._ssh_client:
            try:
                self._ssh_client.close()
                logger.info(f"SSH connection closed for {self.host}")
            except Exception as e:
                logger.warning(f"Error closing SSH connection: {e}")

        self._authenticated = False
        self._ssh_client = None

    def __enter__(self):
        """Context manager entry."""
        self.authenticate()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


def collect_fortigate_sessions(
    devices: List[Dict[str, Any]], blacklist_ips: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Collect sessions from multiple FortiGate devices.

    Args:
        devices: List of device configurations
        blacklist_ips: Optional list of blacklisted IPs to filter

    Returns:
        Collection results dictionary
    """
    results = {
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

        except Exception as e:
            results["devices_failed"] += 1
            results["errors"].append({"device": device_config.get("host", "unknown"), "error": str(e)})
            logger.error(f"Failed to collect from {device_config.get('host')}: {e}")

    logger.info(
        f"FortiGate collection complete: "
        f"{results['devices_success']}/{results['devices_checked']} devices, "
        f"{results['total_sessions']} sessions"
    )

    return results

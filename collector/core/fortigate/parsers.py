"""Parsing helpers for FortiGate collector output."""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


def parse_device_info(status_output: str) -> Dict[str, Any]:
    """Parse device info from `get system status` output."""
    try:
        info = {}

        for line in status_output.split("\n"):
            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            info[key.strip().lower().replace(" ", "_")] = value.strip()

        device_info = {
            "hostname": info.get("hostname", "unknown"),
            "serial_number": info.get("serial-number", "unknown"),
            "firmware": info.get("version", "unknown"),
            "model": info.get("platform_type", "FortiGate"),
            "uptime": info.get("system_time", "unknown"),
        }
        logger.debug(f"Device info: {device_info}")
        return device_info
    except Exception as exc:
        logger.warning(f"Failed to parse device info: {exc}")
        return {}


def parse_session_output(output: str) -> List[Dict[str, Any]]:
    """Parse SSH session list output into session dictionaries."""
    sessions = []

    try:
        session_blocks = re.split(r"session info:", output)
        for block in session_blocks[1:]:
            session = parse_session_block(block)
            if session:
                sessions.append(session)
    except Exception as exc:
        logger.error(f"Failed to parse session output: {exc}")

    return sessions


def parse_session_block(block: str) -> Optional[Dict[str, Any]]:
    """Parse a single FortiGate session block."""
    try:
        session: Dict[str, Any] = {"timestamp": datetime.now().isoformat()}
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

        numeric_fields = {
            "proto",
            "duration",
            "expire",
            "policy_id",
            "src_port",
            "dst_port",
            "bytes_sent",
            "bytes_received",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, block)
            if not match:
                continue

            raw_value = match.group(1)
            session[key] = int(raw_value) if key in numeric_fields else raw_value

        proto_map: Dict[int, str] = {6: "TCP", 17: "UDP", 1: "ICMP"}
        if "proto" in session:
            proto_num = session["proto"]
            session["protocol"] = proto_map.get(proto_num, str(proto_num))

        if "src_ip" in session and "dst_ip" in session:
            return session

        return None
    except Exception as exc:
        logger.warning(f"Failed to parse session block: {exc}")
        return None


def parse_policy_output(output: str) -> List[Dict[str, Any]]:
    """Parse `show firewall policy` output into policy dictionaries."""
    policies: List[Dict[str, Any]] = []
    current_policy: Dict[str, Any] = {}

    for line in output.split("\n"):
        line = line.strip()
        if line.startswith("edit "):
            if current_policy:
                policies.append(current_policy)
            policy_id = re.search(r"edit (\d+)", line)
            current_policy = {"id": int(policy_id.group(1)) if policy_id else 0}
            continue

        if not line.startswith("set "):
            continue

        parts = line.split(" ", 2)
        if len(parts) >= 3:
            key = parts[1]
            value = parts[2].strip('"')
            current_policy[key] = value

    if current_policy:
        policies.append(current_policy)

    return policies

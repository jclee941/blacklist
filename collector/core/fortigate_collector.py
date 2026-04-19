"""Backward-compatible FortiGate collector imports."""

# pyright: reportMissingImports=false

from .fortigate import FortiGateCollector, collect_fortigate_sessions

__all__ = ["FortiGateCollector", "collect_fortigate_sessions"]

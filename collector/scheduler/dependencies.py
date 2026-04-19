"""Shared scheduler dependencies with package/script import fallbacks."""

import importlib

try:
    from ..core.database import db_service
    from ..core.regtech_collector import regtech_collector
except ImportError:
    db_service = importlib.import_module("core.database").db_service
    regtech_collector = importlib.import_module("core.regtech_collector").regtech_collector

from ..config import CollectorConfig

__all__ = ["CollectorConfig", "db_service", "regtech_collector"]

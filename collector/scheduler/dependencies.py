"""Shared scheduler dependencies with flexible import strategy."""

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import CollectorConfig


def _import_with_fallback(module_path, relative_module, attr):
    """Try relative import first, then absolute, then PYTHONPATH-based."""
    try:
        return getattr(importlib.import_module(relative_module, package=__package__), attr)
    except (ImportError, AttributeError):
        pass
    # Method 2: absolute import (works when PYTHONPATH includes collector/)
    try:
        return getattr(importlib.import_module(module_path), attr)
    except (ImportError, AttributeError):
        pass
    # Method 3: core.X (works inside Docker where PYTHONPATH=/app)
    try:
        return getattr(importlib.import_module(f"core.{module_path.split('.')[-1]}"), attr)
    except (ImportError, AttributeError):
        raise ImportError(f"Cannot import {attr} from {module_path}")


db_service = _import_with_fallback("collector.core.database", "..core.database", "db_service")
regtech_collector = _import_with_fallback(
    "collector.core.regtech_collector", "..core.regtech_collector", "regtech_collector"
)

if not TYPE_CHECKING:
    CollectorConfig = importlib.import_module("collector.config").CollectorConfig

__all__ = ["CollectorConfig", "db_service", "regtech_collector"]

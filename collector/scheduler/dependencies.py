"""Shared scheduler dependencies with flexible import strategy."""

import importlib


def _import_with_fallback(module_path, relative_module, attr):
    """Try relative import first, then absolute, then PYTHONPATH-based."""
    # Method 1: relative import via parent package
    try:
        mod = importlib.import_module(relative_module, package=__package__)
        return getattr(mod, attr)
    except (ImportError, AttributeError):
        pass
    # Method 2: absolute import (works when PYTHONPATH includes collector/)
    try:
        mod = importlib.import_module(module_path)
        return getattr(mod, attr)
    except (ImportError, AttributeError):
        pass
    # Method 3: core.X (works inside Docker where PYTHONPATH=/app)
    try:
        mod = importlib.import_module(f"core.{module_path.split('.')[-1]}")
        return getattr(mod, attr)
    except (ImportError, AttributeError):
        raise ImportError(f"Cannot import {attr} from {module_path}")


db_service = _import_with_fallback("collector.core.database", "..core.database", "db_service")
regtech_collector = _import_with_fallback(
    "collector.core.regtech_collector", "..core.regtech_collector", "regtech_collector"
)

try:
    from ..config import CollectorConfig
except ImportError:
    CollectorConfig = importlib.import_module("collector.config").CollectorConfig

__all__ = ["CollectorConfig", "db_service", "regtech_collector"]

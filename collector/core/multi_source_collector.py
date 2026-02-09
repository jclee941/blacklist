"""
Multi-Source Collector — Backward Compatibility Re-export

Re-exports from the refactored collector/core/multi_source/ package.
All external imports continue to work unchanged.
"""

from core.multi_source.collector import MultiSourceCollector  # noqa: F401
from core.multi_source.models import SourceConfig, SourceType  # noqa: F401

# Global singleton instance (backward-compat)
multi_source_collector = MultiSourceCollector()

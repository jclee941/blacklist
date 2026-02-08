"""
REGTECH Collector Service — Backward Compatibility Re-export

This module re-exports from the refactored collector/core/regtech/ package.
All external imports of `from collector.core.regtech_collector import RegtechCollector`
continue to work unchanged.

Refactored: 960L monolith → regtech/ package (auth.py, data_processor.py, collector.py)
"""

from collector.core.regtech.collector import RegtechCollector  # noqa: F401

# Global singleton instance (backward-compat)
regtech_collector = RegtechCollector()

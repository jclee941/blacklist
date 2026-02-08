"""
Monitoring API routes package

Provides endpoints for metrics, health checks, and monitoring data.

Created: 2025-11-21 (Cache Metrics Integration - MEDIUM PRIORITY #8)
"""

from flask import Blueprint

monitoring_bp = Blueprint("monitoring", __name__)

from . import metrics  # noqa

"""
Flask error handlers for centralized error processing

This module provides Flask error handlers that catch and format exceptions
into standardized JSON responses. All errors follow RFC 7807-inspired format.

Error Handler Hierarchy:
1. APIError - Custom API exceptions from core.exceptions
2. HTTPException - Werkzeug HTTP errors (404, 405, etc.)
3. Exception - Catch-all for unexpected errors

Usage:
    from core.errors.handlers import register_error_handlers

    app = Flask(__name__)
    register_error_handlers(app)

Created: 2025-11-21 (Error Handling Standardization - HIGH PRIORITY #4)
Updated: 2025-11-21 (Phase 4: Error Metrics Integration)
"""

import logging
import traceback
from flask import jsonify, request, g
from werkzeug.exceptions import HTTPException
from core.exceptions import APIError
from datetime import datetime
import uuid


logger = logging.getLogger(__name__)

# Import error metrics collector
try:
    from core.monitoring import error_metrics

    METRICS_ENABLED = True
except ImportError:
    logger.warning("Error metrics not available - metrics collection disabled")
    METRICS_ENABLED = False


def register_error_handlers(app):
    """
    Register all error handlers with Flask app

    Args:
        app: Flask application instance
    """

    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        """Handle custom API errors"""
        # Log error with structured data
        # Note: Use 'error_message' instead of 'message' to avoid conflict with LogRecord.message
        logger.error(
            f"API Error: {error.error_code}",
            extra={
                "error_code": error.error_code,
                "error_message": error.message,
                "status_code": error.status_code,
                "details": error.details,
                "request_id": getattr(g, "request_id", None) or getattr(request, "id", "unknown"),
                "path": request.path,
                "method": request.method,
                "ip_address": request.remote_addr,
            },
        )

        # Record error metrics (Phase 4)
        if METRICS_ENABLED:
            try:
                error_metrics.record_error(
                    exception_type=type(error).__name__,
                    status_code=error.status_code,
                    endpoint=request.path,
                    method=request.method,
                    message=error.message,
                    request_id=getattr(g, "request_id", None) or getattr(request, "id", "unknown"),
                    user_agent=request.headers.get("User-Agent"),
                )
            except Exception as e:
                logger.warning(f"Failed to record error metrics: {e}")

        # Return formatted response
        return jsonify(error.to_api_response()), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        """Handle werkzeug HTTP exceptions"""
        request_id = getattr(request, "id", str(uuid.uuid4()))

        response = {
            "success": False,
            "error": {
                "code": error.name.upper().replace(" ", "_"),
                "message": error.description,
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
                "path": request.path,
            },
        }

        logger.warning(
            f"HTTP Exception: {error.code}",
            extra={
                "error_code": error.code,
                "error_message": error.description,
                "request_id": request_id,
                "path": request.path,
                "method": request.method,
            },
        )

        # Record error metrics (Phase 4)
        if METRICS_ENABLED:
            try:
                error_metrics.record_error(
                    exception_type=type(error).__name__,
                    status_code=error.code,
                    endpoint=request.path,
                    method=request.method,
                    message=error.description,
                    request_id=request_id,
                    user_agent=request.headers.get("User-Agent"),
                )
            except Exception as e:
                logger.warning(f"Failed to record error metrics: {e}")

        return jsonify(response), error.code

    @app.errorhandler(Exception)
    def handle_generic_exception(error: Exception):
        """Handle unexpected exceptions"""
        request_id = getattr(request, "id", str(uuid.uuid4()))

        # Log full stack trace for debugging
        logger.exception(
            "Unhandled exception",
            extra={
                "request_id": request_id,
                "path": request.path,
                "method": request.method,
                "ip_address": request.remote_addr,
            },
        )

        # Record error metrics (Phase 4)
        if METRICS_ENABLED:
            try:
                error_metrics.record_error(
                    exception_type=type(error).__name__,
                    status_code=500,
                    endpoint=request.path,
                    method=request.method,
                    message=str(error),
                    request_id=request_id,
                    user_agent=request.headers.get("User-Agent"),
                )
            except Exception as e:
                logger.warning(f"Failed to record error metrics: {e}")

        # Production: Hide stack trace, development: show it
        if app.config.get("FLASK_ENV") == "development":
            response = {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(error),
                    "details": {
                        "type": type(error).__name__,
                        "traceback": traceback.format_exc(),
                    },
                    "timestamp": datetime.now().isoformat(),
                    "request_id": request_id,
                    "path": request.path,
                },
            }
        else:
            response = {
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred. Please try again later.",
                    "timestamp": datetime.now().isoformat(),
                    "request_id": request_id,
                    "path": request.path,
                },
            }

        return jsonify(response), 500

    @app.before_request
    def assign_request_id():
        """Assign unique ID to each request for tracing"""
        g.request_id = str(uuid.uuid4())

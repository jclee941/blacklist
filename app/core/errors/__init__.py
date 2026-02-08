"""
Error handling package for Flask application

This package provides centralized error handling with standardized
JSON response format following RFC 7807 principles.

Components:
- handlers.py: Flask error handlers for APIError, HTTPException, and generic exceptions

Usage:
    from core.errors.handlers import register_error_handlers

    app = Flask(__name__)
    register_error_handlers(app)
"""

from .handlers import register_error_handlers

__all__ = ["register_error_handlers"]

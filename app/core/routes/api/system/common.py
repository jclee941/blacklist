"""Shared imports for modular system API routes."""

from datetime import datetime
import logging
from typing import Any, cast

from flask import current_app, g, jsonify, request
from psycopg2.extras import RealDictCursor

from ....config import config
from ....exceptions import DatabaseError, InternalServerError, UnauthorizedError
from ...api_routes import api_bp

logger = logging.getLogger(__name__)

database_error_cls = cast(Any, DatabaseError)
internal_server_error_cls = cast(Any, InternalServerError)
unauthorized_error_cls = cast(Any, UnauthorizedError)

__all__ = [
    "DatabaseError",
    "InternalServerError",
    "RealDictCursor",
    "UnauthorizedError",
    "api_bp",
    "config",
    "current_app",
    "database_error_cls",
    "datetime",
    "g",
    "internal_server_error_cls",
    "jsonify",
    "logger",
    "request",
    "unauthorized_error_cls",
]

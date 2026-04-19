"""간단한 통합 수집 관리 패널 블루프린트."""

import logging
from importlib import import_module

from flask import Blueprint

CSRFProtect = import_module("flask_wtf.csrf").CSRFProtect

logger = logging.getLogger(__name__)
collection_bp = Blueprint("simple_collection", __name__, url_prefix="/collection-panel")
csrf = CSRFProtect()

register_collection_panel_data_routes = import_module(
    "app.core.routes.web.collection_panel_data_routes"
).register_collection_panel_data_routes
register_collection_panel_runtime_routes = import_module(
    "app.core.routes.web.collection_panel_runtime_routes"
).register_collection_panel_runtime_routes
register_collection_panel_view_routes = import_module(
    "app.core.routes.web.collection_panel_view_routes"
).register_collection_panel_view_routes

register_collection_panel_view_routes(collection_bp, csrf)
register_collection_panel_data_routes(collection_bp, csrf)
register_collection_panel_runtime_routes(collection_bp, csrf)

__all__ = ["collection_bp", "csrf"]

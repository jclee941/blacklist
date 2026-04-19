"""REGTECH 관리자 라우트 블루프린트."""

from flask import Blueprint

regtech_admin_bp = Blueprint("regtech_admin", __name__)

from .admin_collection_routes import register_admin_collection_routes
from .admin_credentials_routes import register_admin_credentials_routes

register_admin_credentials_routes(regtech_admin_bp)
register_admin_collection_routes(regtech_admin_bp)

__all__ = ["regtech_admin_bp"]

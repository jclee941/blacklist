"""
JWT Authentication Module

Provides JWT-based authentication for the Blacklist API.
"""

from core.auth.decorators import public
from core.auth.jwt_service import JWTService
from core.auth.middleware import jwt_required_hook

__all__ = ["JWTService", "jwt_required_hook", "public"]

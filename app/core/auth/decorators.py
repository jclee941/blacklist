"""
Authentication Decorators

Provides decorators for marking routes as public (no JWT required).
"""

from functools import wraps
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def public(f: F) -> F:
    """Mark an endpoint as public — no JWT authentication required.

    Usage:
        @app.route("/health")
        @public
        def health_check():
            return {"status": "ok"}
    """
    f._public = True  # type: ignore[attr-defined]
    return f

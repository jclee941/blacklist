from collections.abc import Callable
from typing import Final, TypeVar

from flask import Flask
from flask.typing import ResponseReturnValue


F = TypeVar("F", bound=Callable[..., ResponseReturnValue])
RATE_LIMIT_EXEMPT_PATHS: Final = frozenset({"/health", "/api/health", "/metrics"})


def is_rate_limit_exempt_path(path: str) -> bool:
    return path in RATE_LIMIT_EXEMPT_PATHS


def rate_limit(limit_string: str) -> Callable[[F], F]:
    def decorator(function: F) -> F:
        setattr(function, "_rate_limit", limit_string)
        return function

    return decorator


def apply_route_limits(app: Flask, limiter) -> None:
    for endpoint, view in tuple(app.view_functions.items()):
        limit_string = getattr(view, "_rate_limit", None)
        if limit_string:
            app.view_functions[endpoint] = limiter.limit(limit_string)(view)

"""Centralized rate limiting decorator.

Uses Flask-Limiter instance stored on the Flask app.
Gracefully degrades if limiter is not configured.
"""

from functools import wraps

from flask import current_app


def rate_limit(limit_string):
    """Rate limiting decorator - uses app.limiter from app.py"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            limiter = getattr(current_app, "limiter", None)
            if limiter is None:
                return f(*args, **kwargs)

            @limiter.limit(limit_string)
            def limited_route(*args, **kwargs):
                return f(*args, **kwargs)

            return limited_route(*args, **kwargs)

        return decorated_function

    return decorator

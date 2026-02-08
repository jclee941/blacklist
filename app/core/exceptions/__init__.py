"""Exception classes for the blacklist system"""

from .auth_exceptions import AuthenticationError, AuthorizationError
from .base_exceptions import APIError, BlacklistError, ExternalAPIError
from .config_exceptions import ConfigurationError, DependencyError
from .data_exceptions import DataError, DataProcessingError
from .error_utils import create_error_response, handle_exception, log_exception
from .infrastructure_exceptions import CacheError, ConnectionError, DatabaseError
from .service_exceptions import MonitoringError, RateLimitError, ServiceUnavailableError
from .validation_exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)

__all__ = [
    # Base
    "BlacklistError",
    "APIError",
    "ExternalAPIError",
    # Validation
    "ValidationError",
    "BadRequestError",
    "NotFoundError",
    "ConflictError",
    "ForbiddenError",
    "InternalServerError",
    "UnauthorizedError",
    # Infrastructure
    "CacheError",
    "DatabaseError",
    "ConnectionError",
    # Authentication/Authorization
    "AuthenticationError",
    "AuthorizationError",
    # Service
    "RateLimitError",
    "ServiceUnavailableError",
    "MonitoringError",
    # Data
    "DataProcessingError",
    "DataError",
    # Configuration
    "ConfigurationError",
    "DependencyError",
    # Utilities
    "handle_exception",
    "log_exception",
    "create_error_response",
]

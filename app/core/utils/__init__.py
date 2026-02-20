"""
Core Utilities Package
Utility functions for the blacklist application

Updated: 2025-11-21 (Error Handling Standardization - HIGH PRIORITY #4)
"""

# Response utilities (Phase 3: Standardized Response Formatting)
from .response_utils import (
    success_response,
    paginated_response,
    empty_response,
    created_response,
    deleted_response,
    health_response,
    batch_operation_response,
    statistics_response,
    collection_response,
)

# Database utilities
from .db_utils import execute_query, execute_write

# Cache utilities
from .cache_utils import CacheManager, cached

# Validation utilities
from .validators import (
    validate_ip,
    is_private_ip,
    is_public_ip,
    filter_private_ips,
    filter_public_ips_only,
    validate_pagination,
    validate_string_length,
    ValidationError,
)

__all__ = [
    # Response utilities
    "success_response",
    "paginated_response",
    "empty_response",
    "created_response",
    "deleted_response",
    "health_response",
    "batch_operation_response",
    "statistics_response",
    "collection_response",
    # Database utilities
    "execute_query",
    "execute_write",
    # Cache utilities
    "CacheManager",
    "cached",
    # Validation utilities
    "validate_ip",
    "is_private_ip",
    "is_public_ip",
    "filter_private_ips",
    "filter_public_ips_only",
    "validate_pagination",
    "validate_string_length",
    "ValidationError",
]

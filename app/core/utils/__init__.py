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
from .validators import *

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
]

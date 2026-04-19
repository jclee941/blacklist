"""Error handling utility functions"""

import logging
from typing import Any, Dict, Optional

from .auth_exceptions import AuthorizationError
from .base_exceptions import BlacklistError
from .data_exceptions import DataProcessingError
from .service_exceptions import ServiceUnavailableError
from .validation_exceptions import ValidationError


def handle_exception(exc: Exception, context: Optional[Dict[str, Any]] = None) -> BlacklistError:
    """
    일반 예외를 Blacklist 예외로 변환

    Args:
        exc: 원본 예외
        context: 추가 컨텍스트 정보

    Returns:
        BlacklistError 인스턴스
    """
    if isinstance(exc, BlacklistError):
        return exc

    # 예외 타입에 따른 적절한 BlacklistError 변환
    if isinstance(exc, ValueError):
        return ValidationError(str(exc), cause=exc)
    elif isinstance(exc, FileNotFoundError):
        return DataProcessingError(f"File not found: {exc}", cause=exc)
    elif isinstance(exc, PermissionError):
        return AuthorizationError(f"Permission denied: {exc}", cause=exc)
    elif isinstance(exc, ConnectionError):
        return ServiceUnavailableError(f"Connection failed: {exc}", cause=exc)
    else:
        return BlacklistError(f"Unexpected error: {exc}", cause=exc, details=context)


def log_exception(exc: Exception, logger_instance: Optional[logging.Logger] = None):
    """
    예외를 구조화된 형태로 로깅

    Args:
        exc: 로깅할 예외
        logger_instance: 사용할 로거 (기본값: 모듈 로거)
    """
    log = logger_instance or logging.getLogger(__name__)

    if isinstance(exc, BlacklistError):
        log.error(
            "{exc.error_code}: {exc.message}",
            extra={
                "error_code": exc.error_code,
                "details": exc.details,
                "cause": str(exc.cause) if exc.cause else None,
            },
        )
    else:
        log.error(f"Unhandled exception: {exc}", exc_info=True)


def create_error_response(exc: Exception, include_details: bool = False) -> Dict[str, Any]:
    """
    예외를 API 응답 형태로 변환

    Args:
        exc: 변환할 예외
        include_details: 상세 정보 포함 여부

    Returns:
        API 응답 딕셔너리
    """
    if isinstance(exc, BlacklistError):
        response = exc.to_api_response()
        if not include_details:
            response.pop("details", None)
        return response
    else:
        return {
            "error": "Internal server error",
            "error_code": "INTERNAL_ERROR",
            "message": str(exc) if include_details else "An unexpected error occurred",
        }

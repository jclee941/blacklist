"""
에러 핸들링 유틸리티
"""

import logging
from flask import jsonify
from datetime import datetime

logger = logging.getLogger(__name__)


def handle_exception(exception: Exception, context: str = "") -> tuple:
    """예외 처리 및 JSON 응답 생성"""
    error_message = f"{context}: {str(exception)}" if context else str(exception)
    logger.error(error_message, exc_info=True)

    return (
        jsonify(
            {
                "success": False,
                "error": error_message,
                "timestamp": datetime.now().isoformat(),
            }
        ),
        500,
    )

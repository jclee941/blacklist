"""
Enhanced Logger Configuration with Tagging System
로그 태깅 및 구조화된 로깅 시스템
"""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import os
from ..config import config


class StructuredFormatter(logging.Formatter):
    """구조화된 JSON 로그 포매터"""

    def format(self, record):
        # 기본 로그 데이터
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 환경 정보 추가
        log_data["environment"] = config.ENVIRONMENT
        log_data["service"] = config.SERVICE_NAME
        log_data["container_id"] = config.HOSTNAME

        # 커스텀 태그 추가
        if hasattr(record, "tags"):
            log_data["tags"] = record.tags

        # 추가 컨텍스트
        if hasattr(record, "context"):
            log_data["context"] = record.context

        # 성능 메트릭
        if hasattr(record, "metrics"):
            log_data["metrics"] = record.metrics

        # 에러 정보
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": (self.formatException(record.exc_info) if record.exc_info else None),
            }

        return json.dumps(log_data, ensure_ascii=False)


class TaggedLogger(logging.LoggerAdapter):
    """태그 지원 로거 어댑터"""

    def __init__(self, logger, tags: Optional[Dict[str, Any]] = None):
        super().__init__(logger, {})
        self.tags = tags or {}

    def process(self, msg, kwargs):
        # 태그 추가
        extra = kwargs.get("extra", {})
        extra["tags"] = {**self.tags, **extra.get("tags", {})}
        kwargs["extra"] = extra
        return msg, kwargs

    def with_tags(self, **tags):
        """추가 태그와 함께 새로운 로거 생성"""
        new_tags = {**self.tags, **tags}
        return TaggedLogger(self.logger, new_tags)

    def log_operation(self, operation: str, status: str, **kwargs):
        """작업 로깅 헬퍼"""
        self.info(
            f"{operation} - {status}",
            extra={
                "tags": {"operation": operation, "status": status},
                "context": kwargs,
            },
        )

    def log_metric(self, metric_name: str, value: Any, unit: str = None, **tags):
        """메트릭 로깅 헬퍼"""
        self.info(
            f"Metric: {metric_name}={value}{' ' + unit if unit else ''}",
            extra={
                "metrics": {"name": metric_name, "value": value, "unit": unit},
                "tags": tags,
            },
        )


def setup_logger(name: str = None, level: int = logging.INFO) -> TaggedLogger:
    """향상된 로거 설정"""

    # 로거 생성
    logger = logging.getLogger(name or __name__)
    logger.setLevel(level)

    # 기존 핸들러 제거
    logger.handlers.clear()

    # 콘솔 핸들러 (구조화된 JSON)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(StructuredFormatter())
    logger.addHandler(console_handler)

    # 파일 핸들러 (선택적) - 권한 문제 방지
    log_dir = config.LOG_DIR
    try:
        if os.path.exists(log_dir):
            # 로그 파일 경로
            log_file = os.path.join(log_dir, f"{name or 'app'}.jsonl")

            # 디렉토리 쓰기 권한 확인
            if os.access(log_dir, os.W_OK):
                file_handler = logging.FileHandler(log_file, encoding="utf-8")
                file_handler.setLevel(level)
                file_handler.setFormatter(StructuredFormatter())
                logger.addHandler(file_handler)
            else:
                # 권한이 없으면 콘솔에만 로그 출력
                logger.warning(f"Log directory {log_dir} is not writable, using console only")
    except Exception as e:
        # 파일 로깅 실패시 콘솔에만 로그 출력
        logger.warning(f"Failed to setup file logging: {e}")

    # 기본 태그 설정
    default_tags = {
        "service": config.SERVICE_NAME,
        "version": config.APP_VERSION or "unknown",
        "environment": config.ENVIRONMENT,
    }

    return TaggedLogger(logger, default_tags)


# 전역 로거 인스턴스
logger = setup_logger("blacklist")

# 서비스별 로거
collection_logger = logger.with_tags(component="collection")
api_logger = logger.with_tags(component="api")
db_logger = logger.with_tags(component="database")
scheduler_logger = logger.with_tags(component="scheduler")

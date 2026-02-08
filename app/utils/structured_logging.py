#!/usr/bin/env python3
"""
스마트 로깅 시스템 - 중복 방지 및 노이즈 필터링
Phase 2.1: Structlog 기반 구조화된 로깅
"""

import logging
import time
import re
from datetime import datetime
from collections import defaultdict
import structlog
from structlog.processors import JSONRenderer
import sys


class DuplicateFilter(logging.Filter):
    """중복 로그 메시지 필터링"""

    def __init__(self, max_duplicates: int = 3, time_window: int = 300):
        super().__init__()
        self.max_duplicates = max_duplicates
        self.time_window = time_window  # 5분 윈도우
        self.message_counts = defaultdict(list)
        self.suppressed_messages = set()

    def filter(self, record):
        """로그 레코드 필터링"""
        message_key = f"{record.name}:{record.levelname}:{record.getMessage()}"
        current_time = time.time()

        # 시간 윈도우 밖의 기록들 정리
        self.message_counts[message_key] = [
            t for t in self.message_counts[message_key] if current_time - t < self.time_window
        ]

        # 현재 시간 추가
        self.message_counts[message_key].append(current_time)

        # 중복 횟수 체크
        count = len(self.message_counts[message_key])

        if count > self.max_duplicates:
            if message_key not in self.suppressed_messages:
                # 첫 억제 시에만 알림 로그 생성
                _suppressed_record = logging.LogRecord(
                    name=record.name,
                    level=logging.WARNING,
                    pathname=record.pathname,
                    lineno=record.lineno,
                    msg=f"중복 로그 억제: '{record.getMessage()[:50]}...' (이후 {self.time_window}초 동안 억제)",
                    args=(),
                    exc_info=None,
                )
                self.suppressed_messages.add(message_key)
                # 억제 알림은 통과시키고, 원래 메시지는 차단
                return False
            return False

        # 억제되었던 메시지가 다시 나타나면 억제 세트에서 제거
        self.suppressed_messages.discard(message_key)
        return True


class HealthCheckFilter(logging.Filter):
    """헬스체크 관련 정상 로그 필터링"""

    def __init__(self, suppress_normal_health_checks: bool = True):
        super().__init__()
        self.suppress_normal_health_checks = suppress_normal_health_checks
        self.health_patterns = [
            r"GET /health HTTP/1\.1.*200",
            r"Request started.*GET.*\/health",
            r"Request completed.*GET.*\/health",
            r"Request started.*path.*\/health",
            r"Request completed.*status_code.*200.*\/health",
        ]

    def filter(self, record):
        """헬스체크 로그 필터링"""
        if not self.suppress_normal_health_checks:
            return True

        message = record.getMessage()

        # 정상 헬스체크 로그인지 확인
        for pattern in self.health_patterns:
            if re.search(pattern, message):
                # 오류가 아닌 정상 헬스체크는 필터링
                if record.levelname in ["INFO", "DEBUG"]:
                    return False

        return True


class LogLevelFixer(logging.Filter):
    """null 로그 레벨 수정"""

    def filter(self, record):
        """로그 레벨 수정"""
        message = record.getMessage().lower()

        # 메시지 내용에 따라 로그 레벨 추론
        if any(keyword in message for keyword in ["error", "failed", "exception", "critical"]):
            record.levelno = logging.ERROR
            record.levelname = "ERROR"
        elif any(keyword in message for keyword in ["warning", "warn", "경고", "실패"]):
            record.levelno = logging.WARNING
            record.levelname = "WARNING"
        elif any(keyword in message for keyword in ["debug", "디버그"]):
            record.levelno = logging.DEBUG
            record.levelname = "DEBUG"
        else:
            # 기본값은 INFO
            record.levelno = logging.INFO
            record.levelname = "INFO"

        return True


class SmartLogFormatter(logging.Formatter):
    """스마트 로그 포맷터 - JSON과 텍스트 지원"""

    def __init__(self, use_json: bool = True):
        self.use_json = use_json
        if use_json:
            super().__init__()
        else:
            super().__init__(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

    def format(self, record):
        """로그 레코드 포맷팅"""
        if self.use_json:
            import json

            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat() + "+00:00",
                "level": record.levelname,
                "name": record.name,
                "message": record.getMessage(),
                "context": getattr(record, "context", {}),
            }

            if record.exc_info:
                log_entry["exc_info"] = self.formatException(record.exc_info)

            return json.dumps(log_entry, ensure_ascii=False)
        else:
            return super().format(record)


def setup_smart_logging(
    logger_name: str,
    suppress_duplicates: bool = True,
    suppress_health_checks: bool = True,
    fix_log_levels: bool = True,
) -> logging.Logger:
    """스마트 로깅 설정"""

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    # 기존 핸들러 제거
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 콘솔 핸들러 생성
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(SmartLogFormatter(use_json=False))

    # 필터 적용
    if fix_log_levels:
        console_handler.addFilter(LogLevelFixer())

    if suppress_duplicates:
        console_handler.addFilter(DuplicateFilter(max_duplicates=2, time_window=300))

    if suppress_health_checks:
        console_handler.addFilter(HealthCheckFilter(suppress_normal_health_checks=True))

    logger.addHandler(console_handler)
    logger.propagate = False  # 상위 로거로 전파 방지

    return logger


def configure_structlog():
    """
    Phase 2.1: Structlog 전역 설정
    JSON 형식의 구조화된 로깅
    """
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 루트 로거 설정
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )


def get_structured_logger(name: str):
    """
    구조화된 로거 생성

    Usage:
        logger = get_structured_logger(__name__)
        logger.info("blacklist_decision", ip="1.2.3.4", decision="BLOCKED", reason="whitelist")
    """
    return structlog.get_logger(name)


def setup_smart_logging_for_app(app):
    """Flask 앱에 스마트 로깅 적용"""

    # 주요 로거들에 스마트 로깅 적용
    loggers_to_enhance = [
        "src.core.app.middleware",
        "request",
        "src.core.app.blueprints",
        "src.core.app.config",
        "werkzeug",
    ]

    for logger_name in loggers_to_enhance:
        setup_smart_logging(
            logger_name,
            suppress_duplicates=True,
            suppress_health_checks=True,
            fix_log_levels=True,
        )

    # 애플리케이션 로거 설정
    app.logger = setup_smart_logging(
        "blacklist-app",
        suppress_duplicates=True,
        suppress_health_checks=True,
        fix_log_levels=True,
    )

    app.logger.info("🎯 스마트 로깅 시스템 활성화됨")
    app.logger.info("✅ 중복 로그 필터링 활성화")
    app.logger.info("✅ 헬스체크 노이즈 필터링 활성화")
    app.logger.info("✅ 로그 레벨 자동 수정 활성화")


if __name__ == "__main__":
    # 테스트
    test_logger = setup_smart_logging("test_logger")

    # 중복 메시지 테스트
    for i in range(5):
        test_logger.info("중복 테스트 메시지")

    # 헬스체크 메시지 테스트
    test_logger.info('GET /health HTTP/1.1" 200 -')
    test_logger.info("Request started GET /health")

    # 오류 메시지 테스트
    test_logger.info("Error occurred in database connection")

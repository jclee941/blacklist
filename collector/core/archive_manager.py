"""
Archive Manager — 수집 원본 파일 보관

수집된 원본 데이터(XLS, HTML 등)를 날짜별 디렉토리에 보관합니다.
경로 패턴: {ARCHIVE_DIR}/{source}/{YYYY-MM-DD}/{archive_filename}

파일명 규칙:
    {SOURCE}_{YYYYMMDDTHHmmss}_P{start}-{end}_{original_name}
    예: REGTECH_20260211T143022_P20260201-20260211_page1.html
    기간 정보 없을 시: REGTECH_20260211T143022_page1.html
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from datetime import datetime, timedelta

from collector.config import CollectorConfig

logger = logging.getLogger(__name__)


def _safe_archive_component(value: str, fallback: str) -> str:
    component = os.path.basename(value.replace("\\", "/"))
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", component).strip("._")
    return sanitized or fallback


def _prune_and_measure_archive() -> int:
    cutoff = datetime.now() - timedelta(days=CollectorConfig.ARCHIVE_RETENTION_DAYS)
    total_bytes = 0
    for root, _directories, filenames in os.walk(CollectorConfig.ARCHIVE_DIR):
        for filename in filenames:
            path = os.path.join(root, filename)
            try:
                if datetime.fromtimestamp(os.path.getmtime(path)) < cutoff:
                    os.remove(path)
                    continue
                total_bytes += os.path.getsize(path)
            except OSError as exc:
                logger.warning("archive.inspect_failed: path=%s error=%s", path, exc)
    return total_bytes


def _has_archive_capacity(incoming_bytes: int) -> bool:
    if incoming_bytes > CollectorConfig.MAX_ARCHIVE_BYTES:
        return False
    return _prune_and_measure_archive() + incoming_bytes <= CollectorConfig.MAX_ARCHIVE_BYTES


def generate_archive_filename(
    source: str,
    original_name: str,
    period_start: str | None = None,
    period_end: str | None = None,
) -> str:
    """아카이브 파일명을 생성합니다.

    규칙: {SOURCE}_{timestamp}_P{start}-{end}_{original_name}
    기간 정보가 없으면 P 세그먼트를 생략합니다.

    Args:
        source: 수집 소스 (예: "REGTECH")
        original_name: 원본 파일명 (예: "blacklist.xls")
        period_start: 수집 대상 시작일 (예: "2026-02-01", "20260201")
        period_end: 수집 대상 종료일 (예: "2026-02-11", "20260211")

    Returns:
        생성된 아카이브 파일명
    """
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    safe_source = _safe_archive_component(source, "UNKNOWN").upper()
    parts = [safe_source, timestamp]

    if period_start or period_end:
        start = _normalize_date(period_start) if period_start else "unknown"
        end = _normalize_date(period_end) if period_end else "unknown"
        parts.append(f"P{start}-{end}")

    parts.append(_safe_archive_component(original_name, "archive"))
    return "_".join(parts)


def _normalize_date(date_str: str) -> str:
    """날짜 문자열을 YYYYMMDD 형식으로 정규화합니다.

    지원 형식: "2026-02-01", "20260201", "2026.02.01", "2026/02/01"
    """
    cleaned = date_str.strip().replace("-", "").replace(".", "").replace("/", "")
    # 8자리 숫자가 아닌 경우 원본 반환 (안전 폴백)
    if len(cleaned) == 8 and cleaned.isdigit():
        return cleaned
    return _safe_archive_component(date_str, "unknown")


def archive_file(
    source: str,
    src_path: str,
    filename: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
) -> str | None:
    """원본 파일을 아카이브 디렉토리에 복사합니다.

    Args:
        source: 수집 소스 이름 (예: "REGTECH")
        src_path: 원본 파일 경로
        filename: 원본 파일명 (None이면 src_path에서 추출)
        period_start: 수집 대상 시작일
        period_end: 수집 대상 종료일

    Returns:
        아카이브 경로 (성공 시) 또는 None (비활성화/실패 시)
    """
    if not CollectorConfig.ARCHIVE_ENABLED:
        return None

    if not os.path.exists(src_path):
        logger.warning("archive.source_not_found: path=%s", src_path)
        return None

    try:
        if not _has_archive_capacity(os.path.getsize(src_path)):
            logger.warning("archive.capacity_exceeded: source=%s", source)
            return None
    except OSError as exc:
        logger.warning("archive.inspect_failed: path=%s error=%s", src_path, exc)
        return None

    today = datetime.now().strftime("%Y-%m-%d")
    archive_dir = os.path.join(
        CollectorConfig.ARCHIVE_DIR,
        _safe_archive_component(source, "unknown").lower(),
        today,
    )

    try:
        os.makedirs(archive_dir, exist_ok=True)
    except OSError as e:
        logger.error("archive.mkdir_failed: dir=%s error=%s", archive_dir, e)
        return None

    original_name = filename or os.path.basename(src_path)
    dest_filename = generate_archive_filename(source, original_name, period_start, period_end)
    dest_path = os.path.join(archive_dir, dest_filename)

    try:
        shutil.copy2(src_path, dest_path)
        logger.info("archive.saved: source=%s path=%s", source, dest_path)
        return dest_path
    except OSError as e:
        logger.error("archive.copy_failed: source=%s error=%s", source, e)
        return None


def archive_content(
    source: str,
    content: str,
    filename: str,
    period_start: str | None = None,
    period_end: str | None = None,
) -> str | None:
    """텍스트 콘텐츠를 아카이브 디렉토리에 저장합니다.

    Args:
        source: 수집 소스 이름 (예: "REGTECH")
        content: 저장할 텍스트 콘텐츠
        filename: 원본 파일명
        period_start: 수집 대상 시작일
        period_end: 수집 대상 종료일

    Returns:
        아카이브 경로 (성공 시) 또는 None (비활성화/실패 시)
    """
    if not CollectorConfig.ARCHIVE_ENABLED:
        return None

    content_bytes = len(content.encode("utf-8"))
    if not _has_archive_capacity(content_bytes):
        logger.warning("archive.capacity_exceeded: source=%s", source)
        return None

    today = datetime.now().strftime("%Y-%m-%d")
    archive_dir = os.path.join(
        CollectorConfig.ARCHIVE_DIR,
        _safe_archive_component(source, "unknown").lower(),
        today,
    )

    try:
        os.makedirs(archive_dir, exist_ok=True)
    except OSError as e:
        logger.error("archive.mkdir_failed: dir=%s error=%s", archive_dir, e)
        return None

    dest_filename = generate_archive_filename(source, filename, period_start, period_end)
    dest_path = os.path.join(archive_dir, dest_filename)

    try:
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("archive.saved: source=%s path=%s", source, dest_path)
        return dest_path
    except OSError as e:
        logger.error("archive.write_failed: source=%s error=%s", source, e)
        return None

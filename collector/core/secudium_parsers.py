"""
Secudium (ISAP) response parsers.

Handles two non-standard formats:
1. DHTMLX Grid JSON — Black IP list responses from /isap-api/secinfo/list/black_ip
   Format: {"rows": [{"id": N, "data": ["", "", "title", "author", "date", "<button ...>", "0", "N"]}]}
2. XLS files — Downloaded Black IP attachments containing IP addresses

Data field mapping (0-indexed):
  data[0] = checkbox placeholder (empty)
  data[1] = row number placeholder (empty)
  data[2] = title (e.g., "[SK쉴더스] 신규 침해 Black IP - 2026-02-06")
  data[3] = author (e.g., "정예린")
  data[4] = registration date (e.g., "2026-02-06 01:25:51")
  data[5] = download button HTML with embedded UUID and filename
  data[6] = count or view count
  data[7] = edit_yn flag ("N")
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote

import structlog

if TYPE_CHECKING:
    import pandas as pd

logger = structlog.get_logger(__name__)

# Regex to extract download params from DHTMLX button HTML
# Matches: onclick='download("UUID", "filename.xls");' or similar variants
_DOWNLOAD_RE = re.compile(
    r"""download\(\s*["']([^"']+)["']\s*,\s*["']([^"']+)["']\s*\)""",
    re.IGNORECASE,
)

# IP address regex (IPv4)
_IPV4_RE = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b")

# CIDR notation
_CIDR_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)/(?:[0-9]|[12]\d|3[0-2])\b"
)


def parse_black_ip_list(response_json: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse DHTMLX grid JSON response into structured records.

    Args:
        response_json: Raw JSON from /isap-api/secinfo/list/black_ip

    Returns:
        List of dicts with keys: id, title, author, date, download_html, count, edit_yn
    """
    if not response_json or not isinstance(response_json, dict):
        return []
    rows = response_json.get("rows", [])
    if not rows:
        logger.warning("secudium.parse.empty_response", raw_keys=list(response_json.keys()))
        return []

    records = []
    for row in rows:
        row_id = row.get("id")
        data = row.get("data", [])

        if len(data) < 6:
            logger.warning("secudium.parse.short_row", row_id=row_id, data_len=len(data))
            continue

        record = {
            "id": row_id,
            "title": data[2] if len(data) > 2 else "",
            "author": data[3] if len(data) > 3 else "",
            "date": data[4] if len(data) > 4 else "",
            "download_html": data[5] if len(data) > 5 else "",
            "count": data[6] if len(data) > 6 else "0",
            "edit_yn": data[7] if len(data) > 7 else "N",
        }
        records.append(record)

    logger.info("secudium.parse.list_complete", record_count=len(records))
    return records


def extract_download_info(download_html: str) -> tuple[str, str] | None:
    """Extract server filename (UUID) and display filename from download button HTML.

    The DHTMLX grid embeds download info in onclick handlers:
      <button onclick='download("a1b2c3d4-uuid", "filename.xls");'>Down</button>

    Args:
        download_html: Raw HTML string from data[5]

    Returns:
        Tuple of (server_filename_uuid, display_filename) or None if not found
    """
    if not download_html:
        return None

    match = _DOWNLOAD_RE.search(download_html)
    if not match:
        logger.debug("secudium.parse.no_download_link", html_preview=download_html[:100])
        return None

    server_filename = match.group(1).strip()
    display_filename = unquote(match.group(2).strip())

    return server_filename, display_filename


def parse_xls_file(file_path: str) -> list[dict[str, Any]]:
    """Parse a Secudium Black IP XLS file and extract IP addresses.

    XLS files from Secudium typically contain columns like:
    - IP address
    - Port (optional)
    - Country/region
    - Description/category
    - Detection date

    Falls back to text extraction if pandas parsing fails.

    Args:
        file_path: Path to the downloaded XLS file

    Returns:
        List of dicts with at minimum: ip, port (optional), description, source_date
    """
    try:
        return _parse_xls_with_pandas(file_path)
    except Exception as e:
        logger.warning("secudium.parse.pandas_failed", error=str(e), file=file_path)
        return _parse_xls_as_text(file_path)


def _parse_xls_with_pandas(file_path: str) -> list[dict[str, Any]]:
    """Parse XLS using pandas (primary method)."""
    import pandas as pd

    df = pd.read_excel(file_path, engine="xlrd")
    logger.info("secudium.parse.xls_loaded", rows=len(df), columns=list(df.columns))

    if df.empty:
        return []

    ip_column = _find_ip_column(df)
    if ip_column is None:
        logger.warning("secudium.parse.no_ip_column", columns=list(df.columns))
        return _extract_ips_from_all_columns(df)

    results = []
    for _, row in df.iterrows():
        ip_value = str(row.get(ip_column, "")).strip()
        if not ip_value or not _is_valid_ip_or_cidr(ip_value):
            continue

        record = {
            "ip": ip_value,
            "port": _extract_port(row, df.columns),
            "description": _extract_description(row, df.columns),
            "source_date": _extract_date(row, df.columns),
            "raw_row": {str(k): str(v) for k, v in row.items() if pd.notna(v)},
        }
        results.append(record)

    logger.info("secudium.parse.xls_complete", ip_count=len(results))
    return results


def _parse_xls_as_text(file_path: str) -> list[dict[str, Any]]:
    """Fallback: read XLS as binary/text and extract IPs via regex."""
    try:
        with open(file_path, "rb") as f:
            content = f.read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.error("secudium.parse.text_fallback_failed", error=str(e))
        return []

    ips = set()
    for match in _CIDR_RE.finditer(content):
        ips.add(match.group())
    for match in _IPV4_RE.finditer(content):
        ip = match.group()
        if not ip.startswith(("0.", "127.", "255.")):
            ips.add(ip)

    results = [{"ip": ip, "port": None, "description": "regex_extracted", "source_date": None} for ip in ips]
    logger.info("secudium.parse.text_fallback_complete", ip_count=len(results))
    return results


def _find_ip_column(df: "pd.DataFrame") -> str | None:
    """Heuristically find the column containing IP addresses."""
    ip_keywords = ["ip", "IP", "아이피", "주소", "address", "addr", "host", "destination", "dst", "src"]

    for col in df.columns:
        col_str = str(col).lower()
        for keyword in ip_keywords:
            if keyword.lower() in col_str:
                sample = df[col].dropna().head(5).astype(str)
                if any(_IPV4_RE.search(str(v)) for v in sample):
                    return col

    for col in df.columns:
        sample = df[col].dropna().head(10).astype(str)
        ip_ratio = sum(1 for v in sample if _IPV4_RE.fullmatch(str(v).strip())) / max(len(sample), 1)
        if ip_ratio > 0.5:
            return col

    return None


def _extract_ips_from_all_columns(df: "pd.DataFrame") -> list[dict[str, Any]]:
    """Last resort: scan all columns for IP addresses."""
    ips = set()
    for col in df.columns:
        for val in df[col].dropna().astype(str):
            for match in _IPV4_RE.finditer(str(val)):
                ip = match.group()
                if not ip.startswith(("0.", "127.", "255.")):
                    ips.add(ip)

    return [{"ip": ip, "port": None, "description": "column_scan", "source_date": None} for ip in ips]


def _extract_port(row: "pd.Series", columns: "pd.Index") -> int | None:
    """Try to extract port from row."""
    port_keywords = ["port", "포트", "PORT"]
    for col in columns:
        if any(k.lower() in str(col).lower() for k in port_keywords):
            try:
                val = int(float(row[col]))
                if 0 < val <= 65535:
                    return val
            except (ValueError, TypeError):
                pass
    return None


def _extract_description(row: "pd.Series", columns: "pd.Index") -> str:
    """Try to extract description/category from row."""
    desc_keywords = ["설명", "description", "desc", "category", "분류", "유형", "type", "비고", "note", "remark"]
    for col in columns:
        if any(k.lower() in str(col).lower() for k in desc_keywords):
            val = str(row[col]).strip()
            if val and val.lower() != "nan":
                return val
    return ""


def _extract_date(row: "pd.Series", columns: "pd.Index") -> str | None:
    """Try to extract date from row."""
    date_keywords = ["날짜", "date", "일시", "time", "탐지", "등록", "detect", "reg"]
    for col in columns:
        if any(k.lower() in str(col).lower() for k in date_keywords):
            val = str(row[col]).strip()
            if val and val.lower() != "nan" and len(val) >= 8:
                return val
    return None


def _is_valid_ip_or_cidr(value: str) -> bool:
    """Check if string is a valid IPv4 address or CIDR."""
    return bool(_IPV4_RE.fullmatch(value) or _CIDR_RE.fullmatch(value))

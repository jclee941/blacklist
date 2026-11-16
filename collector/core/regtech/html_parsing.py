import logging
import re
from html import unescape
from typing import Any, List, Optional

logger = logging.getLogger(__name__)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_MAINTENANCE_WINDOW_RE = re.compile(r"작업\s*일시\s*:\s*[^○]+")


def maintenance_notice(page: str) -> Optional[str]:
    """Return the notice when REGTECH answers with its portal maintenance page instead of the app.

    During maintenance every URL serves the same static page (title "... 포털 점검 안내"),
    so a login against it fails without saying why.
    """
    title_match = _TITLE_RE.search(page)
    if not title_match:
        return None
    title = " ".join(unescape(title_match.group(1)).split())
    if "점검" not in title:
        return None
    body_text = " ".join(unescape(_TAG_RE.sub(" ", page[title_match.end() :])).split())
    window = _MAINTENANCE_WINDOW_RE.search(body_text)
    return window.group(0).strip() if window else title


class RegtechHtmlParsingMixin:
    def _parse_html_response(self, html_content: str) -> Optional[List[dict[str, Any]]]:
        from core.regtech_parsers import parse_html_response

        return parse_html_response(html_content)

    def _extract_country_info(self, cell_texts: List[str]) -> Optional[str]:
        if not cell_texts:
            return None

        country_patterns = {
            "KR": ["KR", "Korea", "한국", "South Korea", "Republic of Korea"],
            "US": ["US", "USA", "United States", "미국", "America"],
            "CN": ["CN", "China", "중국", "CHN"],
            "JP": ["JP", "Japan", "일본", "JPN"],
            "RU": ["RU", "Russia", "러시아", "Russian"],
            "DE": ["DE", "Germany", "독일", "German"],
            "FR": ["FR", "France", "프랑스", "French"],
            "GB": ["GB", "UK", "United Kingdom", "영국", "Britain"],
            "IN": ["IN", "India", "인도", "Indian"],
        }
        for cell_text in cell_texts:
            if len(cell_text.strip()) < 2:
                continue
            cell_upper = cell_text.upper().strip()
            for country_code, patterns in country_patterns.items():
                for pattern in patterns:
                    if pattern.upper() in cell_upper:
                        logger.info(f"✅ 국가 정보 발견: '{cell_text}' -> {country_code}")
                        return country_code
            if len(cell_text.strip()) == 2 and cell_text.strip().isalpha():
                country_code = cell_text.strip().upper()
                logger.info(f"✅ 국가 코드 발견: {country_code}")
                return country_code
        return None

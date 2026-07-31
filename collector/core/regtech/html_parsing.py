import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


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

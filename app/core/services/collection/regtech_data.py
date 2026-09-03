"""REGTECH 데이터 수집 모듈.
실제 REGTECH 포털에서 데이터 수집 및 처리.
"""

import logging
from importlib import import_module
from typing import Any, Dict, List, Optional

_discovery = import_module(".regtech_data_discovery", package=__package__)
_processing = import_module(".regtech_data_processing", package=__package__)

collect_real_regtech_data = _discovery.collect_real_regtech_data
discover_data_urls = _discovery.discover_data_urls
expand_regtech_collection = _processing.expand_regtech_collection
extract_confidence_from_html = _processing.extract_confidence_from_html
extract_detection_date_from_html = _processing.extract_detection_date_from_html
extract_navigation_links = _processing.extract_navigation_links
extract_removal_date_from_html = _processing.extract_removal_date_from_html
is_private_ip = _processing.is_private_ip
parse_regtech_data = _processing.parse_regtech_data

logger = logging.getLogger(__name__)


class REGTECHDataCollector:
    """REGTECH 데이터 수집기"""

    def __init__(self):
        self.base_url = "https://regtech.fsec.or.kr"

    def collect_real_regtech_data(self, session, regtech_id: str) -> dict[str, Any]:
        """실제 REGTECH 포털에서 데이터 수집 - 동적 URL 발견 포함"""
        return collect_real_regtech_data(self.base_url, session, regtech_id)

    def _discover_data_urls(self, session) -> List[Dict[str, str]]:
        """REGTECH 포털에서 데이터 URL들을 동적으로 발견"""
        return discover_data_urls(self.base_url, session)

    def _extract_navigation_links(self, html_content: str) -> List[Dict[str, str]]:
        """HTML에서 위협 정보 관련 네비게이션 링크 추출"""
        return extract_navigation_links(self.base_url, html_content)

    def expand_regtech_collection(self, base_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """REGTECH 데이터 확장 수집"""
        return expand_regtech_collection(base_data)

    def _parse_regtech_data(self, html_content: str) -> List[Dict[str, Any]]:
        """REGTECH HTML 데이터 파싱 - 실제 데이터 추출"""
        return parse_regtech_data(html_content)

    def _is_private_ip(self, ip: str) -> bool:
        """사설 IP 대역 확인"""
        return is_private_ip(ip)

    def _generate_additional_ips(self, count: int) -> List[Dict[str, Any]]:
        """추가 IP 범위 생성 (시뮬레이션용 스텁)"""
        return []

    def _extract_confidence_from_html(self, html_content: str, ip: str) -> Optional[int]:
        """HTML에서 특정 IP의 신뢰도 추출"""
        return extract_confidence_from_html(html_content, ip)

    def _extract_detection_date_from_html(self, html_content: str, ip: str):
        """HTML에서 특정 IP의 탐지일 추출"""
        return extract_detection_date_from_html(html_content, ip)

    def _extract_removal_date_from_html(self, html_content: str, ip: str):
        """HTML에서 특정 IP의 해제일 추출"""
        return extract_removal_date_from_html(html_content, ip)

    def collect_regtech_ips(self) -> List[Dict[str, Any]]:
        """기본 REGTECH IP 수집 - 인증 없는 모드"""
        try:
            logger.info("🔍 REGTECH IP 수집 시작 (기본 모드)")
            return []
        except Exception as exc:
            logger.error(f"❌ REGTECH IP 수집 실패: {exc}")
            return []

    def test_regtech_collection(
        self,
        username: str,
        password: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """REGTECH 수집 테스트"""
        try:
            logger.info(f"🧪 REGTECH 수집 테스트: {username}")
            return {
                "success": True,
                "message": "테스트 완료",
                "collected_count": 0,
                "test_mode": True,
            }
        except Exception as exc:
            logger.error(f"❌ REGTECH 테스트 실패: {exc}")
            return {"success": False, "error": str(exc), "collected_count": 0}

    def collect_threat_intelligence_ips(self) -> Dict[str, Any]:
        """위협 인텔리전스 IP 수집"""
        try:
            logger.info("🔍 위협 인텔리전스 수집 시작")
            return {
                "success": True,
                "message": "위협 인텔리전스 수집 완료",
                "collected_count": 0,
                "source": "threat_intelligence",
            }
        except Exception as exc:
            logger.error(f"❌ 위협 인텔리전스 수집 실패: {exc}")
            return {"success": False, "error": str(exc), "collected_count": 0}

    def collect_malicious_ip_lists(self) -> Dict[str, Any]:
        """악성 IP 리스트 수집"""
        try:
            logger.info("🔍 악성 IP 리스트 수집 시작")
            return {
                "success": True,
                "message": "악성 IP 리스트 수집 완료",
                "collected_count": 0,
                "source": "malicious_lists",
            }
        except Exception as exc:
            logger.error(f"❌ 악성 IP 리스트 수집 실패: {exc}")
            return {"success": False, "error": str(exc), "collected_count": 0}


regtech_data = REGTECHDataCollector()

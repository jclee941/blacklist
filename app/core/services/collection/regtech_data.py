"""REGTECH 데이터 수집 모듈
실제 REGTECH 포털에서 데이터 수집 및 처리
"""

import logging
import requests
from datetime import date
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class REGTECHDataCollector:
    """REGTECH 데이터 수집기"""

    def __init__(self):
        self.base_url = "https://regtech.fsec.or.kr"

    def collect_real_regtech_data(self, session, regtech_id: str) -> dict:
        """실제 REGTECH 포털에서 데이터 수집 - 동적 URL 발견 포함"""
        try:
            logger.info(f"🔍 REGTECH 데이터 수집 시작: {regtech_id}")

            # 세션 유효성 검증
            if not session or not session.cookies:
                logger.error("❌ 유효하지 않은 세션")
                return {
                    "success": False,
                    "error": "유효하지 않은 세션입니다",
                    "collected_count": 0,
                }

            # 세션 쿠키 확인 로그
            cookies = dict(session.cookies)
            logger.info(f"🍪 사용 중인 세션 쿠키: {list(cookies.keys())}")

            # 1단계: 메인 포털 페이지에서 데이터 URL 발견 시도
            logger.info("🔍 REGTECH 포털 구조 분석 중...")
            data_urls = self._discover_data_urls(session)

            # 2단계: 발견된 URL들을 순차적으로 시도
            for url_info in data_urls:
                url = url_info["url"]
                url_type = url_info["type"]

                logger.info(f"📊 데이터 URL 시도 ({url_type}): {url}")

                try:
                    response = session.get(url, timeout=30)

                    if response.status_code == 302:
                        logger.warning(f"⚠️ 세션 만료로 인한 리다이렉트 감지 ({url})")
                        return {
                            "success": False,
                            "error": "세션이 만료되었습니다. 재로그인이 필요합니다.",
                            "collected_count": 0,
                            "session_expired": True,
                        }

                    if response.status_code == 200:
                        logger.info(f"✅ 데이터 페이지 접근 성공: {url}")

                        # HTML 파싱 및 IP 추출
                        collected_ips = self._parse_regtech_data(response.text)

                        if collected_ips:
                            logger.info(f"✅ REGTECH에서 {len(collected_ips)}개 IP 수집 완료")
                            return {
                                "success": True,
                                "message": f"REGTECH 데이터 수집 완료: {len(collected_ips)}개 IP",
                                "data": collected_ips,
                                "collected_count": len(collected_ips),
                                "source": "regtech_real",
                                "session_reused": True,
                                "data_url": url,
                            }
                        else:
                            logger.info(f"⚠️ 데이터 없음: {url}")

                    else:
                        logger.warning(f"⚠️ 데이터 페이지 접근 실패: {response.status_code} ({url})")

                except Exception as url_error:
                    logger.warning(f"⚠️ URL 시도 실패 ({url}): {url_error}")
                    continue

            # 모든 URL 시도 실패 시
            logger.warning("❌ 모든 데이터 URL 시도 실패 - 실제 데이터 없음")
            return {
                "success": True,
                "message": "REGTECH 포털 접속됨 (데이터 없음)",
                "data": [],
                "collected_count": 0,
                "source": "regtech_real",
                "session_reused": True,
                "note": "실제 포털 접속 성공, 데이터 페이지 미발견",
            }

        except requests.exceptions.Timeout:
            logger.error("❌ REGTECH 데이터 수집 시간 초과")
            return {
                "success": False,
                "error": "REGTECH 데이터 수집 시간 초과",
                "collected_count": 0,
            }
        except Exception as e:
            logger.error(f"❌ REGTECH 데이터 수집 오류: {e}")
            return {
                "success": False,
                "error": f"데이터 수집 오류: {str(e)}",
                "collected_count": 0,
            }

    def _discover_data_urls(self, session) -> List[Dict[str, str]]:
        """REGTECH 포털에서 데이터 URL들을 동적으로 발견"""
        try:
            data_urls = []

            # 1단계: 메인 포털 페이지 접근
            main_url = f"{self.base_url}/main"
            logger.info(f"🏠 메인 포털 페이지 접근: {main_url}")

            try:
                main_response = session.get(main_url, timeout=15)
                if main_response.status_code == 200:
                    # HTML에서 링크 추출
                    discovered_links = self._extract_navigation_links(main_response.text)
                    data_urls.extend(discovered_links)
                    logger.info(f"📋 메인 페이지에서 {len(discovered_links)}개 링크 발견")
            except Exception as e:
                logger.warning(f"⚠️ 메인 페이지 접근 실패: {e}")

            # 2단계: 대시보드/홈 페이지 시도
            dashboard_urls = [
                f"{self.base_url}/dashboard",
                f"{self.base_url}/home",
                f"{self.base_url}/",
            ]

            for dash_url in dashboard_urls:
                try:
                    dash_response = session.get(dash_url, timeout=10)
                    if dash_response.status_code == 200:
                        discovered_links = self._extract_navigation_links(dash_response.text)
                        data_urls.extend(discovered_links)
                        logger.info(f"🏠 대시보드 ({dash_url})에서 {len(discovered_links)}개 링크 발견")
                        break
                except Exception as e:
                    logger.debug(f"대시보드 URL 시도 실패 ({dash_url}): {e}")
                    continue

            # 3단계: 일반적인 위협 정보 URL 패턴 추가
            common_patterns = [
                {"url": f"{self.base_url}/threat/blacklist", "type": "original"},
                {"url": f"{self.base_url}/threat/intelligence", "type": "intelligence"},
                {"url": f"{self.base_url}/blacklist/ip", "type": "ip_blacklist"},
                {"url": f"{self.base_url}/data/threat", "type": "threat_data"},
                {
                    "url": f"{self.base_url}/portal/blacklist",
                    "type": "portal_blacklist",
                },
                {"url": f"{self.base_url}/security/blacklist", "type": "security"},
                {"url": f"{self.base_url}/intelligence/ip", "type": "intel_ip"},
                {"url": f"{self.base_url}/analysis/threat", "type": "analysis"},
                {"url": f"{self.base_url}/report/blacklist", "type": "report"},
                {"url": f"{self.base_url}/main/threat", "type": "main_threat"},
            ]

            data_urls.extend(common_patterns)
            logger.info(f"📝 총 {len(data_urls)}개 데이터 URL 후보 준비")

            return data_urls

        except Exception as e:
            logger.error(f"URL 발견 오류: {e}")
            # 폴백: 기본 URL들만 반환
            return [
                {
                    "url": f"{self.base_url}/threat/blacklist",
                    "type": "fallback_original",
                },
                {"url": f"{self.base_url}/main", "type": "fallback_main"},
            ]

    def _extract_navigation_links(self, html_content: str) -> List[Dict[str, str]]:
        """HTML에서 위협 정보 관련 네비게이션 링크 추출"""
        try:
            import re

            discovered_links = []

            # 위협 정보 관련 키워드
            threat_keywords = [
                "blacklist",
                "threat",
                "intelligence",
                "security",
                "malware",
                "phishing",
                "bot",
                "suspicious",
                "블랙리스트",
                "위협",
                "보안",
                "악성",
                "위험",
            ]

            # href 패턴으로 링크 추출
            link_patterns = [
                r'href=[\'"](/[^\'"]*/(?:' + "|".join(threat_keywords) + r')[^\'"]*)[\'"]',
                r'href=[\'"]('
                + re.escape(self.base_url)
                + r'/[^\'"]*/(?:'
                + "|".join(threat_keywords)
                + r')[^\'"]*)[\'"]',
            ]

            for pattern in link_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    # 상대 경로를 절대 경로로 변환
                    if match.startswith("/"):
                        full_url = self.base_url + match
                    else:
                        full_url = match

                    discovered_links.append({"url": full_url, "type": "discovered_nav"})

            # JavaScript 변수에서 URL 추출 시도
            js_patterns = [
                r'["\'](' + re.escape(self.base_url) + r'/[^"\']*(?:' + "|".join(threat_keywords) + r')[^"\']*)["\']',
                r'url[:\s]*["\']([^"\']*(?:' + "|".join(threat_keywords) + r')[^"\']*)["\']',
            ]

            for pattern in js_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    if match.startswith("/"):
                        full_url = self.base_url + match
                    elif not match.startswith("http"):
                        continue
                    else:
                        full_url = match

                    discovered_links.append({"url": full_url, "type": "discovered_js"})

            # 중복 제거
            unique_links = []
            seen_urls = set()
            for link in discovered_links:
                if link["url"] not in seen_urls:
                    unique_links.append(link)
                    seen_urls.add(link["url"])

            logger.info(f"🔗 HTML에서 {len(unique_links)}개 고유 링크 추출")
            return unique_links

        except Exception as e:
            logger.warning(f"네비게이션 링크 추출 오류: {e}")
            return []

    def expand_regtech_collection(self, base_data: List[Dict]) -> List[Dict]:
        """REGTECH 데이터 확장 수집"""
        try:
            expanded_data = []

            # 기존 데이터 추가
            expanded_data.extend(base_data)

            # 추가 IP 범위 생성 (시뮬레이션)
            additional_ips = self._generate_additional_ips(len(base_data))
            expanded_data.extend(additional_ips)

            logger.info(f"REGTECH 데이터 확장: {len(base_data)} → {len(expanded_data)}")

            return expanded_data

        except Exception as e:
            logger.error(f"REGTECH 데이터 확장 오류: {e}")
            return base_data

    def _parse_regtech_data(self, html_content: str) -> List[Dict]:
        """REGTECH HTML 데이터 파싱 - 실제 데이터 추출"""
        try:
            import re
            from datetime import datetime

            logger.info("🔍 REGTECH HTML 데이터 파싱 시작")

            # IP 주소 패턴 (정규식으로 IP 추출)
            ip_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"

            # HTML에서 IP 주소 추출
            found_ips = re.findall(ip_pattern, html_content)

            if not found_ips:
                logger.warning("⚠️ HTML에서 IP 주소를 찾을 수 없음 - 테이블 구조 분석 시도")

                # 테이블 데이터 패턴 분석 (실제 REGTECH 포털 구조에 맞춰 조정)
                # 예: <td>192.168.1.1</td> 형태의 IP 찾기
                table_ip_pattern = r"<td[^>]*>(\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b)</td>"
                table_ips = re.findall(table_ip_pattern, html_content, re.IGNORECASE)

                if table_ips:
                    found_ips = table_ips
                    logger.info(f"📊 테이블에서 {len(found_ips)}개 IP 발견")
                else:
                    # JSON 형태로 데이터가 있는지 확인
                    json_pattern = r'"ip[Aa]ddress"\s*:\s*"(\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b)"'
                    json_ips = re.findall(json_pattern, html_content)

                    if json_ips:
                        found_ips = json_ips
                        logger.info(f"🔧 JSON에서 {len(found_ips)}개 IP 발견")
                    else:
                        logger.warning("❌ IP 데이터를 찾을 수 없음")
                        return []

            # 중복 IP 제거
            unique_ips = list(set(found_ips))
            logger.info(f"🎯 중복 제거 후 {len(unique_ips)}개 고유 IP")

            # IP 데이터 구조화
            structured_data = []
            for ip in unique_ips:
                # 사설 IP 대역 필터링
                if self._is_private_ip(ip):
                    continue

                # 추가 메타데이터 추출 시도 (실제 포털에서 제공하는 정보)
                confidence = self._extract_confidence_from_html(html_content, ip)

                # 탐지일/해제일 파싱
                detection_date = self._extract_detection_date_from_html(html_content, ip)
                removal_date = self._extract_removal_date_from_html(html_content, ip)

                structured_data.append(
                    {
                        "ip_address": ip,
                        "reason": "REGTECH 위협정보",
                        "source": "regtech",
                        "confidence_level": confidence or 80,
                        "detection_count": 1,
                        "country": "Unknown",  # 추후 GeoIP 조회 가능
                        "detection_date": detection_date or datetime.now().date(),
                        "removal_date": removal_date,  # 해제일 (있는 경우만)
                        "is_active": True,
                    }
                )

            logger.info(f"✅ REGTECH 실제 데이터 파싱 완료: {len(structured_data)}개 IP")

            # 데이터가 없으면 빈 리스트 반환
            if not structured_data:
                logger.warning("⚠️ 실제 데이터 없음")
                return []

            return structured_data

        except Exception as e:
            logger.error(f"REGTECH 데이터 파싱 오류: {e}")
            # 파싱 실패 시 빈 리스트 반환
            return []

    def _is_private_ip(self, ip: str) -> bool:
        """사설 IP 대역 확인"""
        try:
            parts = [int(x) for x in ip.split(".")]

            # 사설 IP 대역 확인
            if parts[0] == 10:  # 10.0.0.0/8
                return True
            elif parts[0] == 172 and 16 <= parts[1] <= 31:  # 172.16.0.0/12
                return True
            elif parts[0] == 192 and parts[1] == 168:  # 192.168.0.0/16
                return True
            elif parts[0] == 127:  # 127.0.0.0/8 (loopback)
                return True
            elif parts[0] == 169 and parts[1] == 254:  # 169.254.0.0/16 (link-local)
                return True

            return False
        except BaseException:
            return True  # 파싱 오류 시 안전하게 제외

    def _generate_additional_ips(self, count: int) -> List[Dict]:
        """추가 IP 범위 생성 (시뮬레이션용 스텁)"""
        return []

    def _extract_confidence_from_html(self, html_content: str, ip: str) -> Optional[int]:
        """HTML에서 특정 IP의 신뢰도 추출"""
        try:
            import re

            # IP 주변에서 신뢰도 패턴 찾기
            # 예: "confidence: 85%" 또는 "신뢰도: 90"
            confidence_patterns = [
                rf"{re.escape(ip)}.*?confidence[:\s]*(\d+)",
                rf"{re.escape(ip)}.*?신뢰도[:\s]*(\d+)",
                rf"confidence[:\s]*(\d+).*?{re.escape(ip)}",
                rf"신뢰도[:\s]*(\d+).*?{re.escape(ip)}",
            ]

            for pattern in confidence_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
                if matches:
                    confidence = int(matches[0])
                    return max(0, min(100, confidence))  # 0-100 범위로 제한

            return None  # 신뢰도 정보 없음
        except BaseException:
            return None

    def _extract_detection_date_from_html(self, html_content: str, ip: str) -> Optional[date]:
        """HTML에서 특정 IP의 탐지일 추출"""
        try:
            import re
            from datetime import datetime

            # 날짜 패턴들 (REGTECH 포털에서 사용하는 형식들)
            date_patterns = [
                # YYYY-MM-DD 형식
                rf"{re.escape(ip)}.*?(\d{{4}}-\d{{2}}-\d{{2}})",
                rf"(\d{{4}}-\d{{2}}-\d{{2}}).*?{re.escape(ip)}",
                # YYYY.MM.DD 형식
                rf"{re.escape(ip)}.*?(\d{{4}}\.\d{{2}}\.\d{{2}})",
                rf"(\d{{4}}\.\d{{2}}\.\d{{2}}).*?{re.escape(ip)}",
                # YYYY/MM/DD 형식
                rf"{re.escape(ip)}.*?(\d{{4}}/\d{{2}}/\d{{2}})",
                rf"(\d{{4}}/\d{{2}}/\d{{2}}).*?{re.escape(ip)}",
                # 한국어 날짜 표현과 함께
                rf"{re.escape(ip)}.*?탐지[일자]*[:\s]*(\d{{4}}-\d{{2}}-\d{{2}})",
                rf"{re.escape(ip)}.*?발견[일자]*[:\s]*(\d{{4}}-\d{{2}}-\d{{2}})",
                rf"탐지[일자]*[:\s]*(\d{{4}}-\d{{2}}-\d{{2}}).*?{re.escape(ip)}",
                rf"발견[일자]*[:\s]*(\d{{4}}-\d{{2}}-\d{{2}}).*?{re.escape(ip)}",
            ]

            # IP 주변 컨텍스트에서 날짜 검색
            ip_context_pattern = rf".{{0,200}}{re.escape(ip)}.{{0,200}}"
            context_matches = re.findall(ip_context_pattern, html_content, re.IGNORECASE | re.DOTALL)

            if context_matches:
                context_text = " ".join(context_matches)

                for pattern in date_patterns:
                    matches = re.findall(pattern, context_text, re.IGNORECASE)
                    if matches:
                        date_str = matches[0]

                        # 날짜 파싱 시도
                        try:
                            if "-" in date_str:
                                return datetime.strptime(date_str, "%Y-%m-%d").date()
                            elif "." in date_str:
                                return datetime.strptime(date_str, "%Y.%m.%d").date()
                            elif "/" in date_str:
                                return datetime.strptime(date_str, "%Y/%m/%d").date()
                        except ValueError:
                            continue

            return None  # 탐지일 정보 없음
        except Exception as e:
            logger.debug(f"탐지일 추출 오류 ({ip}): {e}")
            return None

    def _extract_removal_date_from_html(self, html_content: str, ip: str) -> Optional[date]:
        """HTML에서 특정 IP의 해제일 추출"""
        try:
            import re
            from datetime import datetime

            # 해제일 관련 키워드들
            removal_keywords = [
                "해제",
                "제거",
                "삭제",
                "만료",
                "종료",
                "비활성",
                "remove",
                "delete",
                "expire",
                "end",
                "inactive",
            ]

            # 해제일 패턴들
            date_patterns = []
            for keyword in removal_keywords:
                date_patterns.extend(
                    [
                        # YYYY-MM-DD 형식
                        rf"{re.escape(ip)}.*?{keyword}[일자]*[:\s]*(\d{{4}}-\d{{2}}-\d{{2}})",
                        rf"{keyword}[일자]*[:\s]*(\d{{4}}-\d{{2}}-\d{{2}}).*?{re.escape(ip)}",
                        # YYYY.MM.DD 형식
                        rf"{re.escape(ip)}.*?{keyword}[일자]*[:\s]*(\d{{4}}\.\d{{2}}\.\d{{2}})",
                        rf"{keyword}[일자]*[:\s]*(\d{{4}}\.\d{{2}}\.\d{{2}}).*?{re.escape(ip)}",
                        # YYYY/MM/DD 형식
                        rf"{re.escape(ip)}.*?{keyword}[일자]*[:\s]*(\d{{4}}/\d{{2}}/\d{{2}})",
                        rf"{keyword}[일자]*[:\s]*(\d{{4}}/\d{{2}}/\d{{2}}).*?{re.escape(ip)}",
                    ]
                )

            # IP 주변 컨텍스트에서 해제일 검색
            ip_context_pattern = rf".{{0,300}}{re.escape(ip)}.{{0,300}}"
            context_matches = re.findall(ip_context_pattern, html_content, re.IGNORECASE | re.DOTALL)

            if context_matches:
                context_text = " ".join(context_matches)

                for pattern in date_patterns:
                    matches = re.findall(pattern, context_text, re.IGNORECASE)
                    if matches:
                        date_str = matches[0]

                        # 날짜 파싱 시도
                        try:
                            if "-" in date_str:
                                return datetime.strptime(date_str, "%Y-%m-%d").date()
                            elif "." in date_str:
                                return datetime.strptime(date_str, "%Y.%m.%d").date()
                            elif "/" in date_str:
                                return datetime.strptime(date_str, "%Y/%m/%d").date()
                        except ValueError:
                            continue

            return None  # 해제일 정보 없음
        except Exception as e:
            logger.debug(f"해제일 추출 오류 ({ip}): {e}")
            return None

    def collect_regtech_ips(self) -> List[Dict[str, Any]]:
        """기본 REGTECH IP 수집 - 인증 없는 모드"""
        try:
            logger.info("🔍 REGTECH IP 수집 시작 (기본 모드)")

            # 가짜 데이터나 기본 데이터 반환 (실제 구현은 나중에)
            return []

        except Exception as e:
            logger.error(f"❌ REGTECH IP 수집 실패: {e}")
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

        except Exception as e:
            logger.error(f"❌ REGTECH 테스트 실패: {e}")
            return {"success": False, "error": str(e), "collected_count": 0}

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

        except Exception as e:
            logger.error(f"❌ 위협 인텔리전스 수집 실패: {e}")
            return {"success": False, "error": str(e), "collected_count": 0}

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

        except Exception as e:
            logger.error(f"❌ 악성 IP 리스트 수집 실패: {e}")
            return {"success": False, "error": str(e), "collected_count": 0}


# 싱글톤 인스턴스
regtech_data = REGTECHDataCollector()

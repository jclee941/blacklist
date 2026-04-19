"""REGTECH HTML 파싱/데이터 처리 로직."""

import logging
import re
from datetime import date, datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def extract_navigation_links(base_url: str, html_content: str) -> List[Dict[str, str]]:
    """HTML에서 위협 정보 관련 네비게이션 링크 추출"""
    try:
        discovered_links = []
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
        link_patterns = [
            r'href=[\'"](/[^\'"]*/(?:' + "|".join(threat_keywords) + r')[^\'"]*)[\'"]',
            r'href=[\'"](' + re.escape(base_url) + r'/[^\'"]*/(?:' + "|".join(threat_keywords) + r')[^\'"]*)[\'"]',
        ]

        for pattern in link_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                full_url = base_url + match if match.startswith("/") else match
                discovered_links.append({"url": full_url, "type": "discovered_nav"})

        js_patterns = [
            r'["\'](' + re.escape(base_url) + r'/[^"\']*(?:' + "|".join(threat_keywords) + r')[^"\']*)["\']',
            r'url[:\s]*["\']([^"\']*(?:' + "|".join(threat_keywords) + r')[^"\']*)["\']',
        ]
        for pattern in js_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if match.startswith("/"):
                    full_url = base_url + match
                elif not match.startswith("http"):
                    continue
                else:
                    full_url = match
                discovered_links.append({"url": full_url, "type": "discovered_js"})

        unique_links = []
        seen_urls = set()
        for link in discovered_links:
            if link["url"] not in seen_urls:
                unique_links.append(link)
                seen_urls.add(link["url"])

        logger.info(f"🔗 HTML에서 {len(unique_links)}개 고유 링크 추출")
        return unique_links
    except Exception as exc:
        logger.warning(f"네비게이션 링크 추출 오류: {exc}")
        return []


def expand_regtech_collection(base_data: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """REGTECH 데이터 확장 수집"""
    try:
        expanded_data = []
        expanded_data.extend(base_data)
        additional_ips = _generate_additional_ips(len(base_data))
        expanded_data.extend(additional_ips)
        logger.info(f"REGTECH 데이터 확장: {len(base_data)} → {len(expanded_data)}")
        return expanded_data
    except Exception as exc:
        logger.error(f"REGTECH 데이터 확장 오류: {exc}")
        return base_data


def parse_regtech_data(html_content: str) -> List[Dict[str, object]]:
    """REGTECH HTML 데이터 파싱 - 실제 데이터 추출"""
    try:
        logger.info("🔍 REGTECH HTML 데이터 파싱 시작")
        ip_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
        found_ips = re.findall(ip_pattern, html_content)

        if not found_ips:
            logger.warning("⚠️ HTML에서 IP 주소를 찾을 수 없음 - 테이블 구조 분석 시도")
            table_ip_pattern = r"<td[^>]*>(\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b)</td>"
            table_ips = re.findall(table_ip_pattern, html_content, re.IGNORECASE)
            if table_ips:
                found_ips = table_ips
                logger.info(f"📊 테이블에서 {len(found_ips)}개 IP 발견")
            else:
                json_pattern = r'"ip[Aa]ddress"\s*:\s*"(\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b)"'
                json_ips = re.findall(json_pattern, html_content)
                if json_ips:
                    found_ips = json_ips
                    logger.info(f"🔧 JSON에서 {len(found_ips)}개 IP 발견")
                else:
                    logger.warning("❌ IP 데이터를 찾을 수 없음")
                    return []

        unique_ips = list(set(found_ips))
        logger.info(f"🎯 중복 제거 후 {len(unique_ips)}개 고유 IP")
        structured_data = []
        for ip in unique_ips:
            if is_private_ip(ip):
                continue

            confidence = extract_confidence_from_html(html_content, ip)
            detection_date = extract_detection_date_from_html(html_content, ip)
            removal_date = extract_removal_date_from_html(html_content, ip)
            structured_data.append(
                {
                    "ip_address": ip,
                    "reason": "REGTECH 위협정보",
                    "source": "regtech",
                    "confidence_level": confidence or 80,
                    "detection_count": 1,
                    "country": "Unknown",
                    "detection_date": detection_date or datetime.now().date(),
                    "removal_date": removal_date,
                    "is_active": True,
                }
            )

        logger.info(f"✅ REGTECH 실제 데이터 파싱 완료: {len(structured_data)}개 IP")
        if not structured_data:
            logger.warning("⚠️ 실제 데이터 없음")
            return []
        return structured_data
    except Exception as exc:
        logger.error(f"REGTECH 데이터 파싱 오류: {exc}")
        return []


def is_private_ip(ip: str) -> bool:
    """사설 IP 대역 확인"""
    try:
        parts = [int(x) for x in ip.split(".")]
        if parts[0] == 10:
            return True
        if parts[0] == 172 and 16 <= parts[1] <= 31:
            return True
        if parts[0] == 192 and parts[1] == 168:
            return True
        if parts[0] == 127:
            return True
        if parts[0] == 169 and parts[1] == 254:
            return True
        return False
    except BaseException:
        return True


def _generate_additional_ips(count: int) -> List[Dict[str, object]]:
    """추가 IP 범위 생성 (시뮬레이션용 스텁)"""
    return []


def extract_confidence_from_html(html_content: str, ip: str) -> Optional[int]:
    """HTML에서 특정 IP의 신뢰도 추출"""
    try:
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
                return max(0, min(100, confidence))
        return None
    except BaseException:
        return None


def extract_detection_date_from_html(html_content: str, ip: str) -> Optional[date]:
    """HTML에서 특정 IP의 탐지일 추출"""
    try:
        date_patterns = [
            rf"{re.escape(ip)}.*?(\d{{4}}-\d{{2}}-\d{{2}})",
            rf"(\d{{4}}-\d{{2}}-\d{{2}}).*?{re.escape(ip)}",
            rf"{re.escape(ip)}.*?(\d{{4}}\.\d{{2}}\.\d{{2}})",
            rf"(\d{{4}}\.\d{{2}}\.\d{{2}}).*?{re.escape(ip)}",
            rf"{re.escape(ip)}.*?(\d{{4}}/\d{{2}}/\d{{2}})",
            rf"(\d{{4}}/\d{{2}}/\d{{2}}).*?{re.escape(ip)}",
            rf"{re.escape(ip)}.*?탐지[일자]*[:\s]*(\d{{4}}-\d{{2}}-\d{{2}})",
            rf"{re.escape(ip)}.*?발견[일자]*[:\s]*(\d{{4}}-\d{{2}}-\d{{2}})",
            rf"탐지[일자]*[:\s]*(\d{{4}}-\d{{2}}-\d{{2}}).*?{re.escape(ip)}",
            rf"발견[일자]*[:\s]*(\d{{4}}-\d{{2}}-\d{{2}}).*?{re.escape(ip)}",
        ]
        ip_context_pattern = rf".{{0,200}}{re.escape(ip)}.{{0,200}}"
        context_matches = re.findall(ip_context_pattern, html_content, re.IGNORECASE | re.DOTALL)
        if context_matches:
            context_text = " ".join(context_matches)
            for pattern in date_patterns:
                matches = re.findall(pattern, context_text, re.IGNORECASE)
                if matches:
                    return _parse_supported_date(matches[0])
        return None
    except Exception as exc:
        logger.debug(f"탐지일 추출 오류 ({ip}): {exc}")
        return None


def extract_removal_date_from_html(html_content: str, ip: str) -> Optional[date]:
    """HTML에서 특정 IP의 해제일 추출"""
    try:
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
        date_patterns = []
        for keyword in removal_keywords:
            date_patterns.extend(
                [
                    rf"{re.escape(ip)}.*?{keyword}[일자]*[:\s]*(\d{{4}}-\d{{2}}-\d{{2}})",
                    rf"{keyword}[일자]*[:\s]*(\d{{4}}-\d{{2}}-\d{{2}}).*?{re.escape(ip)}",
                    rf"{re.escape(ip)}.*?{keyword}[일자]*[:\s]*(\d{{4}}\.\d{{2}}\.\d{{2}})",
                    rf"{keyword}[일자]*[:\s]*(\d{{4}}\.\d{{2}}\.\d{{2}}).*?{re.escape(ip)}",
                    rf"{re.escape(ip)}.*?{keyword}[일자]*[:\s]*(\d{{4}}/\d{{2}}/\d{{2}})",
                    rf"{keyword}[일자]*[:\s]*(\d{{4}}/\d{{2}}/\d{{2}}).*?{re.escape(ip)}",
                ]
            )

        ip_context_pattern = rf".{{0,300}}{re.escape(ip)}.{{0,300}}"
        context_matches = re.findall(ip_context_pattern, html_content, re.IGNORECASE | re.DOTALL)
        if context_matches:
            context_text = " ".join(context_matches)
            for pattern in date_patterns:
                matches = re.findall(pattern, context_text, re.IGNORECASE)
                if matches:
                    return _parse_supported_date(matches[0])
        return None
    except Exception as exc:
        logger.debug(f"해제일 추출 오류 ({ip}): {exc}")
        return None


def _parse_supported_date(date_str: str) -> Optional[date]:
    try:
        if "-" in date_str:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        if "." in date_str:
            return datetime.strptime(date_str, "%Y.%m.%d").date()
        if "/" in date_str:
            return datetime.strptime(date_str, "%Y/%m/%d").date()
        return None
    except ValueError:
        return None

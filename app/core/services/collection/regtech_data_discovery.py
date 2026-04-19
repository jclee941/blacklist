"""REGTECH 포털 접속/URL 발견 로직."""

import logging

import requests

from .regtech_data_processing import extract_navigation_links, parse_regtech_data

logger = logging.getLogger(__name__)


def collect_real_regtech_data(base_url: str, session, regtech_id: str) -> dict[str, object]:
    """실제 REGTECH 포털에서 데이터 수집 - 동적 URL 발견 포함"""
    try:
        logger.info(f"🔍 REGTECH 데이터 수집 시작: {regtech_id}")
        if not session or not session.cookies:
            logger.error("❌ 유효하지 않은 세션")
            return {
                "success": False,
                "error": "유효하지 않은 세션입니다",
                "collected_count": 0,
            }

        cookies = dict(session.cookies)
        logger.info(f"🍪 사용 중인 세션 쿠키: {list(cookies.keys())}")
        logger.info("🔍 REGTECH 포털 구조 분석 중...")
        data_urls = discover_data_urls(base_url, session)

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
                    collected_ips = parse_regtech_data(response.text)
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

                    logger.info(f"⚠️ 데이터 없음: {url}")
                else:
                    logger.warning(f"⚠️ 데이터 페이지 접근 실패: {response.status_code} ({url})")
            except Exception as url_error:
                logger.warning(f"⚠️ URL 시도 실패 ({url}): {url_error}")
                continue

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
    except Exception as exc:
        logger.error(f"❌ REGTECH 데이터 수집 오류: {exc}")
        return {
            "success": False,
            "error": f"데이터 수집 오류: {str(exc)}",
            "collected_count": 0,
        }


def discover_data_urls(base_url: str, session):
    """REGTECH 포털에서 데이터 URL들을 동적으로 발견"""
    try:
        data_urls = []
        main_url = f"{base_url}/main"
        logger.info(f"🏠 메인 포털 페이지 접근: {main_url}")

        try:
            main_response = session.get(main_url, timeout=15)
            if main_response.status_code == 200:
                discovered_links = extract_navigation_links(base_url, main_response.text)
                data_urls.extend(discovered_links)
                logger.info(f"📋 메인 페이지에서 {len(discovered_links)}개 링크 발견")
        except Exception as exc:
            logger.warning(f"⚠️ 메인 페이지 접근 실패: {exc}")

        dashboard_urls = [
            f"{base_url}/dashboard",
            f"{base_url}/home",
            f"{base_url}/",
        ]
        for dash_url in dashboard_urls:
            try:
                dash_response = session.get(dash_url, timeout=10)
                if dash_response.status_code == 200:
                    discovered_links = extract_navigation_links(base_url, dash_response.text)
                    data_urls.extend(discovered_links)
                    logger.info(f"🏠 대시보드 ({dash_url})에서 {len(discovered_links)}개 링크 발견")
                    break
            except Exception as exc:
                logger.debug(f"대시보드 URL 시도 실패 ({dash_url}): {exc}")
                continue

        common_patterns = [
            {"url": f"{base_url}/threat/blacklist", "type": "original"},
            {"url": f"{base_url}/threat/intelligence", "type": "intelligence"},
            {"url": f"{base_url}/blacklist/ip", "type": "ip_blacklist"},
            {"url": f"{base_url}/data/threat", "type": "threat_data"},
            {"url": f"{base_url}/portal/blacklist", "type": "portal_blacklist"},
            {"url": f"{base_url}/security/blacklist", "type": "security"},
            {"url": f"{base_url}/intelligence/ip", "type": "intel_ip"},
            {"url": f"{base_url}/analysis/threat", "type": "analysis"},
            {"url": f"{base_url}/report/blacklist", "type": "report"},
            {"url": f"{base_url}/main/threat", "type": "main_threat"},
        ]
        data_urls.extend(common_patterns)
        logger.info(f"📝 총 {len(data_urls)}개 데이터 URL 후보 준비")
        return data_urls
    except Exception as exc:
        logger.error(f"URL 발견 오류: {exc}")
        return [
            {"url": f"{base_url}/threat/blacklist", "type": "fallback_original"},
            {"url": f"{base_url}/main", "type": "fallback_main"},
        ]

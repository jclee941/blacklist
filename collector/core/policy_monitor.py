#!/usr/bin/env python3
"""
REGTECH 포털 정책 변경 모니터링 시스템
- 포털 구조 변경 감지
- 데이터 제공 상태 모니터링
- 관리자 알림 시스템
"""

import logging
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import requests
from bs4 import BeautifulSoup  # type: ignore[import-untyped]
import psycopg2  # type: ignore[import-untyped]
from psycopg2.extras import RealDictCursor  # type: ignore[import-untyped]


logger = logging.getLogger(__name__)


class REGTECHPolicyMonitor:
    """REGTECH 포털 정책 변경 모니터링 시스템"""

    def __init__(self, config):
        self.config = config
        self.base_url = config.get("regtech_base_url", "https://regtech.fsec.or.kr")
        self.session = requests.Session()
        self.session.timeout = 30

        # 모니터링 상태 저장소
        self.last_check_time = None
        self.baseline_structure = None
        self.baseline_headers = None
        self.data_availability_history = []

        # 변경 감지 임계값
        self.structure_change_threshold = 0.15  # 15% 이상 변경 시 알림
        self.consecutive_no_data_threshold = 5  # 5회 연속 데이터 없음 시 알림

    def _get_db_connection(self):
        """데이터베이스 연결"""
        return psycopg2.connect(
            host=self.config.get("postgres_host", "blacklist-postgres"),
            port=self.config.get("postgres_port", 5432),
            database=self.config.get("postgres_db", "blacklist"),
            user=self.config.get("postgres_user", "postgres"),
            password=self.config.get("postgres_password", "postgres"),
            cursor_factory=RealDictCursor,
        )

    def _authenticate_regtech(self) -> bool:
        """REGTECH 포털 인증 (Updated 2025-12-22)"""
        try:
            # FIXED: 올바른 로그인 엔드포인트 사용
            login_page_url = f"{self.base_url}/login/loginForm"
            auth_url = f"{self.base_url}/login/addLogin"  # 수정: /login/login -> /login/addLogin

            # User-Agent 설정 (필수)
            self.session.headers.update(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "ko-KR,ko;q=0.9",
                    "Referer": login_page_url,
                }
            )

            # 로그인 페이지 접근 (세션 쿠키 획득)
            response = self.session.get(login_page_url)
            logger.info(f"Login page status: {response.status_code}")

            # 로그인 데이터 (loginForm 필드와 일치)
            login_data = {
                "username": self.config.get("regtech_id", ""),
                "password": self.config.get("regtech_pw", ""),
                "login_error": "",
                "smsTimeExcess": "N",
                "txId": "",
                "token": "",
                "memberId": "",
            }

            # 로그인 요청
            login_response = self.session.post(auth_url, data=login_data, allow_redirects=True)
            logger.info(f"Login response status: {login_response.status_code}, URL: {login_response.url}")

            # 인증 성공 확인 (로그아웃 버튼, 마이페이지, 또는 메인 페이지 리다이렉트)
            if "로그아웃" in login_response.text or "마이페이지" in login_response.text:
                logger.info("✅ REGTECH 인증 성공")
                return True
            elif "/main" in login_response.url:
                logger.info("✅ REGTECH 인증 성공 (메인 페이지 리다이렉트)")
                return True
            else:
                logger.error(f"❌ REGTECH 인증 실패 (redirect to: {login_response.url})")
                # 에러 메시지 추출
                soup = BeautifulSoup(login_response.text, "html.parser")
                error_msg = soup.find(id="login_error")
                if error_msg and error_msg.get("value"):
                    logger.error(f"Login error: {error_msg.get('value')}")
                return False

        except Exception as e:
            logger.error(f"REGTECH 인증 중 오류: {e}")
            return False

    def _get_portal_structure_fingerprint(self) -> Dict[str, Any]:
        """포털 구조 지문 생성"""
        try:
            # 메인 페이지 구조 분석
            main_url = f"{self.base_url}/blacklist"
            response = self.session.get(main_url)
            soup = BeautifulSoup(response.text, "html.parser")

            # 구조 요소 추출
            structure_data: Dict[str, Any] = {
                "forms": len(soup.find_all("form")),
                "tables": len(soup.find_all("table")),
                "inputs": len(soup.find_all("input")),
                "selects": len(soup.find_all("select")),
                "buttons": len(soup.find_all("button")),
                "scripts": len(soup.find_all("script")),
                "css_links": len(soup.find_all("link", {"rel": "stylesheet"})),
            }

            # HTML 구조 해시
            html_structure = " ".join([tag.name for tag in soup.find_all()])
            structure_data["html_hash"] = hashlib.md5(html_structure.encode("utf-8")).hexdigest()[:16]

            # 주요 텍스트 콘텐츠 해시 (정책 변경 감지용)
            main_text = soup.get_text(separator=" ", strip=True)
            structure_data["content_hash"] = hashlib.md5(main_text.encode("utf-8")).hexdigest()[:16]

            # 테이블 헤더 정보 (데이터 구조 변경 감지용)
            table_headers = []
            for table in soup.find_all("table"):
                headers = [th.get_text(strip=True) for th in table.find_all("th")]
                if headers:
                    table_headers.append(headers)

            structure_data["table_headers"] = table_headers
            structure_data["timestamp"] = datetime.now().isoformat()

            return structure_data

        except Exception as e:
            logger.error(f"포털 구조 분석 중 오류: {e}")
            return {}

    def _check_data_availability(self) -> Dict[str, Any]:
        """데이터 제공 상태 확인"""
        try:
            # 최근 7일간 데이터 확인
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)

            # 블랙리스트 페이지 접근
            blacklist_url = f"{self.base_url}/blacklist"

            # 날짜 범위로 조회
            search_data = {
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "page_size": 10,
            }

            response = self.session.post(blacklist_url, data=search_data)
            soup = BeautifulSoup(response.text, "html.parser")

            availability_info: Dict[str, Any] = {
                "timestamp": datetime.now().isoformat(),
                "status": "unknown",
                "data_count": 0,
                "response_size": len(response.text),
                "has_data_table": False,
                "error_messages": [],
            }

            # 데이터 존재 여부 확인
            if "데이터가 없습니다" in response.text or "조회된 데이터가 없습니다" in response.text:
                availability_info["status"] = "no_data"
                availability_info["error_messages"].append("No data available message found")
            elif response.text and "오류" in response.text:
                availability_info["status"] = "error"
                error_text = soup.find(text=lambda text: text and "오류" in text)
                if error_text:
                    availability_info["error_messages"].append(str(error_text).strip())
            else:
                # 데이터 테이블 확인
                data_table = soup.find("table")
                if data_table:
                    availability_info["has_data_table"] = True
                    rows = data_table.find_all("tr")
                    # 헤더 제외하고 데이터 행 수 계산
                    availability_info["data_count"] = max(0, len(rows) - 1)
                    availability_info["status"] = "data_available" if len(rows) > 1 else "no_data"
                else:
                    availability_info["status"] = "no_table"

            return availability_info

        except Exception as e:
            logger.error(f"데이터 가용성 확인 중 오류: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error_messages": [str(e)],
            }

    def _compare_structures(self, current: Dict, baseline: Dict) -> Dict[str, Any]:
        """구조 변경 사항 비교"""
        if not baseline:
            return {"change_detected": False, "message": "No baseline to compare"}

        changes: Dict[str, Any] = {
            "change_detected": False,
            "changes": [],
            "change_percentage": 0.0,
            "severity": "low",
        }

        # 구조 요소 변경 확인
        structure_keys = [
            "forms",
            "tables",
            "inputs",
            "selects",
            "buttons",
            "scripts",
            "css_links",
        ]
        changed_elements = 0
        total_elements = len(structure_keys)

        for key in structure_keys:
            if current.get(key, 0) != baseline.get(key, 0):
                changed_elements += 1
                changes["changes"].append(f"{key}: {baseline.get(key, 0)} → {current.get(key, 0)}")

        # 해시 변경 확인
        if current.get("html_hash") != baseline.get("html_hash"):
            changes["changes"].append("HTML 구조 해시 변경됨")
            changed_elements += 1
            total_elements += 1

        if current.get("content_hash") != baseline.get("content_hash"):
            changes["changes"].append("콘텐츠 해시 변경됨")
            changed_elements += 1
            total_elements += 1

        # 테이블 헤더 변경 확인
        current_headers = current.get("table_headers", [])
        baseline_headers = baseline.get("table_headers", [])

        if current_headers != baseline_headers:
            changes["changes"].append("테이블 헤더 구조 변경됨")
            changed_elements += 1
            total_elements += 1

        # 변경 비율 계산
        if total_elements > 0:
            changes["change_percentage"] = (changed_elements / total_elements) * 100

        # 변경 감지 및 심각도 설정
        if changes["change_percentage"] > self.structure_change_threshold * 100:
            changes["change_detected"] = True
            if changes["change_percentage"] > 50:
                changes["severity"] = "high"
            elif changes["change_percentage"] > 25:
                changes["severity"] = "medium"
            else:
                changes["severity"] = "low"

        return changes

    def _store_monitoring_data(self, structure_data: Dict, availability_data: Dict, change_analysis: Dict):
        """모니터링 데이터 저장"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            # 모니터링 테이블이 없으면 생성
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS regtech_monitoring (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    structure_data JSONB,
                    availability_data JSONB,
                    change_analysis JSONB,
                    alert_sent BOOLEAN DEFAULT FALSE
                )
            """
            )

            # 데이터 삽입
            cursor.execute(
                """
                INSERT INTO regtech_monitoring 
                (structure_data, availability_data, change_analysis)
                VALUES (%s, %s, %s)
            """,
                (
                    json.dumps(structure_data),
                    json.dumps(availability_data),
                    json.dumps(change_analysis),
                ),
            )

            conn.commit()
            cursor.close()
            conn.close()

            logger.info("모니터링 데이터 저장 완료")

        except Exception as e:
            logger.error(f"모니터링 데이터 저장 중 오류: {e}")

    def _send_alert(self, alert_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """관리자 알림 전송"""
        try:
            # 데이터베이스에 알림 로그 저장
            conn = self._get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS regtech_alerts (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    alert_type VARCHAR(50),
                    message TEXT,
                    details JSONB,
                    resolved BOOLEAN DEFAULT FALSE
                )
            """
            )

            cursor.execute(
                """
                INSERT INTO regtech_alerts (alert_type, message, details)
                VALUES (%s, %s, %s)
            """,
                (alert_type, message, json.dumps(details or {})),
            )

            conn.commit()
            cursor.close()
            conn.close()

            logger.warning(f"알림 발송: [{alert_type}] {message}")

            # 실제 알림 시스템 연동 (이메일, Slack 등)
            # 여기에 실제 알림 로직 구현

        except Exception as e:
            logger.error(f"알림 전송 중 오류: {e}")

    def _check_consecutive_no_data(self) -> bool:
        """연속 데이터 부재 확인"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            # 최근 확인 기록에서 연속 no_data 상태 확인
            cursor.execute(
                """
                SELECT availability_data->>'status' as status
                FROM regtech_monitoring 
                ORDER BY timestamp DESC 
                LIMIT %s
            """,
                (self.consecutive_no_data_threshold,),
            )

            results = cursor.fetchall()
            cursor.close()
            conn.close()

            if len(results) >= self.consecutive_no_data_threshold:
                no_data_count = sum(1 for r in results if r["status"] == "no_data")
                return no_data_count >= self.consecutive_no_data_threshold

            return False

        except Exception as e:
            logger.error(f"연속 데이터 부재 확인 중 오류: {e}")
            return False

    def run_monitoring_check(self) -> Dict[str, Any]:
        """모니터링 검사 실행"""
        logger.info("REGTECH 포털 모니터링 검사 시작")

        try:
            # 인증
            if not self._authenticate_regtech():
                return {
                    "success": False,
                    "error": "Authentication failed",
                    "timestamp": datetime.now().isoformat(),
                }

            # 현재 포털 구조 분석
            current_structure = self._get_portal_structure_fingerprint()

            # 데이터 가용성 확인
            availability_data = self._check_data_availability()

            # 베이스라인과 비교
            change_analysis = self._compare_structures(current_structure, self.baseline_structure)

            # 모니터링 데이터 저장
            self._store_monitoring_data(current_structure, availability_data, change_analysis)

            # 알림 조건 확인
            alerts_sent = []

            # 1. 구조 변경 알림
            if change_analysis.get("change_detected", False):
                alert_message = f"REGTECH 포털 구조 변경 감지 ({change_analysis['change_percentage']:.1f}% 변경)"
                self._send_alert("structure_change", alert_message, change_analysis)
                alerts_sent.append("structure_change")

            # 2. 연속 데이터 부재 알림
            if self._check_consecutive_no_data():
                alert_message = f"REGTECH 포털에서 {self.consecutive_no_data_threshold}회 연속 데이터 부재"
                self._send_alert("consecutive_no_data", alert_message, availability_data)
                alerts_sent.append("consecutive_no_data")

            # 3. 새로운 데이터 감지 알림
            if availability_data.get("status") == "data_available" and availability_data.get("data_count", 0) > 0:
                # 이전에 데이터가 없었다면 알림
                self._send_alert(
                    "data_available",
                    f"REGTECH 포털에 새로운 데이터 감지 ({availability_data['data_count']}개)",
                    availability_data,
                )
                alerts_sent.append("data_available")

            # 베이스라인 업데이트 (구조 변경이 확정된 경우)
            if change_analysis.get("change_detected", False) and change_analysis.get("severity") != "high":
                self.baseline_structure = current_structure
                logger.info("베이스라인 구조 업데이트")

            # 베이스라인이 없다면 현재 구조를 베이스라인으로 설정
            if not self.baseline_structure:
                self.baseline_structure = current_structure
                logger.info("초기 베이스라인 구조 설정")

            self.last_check_time = datetime.now()

            return {
                "success": True,
                "timestamp": self.last_check_time.isoformat(),
                "structure_changes": change_analysis,
                "data_availability": availability_data,
                "alerts_sent": alerts_sent,
                "baseline_updated": not self.baseline_structure == current_structure,
            }

        except Exception as e:
            logger.error(f"모니터링 검사 중 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_monitoring_summary(self, days: int = 7) -> Dict[str, Any]:
        """모니터링 요약 정보"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()

            # 최근 N일간 모니터링 데이터
            cursor.execute(
                """
                SELECT 
                    COUNT(*) as total_checks,
                    COUNT(CASE WHEN availability_data->>'status' = 'data_available' THEN 1 END) as data_available_count,
                    COUNT(CASE WHEN availability_data->>'status' = 'no_data' THEN 1 END) as no_data_count,
                    COUNT(CASE WHEN change_analysis->>'change_detected' = 'true' THEN 1 END) as structure_changes,
                    MAX(timestamp) as last_check
                FROM regtech_monitoring 
                WHERE timestamp >= NOW() - INTERVAL '%s days'
            """,
                (days,),
            )

            summary = dict(cursor.fetchone())

            # 최근 알림 조회
            cursor.execute(
                """
                SELECT alert_type, COUNT(*) as count
                FROM regtech_alerts 
                WHERE timestamp >= NOW() - INTERVAL '%s days'
                GROUP BY alert_type
            """,
                (days,),
            )

            alerts_summary = {row["alert_type"]: row["count"] for row in cursor.fetchall()}

            cursor.close()
            conn.close()

            return {
                "period_days": days,
                "monitoring_summary": summary,
                "alerts_summary": alerts_summary,
                "last_update": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"모니터링 요약 조회 중 오류: {e}")
            return {"error": str(e)}

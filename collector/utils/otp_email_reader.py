#!/usr/bin/env python3
"""
SECUDIUM OTP Email Auto-Reader

Purpose: IMAP으로 이메일에서 SECUDIUM OTP 코드 자동 추출
"""

import imaplib
import email
from email.header import decode_header
import re
from typing import Optional
import time
import structlog

logger = structlog.get_logger()


class OTPEmailReader:
    """Email에서 SECUDIUM OTP 코드를 자동으로 읽어오는 클래스"""

    def __init__(
        self,
        email_address: str,
        email_password: str,
        imap_server: str = "imap.kakao.com",
    ):
        """
        Args:
            email_address: SECUDIUM 가입 이메일
            email_password: 이메일 비밀번호 (또는 앱 비밀번호)
            imap_server: IMAP 서버 주소 (기본: imap.kakao.com)
        """
        self.email_address = email_address
        self.email_password = email_password
        self.imap_server = imap_server
        self.imap = None

    def connect(self) -> bool:
        """IMAP 서버 연결"""
        try:
            self.imap = imaplib.IMAP4_SSL(self.imap_server)
            self.imap.login(self.email_address, self.email_password)
            logger.info("email_imap_connected", server=self.imap_server)
            return True
        except Exception as e:
            logger.error("email_imap_connection_failed", error=str(e))
            return False

    def disconnect(self):
        """IMAP 연결 종료"""
        if self.imap:
            try:
                self.imap.close()
                self.imap.logout()
                logger.info("email_imap_disconnected")
            except Exception:
                pass

    def get_latest_otp(self, max_wait_seconds: int = 60) -> Optional[str]:
        """
        최신 SECUDIUM OTP 이메일에서 코드 추출

        로그인 step 1 이전에 이미 존재하던 OTP 이메일을 무시하고,
        step 1 이후에 새로 도착한 OTP 이메일만 읽습니다.

        Args:
            max_wait_seconds: OTP 이메일 대기 최대 시간 (초)

        Returns:
            6자리 OTP 코드 또는 None
        """
        if not self.connect():
            return None

        try:
            # INBOX 선택
            self.imap.select("INBOX")

            search_criteria = '(OR (OR (OR FROM "secudium" FROM "skinfosec") SUBJECT "SECUDIUM") SUBJECT "OTP")'

            initial_latest_id = None
            status, messages = self.imap.search(None, search_criteria)
            if status == "OK" and messages[0]:
                email_ids = messages[0].split()
                initial_latest_id = email_ids[-1]
                logger.info(
                    "otp_initial_snapshot",
                    latest_email_id=initial_latest_id.decode(),
                    total_otp_emails=len(email_ids),
                )

            start_time = time.time()
            otp_code = None

            while time.time() - start_time < max_wait_seconds:
                # IMAP NOOP으로 메일박스 새로고침 (새 이메일 감지)
                self.imap.noop()

                status, messages = self.imap.search(None, search_criteria)

                if status == "OK" and messages[0]:
                    email_ids = messages[0].split()
                    latest_email_id = email_ids[-1]

                    if initial_latest_id and latest_email_id == initial_latest_id:
                        logger.info(
                            "otp_waiting_for_new_email",
                            elapsed=int(time.time() - start_time),
                        )
                        time.sleep(3)
                        continue

                    status, msg_data = self.imap.fetch(latest_email_id, "(RFC822)")

                    if status == "OK":
                        raw_email = msg_data[0][1]
                        msg = email.message_from_bytes(raw_email)

                        subject = self._decode_header(msg["Subject"])
                        logger.info("email_found", subject=subject, email_id=latest_email_id.decode())

                        otp_code = self._extract_otp_from_message(msg)

                        if otp_code:
                            logger.info("otp_code_extracted", code_length=len(otp_code))
                            break

                # OTP 못 찾으면 3초 대기 후 재시도
                if not otp_code:
                    logger.info("otp_waiting", elapsed=int(time.time() - start_time))
                    time.sleep(3)

            if not otp_code:
                logger.warning(
                    "otp_timeout",
                    max_wait_seconds=max_wait_seconds,
                    initial_id=initial_latest_id.decode() if initial_latest_id else "none",
                )

            return otp_code

        except Exception as e:
            logger.error("otp_extraction_failed", error=str(e))
            return None
        finally:
            self.disconnect()

    def _decode_header(self, header: str) -> str:
        """이메일 헤더 디코딩"""
        if not header:
            return ""

        decoded_parts = decode_header(header)
        decoded_str = ""

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_str += part.decode(encoding or "utf-8", errors="ignore")
            else:
                decoded_str += part

        return decoded_str

    def _extract_otp_from_message(self, msg) -> Optional[str]:
        """이메일 제목 또는 본문에서 OTP 코드 추출

        SK쉴더스 Secudium OTP 이메일은 제목에 OTP 코드를 포함:
        예: [SK쉴더스] OTP[538542] 인증 번호
        """

        # 1) 제목에서 OTP 추출 (SK쉴더스 형식: OTP[XXXXXX])
        subject = self._decode_header(msg.get("Subject", ""))
        subject_patterns = [
            r"OTP\[(\d{6})\]",  # OTP[538542]
            r"OTP[:\s]+(\d{6})",  # OTP: 538542
        ]
        for pattern in subject_patterns:
            match = re.search(pattern, subject)
            if match:
                otp_code = match.group(1)
                logger.info("otp_extracted_from_subject", code_length=len(otp_code), subject=subject)
                return otp_code

        # 2) 본문에서 OTP 추출 (폴백)
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain" or content_type == "text/html":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode("utf-8", errors="ignore")
                    except Exception:
                        pass
        else:
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode("utf-8", errors="ignore")
            except Exception:
                pass

        logger.debug("email_body_extracted", length=len(body))

        body_patterns = [
            r"OTP\[(\d{6})\]",  # OTP[123456]
            r"OTP[:\s]+(\d{6})",  # OTP: 123456
            r"인증번호[:\s]+(\d{6})",  # 인증번호: 123456
            r"확인번호[:\s]+(\d{6})",  # 확인번호: 123456
            r"코드[:\s]+(\d{6})",  # 코드: 123456
            r"[^0-9](\d{6})[^0-9]",  # 6자리 숫자 (일반)
        ]

        for pattern in body_patterns:
            match = re.search(pattern, body)
            if match:
                otp_code = match.group(1)
                logger.info("otp_extracted_from_body", pattern=pattern, code_length=len(otp_code))
                return otp_code

        logger.warning("otp_not_found", subject=subject, body_preview=body[:200])
        return None


def test_otp_reader():
    """테스트 함수"""
    import os

    # 환경 변수에서 이메일 정보 읽기
    email_address = os.getenv("SECUDIUM_EMAIL")
    email_password = os.getenv("SECUDIUM_EMAIL_PASSWORD")

    if not email_address or not email_password:
        print("환경 변수 설정 필요:")
        print("export SECUDIUM_EMAIL='your_email@example.com'")
        print("export SECUDIUM_EMAIL_PASSWORD='your_password'")
        return

    reader = OTPEmailReader(email_address, email_password)

    print("OTP 이메일 대기 중... (최대 60초)")
    otp_code = reader.get_latest_otp(max_wait_seconds=60)

    if otp_code:
        print(f"✅ OTP 코드 추출 성공: {otp_code}")
    else:
        print("❌ OTP 코드를 찾을 수 없습니다")


if __name__ == "__main__":
    import structlog

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    )
    test_otp_reader()

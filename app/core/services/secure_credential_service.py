"""
🔐 보안 인증정보 관리 서비스
REGTECH Blacklist Intelligence Platform - Secure Credential Management Service
Version: 1.0.0 (September 2025)

데이터베이스 기반 암호화된 인증정보 저장 및 관리
- AES-256 암호화 기반 안전한 저장
- 환경변수 기반 암호화 키 관리
- 다중 서비스 지원 (REGTECH, CloudFlare, 기타)
- 자동 암호화/복호화 처리
- 활성/비활성 상태 관리
"""

import json
import base64
from datetime import datetime
from typing import Dict, Optional, List, Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..config import config
from .credential.crypto import decrypt_data, encrypt_data, setup_encryption
from .credential.database import close_connection, get_database_connection
from .credential.helpers import (
    delete_regtech_credentials,
    get_regtech_credentials,
    migrate_existing_credentials as migrate_existing_credentials_impl,
    save_regtech_credentials,
    secure_credential_service,
    validate_credentials as validate_credentials_impl,
    validate_regtech_credentials,
)

import logging

logger = logging.getLogger(__name__)


class SecureCredentialService:
    """보안 인증정보 관리 서비스 - 암호화된 DB 저장"""

    def __init__(self, db_service=None):
        """서비스 초기화"""
        self.db_service = db_service
        self._cipher_suite = None
        self._salt = None
        self._setup_encryption()

    def _setup_encryption(self):
        """암호화 키 설정"""
        setup_encryption(self, config, logger, base64, Fernet, PBKDF2HMAC, hashes)

    def _get_database_connection(self):
        """데이터베이스 연결 획득

        Returns:
            Connection object (never None - raises on failure)

        Raises:
            RuntimeError: If database connection cannot be established
        """
        return get_database_connection(self)

    def _close_connection(self, conn):
        """데이터베이스 연결 반환"""
        close_connection(self, conn, logger)

    def _encrypt_data(self, data: str) -> str:
        """데이터 암호화"""
        return encrypt_data(self, data, logger, base64)

    def _decrypt_data(self, encrypted_data: str) -> str:
        """데이터 복호화"""
        return decrypt_data(self, encrypted_data, logger, base64)

    def save_credentials(
        self,
        service_name: str,
        username: str,
        password: str,
        config: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
        collection_interval: int = 86400,
    ) -> bool:
        """
        암호화된 인증정보 저장

        Args:
            service_name: 서비스명 (REGTECH, CLOUDFLARE 등)
            username: 사용자명
            password: 비밀번호
            config: 추가 설정 정보
            enabled: 활성화 여부
            collection_interval: 수집 주기 (초)

        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 데이터 준비
            credential_data = {
                "username": username,
                "password": password,
                "config": config or {},
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
            }

            # JSON 직렬화 및 암호화
            json_data = json.dumps(credential_data)
            encrypted_data = self._encrypt_data(json_data)

            # 데이터베이스 저장
            conn = self._get_database_connection()
            cursor = conn.cursor()

            # UPSERT 쿼리 실행
            cursor.execute(
                """
                INSERT INTO collection_credentials
                (
                    service_name, username, password, config,
                    encrypted, is_active, enabled,
                    collection_interval, source, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (service_name)
                DO UPDATE SET
                    username = EXCLUDED.username,
                    password = EXCLUDED.password,
                    config = EXCLUDED.config,
                    encrypted = EXCLUDED.encrypted,
                    is_active = EXCLUDED.is_active,
                    enabled = EXCLUDED.enabled,
                    collection_interval = EXCLUDED.collection_interval,
                    source = EXCLUDED.source,
                    updated_at = EXCLUDED.updated_at
            """,
                (
                    service_name.upper(),
                    username,  # 평문 저장 (호환성)
                    encrypted_data,  # 암호화된 패스워드
                    json.dumps(config or {}),
                    True,  # encrypted 플래그
                    True,  # is_active
                    enabled,
                    collection_interval,
                    service_name.upper(),
                    datetime.now(),
                ),
            )

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"✅ {service_name} 인증정보 암호화 저장 완료: {username}")
            return True

        except Exception as e:
            logger.error(f"❌ {service_name} 인증정보 저장 실패: {e}")
            return False

    def update_credential_settings(
        self,
        service_name: str,
        username: str,
        enabled: bool,
        collection_interval: int,
    ) -> bool:
        try:
            conn = self._get_database_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT password, encrypted FROM collection_credentials WHERE service_name = %s",
                (service_name.upper(),),
            )
            result = cursor.fetchone()

            if not result:
                logger.warning(f"⚠️ {service_name} 인증정보를 찾을 수 없음 (업데이트 실패)")
                cursor.close()
                self._close_connection(conn)
                return False

            current_password, is_encrypted = result
            new_password_payload = current_password

            if is_encrypted and current_password:
                try:
                    decrypted_json = self._decrypt_data(current_password)
                    credential_data = json.loads(decrypted_json)

                    if credential_data.get("username") != username:
                        logger.info(f"🔄 {service_name} 사용자명 변경 감지: 내부 페이로드 업데이트")
                        credential_data["username"] = username
                        credential_data["updated_at"] = datetime.now().isoformat()

                        new_json = json.dumps(credential_data)
                        new_password_payload = self._encrypt_data(new_json)
                except Exception as e:
                    logger.error(f"❌ {service_name} 내부 페이로드 업데이트 실패 (기존 패스워드 유지): {e}")

            cursor.execute(
                """
                UPDATE collection_credentials
                SET
                    username = %s,
                    password = %s,
                    enabled = %s,
                    collection_interval = %s,
                    is_active = TRUE,
                    updated_at = %s
                WHERE service_name = %s
                """,
                (
                    username,
                    new_password_payload,
                    enabled,
                    collection_interval,
                    datetime.now(),
                    service_name.upper(),
                ),
            )

            affected_rows = cursor.rowcount
            conn.commit()
            cursor.close()
            self._close_connection(conn)

            if affected_rows > 0:
                logger.info(f"✅ {service_name} 인증정보 설정 업데이트 완료")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"❌ {service_name} 인증정보 설정 업데이트 실패: {e}")
            return False

    def get_credentials(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        암호화된 인증정보 조회

        Args:
            service_name: 서비스명

        Returns:
            Dict: 복호화된 인증정보 또는 None
        """
        try:
            conn = self._get_database_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    username, password, config, encrypted,
                    created_at, updated_at, enabled,
                    collection_interval, last_collection
                FROM collection_credentials
                WHERE service_name = %s AND is_active = true
            """,
                (service_name.upper(),),
            )

            result = cursor.fetchone()
            cursor.close()
            self._close_connection(conn)

            if not result:
                logger.warning(f"⚠️ {service_name} 인증정보를 찾을 수 없음")
                return None

            (
                username,
                password,
                config,
                encrypted,
                created_at,
                updated_at,
                enabled,
                collection_interval,
                last_collection,
            ) = result

            if encrypted:
                # 암호화된 데이터 복호화
                try:
                    decrypted_json = self._decrypt_data(password)
                    credential_data = json.loads(decrypted_json)

                    return {
                        "username": credential_data.get("username", username),
                        "password": credential_data.get("password", ""),
                        "config": credential_data.get("config", {}),
                        "service_name": service_name,
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "enabled": enabled,
                        "collection_interval": collection_interval,
                        "last_collection": last_collection,
                        "encrypted": True,
                    }
                except Exception as decrypt_error:
                    logger.error(f"❌ {service_name} 인증정보 복호화 실패: {decrypt_error}")
                    return None
            else:
                # 평문 데이터 (기존 호환성)
                return {
                    "username": username,
                    "password": password,
                    "config": config if config else {},
                    "service_name": service_name,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "enabled": enabled,
                    "collection_interval": collection_interval,
                    "last_collection": last_collection,
                    "encrypted": False,
                }

        except Exception as e:
            logger.error(f"❌ {service_name} 인증정보 조회 실패: {e}")
            return None

    def list_credentials(self) -> List[Dict[str, Any]]:
        """모든 활성 인증정보 목록 조회 (비밀번호 제외)"""
        try:
            conn = self._get_database_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT service_name, username, encrypted, created_at, updated_at, is_active
                FROM collection_credentials
                WHERE is_active = true
                ORDER BY service_name
            """)

            results = cursor.fetchall()
            cursor.close()
            self._close_connection(conn)

            credentials_list = []
            for row in results:
                service_name, username, encrypted, created_at, updated_at, is_active = row
                credentials_list.append(
                    {
                        "service_name": service_name,
                        "username": username,
                        "encrypted": bool(encrypted),
                        "has_password": bool(username),  # username이 있으면 password도 있다고 가정
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "is_active": is_active,
                    }
                )

            return credentials_list

        except Exception as e:
            logger.error(f"❌ 인증정보 목록 조회 실패: {e}")
            return []

    def delete_credentials(self, service_name: str) -> bool:
        """인증정보 삭제 (논리적 삭제 - is_active = false)"""
        try:
            conn = self._get_database_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE collection_credentials
                SET is_active = false, updated_at = %s
                WHERE service_name = %s
            """,
                (datetime.now(), service_name.upper()),
            )

            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()
            self._close_connection(conn)

            if deleted_count > 0:
                logger.info(f"✅ {service_name} 인증정보 삭제 완료")
                return True
            else:
                logger.warning(f"⚠️ {service_name} 인증정보가 존재하지 않음")
                return False

        except Exception as e:
            logger.error(f"❌ {service_name} 인증정보 삭제 실패: {e}")
            return False

    def activate_credentials(self, service_name: str) -> bool:
        """인증정보 활성화"""
        try:
            conn = self._get_database_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE collection_credentials
                SET is_active = true, updated_at = %s
                WHERE service_name = %s
            """,
                (datetime.now(), service_name.upper()),
            )

            updated_count = cursor.rowcount
            conn.commit()
            cursor.close()
            self._close_connection(conn)

            if updated_count > 0:
                logger.info(f"✅ {service_name} 인증정보 활성화 완료")
                return True
            else:
                logger.warning(f"⚠️ {service_name} 인증정보가 존재하지 않음")
                return False

        except Exception as e:
            logger.error(f"❌ {service_name} 인증정보 활성화 실패: {e}")
            return False

    def validate_credentials(self, service_name: str) -> Dict[str, Any]:
        """인증정보 유효성 검증"""
        return validate_credentials_impl(self, service_name, logger)

    def migrate_existing_credentials(self) -> Dict[str, Any]:
        """기존 평문 인증정보를 암호화된 형태로 마이그레이션"""
        return migrate_existing_credentials_impl(self, logger)


if __name__ == "__main__":
    # 테스트 코드
    logger.info("🔐 보안 인증정보 서비스 테스트")

    # 테스트 저장
    test_result = save_regtech_credentials("test_user", "test_password")
    logger.info(f"저장 테스트: {'✅ 성공' if test_result else '❌ 실패'}")

    # 테스트 조회
    credentials = get_regtech_credentials()
    if credentials:
        logger.info(f"조회 테스트: ✅ 성공 - {credentials['username']}")
    else:
        logger.info("조회 테스트: ❌ 실패")

    # 유효성 검증
    validation = validate_regtech_credentials()
    logger.info(f"검증 테스트: {'✅ 유효' if validation['valid'] else '❌ 무효'}")

    # 마이그레이션 테스트
    migration_result = secure_credential_service.migrate_existing_credentials()
    logger.info(f"마이그레이션: {migration_result['migrated_count']}개 완료")

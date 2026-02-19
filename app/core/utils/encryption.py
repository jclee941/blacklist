"""
암호화 유틸리티 모듈
인증 정보와 민감한 데이터를 안전하게 암호화/복호화
"""

import base64
import hashlib
import os
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional, Dict, Any

from ..config import config

logger = logging.getLogger(__name__)


class CredentialEncryption:
    """인증 정보 암호화 클래스"""

    def __init__(self, master_key: Optional[str] = None):
        """
        암호화 인스턴스 초기화

        Args:
            master_key: 마스터 키 (없으면 환경변수나 자동 생성)
        """
        self.master_key = master_key or self._get_or_create_master_key()
        self.fernet = self._create_fernet_instance()

    def _get_or_create_master_key(self) -> str:
        """마스터 키 획득 또는 생성"""
        # 1. Docker Compose Secret에서 키 확인
        secret_file = "/run/secrets/credential_master_key"
        if os.path.exists(secret_file):
            try:
                with open(secret_file, "r") as f:
                    secret_key = f.read().strip()
                    logger.info("Docker Secret에서 마스터 키 로드")
                    return secret_key
            except Exception as e:
                logger.warning(f"Docker Secret 파일 읽기 실패: {e}")

        # 2. 환경변수에서 키 확인 (폴백)
        env_key = config.CREDENTIAL_MASTER_KEY
        if env_key:
            logger.info("환경변수에서 마스터 키 로드 (폴백)")
            return env_key

        # 3. 파일에서 키 확인 (폴백)
        key_file = "/app/config/.master_key"
        if os.path.exists(key_file):
            try:
                with open(key_file, "r") as f:
                    file_key = f.read().strip()
                    logger.info("파일에서 마스터 키 로드 (폴백)")
                    return file_key
            except Exception as e:
                logger.warning(f"키 파일 읽기 실패: {e}")

        # 4. 새로운 키 생성 (최종 폴백)
        new_key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        logger.info("새로운 마스터 키 생성 (최종 폴백)")

        # 키 파일에 저장 시도 (개발 환경 등에서 사용)
        try:
            os.makedirs("/app/config", exist_ok=True)
            with open(key_file, "w") as f:
                f.write(new_key)
            logger.info("새로운 마스터 키를 파일에 저장")
        except Exception as e:
            logger.warning(f"새로운 마스터 키 파일 저장 실패: {e}")

        return new_key

    def _create_fernet_instance(self) -> Fernet:
        """Fernet 암호화 인스턴스 생성"""
        # 마스터 키에서 암호화 키 파생 (고정 솔트 사용으로 일관된 복호화 보장)
        # Collector와 동일한 고정 솔트 사용
        salt_env = config.ENCRYPTION_SALT
        salt = salt_env.encode() if salt_env else b"blacklist-regtech-salt-2025"

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key_bytes = self.master_key if isinstance(self.master_key, bytes) else self.master_key.encode()
        key = base64.urlsafe_b64encode(kdf.derive(key_bytes))
        return Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """
        문자열 암호화

        Args:
            plaintext: 암호화할 평문

        Returns:
            str: 암호화된 문자열 (Base64 인코딩)
        """
        try:
            if not plaintext:
                return ""

            encrypted_bytes = self.fernet.encrypt(plaintext.encode("utf-8"))
            encrypted_string = base64.urlsafe_b64encode(encrypted_bytes).decode()
            logger.debug("문자열 암호화 완료")
            return encrypted_string

        except Exception as e:
            logger.error(f"암호화 실패: {e}")
            raise EncryptionError(f"암호화 실패: {e}")

    def decrypt(self, encrypted_string: str) -> str:
        """
        문자열 복호화

        Args:
            encrypted_string: 암호화된 문자열 (Base64 인코딩)

        Returns:
            str: 복호화된 평문
        """
        try:
            if not encrypted_string:
                return ""

            encrypted_bytes = base64.urlsafe_b64decode(encrypted_string.encode())
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            decrypted_string = decrypted_bytes.decode("utf-8")
            logger.debug("문자열 복호화 완료")
            return decrypted_string

        except Exception as e:
            logger.error(f"복호화 실패: {e}")
            raise EncryptionError(f"복호화 실패: {e}")

    def encrypt_credentials(self, username: str, password: str) -> Dict[str, Any]:
        """
        인증 정보 암호화

        Args:
            username: 사용자명
            password: 비밀번호

        Returns:
            dict: 암호화된 인증 정보
        """
        try:
            return {
                "username": self.encrypt(username),
                "password": self.encrypt(password),
                "encrypted": True,
                "encryption_version": "1.0",
            }
        except Exception as e:
            logger.error(f"인증 정보 암호화 실패: {e}")
            raise EncryptionError(f"인증 정보 암호화 실패: {e}")

    def decrypt_credentials(self, encrypted_data: Dict[str, str]) -> Dict[str, str]:
        """
        인증 정보 복호화

        Args:
            encrypted_data: 암호화된 인증 정보

        Returns:
            dict: 복호화된 인증 정보
        """
        try:
            if not encrypted_data.get("encrypted", False):
                # 암호화되지 않은 데이터는 그대로 반환
                return {
                    "username": encrypted_data.get("username", ""),
                    "password": encrypted_data.get("password", ""),
                }

            return {
                "username": self.decrypt(encrypted_data["username"]),
                "password": self.decrypt(encrypted_data["password"]),
            }
        except Exception as e:
            logger.error(f"인증 정보 복호화 실패: {e}")
            raise EncryptionError(f"인증 정보 복호화 실패: {e}")

    def create_password_hash(self, password: str) -> str:
        """
        비밀번호 해시 생성 (단방향)

        Args:
            password: 원본 비밀번호

        Returns:
            str: SHA256 해시값
        """
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password_hash(self, password: str, hash_value: str) -> bool:
        """
        비밀번호 해시 검증

        Args:
            password: 검증할 비밀번호
            hash_value: 저장된 해시값

        Returns:
            bool: 일치 여부
        """
        return self.create_password_hash(password) == hash_value


class EncryptionError(Exception):
    """암호화 관련 예외"""


# 글로벌 암호화 인스턴스
encryption_service = CredentialEncryption()


def encrypt_string(plaintext: str) -> str:
    """편의 함수: 문자열 암호화"""
    return encryption_service.encrypt(plaintext)


def decrypt_string(encrypted_string: str) -> str:
    """편의 함수: 문자열 복호화"""
    return encryption_service.decrypt(encrypted_string)


def encrypt_credentials(username: str, password: str) -> Dict[str, str]:
    """편의 함수: 인증 정보 암호화"""
    return encryption_service.encrypt_credentials(username, password)


def decrypt_credentials(encrypted_data: Dict[str, str]) -> Dict[str, str]:
    """편의 함수: 인증 정보 복호화"""
    return encryption_service.decrypt_credentials(encrypted_data)

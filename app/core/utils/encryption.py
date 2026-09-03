"""
암호화 유틸리티 모듈
인증 정보와 민감한 데이터를 안전하게 암호화/복호화
"""

import base64
import hashlib
import os
import logging
from collections.abc import Mapping
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional

from ..config import config

logger = logging.getLogger(__name__)


class CredentialEncryption:
    """인증 정보 암호화 클래스"""

    def __init__(self, master_key: Optional[str] = None, salt: Optional[str] = None):
        """
        암호화 인스턴스 초기화

        Args:
            master_key: 마스터 키 (없으면 환경변수나 자동 생성)
        """
        self.master_key = master_key or self._get_or_create_master_key()
        resolved_salt = salt or config.ENCRYPTION_SALT
        if not resolved_salt:
            raise EncryptionError("ENCRYPTION_SALT is required")
        self.salt: str = resolved_salt
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

        raise EncryptionError("CREDENTIAL_MASTER_KEY is required")

    def _create_fernet_instance(self) -> Fernet:
        """Fernet 암호화 인스턴스 생성"""
        # 마스터 키에서 암호화 키 파생 (고정 솔트 사용으로 일관된 복호화 보장)
        # Collector와 동일한 고정 솔트 사용
        salt = self.salt.encode()

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

    def encrypt_credentials(self, username: str, password: str) -> dict[str, str | bool]:
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

    def decrypt_credentials(self, encrypted_data: Mapping[str, str | bool]) -> dict[str, str]:
        """
        인증 정보 복호화

        Args:
            encrypted_data: 암호화된 인증 정보

        Returns:
            dict: 복호화된 인증 정보
        """
        try:
            username = encrypted_data.get("username", "")
            password = encrypted_data.get("password", "")
            if not isinstance(username, str) or not isinstance(password, str):
                raise EncryptionError("Credential fields must be strings")
            if not encrypted_data.get("encrypted", False):
                # 암호화되지 않은 데이터는 그대로 반환
                return {
                    "username": username,
                    "password": password,
                }

            return {
                "username": self.decrypt(username),
                "password": self.decrypt(password),
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


class LazyCredentialEncryption:
    def __init__(self) -> None:
        self._service: CredentialEncryption | None = None

    def _get_service(self) -> CredentialEncryption:
        if self._service is None:
            self._service = CredentialEncryption()
        return self._service

    @property
    def fernet(self) -> Fernet:
        return self._get_service().fernet

    def encrypt(self, plaintext: str) -> str:
        return self._get_service().encrypt(plaintext)

    def decrypt(self, encrypted_string: str) -> str:
        return self._get_service().decrypt(encrypted_string)

    def encrypt_credentials(self, username: str, password: str) -> dict[str, str | bool]:
        return self._get_service().encrypt_credentials(username, password)

    def decrypt_credentials(self, encrypted_data: Mapping[str, str | bool]) -> dict[str, str]:
        return self._get_service().decrypt_credentials(encrypted_data)


encryption_service = LazyCredentialEncryption()


def encrypt_string(plaintext: str) -> str:
    """편의 함수: 문자열 암호화"""
    return encryption_service.encrypt(plaintext)


def decrypt_string(encrypted_string: str) -> str:
    """편의 함수: 문자열 복호화"""
    return encryption_service.decrypt(encrypted_string)


def encrypt_credentials(username: str, password: str) -> dict[str, str | bool]:
    """편의 함수: 인증 정보 암호화"""
    return encryption_service.encrypt_credentials(username, password)


def decrypt_credentials(encrypted_data: Mapping[str, str | bool]) -> dict[str, str]:
    """편의 함수: 인증 정보 복호화"""
    return encryption_service.decrypt_credentials(encrypted_data)

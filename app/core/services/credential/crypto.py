"""Crypto helpers for SecureCredentialService."""

from __future__ import annotations

from typing import Any


def setup_encryption(
    service: Any,
    app_config: Any,
    logger: Any,
    base64_module: Any,
    fernet_cls: Any,
    pbkdf2_cls: Any,
    hashes_module: Any,
) -> None:
    """Initialize the credential cipher without changing the algorithm."""
    try:
        master_key = app_config.CREDENTIAL_MASTER_KEY
        if not master_key:
            raise RuntimeError(
                "CREDENTIAL_MASTER_KEY environment variable is required. "
                "Generate with: python -c 'import secrets; print(secrets.token_hex(32))'"
            )

        salt_env = app_config.ENCRYPTION_SALT
        if not salt_env:
            raise RuntimeError("ENCRYPTION_SALT environment variable is required")
        service._salt = salt_env.encode()

        kdf = pbkdf2_cls(
            algorithm=hashes_module.SHA256(),
            length=32,
            salt=service._salt,
            iterations=100000,
        )
        key = base64_module.urlsafe_b64encode(kdf.derive(master_key.encode()))
        service._cipher_suite = fernet_cls(key)

        logger.info("🔐 암호화 시스템 초기화 완료")
    except Exception as exc:
        logger.error(f"❌ 암호화 시스템 초기화 실패: {exc}")
        raise


def encrypt_data(service: Any, data: str, logger: Any, base64_module: Any) -> str:
    """Encrypt credential payload data."""
    try:
        if service._cipher_suite is None:
            raise RuntimeError("Cipher suite not initialized")
        encrypted = service._cipher_suite.encrypt(data.encode())
        return base64_module.b64encode(encrypted).decode()
    except Exception as exc:
        logger.error(f"❌ 데이터 암호화 실패: {exc}")
        raise


def decrypt_data(service: Any, encrypted_data: str, logger: Any, base64_module: Any) -> str:
    """Decrypt credential payload data."""
    try:
        if service._cipher_suite is None:
            raise RuntimeError("Cipher suite not initialized")
        decoded = base64_module.b64decode(encrypted_data.encode())
        decrypted = service._cipher_suite.decrypt(decoded)
        return decrypted.decode()
    except Exception as exc:
        logger.error(f"❌ 데이터 복호화 실패: {exc}")
        raise

"""
Collector-specific exceptions
수집기 관련 커스텀 예외 클래스
"""


class CredentialError(Exception):
    """Base exception for credential-related errors"""

    pass


class CredentialNotFoundError(CredentialError):
    """Raised when required credentials are missing from DB"""

    def __init__(self, source: str):
        self.source = source
        super().__init__(
            f"{source.upper()} credentials not found in database. Please add credentials via API: POST /api/credentials"
        )


class CredentialDecryptionError(CredentialError):
    """Raised when credential decryption fails"""

    def __init__(self, source: str, original_error: Exception = None):
        self.source = source
        self.original_error = original_error
        super().__init__(f"Failed to decrypt {source.upper()} credentials: {str(original_error)}")


class MissingMasterKeyError(CredentialError):
    """Raised when CREDENTIAL_MASTER_KEY is not set"""

    def __init__(self):
        super().__init__(
            "CREDENTIAL_MASTER_KEY environment variable is not set. Cannot decrypt credentials from database."
        )

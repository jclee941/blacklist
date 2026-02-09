"""Mock FortiManager Configuration"""


class MockConfig:
    """Mock FortiManager/FortiGate 설정"""

    # 인증
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "admin"

    # API 설정
    API_VERSION = "7.4.0"
    BUILD_NUMBER = 2463

    # 세션 설정
    SESSION_TIMEOUT = 3600  # 1시간

    # ADOM 설정
    DEFAULT_ADOM = "root"

    # External Resource 설정
    DEFAULT_REFRESH_RATE = 5  # 5분

    # Mock 데이터
    MOCK_SERIAL_NUMBER = "FGVM0000000001"
    MOCK_HOSTNAME = "FortiGate-VM64"
    MOCK_MODEL = "FortiGate-VM64"

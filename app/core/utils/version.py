"""
공통 버전 유틸리티
"""

import logging
from pathlib import Path

from ..config import config

logger = logging.getLogger(__name__)


def get_app_version():
    """앱 버전 정보 가져오기

    우선순위:
    1. APP_VERSION 환경변수
    2. VERSION 파일 + Git 정보
    3. VERSION 파일만
    4. 기본값 (0.0.0-dev)
    """
    # 환경변수에서 우선 가져오기
    version = config.APP_VERSION
    if version:
        return version

    # VERSION 파일 읽기
    try:
        version_file = Path(__file__).parents[3] / "VERSION"
        if version_file.exists():
            base_version = version_file.read_text().strip()

            # Git 정보가 있으면 추가
            commit_hash = config.COMMIT_HASH
            build_number = config.BUILD_NUMBER

            if commit_hash and build_number:
                return f"{base_version}-{build_number}-{commit_hash[:7]}"
            elif commit_hash:
                return f"{base_version}-{commit_hash[:7]}"
            elif build_number:
                return f"{base_version}-{build_number}"
            else:
                return base_version
    except Exception as e:
        logger.debug("Failed to read version file: %s", e)

    # 기본값
    return "0.0.0-dev"

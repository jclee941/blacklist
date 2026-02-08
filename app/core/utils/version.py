"""
공통 버전 유틸리티
"""

import os
from pathlib import Path


def get_app_version():
    """앱 버전 정보 가져오기

    우선순위:
    1. APP_VERSION 환경변수
    2. VERSION 파일 + Git 정보
    3. VERSION 파일만
    4. 기본값 (0.0.0-dev)
    """
    # 환경변수에서 우선 가져오기
    version = os.getenv("APP_VERSION")
    if version:
        return version

    # VERSION 파일 읽기
    try:
        version_file = Path(__file__).parents[3] / "VERSION"
        if version_file.exists():
            base_version = version_file.read_text().strip()

            # Git 정보가 있으면 추가
            commit_hash = os.getenv("COMMIT_HASH", "").strip()
            build_number = os.getenv("BUILD_NUMBER", "").strip()

            if commit_hash and build_number:
                return f"{base_version}-{build_number}-{commit_hash[:7]}"
            elif commit_hash:
                return f"{base_version}-{commit_hash[:7]}"
            elif build_number:
                return f"{base_version}-{build_number}"
            else:
                return base_version
    except Exception:
        pass

    # 기본값
    return "0.0.0-dev"

"""API 라우트 - 모듈화된 구조
메인 API 블루프린트와 모든 하위 API 모듈을 임포트
"""

from flask import Blueprint

# 메인 API 블루프린트 생성
api_bp = Blueprint("api", __name__, url_prefix="/api")

# 모든 API 모듈 임포트

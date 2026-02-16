#!/usr/bin/env python3
"""
Collection Triggering
Routes: /collection/regtech/trigger
"""

from flask import Blueprint, jsonify, request
from datetime import datetime
import logging

from core.utils.rate_limit import rate_limit
from ....config import config

logger = logging.getLogger(__name__)


blacklist_collection_bp = Blueprint("blacklist_collection", __name__)


@blacklist_collection_bp.route("/collection/regtech/trigger", methods=["POST"])
@rate_limit("5 per hour")  # Resource-intensive operation
def trigger_regtech_collection():
    """REGTECH 수집 트리거 - 날짜 범위 지원"""
    try:
        import requests

        data = request.get_json() or {}

        # 컬렉터 서비스 호출 (내부 네트워크)
        collector_response = requests.post(
            config.COLLECTOR_URL + "/api/force-collection/REGTECH",
            timeout=30,
            json={
                "source": "regtech_api_trigger",
                "start_date": data.get("start_date"),
                "end_date": data.get("end_date"),
            },
        )

        if collector_response.status_code == 200:
            return jsonify(
                {
                    "success": True,
                    "message": "REGTECH 수집이 시작되었습니다",
                    "timestamp": datetime.now().isoformat(),
                }
            )
        else:
            return jsonify(
                {
                    "success": False,
                    "error": f"컬렉터 서비스 오류: {collector_response.status_code}",
                    "timestamp": datetime.now().isoformat(),
                }
            ), 502

    except Exception as e:
        logger.error(f"REGTECH collection trigger failed: {e}")
        return jsonify({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}), 500

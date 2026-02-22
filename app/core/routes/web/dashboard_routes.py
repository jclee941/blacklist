"""
Dashboard Routes
대시보드 및 메인 페이지 관련 라우트
"""

from flask import render_template, jsonify
import logging
import psutil
import os
from datetime import datetime
from . import web_bp

logger = logging.getLogger(__name__)


@web_bp.route("/", methods=["GET"])
def index():
    """메인페이지 - HTML 랜딩 페이지"""
    return render_template("index.html")


@web_bp.route("/debug/routes", methods=["GET"])
def debug_routes():
    """디버그: 등록된 모든 라우트 확인"""
    from flask import current_app

    routes = []
    for rule in current_app.url_map.iter_rules():
        routes.append(
            {
                "endpoint": rule.endpoint,
                "methods": list(rule.methods),
                "rule": str(rule),
            }
        )
    return jsonify({"status": "success", "routes": routes, "total_routes": len(routes)})


@web_bp.route("/connection-status", methods=["GET"])
def connection_status():
    """연결 상태 페이지"""
    return render_template("connection_status.html")


@web_bp.route("/data-management", methods=["GET"])
def data_management():
    """데이터 관리 페이지"""
    return render_template("data_management.html")


@web_bp.route("/system-logs", methods=["GET"])
def system_logs():
    """시스템 로그 페이지"""
    return render_template("system_logs.html")


@web_bp.route("/api/system/logs", methods=["GET"])
def api_system_logs():
    """실제 시스템 상태만 반환 - 가짜 로그 제거"""
    try:
        # 실제 시스템 정보만 수집
        system_info = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        }

        # 실제 시스템 상태만 반환
        logs = [
            {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "message": f"시스템 상태 - CPU: {system_info['cpu_percent']:.1f}%, "
                f"메모리: {system_info['memory_percent']:.1f}%, "
                f"디스크: {system_info['disk_percent']:.1f}%",
                "module": "System Monitor",
            }
        ]

        return jsonify(
            {
                "success": True,
                "logs": logs,
                "system_info": system_info,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"System logs API error: {e}")
        return jsonify({"success": False, "error": str(e), "logs": []}), 500


@web_bp.route("/api/system/containers", methods=["GET"])
def api_system_containers():
    """시스템 상태 정보 API (Docker 대신 프로세스 정보)"""
    try:
        # 현재 프로세스 정보 및 시스템 상태
        containers = []

        # 현재 애플리케이션 정보
        current_pid = os.getpid()
        try:
            process = psutil.Process(current_pid)
            uptime_seconds = int((datetime.now() - datetime.fromtimestamp(process.create_time())).total_seconds())
            containers.append(
                {
                    "name": "blacklist-app",
                    "status": f"Up {uptime_seconds}s",
                    "image": "Flask Application (Gunicorn)",
                    "memory_percent": f"{process.memory_percent():.1f}%",
                    "cpu_percent": f"{process.cpu_percent():.1f}%",
                }
            )
        except BaseException:
            containers.append(
                {
                    "name": "blacklist-app",
                    "status": "Running",
                    "image": "Flask Application",
                    "memory_percent": "N/A",
                    "cpu_percent": "N/A",
                }
            )

        # 시스템 전체 정보 추가
        containers.append(
            {
                "name": "system-monitor",
                "status": "Active",
                "image": "System Resources",
                "memory_percent": f"{psutil.virtual_memory().percent:.1f}%",
                "cpu_percent": f"{psutil.cpu_percent(interval=0.1):.1f}%",
            }
        )

        return jsonify(
            {
                "success": True,
                "containers": containers,
                "system_stats": {
                    "cpu_count": psutil.cpu_count(),
                    "memory_total": f"{psutil.virtual_memory().total / (1024**3):.1f} GB",
                    "disk_total": f"{psutil.disk_usage('/').total / (1024**3):.1f} GB",
                },
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"System containers API error: {e}")
        return jsonify({"success": False, "error": str(e), "containers": []}), 500


@web_bp.route("/data-table", methods=["GET"])
def data_table():
    """데이터 테이블 페이지"""
    return render_template("data_table.html")


@web_bp.route("/search", methods=["GET"])
def search_page():
    """IP 검색 페이지"""
    return render_template("blacklist_search.html")


@web_bp.route("/detection-analytics", methods=["GET"])
def detection_analytics_page():
    """탐지 분석 페이지"""
    return render_template("detection_chart.html")


@web_bp.route("/statistics")
def statistics():
    """통계 페이지"""
    return render_template("statistics.html")


@web_bp.route("/data")
def data():
    """데이터 테이블 페이지 (네비게이션 메뉴용)"""
    return render_template("data_table.html")


@web_bp.route("/fortinet-api")
def fortinet_api():
    """FortiGate API 페이지"""
    return render_template("fortinet_api.html")

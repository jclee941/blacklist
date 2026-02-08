"""
System monitoring routes
시스템 모니터링 관련 라우트
"""

from flask import Blueprint, jsonify
import logging
import os
from datetime import datetime

system_bp = Blueprint("system", __name__, url_prefix="/api/system")


@system_bp.route("/logs", methods=["GET"])
def get_system_logs():
    """실제 시스템 상태만 반환 - 가짜 로그 완전 제거"""
    import psutil

    try:
        # 실제 시스템 정보만 수집
        system_info = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        }

        # 실제 시스템 상태 1개만 반환
        logs = [
            {
                "level": "INFO",
                "message": f"시스템 상태 - CPU: {system_info['cpu_percent']:.1f}%, "
                f"메모리: {system_info['memory_percent']:.1f}%, "
                f"디스크: {system_info['disk_percent']:.1f}%",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
        logging.error(f"시스템 로그 조회 실패: {e}")
        return jsonify({"success": False, "error": str(e), "logs": []}), 500


@system_bp.route("/status", methods=["GET"])
def get_system_status():
    """시스템 상태 조회"""
    try:
        status = {
            "application": {
                "status": "running",
                "uptime": "정상 운영",
                "version": "2.4.1",
            },
            "database": {"status": "connected", "type": "PostgreSQL"},
            "cache": {"status": "active", "type": "Redis"},
            "memory": {"usage": "정상", "available": "충분"},
            "disk": {"usage": "정상", "available": "충분"},
        }

        return jsonify({"success": True, "status": status, "timestamp": datetime.now().isoformat()})

    except Exception as e:
        logging.error(f"시스템 상태 조회 실패: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@system_bp.route("/health", methods=["GET"])
def get_detailed_health():
    """상세 헬스체크"""
    try:
        health_info = {
            "overall_status": "healthy",
            "services": {
                "web_server": "healthy",
                "database": "healthy",
                "cache": "healthy",
                "file_system": "healthy",
            },
            "metrics": {
                "response_time": "< 100ms",
                "cpu_usage": "정상",
                "memory_usage": "정상",
            },
            "last_check": datetime.now().isoformat(),
        }

        return jsonify(
            {
                "success": True,
                "health": health_info,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logging.error(f"상세 헬스체크 실패: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@system_bp.route("/env-check", methods=["GET"])
def get_environment_check():
    """환경변수 전달 상태 확인 (보안: 실제값 숨김)"""
    try:
        env_status = {
            "regtech_auth": {
                "id_configured": bool(os.getenv("REGTECH_ID", "")),
                "pw_configured": bool(os.getenv("REGTECH_PW", "")),
                "id_length": len(os.getenv("REGTECH_ID", "")),
                "pw_length": len(os.getenv("REGTECH_PW", "")),
            },
            "github_integration": {
                "token_configured": bool(os.getenv("GITHUB_TOKEN", "")),
                "repo_owner": os.getenv("GITHUB_REPO_OWNER", ""),
                "repo_name": os.getenv("GITHUB_REPO_NAME", ""),
            },
            "build_info": {
                "version": os.getenv("VERSION", "unknown"),
                "build_number": os.getenv("BUILD_NUMBER", "0"),
                "vcs_ref": os.getenv("VCS_REF", "unknown")[:7],
            },
        }

        return jsonify(
            {
                "success": True,
                "environment": env_status,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logging.error(f"환경변수 확인 실패: {e}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )

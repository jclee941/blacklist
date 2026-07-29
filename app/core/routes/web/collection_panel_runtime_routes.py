"""수집 패널 런타임/수집기 연동 라우트."""

import logging
from datetime import datetime, timedelta

import requests
from flask import current_app, jsonify, request

from ...config import config

logger = logging.getLogger(__name__)


def register_collection_panel_runtime_routes(bp, csrf):
    @bp.route("/api/collector-status")
    def get_collector_status():
        """수집기 실시간 상태 조회"""
        try:
            try:
                response = requests.get(
                    f"{config.COLLECTOR_URL}/status",
                    timeout=2,
                    **config.COLLECTOR_AUTH_REQUEST_KWARGS,
                )
                collector_data = response.json()
                collectors = collector_data.get("collectors", {})

                status_info = []
                for source, info in collectors.items():
                    last_run = info.get("last_run")
                    next_run = info.get("next_run")
                    last_run_dt = datetime.fromisoformat(last_run) if last_run else None
                    next_run_dt = datetime.fromisoformat(next_run) if next_run else None
                    is_running = False
                    if last_run_dt and next_run_dt:
                        now = datetime.now()
                        time_since_last = (now - last_run_dt.replace(tzinfo=None)).total_seconds()
                        is_running = time_since_last < 300

                    status_info.append(
                        {
                            "source": source,
                            "enabled": info.get("enabled", False),
                            "is_running": is_running,
                            "run_count": info.get("run_count", 0),
                            "error_count": info.get("error_count", 0),
                            "last_run": (last_run_dt.strftime("%Y-%m-%d %H:%M:%S") if last_run_dt else "없음"),
                            "next_run": (next_run_dt.strftime("%Y-%m-%d %H:%M:%S") if next_run_dt else "없음"),
                            "interval": info.get("interval_seconds", 86400) // 3600,
                        }
                    )

                return jsonify(
                    {
                        "success": True,
                        "collectors": status_info,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            except requests.exceptions.RequestException as exc:
                logger.warning(f"Collector health endpoint unreachable: {exc}")
                return jsonify(
                    {
                        "success": False,
                        "error": "수집기가 응답하지 않습니다",
                        "collectors": [],
                    }
                )
        except Exception as exc:
            logger.error(f"Collector status query failed: {exc}")
            return jsonify({"success": False, "error": str(exc), "collectors": []})

    @bp.route("/api/live-logs")
    def get_live_logs():
        """실시간 수집 로그 조회 (from collector's memory buffer)"""
        try:
            response = requests.get(
                f"{config.COLLECTOR_URL}/logs",
                timeout=2,
                **config.COLLECTOR_AUTH_REQUEST_KWARGS,
            )
            data = response.json()
            if not data or "logs" not in data:
                return jsonify({"success": False, "error": "로그 데이터 없음", "logs": []})

            logs = data["logs"][-50:] if len(data["logs"]) > 50 else data["logs"]
            return jsonify({"success": True, "logs": logs, "count": len(logs)})
        except requests.exceptions.Timeout:
            logger.error("Collector logs endpoint timeout")
            return jsonify({"success": False, "error": "로그 조회 시간 초과", "logs": []})
        except requests.exceptions.RequestException as exc:
            logger.error(f"Failed to fetch logs from collector: {exc}")
            return jsonify({"success": False, "error": f"수집기 연결 실패: {str(exc)}", "logs": []})
        except Exception as exc:
            logger.error(f"Live logs query failed: {exc}")
            return jsonify({"success": False, "error": str(exc), "logs": []})

    @bp.route("/trigger", methods=["POST"])
    @csrf.exempt
    def trigger_collection():
        """
        Trigger manual collection from panel.
        Body: {"source": "regtech" | "all", "start_date": "2025-01-01", "end_date": "2025-01-10"} (optional)
        """
        try:
            collection_service = current_app.extensions["collection_service"]
            data = request.get_json() or {}
            source = data.get("source", "all")
            start_date = data.get("start_date")
            end_date = data.get("end_date")

            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

            logger.info(f"Collection trigger requested: source={source}, dates={start_date} to {end_date}")
            if source.lower() == "regtech":
                result = collection_service.trigger_regtech_collection(
                    start_date=start_date,
                    end_date=end_date,
                )
            elif source.lower() == "all":
                result = collection_service.trigger_all_collections()
            else:
                result = collection_service.trigger_collection(source)

            if result.get("success"):
                logger.info(f"✅ Collection completed: {result.get('collected_count', 0)} items")
                return jsonify(
                    {
                        "success": True,
                        "message": "Collection triggered successfully",
                        "collected_count": result.get("collected_count", 0),
                        "source": source,
                        "start_date": start_date,
                        "end_date": end_date,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

            logger.warning(f"Collection failed: {result.get('error', 'Unknown error')}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": result.get("error", "Collection failed"),
                        "source": source,
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                500,
            )
        except Exception as exc:
            logger.error(f"Collection trigger error: {exc}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": str(exc),
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                500,
            )

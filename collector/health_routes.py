import logging
from datetime import datetime

from flask import Response, jsonify, request


logger = logging.getLogger(__name__)


def _failure_response(error: str, status: int) -> tuple[Response, int]:
    return jsonify({"success": False, "error": error, "timestamp": datetime.now().isoformat()}), status


def register_health_routes(server):
    app = server.app

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify(
            {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "collectors": server._get_collector_status(),
            }
        )

    @app.route("/status", methods=["GET"])
    def status():
        return jsonify(
            {
                "collectors": server._get_collector_status(),
                "timestamp": datetime.now().isoformat(),
            }
        )

    @app.route("/logs", methods=["GET"])
    def logs():
        return jsonify(
            {
                "logs": list(server.log_buffer),
                "count": len(server.log_buffer),
                "timestamp": datetime.now().isoformat(),
            }
        )

    @app.route("/trigger", methods=["POST"])
    def trigger_collection():
        try:
            data = request.get_json() or {}
            source = data.get("source", "regtech").upper()
            start_date = data.get("start_date")
            end_date = data.get("end_date")

            if not server.scheduler:
                return jsonify({"success": False, "error": "Scheduler not available"}), 500

            logger.info("Manual collection triggered: %s, %s ~ %s", source, start_date, end_date)
            if source != "REGTECH":
                return jsonify({"success": False, "error": f"Invalid source: {source}"}), 400

            result = server.scheduler.force_collection(source)
            if not result.get("success"):
                return _failure_response(result.get("error", "Collection failed"), 500)

            return jsonify({"success": True, "result": result, "timestamp": datetime.now().isoformat()})
        except Exception as e:
            logger.error("Manual trigger error: %s", e)
            return _failure_response(str(e), 500)

    @app.route("/api/test-auth/<source>", methods=["POST"])
    def test_authentication(source):
        try:
            source_upper = source.upper()
            if source_upper != "REGTECH":
                return jsonify({"success": False, "error": f"Invalid source: {source_upper}"}), 400

            credentials = server._db.get_collection_credentials(source_upper)
            if not credentials:
                return jsonify({"success": False, "error": f"No credentials found for {source_upper}"}), 404

            username = credentials.get("username")
            password = credentials.get("password")
            if not credentials.get("enabled", False):
                return jsonify({"success": False, "error": f"{source_upper} collection is disabled"}), 403
            if not isinstance(username, str) or not isinstance(password, str):
                return jsonify({"success": False, "error": f"Invalid credentials found for {source_upper}"}), 400

            logger.info("Testing authentication for %s with user: %s", source_upper, username)
            from .core.regtech_collector import RegtechCollector

            auth_result = RegtechCollector().authenticate(username, password)
            test_timestamp = datetime.now()
            logger.info(
                "Test completed: %s - %s at %s",
                source_upper,
                "인증 성공" if auth_result else "인증 실패",
                test_timestamp,
            )
            if auth_result:
                logger.info("✅ %s authentication successful", source_upper)
                return jsonify({"success": True, "message": "인증 성공", "timestamp": test_timestamp.isoformat()})

            logger.warning("❌ %s authentication failed", source_upper)
            return jsonify({"success": False, "error": "인증 실패", "timestamp": test_timestamp.isoformat()})
        except Exception as e:
            logger.error("Error testing authentication for %s: %s", source, e)
            return _failure_response(str(e), 200)

    @app.route("/api/force-collection/<source>", methods=["POST"])
    def force_collection(source):
        try:
            source_upper = source.upper()
            if not server.scheduler:
                return jsonify({"success": False, "error": "Scheduler not available"}), 500
            if source_upper != "REGTECH":
                return jsonify({"success": False, "error": f"Invalid source: {source_upper}"}), 400

            credentials = server._db.get_collection_credentials(source_upper)
            if credentials and not credentials.get("enabled", False):
                return jsonify({"success": False, "error": f"{source_upper} 수집이 비활성화되어 있습니다"}), 403

            logger.info("Forcing immediate collection for %s", source_upper)
            result = server.scheduler.force_collection(source_upper)
            if result.get("success"):
                return jsonify(
                    {
                        "success": True,
                        "message": f"{source_upper} 수집 완료",
                        "data": result,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            return jsonify(
                {
                    "success": False,
                    "error": result.get("error", "수집 실패"),
                    "timestamp": datetime.now().isoformat(),
                }
            ), 500
        except Exception as e:
            logger.error("Error forcing collection for %s: %s", source, e)
            return _failure_response(str(e), 500)

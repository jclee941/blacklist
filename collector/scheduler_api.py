"""
Scheduler API Endpoints
Provides HTTP API for scheduler management
"""

from flask import Flask, jsonify
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def create_scheduler_api(scheduler_instance):
    """Create Flask app with scheduler API endpoints"""

    app = Flask(__name__)

    @app.route("/api/scheduler/status", methods=["GET"])
    def get_status():
        """Get scheduler status"""
        try:
            status = scheduler_instance.get_status()
            return jsonify({"success": True, **status})
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/scheduler/force-collection/<source>", methods=["POST"])
    def force_collection(source):
        """Force immediate collection for specific source"""
        try:
            source_upper = source.upper()

            if source_upper not in scheduler_instance.collectors:
                available = list(scheduler_instance.collectors.keys())
                return jsonify(
                    {
                        "success": False,
                        "error": f"Unknown source: {source_upper}. Available: {available}",
                    }
                ), 400

            logger.info(f"Forcing collection for {source_upper}")

            result = scheduler_instance.force_collection(source_upper)

            return jsonify(result)

        except Exception as e:
            logger.error(f"Error forcing collection: {e}")
            return jsonify({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}), 500

    @app.route("/api/scheduler/restart", methods=["POST"])
    def restart_scheduler():
        """Restart scheduler to pick up new configuration"""
        try:
            logger.info("Restarting scheduler...")

            # Stop current scheduler
            scheduler_instance.stop()

            # Start scheduler (will re-setup schedules and pick up new configuration)
            scheduler_instance.start()

            logger.info("✅ Scheduler restarted successfully")

            return jsonify(
                {
                    "success": True,
                    "message": "Scheduler restarted",
                    "collectors": list(scheduler_instance.collectors.keys()),
                    "timestamp": datetime.now().isoformat(),
                }
            )

        except Exception as e:
            logger.error(f"Error restarting scheduler: {e}")
            return jsonify({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}), 500

    @app.route("/api/scheduler/collectors", methods=["GET"])
    def list_collectors():
        """List all available collectors"""
        try:
            collectors_info = {}
            stats = scheduler_instance.collection_stats

            for name, method_name in scheduler_instance.collectors.items():
                collectors_info[name] = {
                    "name": name,
                    "method": method_name,
                    "enabled": scheduler_instance.running,
                }

            return jsonify(
                {
                    "success": True,
                    "collectors": collectors_info,
                    "total": len(collectors_info),
                    "scheduler_running": scheduler_instance.running,
                    "stats": {
                        "total_runs": stats.get("total_runs", 0),
                        "successful_runs": stats.get("successful_runs", 0),
                        "failed_runs": stats.get("failed_runs", 0),
                        "last_run": stats.get("last_run"),
                        "last_success": stats.get("last_success"),
                    },
                }
            )

        except Exception as e:
            logger.error(f"Error listing collectors: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    return app

#!/usr/bin/env python3
"""
Minimal Flask app for testing
"""

import os
import logging
from flask import Flask, jsonify
from datetime import datetime

logger = logging.getLogger(__name__)


def create_app():
    """Create minimal Flask app"""
    app = Flask(__name__)

    @app.route("/")
    def index():
        return jsonify({"message": "Blacklist App Running", "status": "ok"})

    @app.route("/health")
    def health_check():
        """Health check endpoint"""
        return jsonify(
            {
                "status": "healthy",
                "mode": "minimal",
                "timestamp": datetime.now().isoformat(),
            }
        )

    return app


# Create app instance for WSGI servers (like Gunicorn)
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 2542))
    logger.info(f"🚀 Starting Minimal Flask application on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)

#!/usr/bin/env python3
"""
Independent container Flask application execution script
"""

import sys
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))


def get_flask_app():
    try:
        from core.app import create_app

        app = create_app()
        logger.info("✅ Flask app created via core.app factory (Phase 1.3 security enabled)")
        return app
    except ImportError as e1:
        logger.critical(f"❌ core.app import failed: {e1}")
        sys.exit(1)


app = get_flask_app()


def run_server() -> None:
    port = int(os.environ.get("PORT", 2542))
    certificate = os.environ.get("INTERNAL_TLS_CERT", "/run/blacklist/tls/tls.crt")
    private_key = os.environ.get("INTERNAL_TLS_KEY", "/run/blacklist/tls/tls.key")
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        ssl_context=(certificate, private_key),
    )


if __name__ == "__main__":
    run_server()

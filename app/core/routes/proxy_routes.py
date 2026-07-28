"""
API Proxy Routes
Forwards frontend requests from /api/proxy/collection/* to /api/collection/*
This allows the Next.js frontend to call backend APIs through a consistent proxy pattern.
"""

from flask import Blueprint, request, jsonify
import logging
import requests

from ..config import config

logger = logging.getLogger(__name__)

proxy_bp = Blueprint("proxy", __name__, url_prefix="/api/proxy")

COLLECTOR_SERVICE_URL = config.COLLECTOR_URL


def forward_to_backend(endpoint: str, method: str | None = None):
    """
    Forward request to backend API

    Args:
        endpoint: Backend endpoint (e.g., "/collection/status")
        method: HTTP method (if None, uses request.method)

    Returns:
        Response from backend API
    """
    url = f"{config.BLACKLIST_API_URL}{endpoint}"

    try:
        method = method or request.method
        query_params = request.args.to_dict(flat=False)

        # Prepare headers (forward relevant headers, always include Content-Type for JSON)
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        authorization = request.headers.get("Authorization")
        if authorization:
            headers["Authorization"] = authorization

        # Forward request with same method, headers, and body
        if method == "GET":
            response = requests.get(url, params=query_params, headers=headers, timeout=30)
        elif method == "POST":
            data = request.get_json(silent=True) or {}
            response = requests.post(url, json=data, headers=headers, timeout=30)
        elif method == "PUT":
            data = request.get_json(silent=True) or {}
            response = requests.put(url, json=data, headers=headers, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            return jsonify({"success": False, "error": f"Unsupported method: {method}"}), 405

        # Return backend response with same status code
        try:
            return response.json(), response.status_code
        except ValueError:
            # Response is not JSON
            return {"success": False, "error": response.text}, response.status_code

    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to backend API: {url}")
        return jsonify({"success": False, "error": "Backend API unavailable"}), 503
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@proxy_bp.route("/collection/status", methods=["GET"])
def proxy_collection_status():
    """Proxy: GET /api/collection/status"""
    return forward_to_backend("/collection/status")


@proxy_bp.route("/collection/credentials/<source>", methods=["GET", "PUT"])
def proxy_credentials(source: str):
    """Proxy: GET/PUT /api/collection/credentials/<source>"""
    return forward_to_backend(f"/collection/credentials/{source}")


@proxy_bp.route("/collection/credentials/<source>/test", methods=["POST"])
def proxy_test_credentials(source: str):
    """Proxy: POST /api/collection/credentials/<source>/test"""
    return forward_to_backend(f"/collection/credentials/{source}/test")


@proxy_bp.route("/collection/trigger/<source>", methods=["POST"])
def proxy_trigger_collection(source: str):
    """Proxy: POST trigger to collector service (port 8545)"""
    try:
        url = f"{COLLECTOR_SERVICE_URL}/trigger"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        data = request.get_json(silent=True) or {}
        data["source"] = source
        response = requests.post(url, json=data, headers=headers, timeout=120)
        try:
            return response.json(), response.status_code
        except ValueError:
            return {"success": False, "error": response.text}, response.status_code
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to collector service: {COLLECTOR_SERVICE_URL}")
        return jsonify({"success": False, "error": "Collector service unavailable"}), 503
    except Exception as e:
        logger.error(f"Collector proxy error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@proxy_bp.route("/collection/history", methods=["GET"])
def proxy_collection_history():
    """Proxy: GET /api/collection/history"""
    return forward_to_backend("/collection/history")


@proxy_bp.route("/collection/statistics", methods=["GET"])
def proxy_collection_statistics():
    """Proxy: GET /api/collection/statistics -> /api/collection/statistics"""
    return forward_to_backend("/collection/statistics")


@proxy_bp.route("/collection/health", methods=["GET"])
def proxy_collection_health():
    """Proxy: GET /api/collection/health"""
    return forward_to_backend("/collection/health")

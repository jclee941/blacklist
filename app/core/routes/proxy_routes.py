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
    url = f"{config.BLACKLIST_API_URL}{endpoint}"

    try:
        method = method or request.method
        query_params = request.args.to_dict(flat=False)

        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        authorization = request.headers.get("Authorization")
        if authorization:
            headers["Authorization"] = authorization

        if method == "GET":
            response = requests.get(
                url,
                params=query_params,
                headers=headers,
                timeout=30,
                verify=config.INTERNAL_CA_CERT,
            )
        elif method == "POST":
            data = request.get_json(silent=True) or {}
            response = requests.post(
                url,
                json=data,
                headers=headers,
                timeout=30,
                verify=config.INTERNAL_CA_CERT,
            )
        elif method == "PUT":
            data = request.get_json(silent=True) or {}
            response = requests.put(
                url,
                json=data,
                headers=headers,
                timeout=30,
                verify=config.INTERNAL_CA_CERT,
            )
        elif method == "DELETE":
            response = requests.delete(
                url,
                headers=headers,
                timeout=30,
                verify=config.INTERNAL_CA_CERT,
            )
        else:
            return jsonify({"success": False, "error": f"Unsupported method: {method}"}), 405

        try:
            return response.json(), response.status_code
        except ValueError:
            return {"success": False, "error": "Backend returned a non-JSON response"}, response.status_code

    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to backend API: {url}")
        return jsonify({"success": False, "error": "Backend API unavailable"}), 503
    except Exception:
        logger.exception("Proxy request failed")
        return jsonify({"success": False, "error": "Proxy request failed"}), 500


@proxy_bp.route("/collection/status", methods=["GET"])
def proxy_collection_status():
    return forward_to_backend("/collection/status")


@proxy_bp.route("/collection/credentials/<source>", methods=["GET", "PUT"])
def proxy_credentials(source: str):
    return forward_to_backend(f"/collection/credentials/{source}")


@proxy_bp.route("/collection/credentials/<source>/test", methods=["POST"])
def proxy_test_credentials(source: str):
    return forward_to_backend(f"/collection/credentials/{source}/test")


@proxy_bp.route("/collection/trigger/<source>", methods=["POST"])
def proxy_trigger_collection(source: str):
    try:
        url = f"{COLLECTOR_SERVICE_URL}/trigger"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        headers.update(config.COLLECTOR_AUTH_REQUEST_KWARGS.get("headers", {}))
        data = request.get_json(silent=True) or {}
        data["source"] = source
        response = requests.post(
            url,
            json=data,
            headers=headers,
            timeout=config.COLLECTOR_COLLECTION_TIMEOUT,
            verify=config.INTERNAL_CA_CERT,
        )
        try:
            return response.json(), response.status_code
        except ValueError:
            return {"success": False, "error": "Collector returned a non-JSON response"}, response.status_code
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot connect to collector service: {COLLECTOR_SERVICE_URL}")
        return jsonify({"success": False, "error": "Collector service unavailable"}), 503
    except Exception:
        logger.exception("Collector request failed")
        return jsonify({"success": False, "error": "Collector request failed"}), 500


@proxy_bp.route("/collection/history", methods=["GET"])
def proxy_collection_history():
    return forward_to_backend("/collection/history")


@proxy_bp.route("/collection/statistics", methods=["GET"])
def proxy_collection_statistics():
    return forward_to_backend("/collection/statistics")


@proxy_bp.route("/collection/health", methods=["GET"])
def proxy_collection_health():
    return forward_to_backend("/collection/health")

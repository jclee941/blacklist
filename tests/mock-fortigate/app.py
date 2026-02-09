import os
import uuid
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Admin credentials
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

# In-memory storage
sessions = {}
external_resources = {}
external_connectors = {}  # NEW: External Connectors
address_objects = {}
address_groups = {}
policies = {}


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify(
        {
            "service": "Mock FortiManager/FortiGate",
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "7.4.0",
        }
    )


@app.route("/debug/status", methods=["GET"])
def debug_status():
    """Debug status"""
    return jsonify(
        {
            "sessions": len(sessions),
            "external_resources": len(external_resources),
            "external_connectors": len(external_connectors),
            "address_objects": len(address_objects),
            "address_groups": len(address_groups),
            "policies": len(policies),
        }
    )


@app.route("/jsonrpc", methods=["POST"])
def jsonrpc():
    """JSON-RPC endpoint"""
    try:
        data = request.get_json()
        method = data.get("method")
        params = data.get("params", [{}])[0]
        request_id = data.get("id", 1)
        session_id = data.get("session")

        logger.info(f"JSON-RPC: method={method}, url={params.get('url')}")

        if method == "exec":
            return handle_exec(params, request_id, session_id)
        elif method == "add":
            return handle_add(params, request_id, session_id)
        elif method == "set":
            return handle_set(params, request_id, session_id)
        elif method == "get":
            return handle_get(params, request_id, session_id)
        elif method == "delete":
            return handle_delete(params, request_id, session_id)
        else:
            return error_response(request_id, -32601, f"Unknown method: {method}")
    except Exception as e:
        logger.error(f"JSON-RPC Error: {e}")
        return error_response(1, -32603, str(e))


def handle_exec(params, request_id, session_id=None):
    """Exec handler"""
    url = params.get("url", "")
    data = params.get("data", {})

    # Login
    if url == "/sys/login/user":
        if data.get("user") == ADMIN_USERNAME and data.get("passwd") == ADMIN_PASSWORD:
            new_session = str(uuid.uuid4())
            sessions[new_session] = {
                "user": data.get("user"),
                "login_time": datetime.now().isoformat(),
            }
            logger.info(f"✅ Login: {new_session[:8]}...")
            return success_response(request_id, session=new_session)
        else:
            return error_response(request_id, -10, "Authentication failed")

    # Logout
    elif url == "/sys/logout":
        if session_id and session_id in sessions:
            del sessions[session_id]
        return success_response(request_id)

    # External Resource Refresh
    elif "/obj/system/external-resource" in url and "/refresh" in url:
        logger.info("✅ External resource refresh triggered")
        return success_response(request_id, data={"refreshed": True})

    # External Connector Update (NEW)
    elif "/obj/system/sdn-connector" in url and "/update" in url:
        connector_name = url.split("/")[-2]
        if connector_name in external_connectors:
            # Fetch IPs from blacklist API
            connector = external_connectors[connector_name]
            api_url = connector.get("server")

            try:
                resp = requests.get(api_url, timeout=10)
                if resp.status_code == 200:
                    # Parse IP list
                    ip_list = resp.text.strip().split("\n")

                    # Create/Update Address Objects
                    for ip in ip_list[:100]:  # Limit to 100 IPs
                        if ip.strip():
                            addr_name = f"REGTECH-{ip.replace('.', '_')}"
                            address_objects[addr_name] = {
                                "name": addr_name,
                                "type": "ipmask",
                                "subnet": f"{ip} 255.255.255.255",
                                "comment": "Auto-imported from REGTECH blacklist",
                                "created_at": datetime.now().isoformat(),
                            }

                    external_connectors[connector_name]["last_updated"] = (
                        datetime.now().isoformat()
                    )
                    external_connectors[connector_name]["status"] = "success"

                    logger.info(
                        f"✅ External connector updated: {connector_name} ({len(ip_list)} IPs)"
                    )
                    return success_response(
                        request_id, data={"updated": True, "ip_count": len(ip_list)}
                    )
            except Exception as e:
                logger.error(f"❌ Connector update failed: {e}")
                return error_response(request_id, -1, str(e))

        return error_response(request_id, -1, f"Connector not found: {connector_name}")

    else:
        return error_response(request_id, -32601, f"Unknown URL: {url}")


def handle_add(params, request_id, session_id=None):
    """Add handler"""
    if not check_session(session_id):
        return error_response(request_id, -10, "Not authenticated")

    url = params.get("url", "")
    data = params.get("data", {})

    # External Connector (NEW)
    if "/obj/system/sdn-connector" in url:
        name = data.get("name")
        external_connectors[name] = {
            **data,
            "type": "generic",
            "created_at": datetime.now().isoformat(),
            "last_updated": None,
            "status": "pending",
        }
        logger.info(f"✅ External connector created: {name}")
        return success_response(request_id, data={"name": name})

    # External Resource
    elif "/obj/system/external-resource" in url:
        name = data.get("name")
        external_resources[name] = {
            **data,
            "created_at": datetime.now().isoformat(),
            "last_updated": None,
        }
        logger.info(f"✅ External resource created: {name}")
        return success_response(request_id, data={"name": name})

    # Address Object
    elif "/obj/firewall/address" in url:
        name = data.get("name")
        address_objects[name] = {**data, "created_at": datetime.now().isoformat()}
        logger.info(f"✅ Address object created: {name}")
        return success_response(request_id, data={"name": name})

    # Address Group
    elif "/obj/firewall/addrgrp" in url:
        name = data.get("name")
        address_groups[name] = {**data, "created_at": datetime.now().isoformat()}
        logger.info(f"✅ Address group created: {name}")
        return success_response(request_id, data={"name": name})

    # Policy
    elif "/firewall/policy" in url:
        policy_id = len(policies) + 1
        policies[policy_id] = {
            "policyid": policy_id,
            **data,
            "created_at": datetime.now().isoformat(),
        }
        logger.info(f"✅ Policy created: {policy_id}")
        return success_response(request_id, data={"policyid": policy_id})

    else:
        return error_response(request_id, -32601, f"Unknown URL: {url}")


def handle_set(params, request_id, session_id=None):
    """Set handler"""
    if not check_session(session_id):
        return error_response(request_id, -10, "Not authenticated")

    logger.info(f"✅ Set operation: {params.get('url')}")
    return success_response(request_id)


def handle_get(params, request_id, session_id=None):
    """Get handler"""
    if not check_session(session_id):
        return error_response(request_id, -10, "Not authenticated")

    url = params.get("url", "")

    # External Connectors (NEW)
    if "/obj/system/sdn-connector" in url:
        if url.endswith("/sdn-connector"):
            return success_response(request_id, data=list(external_connectors.values()))
        else:
            # Get specific connector
            connector_name = url.split("/")[-1]
            if connector_name in external_connectors:
                return success_response(
                    request_id, data=external_connectors[connector_name]
                )
            else:
                return success_response(request_id, data=[])

    # External Resources
    elif "/obj/system/external-resource" in url:
        return success_response(request_id, data=list(external_resources.values()))

    # Address Objects
    elif "/obj/firewall/address" in url:
        return success_response(request_id, data=list(address_objects.values()))

    # Address Groups
    elif "/obj/firewall/addrgrp" in url:
        return success_response(request_id, data=list(address_groups.values()))

    # Policies
    elif "/firewall/policy" in url:
        return success_response(request_id, data=list(policies.values()))

    else:
        return success_response(request_id, data=[])


def handle_delete(params, request_id, session_id=None):
    """Delete handler"""
    if not check_session(session_id):
        return error_response(request_id, -10, "Not authenticated")

    logger.info(f"✅ Delete operation: {params.get('url')}")
    return success_response(request_id)


def check_session(session_id):
    """Check session validity"""
    return session_id and session_id in sessions


def success_response(request_id, data=None, session=None):
    """Success response"""
    response = {
        "id": request_id,
        "result": [{"status": {"code": 0, "message": "OK"}, "url": "/success"}],
    }

    if data is not None:
        response["result"][0]["data"] = data

    if session is not None:
        response["session"] = session

    return jsonify(response), 200


def error_response(request_id, code, message):
    """Error response"""
    return jsonify(
        {"id": request_id, "result": [{"status": {"code": code, "message": message}}]}
    ), 200


if __name__ == "__main__":
    logger.info("🚀 Starting Mock FortiManager/FortiGate Server")
    logger.info(f"Admin credentials: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
    logger.info("API Endpoints:")
    logger.info("  - JSON-RPC: POST /jsonrpc")
    logger.info("  - Health: GET /health")
    logger.info("  - Debug: GET /debug/status")

    app.run(host="0.0.0.0", port=8443, debug=False)

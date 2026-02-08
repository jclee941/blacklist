"""
FortiGate Registration API
Push blacklist IPs to FortiGate devices
"""

from flask import Blueprint, jsonify, request, g, current_app
import logging
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
from ...exceptions import ValidationError, InternalServerError

logger = logging.getLogger(__name__)

fortinet_register_bp = Blueprint("fortinet_register", __name__, url_prefix="/api/fortinet")


@fortinet_register_bp.route("/register", methods=["POST"])
def register_to_fortigate():
    """
    Register/Push active blacklist IPs to FortiGate device

    POST /api/fortinet/register

    Request Body:
        {
            "device_ip": "192.168.1.1",
            "username": "admin",
            "password": "password",
            "vdom": "root",  # Optional, default: "root"
            "address_group": "blacklist_group",  # Optional
            "dry_run": false  # Optional, test without applying
        }

    Returns:
        {
            "success": true,
            "data": {
                "registered_count": 1234,
                "failed_count": 0,
                "device_ip": "192.168.1.1",
                "vdom": "root",
                "address_group": "blacklist_group"
            }
        }
    """
    # Get request data
    data = request.get_json()

    # Validate required fields
    required_fields = ["device_ip", "username", "password"]
    missing_fields = [field for field in required_fields if not data.get(field)]

    if missing_fields:
        raise ValidationError(
            message=f"Missing required fields: {', '.join(missing_fields)}",
            field="request_body",
            details={"missing_fields": missing_fields},
        )

    device_ip = data["device_ip"]
    username = data["username"]
    password = data["password"]
    vdom = data.get("vdom", "root")
    address_group = data.get("address_group", "blacklist_group")
    dry_run = data.get("dry_run", False)

    # Get active IPs from database
    db_service = current_app.extensions["db_service"]

    try:
        query = """
            SELECT ip_address, reason, confidence_level
            FROM blacklist_ips_with_auto_inactive
            WHERE is_active = true
              AND ip_address NOT IN (
                  SELECT ip_address
                  FROM whitelist_ips
                  WHERE is_active = true
              )
            ORDER BY confidence_level DESC, ip_address
        """

        rows = db_service.query(query)
        ip_list = [
            {
                "ip": row["ip_address"],
                "reason": row["reason"] or "Blacklisted IP",
                "confidence": row["confidence_level"],
            }
            for row in rows
        ]

        if dry_run:
            return jsonify(
                {
                    "success": True,
                    "data": {
                        "registered_count": len(ip_list),
                        "failed_count": 0,
                        "device_ip": device_ip,
                        "vdom": vdom,
                        "address_group": address_group,
                        "dry_run": True,
                        "sample_ips": ip_list[:10],
                    },
                    "timestamp": datetime.now().isoformat(),
                    "request_id": g.request_id,
                }
            ), 200

        # FortiGate API
        base_url = f"https://{device_ip}/api/v2"
        group_url = f"{base_url}/cmdb/firewall/addrgrp"
        address_url = f"{base_url}/cmdb/firewall/address"

        # Check if group exists
        check_response = requests.get(
            f"{group_url}/{address_group}",
            auth=HTTPBasicAuth(username, password),
            params={"vdom": vdom},
            verify=False,
            timeout=30,
        )

        if check_response.status_code == 404:
            # Create address group
            group_data = {
                "name": address_group,
                "member": [],
                "comment": "Auto-generated blacklist from REGTECH",
            }

            create_response = requests.post(
                group_url,
                auth=HTTPBasicAuth(username, password),
                params={"vdom": vdom},
                json=group_data,
                verify=False,
                timeout=30,
            )

            if create_response.status_code not in [200, 201]:
                raise InternalServerError(
                    message=f"Failed to create address group: {create_response.text}",
                    details={"status_code": create_response.status_code},
                )

        # Register IPs
        registered_count = 0
        failed_count = 0

        for ip_data in ip_list:
            ip_address = ip_data["ip"]
            address_name = f"blacklist_{ip_address.replace('.', '_')}"

            address_obj = {
                "name": address_name,
                "type": "ipmask",
                "subnet": f"{ip_address}/32",
                "comment": ip_data["reason"][:255],
            }

            addr_response = requests.post(
                address_url,
                auth=HTTPBasicAuth(username, password),
                params={"vdom": vdom},
                json=address_obj,
                verify=False,
                timeout=10,
            )

            if addr_response.status_code in [200, 201, 424]:
                registered_count += 1
            else:
                failed_count += 1
                logger.warning(f"Failed to register IP {ip_address}: {addr_response.status_code}")

        # Update group members
        if registered_count > 0:
            member_names = [{"name": f"blacklist_{ip['ip'].replace('.', '_')}"} for ip in ip_list[:registered_count]]

            update_response = requests.put(
                f"{group_url}/{address_group}",
                auth=HTTPBasicAuth(username, password),
                params={"vdom": vdom},
                json={"member": member_names},
                verify=False,
                timeout=30,
            )

            if update_response.status_code not in [200, 201]:
                logger.warning(f"Failed to update group: {update_response.text}")

        return jsonify(
            {
                "success": True,
                "data": {
                    "registered_count": registered_count,
                    "failed_count": failed_count,
                    "total_ips": len(ip_list),
                    "device_ip": device_ip,
                    "vdom": vdom,
                    "address_group": address_group,
                    "dry_run": False,
                },
                "timestamp": datetime.now().isoformat(),
                "request_id": g.request_id,
            }
        ), 200

    except requests.exceptions.RequestException as e:
        logger.error(f"FortiGate API error: {e}", exc_info=True)
        raise InternalServerError(
            message=f"Failed to communicate with FortiGate: {str(e)}",
            details={"device_ip": device_ip},
        )
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Error registering to FortiGate: {e}", exc_info=True)
        raise InternalServerError(
            message="Failed to register blacklist to FortiGate",
            details={"error": str(e)},
        )

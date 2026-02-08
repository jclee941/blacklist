import logging

from flask import Blueprint, Response, current_app, jsonify, request

from ....exceptions import BadRequestError, DatabaseError, NotFoundError
from .handlers import (
    deleted_response,
    paginated_response,
    parse_bool_param,
    success_response,
    validate_list_type,
    validate_pagination,
)
from .repository import IPManagementRepository

logger = logging.getLogger(__name__)

ip_management_api_bp = Blueprint("ip_management_api", __name__, url_prefix="/ip-management")

ip_management_legacy_bp = Blueprint("ip_management_legacy", __name__, url_prefix="/ip")


def _get_repository() -> IPManagementRepository:
    db_service = current_app.extensions.get("db_service")
    if not db_service:
        raise RuntimeError("Database service not initialized")
    return IPManagementRepository(db_service)


@ip_management_api_bp.route("/unified", methods=["GET"])
@ip_management_api_bp.route("/list", methods=["GET"])
def get_unified_ip_list() -> tuple[Response, int]:
    page, limit = validate_pagination(
        request.args.get("page", 1),
        request.args.get("limit", 50),
    )
    list_type = validate_list_type(request.args.get("type"))
    search_ip = request.args.get("ip")
    is_active = parse_bool_param(request.args.get("is_active"), default=True)

    try:
        repo = _get_repository()
        items, total = repo.get_unified_list(
            page=page,
            limit=limit,
            list_type=list_type,
            search_ip=search_ip,
            is_active=is_active,
        )
        return jsonify(paginated_response(items, total, page, limit)), 200

    except Exception as e:
        logger.error(f"Unified IP list query error: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to retrieve unified IP list: {type(e).__name__}",
            table="unified_ip_list",
        )


@ip_management_api_bp.route("/statistics", methods=["GET"])
def get_ip_statistics() -> tuple[Response, int]:
    try:
        repo = _get_repository()
        stats = repo.get_statistics()
        response, status = success_response({"statistics": stats})
        return jsonify(response), status

    except Exception as e:
        logger.error(f"Statistics query error: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to retrieve IP statistics: {type(e).__name__}",
        )


@ip_management_api_bp.route("/whitelist", methods=["GET"])
def get_whitelist() -> tuple[Response, int]:
    page, limit = validate_pagination(
        request.args.get("page", 1),
        request.args.get("limit", 50),
    )

    try:
        repo = _get_repository()
        items, total = repo.get_whitelist(page=page, limit=limit)
        return jsonify(paginated_response(items, total, page, limit)), 200

    except Exception as e:
        logger.error(f"Whitelist query error: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to retrieve whitelist: {type(e).__name__}",
            table="whitelist_ips",
        )


@ip_management_api_bp.route("/whitelist", methods=["POST"])
def create_whitelist() -> tuple[Response, int]:
    data = request.get_json() or {}

    if not data or "ip_address" not in data:
        raise BadRequestError(message="ip_address is required", details={"parameter": "ip_address"})

    try:
        repo = _get_repository()
        result = repo.create_whitelist(
            ip_address=data["ip_address"],
            reason=data.get("reason", "VIP Protection"),
            source=data.get("source", "MANUAL"),
            country=data.get("country"),
        )
        response, _ = success_response(result, 201)
        return jsonify(response), 201

    except Exception as e:
        logger.error(f"Whitelist creation error: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to create whitelist entry: {type(e).__name__}",
            table="whitelist_ips",
        )


@ip_management_api_bp.route("/whitelist/<int:id>", methods=["PUT"])
def update_whitelist(id: int) -> tuple[Response, int]:
    data = request.get_json() or {}

    if not data:
        raise BadRequestError(message="No data provided for update", details={"parameter": "body"})

    try:
        repo = _get_repository()
        result = repo.update_whitelist(id=id, data=data)

        if not result:
            raise NotFoundError(message=f"Whitelist entry with id={id} not found", details={"id": id})

        response, status = success_response(result)
        return jsonify(response), status

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Whitelist update error for id={id}: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to update whitelist entry id={id}: {type(e).__name__}",
            table="whitelist_ips",
        )


@ip_management_api_bp.route("/whitelist/<int:id>", methods=["DELETE"])
def delete_whitelist(id: int) -> tuple[Response, int]:
    try:
        repo = _get_repository()
        deleted_ip = repo.delete_whitelist(id=id)

        if not deleted_ip:
            raise NotFoundError(message=f"Whitelist entry with id={id} not found", details={"id": id})

        response, status = deleted_response(deleted_ip)
        return jsonify(response), status

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Whitelist deletion error for id={id}: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to delete whitelist entry id={id}: {type(e).__name__}",
            table="whitelist_ips",
        )


@ip_management_api_bp.route("/blacklist", methods=["GET"])
def get_blacklist() -> tuple[Response, int]:
    page, limit = validate_pagination(
        request.args.get("page", 1),
        request.args.get("limit", 50),
    )

    try:
        repo = _get_repository()
        items, total = repo.get_blacklist(page=page, limit=limit)
        return jsonify(paginated_response(items, total, page, limit)), 200

    except Exception as e:
        logger.error(f"Blacklist query error: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to retrieve blacklist: {type(e).__name__}",
            table="blacklist_ips",
        )


@ip_management_api_bp.route("/blacklist", methods=["POST"])
def create_blacklist() -> tuple[Response, int]:
    data = request.get_json() or {}

    if not data or "ip_address" not in data:
        raise BadRequestError(message="ip_address is required", details={"parameter": "ip_address"})

    try:
        repo = _get_repository()
        result = repo.create_blacklist(
            ip_address=data["ip_address"],
            reason=data.get("reason", "Malicious Activity"),
            source=data.get("source", "MANUAL"),
            confidence_level=data.get("confidence_level", 50),
            detection_count=data.get("detection_count", 1),
            is_active=data.get("is_active", True),
            country=data.get("country"),
            detection_date=data.get("detection_date"),
            removal_date=data.get("removal_date"),
        )
        response, _ = success_response(result, 201)
        return jsonify(response), 201

    except Exception as e:
        logger.error(f"Blacklist creation error: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to create blacklist entry: {type(e).__name__}",
            table="blacklist_ips",
        )


@ip_management_api_bp.route("/blacklist/<int:id>", methods=["PUT"])
def update_blacklist(id: int) -> tuple[Response, int]:
    data = request.get_json() or {}

    if not data:
        raise BadRequestError(message="No data provided for update", details={"parameter": "body"})

    try:
        repo = _get_repository()
        result = repo.update_blacklist(id=id, data=data)

        if not result:
            raise NotFoundError(message=f"Blacklist entry with id={id} not found", details={"id": id})

        response, status = success_response(result)
        return jsonify(response), status

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Blacklist update error for id={id}: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to update blacklist entry id={id}: {type(e).__name__}",
            table="blacklist_ips",
        )


@ip_management_api_bp.route("/blacklist/<int:id>", methods=["DELETE"])
def delete_blacklist(id: int) -> tuple[Response, int]:
    try:
        repo = _get_repository()
        deleted_ip = repo.delete_blacklist(id=id)

        if not deleted_ip:
            raise NotFoundError(message=f"Blacklist entry with id={id} not found", details={"id": id})

        response, status = deleted_response(deleted_ip)
        return jsonify(response), status

    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Blacklist deletion error for id={id}: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to delete blacklist entry id={id}: {type(e).__name__}",
            table="blacklist_ips",
        )


ip_management_legacy_bp.add_url_rule("/unified", view_func=get_unified_ip_list, methods=["GET"])
ip_management_legacy_bp.add_url_rule("/statistics", view_func=get_ip_statistics, methods=["GET"])
ip_management_legacy_bp.add_url_rule("/whitelist", view_func=get_whitelist, methods=["GET"])
ip_management_legacy_bp.add_url_rule("/whitelist", view_func=create_whitelist, methods=["POST"])
ip_management_legacy_bp.add_url_rule("/whitelist/<int:id>", view_func=update_whitelist, methods=["PUT"])
ip_management_legacy_bp.add_url_rule("/whitelist/<int:id>", view_func=delete_whitelist, methods=["DELETE"])
ip_management_legacy_bp.add_url_rule("/blacklist", view_func=get_blacklist, methods=["GET"])
ip_management_legacy_bp.add_url_rule("/blacklist/list", view_func=get_blacklist, methods=["GET"])
ip_management_legacy_bp.add_url_rule("/blacklist", view_func=create_blacklist, methods=["POST"])
ip_management_legacy_bp.add_url_rule("/blacklist/<int:id>", view_func=update_blacklist, methods=["PUT"])
ip_management_legacy_bp.add_url_rule("/blacklist/<int:id>", view_func=delete_blacklist, methods=["DELETE"])

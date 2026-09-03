from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest
import psycopg2
from flask import Flask, g

from core.errors.handlers import register_error_handlers


def _ip_app() -> Flask:
    from core.routes.api.ip_management.routes import ip_management_api_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(ip_management_api_bp, url_prefix="/api/ip-management")
    register_error_handlers(app)
    app.extensions["db_service"] = MagicMock()
    app.extensions["blacklist_service"] = MagicMock()

    @app.before_request
    def request_id() -> None:
        g.request_id = "security-test-request"

    return app


def _batch_app() -> Flask:
    from core.routes.api.blacklist.batch import blacklist_batch_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(blacklist_batch_bp)
    register_error_handlers(app)
    app.extensions["db_service"] = MagicMock()
    app.extensions["blacklist_service"] = MagicMock()
    return app


def test_collection_credentials_table_cannot_be_browsed() -> None:
    from core.routes.api.database_api import database_api_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(database_api_bp)
    register_error_handlers(app)
    app.extensions["db_service"] = MagicMock()

    response = app.test_client().get("/database/table/collection_credentials")

    assert response.status_code == 400
    app.extensions["db_service"].get_connection.assert_not_called()


@pytest.mark.parametrize("list_name", ["whitelist", "blacklist"])
def test_create_rejects_invalid_ip_address(list_name: str) -> None:
    app = _ip_app()

    response = app.test_client().post(
        f"/api/ip-management/{list_name}",
        json={"ip_address": "999.999.999.999"},
    )

    assert response.status_code == 400


@pytest.mark.parametrize("list_name", ["whitelist", "blacklist"])
def test_update_rejects_identity_field_mass_assignment(list_name: str) -> None:
    app = _ip_app()

    response = app.test_client().put(
        f"/api/ip-management/{list_name}/1",
        json={"ip_address": "203.0.113.20", "source": "FORGED"},
    )

    assert response.status_code == 400


def test_blacklist_create_rejects_out_of_range_confidence() -> None:
    app = _ip_app()

    response = app.test_client().post(
        "/api/ip-management/blacklist",
        json={"ip_address": "203.0.113.20", "confidence_level": 101},
    )

    assert response.status_code == 400


def test_batch_remove_rejects_invalid_ip() -> None:
    app = _batch_app()

    response = app.test_client().post("/blacklist/batch/remove", json={"ips": ["not-an-ip"]})

    assert response.status_code == 400


def test_batch_update_rejects_oversized_request() -> None:
    app = _batch_app()

    response = app.test_client().post(
        "/blacklist/batch/update",
        json={"ips": [f"198.51.100.{index % 255}" for index in range(1001)], "reason": "bulk"},
    )

    assert response.status_code == 413


def test_batch_remove_sql_error_cannot_return_success() -> None:
    app = _batch_app()
    connection = MagicMock()
    cursor = MagicMock()
    cursor.execute.side_effect = psycopg2.DatabaseError("database-secret-detail")
    connection.cursor.return_value = cursor
    app.extensions["db_service"].get_connection.return_value = connection

    response = app.test_client().post("/blacklist/batch/remove", json={"ips": ["203.0.113.10"]})

    assert response.status_code == 500
    assert response.get_json()["success"] is False
    assert "database-secret-detail" not in response.get_data(as_text=True)


def test_ip_mutation_invalidates_blacklist_and_whitelist_cache_keys() -> None:
    app = _ip_app()
    updated = {"id": 1, "ip_address": "203.0.113.10", "reason": "updated"}

    with patch(
        "core.routes.api.ip_management.routes.IPManagementRepository.update_blacklist",
        return_value=updated,
    ):
        response = app.test_client().put(
            "/api/ip-management/blacklist/1",
            json={"reason": "updated"},
        )

    assert response.status_code == 200
    app.extensions["blacklist_service"].redis_client.delete.assert_called_once_with(
        "blacklist:203.0.113.10",
        "whitelist:203.0.113.10",
    )


def test_export_rejects_requested_limit_above_cap() -> None:
    from core.routes.api.blacklist.core import blacklist_core_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(blacklist_core_bp)
    register_error_handlers(app)
    app.extensions["db_service"] = Mock()
    app.extensions["blacklist_service"] = Mock()

    response = app.test_client().get("/blacklist/export-raw?limit=10001")

    assert response.status_code == 400


def test_export_neutralizes_formula_cells_over_http() -> None:
    from core.routes.api.blacklist.core import blacklist_core_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(blacklist_core_bp)
    register_error_handlers(app)
    database = MagicMock()
    connection = MagicMock()
    cursor = MagicMock()
    connection.cursor.return_value.__enter__.return_value = cursor
    cursor.fetchall.return_value = [
        (
            "203.0.113.10",
            "MANUAL",
            "KR",
            None,
            None,
            "=WEBSERVICE('https://example.invalid')",
            90,
            1,
            True,
            None,
            None,
            {},
        )
    ]
    database.get_connection.return_value = connection
    app.extensions["db_service"] = database
    app.extensions["blacklist_service"] = Mock()

    response = app.test_client().get("/blacklist/export-raw?limit=10")

    assert response.status_code == 200
    assert b"'=WEBSERVICE" in response.data
    assert "LIMIT %s" in cursor.execute.call_args.args[0]


def test_settings_error_response_hides_exception_detail() -> None:
    from core.routes.api.settings_api import settings_api_bp

    app = Flask(__name__)
    app.register_blueprint(settings_api_bp)
    settings = MagicMock()
    settings.get_all_settings.side_effect = RuntimeError("settings-secret-detail")
    app.extensions["settings_service"] = settings

    response = app.test_client().get("/settings")

    assert response.status_code == 500
    assert "settings-secret-detail" not in response.get_data(as_text=True)

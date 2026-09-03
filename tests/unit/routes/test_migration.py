import importlib.util

import pytest
from flask import Flask


def _create_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    from core.routes.api import api_bp

    app.register_blueprint(api_bp)
    return app


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/migration/regtech-test-collection"),
        ("POST", "/api/migration/reset-all-data"),
        ("GET", "/api/migration/status"),
        ("GET", "/api/migration/test-page"),
    ],
)
def test_obsolete_migration_route_is_unreachable(method: str, path: str) -> None:
    response = _create_app().test_client().open(path, method=method)

    assert response.status_code == 404


def test_obsolete_migration_module_is_removed() -> None:
    assert importlib.util.find_spec("core.routes.api.migration") is None

from unittest.mock import Mock

from flask import Blueprint, Flask

from core.routes.web.collection_panel_view_routes import register_collection_panel_view_routes


def test_load_credentials_never_returns_password() -> None:
    app = Flask(__name__)
    app.config["TESTING"] = True
    blueprint = Blueprint("collection_panel_security", __name__)
    csrf = Mock()
    csrf.exempt.side_effect = lambda function: function
    register_collection_panel_view_routes(blueprint, csrf)
    app.register_blueprint(blueprint)
    credential_service = Mock()
    credential_service.get_credentials.return_value = {
        "username": "configured-user",
        "password": "sensitive-password",
    }
    app.extensions["secure_credential_service"] = credential_service

    with app.test_client() as client:
        response = client.get("/api/load-credentials")

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "credentials": {
            "regtech_username": "configured-user",
            "has_password": True,
        },
    }

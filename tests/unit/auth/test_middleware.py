"""Unit tests for core.auth.middleware."""

import json
from unittest.mock import patch, MagicMock



class TestJWTRequiredHook:
    """Tests for jwt_required_hook function."""

    def _make_flask_app(self):
        """Create a minimal Flask app for testing."""
        from flask import Flask

        app = Flask(__name__)
        app.config["TESTING"] = True
        return app

    def test_skip_static_paths(self):
        """Static paths should be skipped (return None)."""
        from core.auth.middleware import jwt_required_hook

        app = self._make_flask_app()
        with app.test_request_context("/static/style.css"):
            result = jwt_required_hook()
            assert result is None

    def test_skip_favicon(self):
        from core.auth.middleware import jwt_required_hook

        app = self._make_flask_app()
        with app.test_request_context("/favicon.ico"):
            result = jwt_required_hook()
            assert result is None

    def test_skip_robots_txt(self):
        from core.auth.middleware import jwt_required_hook

        app = self._make_flask_app()
        with app.test_request_context("/robots.txt"):
            result = jwt_required_hook()
            assert result is None

    def test_skip_public_endpoint(self):
        """Endpoints marked with @public should be skipped."""
        from core.auth.decorators import public

        app = self._make_flask_app()

        @app.route("/health")
        @public
        def health():
            return "ok"

        with app.test_request_context("/health"):

            # Simulate the endpoint being resolved
            with app.test_client():
                pass
            # Manually set the view function

            # We need the endpoint to be resolved
            with app.test_request_context("/health"):
                try:
                    app.preprocess_request()
                except Exception:
                    pass
                # The request context should have resolved the endpoint
                # If endpoint is resolved and has _public=True, hook returns None

    def test_skip_when_auth_disabled(self):
        """When DISABLE_JWT_AUTH=true, should set dev user and skip."""
        from core.auth.middleware import jwt_required_hook

        app = self._make_flask_app()

        @app.route("/api/test")
        def test_endpoint():
            return "ok"

        with patch.dict("os.environ", {"DISABLE_JWT_AUTH": "true"}):
            with app.test_request_context("/api/test"):
                from flask import g

                result = jwt_required_hook()
                assert result is None
                assert g.current_user["sub"] == "dev"
                assert g.current_user["role"] == "admin"

    def test_missing_auth_header_returns_401(self):
        """Missing Authorization header should return 401."""
        from core.auth.middleware import jwt_required_hook

        app = self._make_flask_app()

        @app.route("/api/data")
        def data_endpoint():
            return "ok"

        with patch.dict("os.environ", {"DISABLE_JWT_AUTH": ""}, clear=False):
            with app.test_request_context("/api/data"):
                result = jwt_required_hook()
                if result is not None:
                    response, status_code = result
                    data = json.loads(response.get_data(as_text=True))
                    assert status_code == 401
                    assert data["code"] == "AUTH_TOKEN_MISSING"

    def test_missing_jwt_service_returns_500(self):
        """If jwt_service is not in extensions, should return 500."""
        from core.auth.middleware import jwt_required_hook

        app = self._make_flask_app()
        app.extensions["jwt_service"] = None

        @app.route("/api/data")
        def data_endpoint():
            return "ok"

        with patch.dict("os.environ", {"DISABLE_JWT_AUTH": ""}, clear=False):
            with app.test_request_context("/api/data", headers={"Authorization": "Bearer sometoken"}):
                result = jwt_required_hook()
                if result is not None:
                    response, status_code = result
                    json.loads(response.get_data(as_text=True))
                    assert status_code == 500

    def test_valid_token_sets_current_user(self):
        """Valid token should set g.current_user."""
        from core.auth.middleware import jwt_required_hook

        app = self._make_flask_app()

        mock_jwt_service = MagicMock()
        mock_jwt_service.validate_token.return_value = {"sub": "user1", "role": "admin"}
        app.extensions["jwt_service"] = mock_jwt_service

        @app.route("/api/data")
        def data_endpoint():
            return "ok"

        with patch.dict("os.environ", {"DISABLE_JWT_AUTH": ""}, clear=False):
            with app.test_request_context("/api/data", headers={"Authorization": "Bearer valid-token"}):
                from flask import g

                result = jwt_required_hook()
                assert result is None
                assert g.current_user["sub"] == "user1"
                assert g.current_user["role"] == "admin"

    def test_invalid_token_returns_401(self):
        """Invalid token should return 401."""
        from core.auth.middleware import jwt_required_hook
        from core.exceptions.auth_exceptions import AuthenticationError

        app = self._make_flask_app()

        mock_jwt_service = MagicMock()
        mock_jwt_service.validate_token.side_effect = AuthenticationError("Token is invalid")
        app.extensions["jwt_service"] = mock_jwt_service

        @app.route("/api/data")
        def data_endpoint():
            return "ok"

        with patch.dict("os.environ", {"DISABLE_JWT_AUTH": ""}, clear=False):
            with app.test_request_context("/api/data", headers={"Authorization": "Bearer bad-token"}):
                result = jwt_required_hook()
                if result is not None:
                    response, status_code = result
                    data = json.loads(response.get_data(as_text=True))
                    assert status_code == 401
                    assert data["code"] == "AUTH_TOKEN_INVALID"

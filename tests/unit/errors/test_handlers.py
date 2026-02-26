import uuid
from unittest.mock import MagicMock


class TestRegisterErrorHandlers:
    def test_registers_handlers(self):
        mock_app = MagicMock()
        from core.errors.handlers import register_error_handlers

        register_error_handlers(mock_app)
        assert mock_app.errorhandler.called or mock_app.before_request.called


class TestAPIErrorHandler:
    def test_handles_api_error(self):
        from flask import Flask
        from core.exceptions.base_exceptions import APIError
        from core.errors.handlers import register_error_handlers

        app = Flask(__name__)
        register_error_handlers(app)

        @app.route("/test-error")
        def raise_error():
            raise APIError("Test error", status_code=400, error_code="TEST_ERROR")

        with app.test_client() as client:
            resp = client.get("/test-error")
            assert resp.status_code == 400

    def test_api_error_response_format(self):
        from flask import Flask
        from core.exceptions.base_exceptions import APIError
        from core.errors.handlers import register_error_handlers

        app = Flask(__name__)
        register_error_handlers(app)

        @app.route("/test-api-error-format")
        def raise_error():
            raise APIError("Bad input", status_code=422, error_code="VALIDATION_FAIL")

        with app.test_client() as client:
            resp = client.get("/test-api-error-format")
            assert resp.status_code == 422
            data = resp.get_json()
            assert data is not None


class TestHTTPExceptionHandler:
    def test_handles_404(self):
        from flask import Flask
        from core.errors.handlers import register_error_handlers

        app = Flask(__name__)
        register_error_handlers(app)

        with app.test_client() as client:
            resp = client.get("/nonexistent-route-xyz")
            assert resp.status_code == 404
            data = resp.get_json()
            assert data is not None
            assert data.get("success") is False

    def test_handles_405(self):
        from flask import Flask
        from core.errors.handlers import register_error_handlers

        app = Flask(__name__)
        register_error_handlers(app)

        @app.route("/only-get", methods=["GET"])
        def get_only():
            return {"ok": True}

        with app.test_client() as client:
            resp = client.post("/only-get")
            assert resp.status_code == 405


class TestGenericExceptionHandler:
    def test_handles_runtime_error(self):
        from flask import Flask
        from core.errors.handlers import register_error_handlers

        app = Flask(__name__)
        register_error_handlers(app)

        @app.route("/test-runtime-error")
        def raise_runtime():
            raise RuntimeError("unexpected")

        with app.test_client() as client:
            resp = client.get("/test-runtime-error")
            assert resp.status_code == 500

    def test_generic_error_response_format(self):
        from flask import Flask
        from core.errors.handlers import register_error_handlers

        app = Flask(__name__)
        register_error_handlers(app)

        @app.route("/test-generic-format")
        def raise_error():
            raise ValueError("something broke")

        with app.test_client() as client:
            resp = client.get("/test-generic-format")
            assert resp.status_code == 500
            data = resp.get_json()
            assert data is not None
            assert data.get("success") is False


class TestRequestIdAssignment:
    def test_assigns_request_id(self):
        from flask import Flask, g
        from core.errors.handlers import register_error_handlers

        app = Flask(__name__)
        register_error_handlers(app)

        @app.route("/test-request-id")
        def check_id():
            return {"request_id": g.get("request_id", "none")}

        with app.test_client() as client:
            resp = client.get("/test-request-id")
            data = resp.get_json()
            request_id = data.get("request_id", "none")
            assert request_id != "none"
            try:
                uuid.UUID(request_id)
                is_valid_uuid = True
            except ValueError:
                is_valid_uuid = False
            assert is_valid_uuid

    def test_different_requests_get_different_ids(self):
        from flask import Flask, g
        from core.errors.handlers import register_error_handlers

        app = Flask(__name__)
        register_error_handlers(app)

        @app.route("/test-unique-id")
        def check_id():
            return {"request_id": g.get("request_id", "none")}

        with app.test_client() as client:
            resp1 = client.get("/test-unique-id")
            resp2 = client.get("/test-unique-id")
            id1 = resp1.get_json().get("request_id")
            id2 = resp2.get_json().get("request_id")
            assert id1 != id2

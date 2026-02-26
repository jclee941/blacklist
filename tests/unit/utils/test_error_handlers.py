class TestHandleException:
    def test_returns_tuple(self):
        from flask import Flask

        app = Flask(__name__)
        with app.app_context():
            from core.utils.error_handlers import handle_exception

            response, status = handle_exception(ValueError("test error"))
            assert status == 500

    def test_includes_error_message(self):
        from flask import Flask

        app = Flask(__name__)
        with app.app_context():
            from core.utils.error_handlers import handle_exception

            response, status = handle_exception(ValueError("my error"))
            data = response.get_json()
            assert "my error" in data.get("error", "")

    def test_includes_context(self):
        from flask import Flask

        app = Flask(__name__)
        with app.app_context():
            from core.utils.error_handlers import handle_exception

            response, status = handle_exception(ValueError("err"), context="processing")
            data = response.get_json()
            assert "processing" in data.get("error", "")

    def test_success_is_false(self):
        from flask import Flask

        app = Flask(__name__)
        with app.app_context():
            from core.utils.error_handlers import handle_exception

            response, status = handle_exception(RuntimeError("fail"))
            data = response.get_json()
            assert data.get("success") is False

    def test_includes_timestamp(self):
        from flask import Flask

        app = Flask(__name__)
        with app.app_context():
            from core.utils.error_handlers import handle_exception

            response, status = handle_exception(RuntimeError("fail"))
            data = response.get_json()
            assert "timestamp" in data

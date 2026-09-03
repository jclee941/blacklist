from __future__ import annotations

from unittest.mock import MagicMock

from flask import Flask


def test_default_rate_limit_whitelist_excludes_docker_ranges(monkeypatch) -> None:
    from core.config import AppConfig

    monkeypatch.delenv("RATE_LIMIT_WHITELIST", raising=False)

    whitelist = AppConfig().RATE_LIMIT_WHITELIST

    assert "172." not in whitelist
    assert "192.168." not in whitelist


def test_declared_route_limit_is_applied_during_app_setup() -> None:
    from core.utils.rate_limit import apply_route_limits, rate_limit

    app = Flask(__name__)
    limiter = MagicMock()
    limiter.limit.side_effect = lambda _limit: lambda view: view

    @app.get("/limited")
    @rate_limit("2 per minute")
    def limited() -> str:
        return "ok"

    apply_route_limits(app, limiter)

    limiter.limit.assert_called_once_with("2 per minute")


def test_declared_route_limit_returns_429_over_http() -> None:
    from flask_limiter import Limiter

    from core.utils.rate_limit import apply_route_limits, rate_limit

    app = Flask(__name__)
    limiter = Limiter(key_func=lambda: "client", app=app, storage_uri="memory://", default_limits=[])

    @app.get("/limited")
    @rate_limit("2 per minute")
    def limited() -> str:
        return "ok"

    apply_route_limits(app, limiter)
    client = app.test_client()

    assert client.get("/limited").status_code == 200
    assert client.get("/limited").status_code == 200
    assert client.get("/limited").status_code == 429


def test_only_operational_probe_paths_are_rate_limit_exempt() -> None:
    from core.utils.rate_limit import is_rate_limit_exempt_path

    assert is_rate_limit_exempt_path("/health") is True
    assert is_rate_limit_exempt_path("/api/health") is True
    assert is_rate_limit_exempt_path("/metrics") is True
    assert is_rate_limit_exempt_path("/api/auth/login") is False


def test_csv_formula_prefix_is_neutralized() -> None:
    from core.utils.csv_security import neutralize_csv_cell

    assert neutralize_csv_cell("=WEBSERVICE('https://example.invalid')") == "'=WEBSERVICE('https://example.invalid')"
    assert neutralize_csv_cell(" +SUM(1,2)") == "' +SUM(1,2)"
    assert neutralize_csv_cell("ordinary text") == "ordinary text"

from typing import Any

from flask import Flask, g
from pytest import MonkeyPatch

from app.core.routes.api.collection import trigger as trigger_module


def test_regtech_trigger_allows_full_collection_time(monkeypatch: MonkeyPatch) -> None:
    requested_timeout: int | None = None

    def call_collector_api(
        endpoint: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        *,
        timeout: int | None = None,
    ) -> dict[str, bool]:
        nonlocal requested_timeout
        _ = endpoint, method, data
        requested_timeout = timeout
        return {"success": True}

    monkeypatch.setattr(trigger_module, "call_collector_api", call_collector_api)
    app = Flask(__name__)

    with app.test_request_context("/trigger/regtech", method="POST", json={}):
        g.request_id = "test-request"
        _ = trigger_module.trigger_collection("regtech")

    assert requested_timeout == 90

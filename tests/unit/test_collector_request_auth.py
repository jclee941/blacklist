from pathlib import Path
from unittest.mock import patch

import pytest

from core.config import config


AUTH_TOKEN = "test-app-to-collector-token"
REPOSITORY_ROOT = Path(__file__).parents[2]
COLLECTOR_CALLER_PATHS = (
    "app/core/app.py",
    "app/core/routes/proxy_routes.py",
    "app/core/routes/api/blacklist/collection.py",
    "app/core/routes/api/collection/utils.py",
    "app/core/routes/web/collection_panel_runtime_routes.py",
    "app/core/services/blacklist_service.py",
    "app/core/services/blacklist_service_sync.py",
    "app/core/services/collection/collection_status.py",
    "app/core/services/regtech_config_service.py",
)


class ResponseFake:
    status_code: int
    text: str
    _payload: dict[str, bool | str]

    def __init__(self, payload: dict[str, bool | str]) -> None:
        self.status_code = 200
        self.text = ""
        self._payload = payload

    def json(self) -> dict[str, bool | str]:
        return self._payload


def test_collector_auth_request_kwargs_are_empty_without_shared_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COLLECTOR_AUTH_TOKEN", raising=False)

    request_kwargs = config.COLLECTOR_AUTH_REQUEST_KWARGS

    assert request_kwargs == {}


def test_collector_auth_request_kwargs_contain_bearer_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COLLECTOR_AUTH_TOKEN", AUTH_TOKEN)

    request_kwargs = config.COLLECTOR_AUTH_REQUEST_KWARGS

    assert request_kwargs == {"headers": {"Authorization": f"Bearer {AUTH_TOKEN}"}}


def test_collector_get_constructs_authenticated_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COLLECTOR_AUTH_TOKEN", AUTH_TOKEN)
    response = ResponseFake({"status": "healthy"})

    with patch("core.routes.api.collection.utils.requests.get", return_value=response) as request_get:
        from core.routes.api.collection.utils import call_collector_api

        result = call_collector_api("/health")

    assert result == {"status": "healthy"}
    request_get.assert_called_once_with(
        "http://blacklist-collector:8545/health",
        timeout=10,
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )


def test_collector_post_constructs_authenticated_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COLLECTOR_AUTH_TOKEN", AUTH_TOKEN)
    response = ResponseFake({"success": True})
    payload = {"source": "REGTECH"}

    with patch("core.routes.api.collection.utils.requests.post", return_value=response) as request_post:
        from core.routes.api.collection.utils import call_collector_api

        result = call_collector_api("/trigger", method="POST", data=payload)

    assert result == {"success": True}
    request_post.assert_called_once_with(
        "http://blacklist-collector:8545/trigger",
        json=payload,
        timeout=30,
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )


@pytest.mark.parametrize("relative_path", COLLECTOR_CALLER_PATHS)
def test_every_collector_caller_uses_auth_request_kwargs(relative_path: str) -> None:
    source = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")

    assert "COLLECTOR_AUTH_REQUEST_KWARGS" in source

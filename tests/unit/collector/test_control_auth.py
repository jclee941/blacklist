from collections.abc import Iterator

import pytest

from collector.health_server import HealthServer


AUTH_TOKEN = "test-collector-control-token"


class DatabaseFake:
    def get_collection_credentials(self, _service_name: str) -> None:
        return None

    def get_collection_status(self, _service_name: str) -> None:
        return None


class SchedulerFake:
    def __init__(self) -> None:
        self.sources: list[str] = []
        self.collection_stats: dict[str, int] = {
            "total_runs": 0,
            "failed_runs": 0,
            "adaptive_interval": 86_400,
        }

    def force_collection(self, source: str) -> dict[str, bool]:
        self.sources.append(source)
        return {"success": True}

    def _get_next_run_time(self) -> None:
        return None


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[HealthServer, SchedulerFake]]:
    monkeypatch.setenv("DISABLE_JWT_AUTH", "false")
    monkeypatch.setenv("COLLECTOR_AUTH_TOKEN", AUTH_TOKEN)
    scheduler = SchedulerFake()
    health_server = HealthServer(collectors_ref={}, scheduler_ref=scheduler, port=18_545)
    monkeypatch.setattr(health_server, "_db", DatabaseFake())
    yield health_server, scheduler


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/trigger", {"source": "REGTECH"}),
        ("/api/test-auth/REGTECH", None),
        ("/api/force-collection/REGTECH", None),
    ],
)
def test_control_endpoint_rejects_missing_authorization(
    server: tuple[HealthServer, SchedulerFake],
    path: str,
    payload: dict[str, str] | None,
) -> None:
    health_server, scheduler = server

    response = health_server.app.test_client().post(path, json=payload)

    assert response.status_code == 401
    assert response.get_json() == {"error": "Unauthorized"}
    assert scheduler.sources == []


def test_control_endpoint_rejects_invalid_bearer_token(
    server: tuple[HealthServer, SchedulerFake],
) -> None:
    health_server, scheduler = server

    response = health_server.app.test_client().post(
        "/trigger",
        json={"source": "REGTECH"},
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.get_json() == {"error": "Unauthorized"}
    assert scheduler.sources == []


def test_control_endpoint_fails_closed_without_shared_token(
    server: tuple[HealthServer, SchedulerFake],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    health_server, scheduler = server
    monkeypatch.delenv("COLLECTOR_AUTH_TOKEN")

    response = health_server.app.test_client().post(
        "/trigger",
        json={"source": "REGTECH"},
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )

    assert response.status_code == 401
    assert response.get_json() == {"error": "Unauthorized"}
    assert scheduler.sources == []


def test_control_endpoint_accepts_valid_bearer_token(
    server: tuple[HealthServer, SchedulerFake],
) -> None:
    health_server, scheduler = server

    response = health_server.app.test_client().post(
        "/trigger",
        json={"source": "REGTECH"},
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert scheduler.sources == ["REGTECH"]


def test_trigger_propagates_collection_failure(
    server: tuple[HealthServer, SchedulerFake],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    health_server, scheduler = server
    monkeypatch.setattr(
        scheduler,
        "force_collection",
        lambda _source: {"success": False, "error": "page 17 failed"},
    )

    response = health_server.app.test_client().post(
        "/trigger",
        json={"source": "REGTECH"},
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )

    assert response.status_code == 500
    assert response.get_json()["success"] is False
    assert response.get_json()["error"] == "Collection failed"
    assert "page 17 failed" not in response.get_data(as_text=True)


def test_health_endpoint_remains_open_with_coarse_status(
    server: tuple[HealthServer, SchedulerFake],
) -> None:
    health_server, _scheduler = server

    response = health_server.app.test_client().get("/health")

    assert response.status_code == 200
    assert set(response.get_json()) == {"status", "timestamp"}


@pytest.mark.parametrize("path", ["/status", "/logs"])
def test_operational_endpoint_rejects_missing_authorization(
    server: tuple[HealthServer, SchedulerFake],
    path: str,
) -> None:
    health_server, _scheduler = server

    response = health_server.app.test_client().get(path)

    assert response.status_code == 401
    assert response.get_json() == {"error": "Unauthorized"}


@pytest.mark.parametrize("path", ["/status", "/logs"])
def test_operational_endpoint_accepts_control_bearer(
    server: tuple[HealthServer, SchedulerFake],
    path: str,
) -> None:
    health_server, _scheduler = server

    response = health_server.app.test_client().get(
        path,
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
    )

    assert response.status_code == 200


def test_disable_jwt_auth_restores_open_control_access_in_development(
    server: tuple[HealthServer, SchedulerFake],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    health_server, scheduler = server
    monkeypatch.setenv("DISABLE_JWT_AUTH", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")

    response = health_server.app.test_client().post(
        "/trigger",
        json={"source": "REGTECH"},
    )

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert scheduler.sources == ["REGTECH"]


def test_disable_jwt_auth_does_not_bypass_production_control_authentication(
    server: tuple[HealthServer, SchedulerFake],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    health_server, scheduler = server
    monkeypatch.setenv("DISABLE_JWT_AUTH", "true")
    monkeypatch.setenv("ENVIRONMENT", "production")

    response = health_server.app.test_client().post("/trigger", json={"source": "REGTECH"})

    assert response.status_code == 401
    assert scheduler.sources == []

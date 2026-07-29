import pytest

from collector.health_server import CollectorStatus, HealthServer


class DatabaseFake:
    def get_collection_credentials(self, _service_name: str) -> dict[str, bool]:
        return {"enabled": True}

    def get_collection_status(self, _service_name: str) -> dict[str, str | int | bool]:
        return {
            "enabled": True,
            "last_run": "2026-07-28T11:57:29.898479",
            "status": "idle",
            "error_count": 0,
            "success_count": 7,
        }


class SchedulerFake:
    def __init__(self) -> None:
        self.collection_stats: dict[str, str | int] = {
            "total_runs": 4,
            "failed_runs": 0,
            "adaptive_interval": 86_400,
            "last_run": "2026-07-28T09:47:23.970172",
        }

    def _get_next_run_time(self) -> str:
        return "2026-07-29T00:00:00"


class HealthServerHarness(HealthServer):
    def collector_status(self) -> dict[str, CollectorStatus]:
        return self._get_collector_status()

    def run_server(self) -> None:
        self._run_server()


class ServerFake:
    def __init__(self) -> None:
        self.served = False

    def serve_forever(self) -> None:
        self.served = True


def test_collector_status_uses_database_run_totals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scheduler = SchedulerFake()
    server = HealthServerHarness(collectors_ref={}, scheduler_ref=scheduler)
    monkeypatch.setattr(server, "_db", DatabaseFake())

    status = server.collector_status()["REGTECH"]

    assert status["run_count"] == 7
    assert status["error_count"] == 0
    assert status["last_run"] == "2026-07-28T11:57:29.898479"
    assert status["interval_seconds"] == 86_400
    assert status["next_run"] == "2026-07-29T00:00:00"


def test_health_server_serves_tls_on_the_container_network(monkeypatch: pytest.MonkeyPatch) -> None:
    server_fake = ServerFake()
    calls: list[tuple[str, int, object, tuple[str, str], bool]] = []

    def make_server(
        host: str,
        port: int,
        app: object,
        *,
        ssl_context: tuple[str, str],
        threaded: bool,
    ) -> ServerFake:
        calls.append((host, port, app, ssl_context, threaded))
        return server_fake

    monkeypatch.setattr("collector.health_server.make_server", make_server)
    monkeypatch.setenv("INTERNAL_TLS_CERT", "/probe/tls.crt")
    monkeypatch.setenv("INTERNAL_TLS_KEY", "/probe/tls.key")
    server = HealthServerHarness(collectors_ref={}, port=8545)

    server.run_server()

    assert calls == [("0.0.0.0", 8545, server.app, ("/probe/tls.crt", "/probe/tls.key"), True)]
    assert server_fake.served is True

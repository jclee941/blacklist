import subprocess

import pytest

from collector.core.regtech.collector import RegtechCollector


PROXY_URL = "http://host.docker.internal:40000"


class NoWaitLimiter:
    def wait_if_needed(self):
        return True

    def on_failure(self, error_code=None):
        return None

    def on_success(self):
        return None


def page_curl_command(monkeypatch) -> list[str]:
    captured: dict[str, list[str]] = {}

    def fake_run(cmd, *_args, **_kwargs):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="\n403", stderr="")

    monkeypatch.setattr("collector.core.regtech.page_collection.run_text_bounded", fake_run)
    monkeypatch.setattr("collector.core.archive_manager.archive_content", lambda *args, **kwargs: None)
    collector = RegtechCollector()
    monkeypatch.setattr(collector, "rate_limiter", NoWaitLimiter())
    collector._collect_single_page(1, 50, "2026-05-02", "2026-07-31")
    return captured["cmd"]


@pytest.mark.parametrize("enabled", ["true", "TRUE", "1", "yes"])
def test_switch_on_routes_session_and_curl_through_the_proxy(monkeypatch, enabled):
    monkeypatch.setenv("WARP_ENABLED", enabled)
    monkeypatch.setenv("WARP_PROXY_URL", PROXY_URL)

    collector = RegtechCollector()
    command = page_curl_command(monkeypatch)

    assert collector.session.proxies == {"http": PROXY_URL, "https": PROXY_URL}
    assert command[command.index("--proxy") + 1] == PROXY_URL


@pytest.mark.parametrize("enabled", ["false", "", None])
def test_switch_off_ignores_a_configured_proxy_url(monkeypatch, enabled):
    if enabled is None:
        monkeypatch.delenv("WARP_ENABLED", raising=False)
    else:
        monkeypatch.setenv("WARP_ENABLED", enabled)
    monkeypatch.setenv("WARP_PROXY_URL", PROXY_URL)

    collector = RegtechCollector()
    command = page_curl_command(monkeypatch)

    assert collector.proxy_url is None
    assert collector.session.proxies == {}
    assert "--proxy" not in command


def test_switch_on_without_a_proxy_url_connects_directly(monkeypatch):
    monkeypatch.setenv("WARP_ENABLED", "true")
    monkeypatch.setenv("WARP_PROXY_URL", "")

    collector = RegtechCollector()

    assert collector.proxy_url is None
    assert collector.session.proxies == {}

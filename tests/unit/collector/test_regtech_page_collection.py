"""Tests for REGTECH page collection robustness.

Covers the WAF-block hardening fixes:
- curl HTTP status capture (`-w %{http_code}`) instead of hardcoded 200
- failure classification (block_suspect vs transient) via _last_failure_kind
- circuit breaker aborting the run on consecutive block signals
- env-configurable rate limiter defaults
"""

import subprocess

import pytest


class FakeLimiter:
    """Rate limiter double — records calls without sleeping."""

    def __init__(self):
        self.failures = []
        self.successes = 0

    def wait_if_needed(self):
        return True

    def on_failure(self, error_code=None):
        self.failures.append(error_code)

    def on_success(self):
        self.successes += 1


def _completed(stdout: str, returncode: int = 0, stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


@pytest.fixture
def collector(monkeypatch):
    from collector.core.regtech.collector import RegtechCollector

    instance = RegtechCollector()
    instance.rate_limiter = FakeLimiter()
    monkeypatch.setattr("collector.core.archive_manager.archive_content", lambda *args, **kwargs: None)
    yield instance


def _run_curl(monkeypatch, result):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return result

    monkeypatch.setattr("collector.core.regtech.page_collection.subprocess.run", fake_run)
    return captured


class TestHttpStatusCapture:
    def test_403_flags_block_suspect(self, monkeypatch, collector):
        _run_curl(monkeypatch, _completed("<html>denied</html>\n403"))

        assert collector._collect_single_page(1, 50, "2026-05-02", "2026-07-31") is None
        assert collector._last_failure_kind == "block_suspect"
        assert collector.rate_limiter.failures == [403]

    def test_500_is_transient_http_error(self, monkeypatch, collector):
        _run_curl(monkeypatch, _completed("<html>oops</html>\n500"))

        assert collector._collect_single_page(1, 50, "2026-05-02", "2026-07-31") is None
        assert collector._last_failure_kind == "http_error"
        assert collector.rate_limiter.failures == [500]

    def test_empty_body_is_block_suspect(self, monkeypatch, collector):
        _run_curl(monkeypatch, _completed("\n200"))

        assert collector._collect_single_page(1, 50, "2026-05-02", "2026-07-31") is None
        assert collector._last_failure_kind == "block_suspect"
        assert collector.rate_limiter.failures == [None]

    def test_curl_error_is_not_block_suspect(self, monkeypatch, collector):
        _run_curl(monkeypatch, _completed("", returncode=7, stderr="curl: (7) couldn't connect"))

        assert collector._collect_single_page(1, 50, "2026-05-02", "2026-07-31") is None
        assert collector._last_failure_kind == "curl_error"

    def test_success_clears_failure_kind(self, monkeypatch, collector):
        _run_curl(monkeypatch, _completed("<table>data</table>\n200"))
        monkeypatch.setattr(collector, "_parse_response_data", lambda response: [])

        assert collector._collect_single_page(1, 50, "2026-05-02", "2026-07-31") == []
        assert collector._last_failure_kind is None
        assert collector.rate_limiter.successes == 1

    def test_curl_command_captures_status_and_bounds_time(self, monkeypatch, collector):
        captured = _run_curl(monkeypatch, _completed("\n200"))
        collector._collect_single_page(1, 50, "2026-05-02", "2026-07-31")

        cmd = captured["cmd"]
        assert "-sS" in cmd
        assert "--max-time" in cmd
        assert "-w" in cmd
        assert "\n%{http_code}" in cmd


class TestCircuitBreaker:
    def _prepare_run(self, monkeypatch, collector):
        monkeypatch.setenv("DISABLE_EXCEL_COLLECTION", "true")
        monkeypatch.setattr(collector, "_ensure_authenticated", lambda: True)
        monkeypatch.setattr(
            collector,
            "_generate_date_strategies",
            lambda start_date, end_date: [("사용자 지정", "2026-05-02", "2026-07-31")],
        )
        monkeypatch.setattr(collector, "_post_process_collected_data", lambda data: data)

    def test_consecutive_block_signals_abort_run(self, monkeypatch, collector):
        from collector.core.regtech.collector import RegtechCollectionBlockedError

        self._prepare_run(monkeypatch, collector)

        def blocked_page(page_num, page_size, start_date, end_date):
            collector._last_failure_kind = "block_suspect"
            return None

        monkeypatch.setattr(collector, "_collect_single_page", blocked_page)

        with pytest.raises(RegtechCollectionBlockedError):
            collector.collect_blacklist_data(start_date="2026-05-02", end_date="2026-07-31", max_pages=10)

    def test_transient_block_signals_do_not_abort(self, monkeypatch, collector):
        self._prepare_run(monkeypatch, collector)
        item = {
            "ip_address": "1.2.3.4",
            "source": "REGTECH",
            "reason": "test",
            "country": "KR",
            "detection_date": "2026-07-01",
            "removal_date": None,
        }
        outcomes = [None, None, [item], []]

        def flaky_page(page_num, page_size, start_date, end_date):
            outcome = outcomes.pop(0)
            if outcome is None:
                collector._last_failure_kind = "block_suspect"
            else:
                collector._last_failure_kind = None
            return outcome

        monkeypatch.setattr(collector, "_collect_single_page", flaky_page)

        result = collector.collect_blacklist_data(start_date="2026-05-02", end_date="2026-07-31", max_pages=10)
        assert result == [item]


class TestRateLimiterEnvConfig:
    def test_defaults_are_conservative(self, monkeypatch):
        for var in ("REGTECH_RATE_INITIAL", "REGTECH_RATE_MIN", "REGTECH_RATE_MAX", "REGTECH_RATE_BURST"):
            monkeypatch.delenv(var, raising=False)
        import importlib

        import collector.core.rate_limiter as rate_limiter

        reloaded = importlib.reload(rate_limiter)
        assert reloaded.regtech_rate_limiter.rate == 0.2
        assert reloaded.regtech_rate_limiter.min_rate == 0.1
        assert reloaded.regtech_rate_limiter.max_rate == 0.5
        assert reloaded.regtech_rate_limiter.burst_size == 1

    def test_env_overrides_and_empty_fallback(self, monkeypatch):
        monkeypatch.setenv("REGTECH_RATE_INITIAL", "0.33")
        monkeypatch.setenv("REGTECH_RATE_BURST", "")
        import importlib

        import collector.core.rate_limiter as rate_limiter

        reloaded = importlib.reload(rate_limiter)
        try:
            assert reloaded.regtech_rate_limiter.rate == 0.33
            assert reloaded.regtech_rate_limiter.burst_size == 1
        finally:
            monkeypatch.undo()
            importlib.reload(rate_limiter)

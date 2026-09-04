from unittest.mock import Mock

from collector import run_collector


def test_stop_scrubs_credentials_when_collector_was_not_running(monkeypatch) -> None:
    clear_credentials = Mock()
    monkeypatch.setattr(run_collector.CollectorConfig, "clear_credentials_cache", clear_credentials)
    application = run_collector.CollectorApplication()

    application.stop()

    clear_credentials.assert_called_once_with()


def test_stop_scrubs_credentials_after_scheduler_shutdown(monkeypatch) -> None:
    clear_credentials = Mock()
    monkeypatch.setattr(run_collector.CollectorConfig, "clear_credentials_cache", clear_credentials)
    monkeypatch.setattr(run_collector.scheduler, "stop", Mock())
    application = run_collector.CollectorApplication()
    application.running = True

    application.stop()

    clear_credentials.assert_called_once_with()

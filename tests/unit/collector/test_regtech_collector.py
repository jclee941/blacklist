import subprocess
from urllib.parse import parse_qs

import pytest

from collector.core import archive_manager
from collector.core.regtech.collector import RegtechCollector


class RegtechCollectorHarness(RegtechCollector):
    def collect_single_page(
        self,
        page_num: int,
        page_size: int,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> bool:
        return (
            self._collect_single_page(
                page_num=page_num,
                page_size=page_size,
                start_date=start_date,
                end_date=end_date,
            )
            is None
        )


def test_submits_pagination_fields_to_form_action(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_command: list[str] = []

    def run_curl(command: list[str], **_kwargs: bool | int) -> subprocess.CompletedProcess[str]:
        captured_command.extend(command)
        return subprocess.CompletedProcess(command, returncode=0, stdout="<html></html>", stderr="")

    def archive_content(*_args: str, **_kwargs: str | None) -> None:
        return None

    monkeypatch.setattr(subprocess, "run", run_curl)
    monkeypatch.setattr(archive_manager, "archive_content", archive_content)
    collector = RegtechCollectorHarness()
    collector.base_url = "https://regtech.example.com"

    _ = collector.collect_single_page(
        page_num=2,
        page_size=30,
        start_date="2026-04-28",
        end_date="2026-07-28",
    )

    data_url = captured_command[captured_command.index("POST") + 1]
    form_data = parse_qs(captured_command[captured_command.index("--data") + 1], keep_blank_values=True)
    assert data_url == "https://regtech.example.com/fcti/securityAdvisory/advisoryList"
    assert form_data["page"] == ["1"]
    assert form_data["size"] == ["30"]
    assert form_data["startDate"] == ["20260428"]
    assert form_data["endDate"] == ["20260728"]
    assert captured_command.count("Content-Type: application/x-www-form-urlencoded") == 1


def test_page_transport_failure_returns_retryable_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    def run_curl(command: list[str], **_kwargs: bool | int) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, returncode=7, stdout="", stderr="connection failed")

    monkeypatch.setattr(subprocess, "run", run_curl)
    collector = RegtechCollectorHarness()

    def wait_if_needed() -> bool:
        return True

    def on_failure(error_code: int | None = None) -> None:
        _ = error_code

    monkeypatch.setattr(collector.rate_limiter, "wait_if_needed", wait_if_needed)
    monkeypatch.setattr(collector.rate_limiter, "on_failure", on_failure)

    is_retryable_failure = collector.collect_single_page(page_num=1, page_size=50)

    assert is_retryable_failure


def test_rate_limiter_failure_returns_retryable_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    collector = RegtechCollectorHarness()

    def wait_if_needed() -> bool:
        return False

    monkeypatch.setattr(collector.rate_limiter, "wait_if_needed", wait_if_needed)

    is_retryable_failure = collector.collect_single_page(page_num=1, page_size=50)

    assert is_retryable_failure


def test_page_timeout_returns_retryable_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    def run_curl(command: list[str], **_kwargs: bool | int) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, timeout=60)

    monkeypatch.setattr(subprocess, "run", run_curl)
    collector = RegtechCollectorHarness()

    def wait_if_needed() -> bool:
        return True

    def on_failure(error_code: int | None = None) -> None:
        _ = error_code

    monkeypatch.setattr(collector.rate_limiter, "wait_if_needed", wait_if_needed)
    monkeypatch.setattr(collector.rate_limiter, "on_failure", on_failure)

    is_retryable_failure = collector.collect_single_page(page_num=1, page_size=50)

    assert is_retryable_failure

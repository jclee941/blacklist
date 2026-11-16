import subprocess
from types import SimpleNamespace
from urllib.parse import parse_qs

import pytest
import requests

from collector.core import archive_manager
from collector.core.regtech.collector import RegtechCollector
from collector.core.regtech.errors import RegtechMaintenanceError
from collector.core.regtech.html_parsing import maintenance_notice


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

    def run_curl(command: list[str], *_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        captured_command.extend(command)
        return subprocess.CompletedProcess(command, returncode=0, stdout="<html></html>", stderr="")

    def archive_content(*_args: str, **_kwargs: str | None) -> None:
        return None

    monkeypatch.setattr("collector.core.regtech.page_collection.run_text_bounded", run_curl)
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
    def run_curl(command: list[str], *_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, returncode=7, stdout="", stderr="connection failed")

    monkeypatch.setattr("collector.core.regtech.page_collection.run_text_bounded", run_curl)
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
    def run_curl(command: list[str], *_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, timeout=60)

    monkeypatch.setattr("collector.core.regtech.page_collection.run_text_bounded", run_curl)
    collector = RegtechCollectorHarness()

    def wait_if_needed() -> bool:
        return True

    def on_failure(error_code: int | None = None) -> None:
        _ = error_code

    monkeypatch.setattr(collector.rate_limiter, "wait_if_needed", wait_if_needed)
    monkeypatch.setattr(collector.rate_limiter, "on_failure", on_failure)

    is_retryable_failure = collector.collect_single_page(page_num=1, page_size=50)

    assert is_retryable_failure


def test_page_parse_failure_returns_retryable_outcome(monkeypatch: pytest.MonkeyPatch) -> None:
    def run_curl(command: list[str], *_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr("collector.core.regtech.page_collection.run_text_bounded", run_curl)
    monkeypatch.setattr(archive_manager, "archive_content", lambda *_args, **_kwargs: None)
    collector = RegtechCollectorHarness()
    monkeypatch.setattr(collector, "_parse_response_data", lambda _response: None)
    monkeypatch.setattr(collector.rate_limiter, "wait_if_needed", lambda: True)
    monkeypatch.setattr(collector.rate_limiter, "on_failure", lambda *_args, **_kwargs: None)

    is_retryable_failure = collector.collect_single_page(page_num=1, page_size=50)

    assert is_retryable_failure


# Shape of the page REGTECH served for every URL during the 2026-11-16 maintenance (entity-encoded Korean).
MAINTENANCE_PAGE = (
    '<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">'
    "<title>&#44552;&#50997;&#48372;&#50504;&#50896; &#47112;&#44536;&#53580;&#53356; &#54252;&#53560; "
    "&#51216;&#44160; &#50504;&#45236;</title></head><body><article><div>"
    "<p>&#9675; &#51089;&#50629; &#51068;&#49884; : 2026.11.16. 09:00 ~ "
    "<b>&#48324;&#46020; &#44277;&#51648; &#49884;&#44620;&#51648;</b></p></div></article></body></html>"
)
LOGIN_PAGE = '<html><head><title>REGTECH</title></head><body><form id="loginForm"></form></body></html>'


class LoginSessionFake:
    def __init__(self, login_page: str) -> None:
        self.login_page = login_page
        self.headers: dict[str, str] = {}
        self.proxies: dict[str, str] = {}
        self.cookies = requests.cookies.RequestsCookieJar()
        self.posted_urls: list[str] = []

    def get(self, _url: str, timeout: int) -> SimpleNamespace:
        _ = timeout
        return SimpleNamespace(text=self.login_page)

    def post(self, url: str, **_kwargs: object) -> SimpleNamespace:
        self.posted_urls.append(url)
        return SimpleNamespace(status_code=200, url=url, text="")


class AuthLimiterFake:
    def __init__(self) -> None:
        self.failures = 0

    def wait_if_needed(self) -> bool:
        return True

    def on_failure(self) -> None:
        self.failures += 1


def test_maintenance_page_yields_its_work_window() -> None:
    assert (
        maintenance_notice(MAINTENANCE_PAGE)
        == "\uc791\uc5c5 \uc77c\uc2dc : 2026.11.16. 09:00 ~ \ubcc4\ub3c4 \uacf5\uc9c0 \uc2dc\uae4c\uc9c0"
    )
    assert maintenance_notice(LOGIN_PAGE) is None


@pytest.mark.parametrize(("login_page", "posts", "limiter_failures"), [(MAINTENANCE_PAGE, 0, 0), (LOGIN_PAGE, 1, 1)])
def test_authenticate_skips_login_only_while_regtech_is_in_maintenance(
    login_page: str, posts: int, limiter_failures: int
) -> None:
    collector = RegtechCollector()
    session = LoginSessionFake(login_page)
    limiter = AuthLimiterFake()
    collector.session = session
    collector.auth_rate_limiter = limiter

    if login_page is MAINTENANCE_PAGE:
        with pytest.raises(RegtechMaintenanceError, match="09:00"):
            collector.authenticate("user", "secret")
    else:
        assert collector.authenticate("user", "secret") is False

    assert len(session.posted_urls) == posts
    assert limiter.failures == limiter_failures

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from collector.core.regtech.collector import REGTECH_PAGE_SIZE, RegtechCollector


PageData = list[dict[str, str]]
DateStrategy = tuple[str, str | None, str | None]
PageCollector = Callable[[int, int, str | None, str | None], PageData | None]
ExcelDownloader = Callable[[str, str], PageData]


@dataclass(frozen=True, slots=True)
class CollectorScenario:
    strategies: tuple[DateStrategy, ...]
    collect_page: PageCollector
    excel_enabled: bool = False
    download_excel: ExcelDownloader | None = None


def _record_performance(
    _collected_data: PageData,
    _strategies: list[DateStrategy],
    _duration: float,
) -> None:
    return None


def _post_process(data: PageData) -> PageData:
    return data


def _prepare_collector(
    monkeypatch: pytest.MonkeyPatch,
    scenario: CollectorScenario,
) -> RegtechCollector:
    collector = RegtechCollector()
    if scenario.excel_enabled:
        monkeypatch.delenv("DISABLE_EXCEL_COLLECTION", raising=False)
    else:
        monkeypatch.setenv("DISABLE_EXCEL_COLLECTION", "true")

    def date_strategies(_start: str | None, _end: str | None) -> list[DateStrategy]:
        return list(scenario.strategies)

    monkeypatch.setattr(collector, "_ensure_authenticated", lambda: True)
    monkeypatch.setattr(collector, "_generate_date_strategies", date_strategies)
    monkeypatch.setattr(collector, "_collect_single_page", scenario.collect_page)
    monkeypatch.setattr(collector, "_record_collection_performance", _record_performance)
    monkeypatch.setattr(collector, "_post_process_collected_data", _post_process)
    if scenario.download_excel is not None:
        monkeypatch.setattr(collector, "_download_excel_data", scenario.download_excel)
    return collector


def test_collect_blacklist_data_caps_page_size_without_reducing_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[tuple[int, int]] = []

    def collect_page(
        page_num: int, page_size: int, _start_date: str | None, _end_date: str | None
    ) -> list[dict[str, str]]:
        requests.append((page_num, page_size))
        return [{"ip_address": f"192.0.2.{page_num}"}]

    collector = _prepare_collector(
        monkeypatch,
        CollectorScenario(strategies=(("전체 데이터", None, None),), collect_page=collect_page),
    )

    page_size = 2_000
    max_pages = 2
    expected_pages = page_size * max_pages // REGTECH_PAGE_SIZE

    result = collector.collect_blacklist_data(page_size=page_size, max_pages=max_pages)

    assert len(result) == expected_pages
    assert requests == [(page_num, REGTECH_PAGE_SIZE) for page_num in range(1, expected_pages + 1)]


def test_collect_blacklist_data_retries_transient_page_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[int] = []

    def collect_page(
        page_num: int,
        _page_size: int,
        _start_date: str | None,
        _end_date: str | None,
    ) -> list[dict[str, str]] | None:
        requests.append(page_num)
        if page_num == 2 and requests.count(2) == 1:
            return None
        return [{"ip_address": f"192.0.2.{page_num}"}]

    collector = _prepare_collector(
        monkeypatch,
        CollectorScenario(strategies=(("전체 데이터", None, None),), collect_page=collect_page),
    )

    result = collector.collect_blacklist_data(page_size=REGTECH_PAGE_SIZE, max_pages=2)

    assert requests == [1, 2, 2]
    assert len(result) == 2


def test_collect_blacklist_data_attempts_excel_once_before_html_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    excel_requests: list[tuple[str, str]] = []
    page_requests: list[int] = []

    def download_excel(start_date: str, end_date: str) -> list[dict[str, str]]:
        excel_requests.append((start_date, end_date))
        return []

    def collect_page(
        page_num: int,
        _page_size: int,
        _start_date: str | None,
        _end_date: str | None,
    ) -> list[dict[str, str]]:
        page_requests.append(page_num)
        return [{"ip_address": "192.0.2.1"}]

    collector = _prepare_collector(
        monkeypatch,
        CollectorScenario(
            strategies=(("사용자 지정", "2026-07-01", "2026-07-28"),),
            collect_page=collect_page,
            excel_enabled=True,
            download_excel=download_excel,
        ),
    )

    result = collector.collect_blacklist_data(
        page_size=REGTECH_PAGE_SIZE,
        start_date="2026-07-01",
        end_date="2026-07-28",
        max_pages=1,
    )

    assert excel_requests == [("2026-07-01", "2026-07-28")]
    assert page_requests == [1]
    assert len(result) == 1


def test_collect_blacklist_data_falls_back_to_html_for_stale_excel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page_requests: list[int] = []

    def download_excel(_start_date: str, _end_date: str) -> list[dict[str, str]]:
        return [{"ip_address": "192.0.2.10", "detection_date": "2000-01-01"}]

    def collect_page(
        page_num: int,
        _page_size: int,
        _start_date: str | None,
        _end_date: str | None,
    ) -> list[dict[str, str]]:
        page_requests.append(page_num)
        return [{"ip_address": "192.0.2.20"}]

    collector = _prepare_collector(
        monkeypatch,
        CollectorScenario(
            strategies=(("사용자 지정", "2026-07-01", "2026-07-28"),),
            collect_page=collect_page,
            excel_enabled=True,
            download_excel=download_excel,
        ),
    )

    result = collector.collect_blacklist_data(
        page_size=REGTECH_PAGE_SIZE,
        start_date="2026-07-01",
        end_date="2026-07-28",
        max_pages=1,
    )

    assert page_requests == [1]
    assert result == [{"ip_address": "192.0.2.20"}]


def test_collect_blacklist_data_rejects_partial_result_after_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[int] = []

    def collect_page(
        page_num: int,
        _page_size: int,
        _start_date: str | None,
        _end_date: str | None,
    ) -> list[dict[str, str]] | None:
        requests.append(page_num)
        if page_num == 1:
            return [{"ip_address": "192.0.2.1"}]
        return None

    collector = _prepare_collector(
        monkeypatch,
        CollectorScenario(strategies=(("전체 데이터", None, None),), collect_page=collect_page),
    )

    with pytest.raises(RuntimeError):
        _ = collector.collect_blacklist_data(page_size=REGTECH_PAGE_SIZE, max_pages=2)

    assert requests == [1, 2, 2, 2]


def test_collect_blacklist_data_skips_excel_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    excel_requests: list[tuple[str, str]] = []

    def download_excel(start_date: str, end_date: str) -> list[dict[str, str]]:
        excel_requests.append((start_date, end_date))
        return []

    def collect_page(
        _page_num: int,
        _page_size: int,
        _start_date: str | None,
        _end_date: str | None,
    ) -> list[dict[str, str]]:
        return [{"ip_address": "192.0.2.1"}]

    collector = _prepare_collector(
        monkeypatch,
        CollectorScenario(
            strategies=(("사용자 지정", "2026-07-01", "2026-07-28"),),
            collect_page=collect_page,
            download_excel=download_excel,
        ),
    )

    result = collector.collect_blacklist_data(
        page_size=REGTECH_PAGE_SIZE,
        start_date="2026-07-01",
        end_date="2026-07-28",
        max_pages=1,
    )

    assert excel_requests == []
    assert len(result) == 1

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from collector.core.regtech.collector import REGTECH_PAGE_SIZE, RegtechCollector


PageData = list[dict[str, str]]
DateStrategy = tuple[str, str | None, str | None]
PageCollector = Callable[[int, int, str | None, str | None], PageData | None]


@dataclass(frozen=True, slots=True)
class CollectorScenario:
    strategies: tuple[DateStrategy, ...]
    collect_page: PageCollector


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
    monkeypatch.setenv("DISABLE_EXCEL_COLLECTION", "true")

    def date_strategies(_start: str | None, _end: str | None) -> list[DateStrategy]:
        return list(scenario.strategies)

    monkeypatch.setattr(collector, "_ensure_authenticated", lambda: True)
    monkeypatch.setattr(collector, "_generate_date_strategies", date_strategies)
    monkeypatch.setattr(collector, "_collect_single_page", scenario.collect_page)
    monkeypatch.setattr(collector, "_record_collection_performance", _record_performance)
    monkeypatch.setattr(collector, "_post_process_collected_data", _post_process)
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

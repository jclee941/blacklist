import pytest

from collector.core.regtech.collector import REGTECH_PAGE_SIZE, RegtechCollector


def test_collect_blacklist_data_caps_page_size_without_reducing_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collector = RegtechCollector()
    requests: list[tuple[int, int]] = []

    monkeypatch.setenv("DISABLE_EXCEL_COLLECTION", "true")
    monkeypatch.setattr(collector, "_ensure_authenticated", lambda: True)

    def date_strategies(_start_date: str | None, _end_date: str | None) -> list[tuple[str, None, None]]:
        return [("전체 데이터", None, None)]

    monkeypatch.setattr(
        collector,
        "_generate_date_strategies",
        date_strategies,
    )

    def collect_page(page_num: int, page_size: int, _start_date: str | None, _end_date: str | None) -> list[dict[str, str]]:
        requests.append((page_num, page_size))
        return [{"ip_address": f"192.0.2.{page_num}"}]

    monkeypatch.setattr(collector, "_collect_single_page", collect_page)

    def record_performance(
        _collected_data: list[dict[str, str]],
        _strategies: list[tuple[str, str | None, str | None]],
        _duration: float,
    ) -> None:
        return None

    def post_process(data: list[dict[str, str]]) -> list[dict[str, str]]:
        return data

    monkeypatch.setattr(collector, "_record_collection_performance", record_performance)
    monkeypatch.setattr(
        collector,
        "_post_process_collected_data",
        post_process,
    )

    page_size = 2_000
    max_pages = 2
    expected_pages = page_size * max_pages // REGTECH_PAGE_SIZE

    result = collector.collect_blacklist_data(page_size=page_size, max_pages=max_pages)

    assert len(result) == expected_pages
    assert requests == [(page_num, REGTECH_PAGE_SIZE) for page_num in range(1, expected_pages + 1)]

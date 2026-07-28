import pytest

from collector.core.regtech.collector import REGTECH_PAGE_SIZE, RegtechCollector


def test_unbounded_collection_continues_past_page_fifty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collector = RegtechCollector()
    requests: list[int] = []

    monkeypatch.setenv("DISABLE_EXCEL_COLLECTION", "true")
    monkeypatch.setattr(collector, "_ensure_authenticated", lambda: True)

    def date_strategies(
        _start_date: str | None,
        _end_date: str | None,
    ) -> list[tuple[str, None, None]]:
        return [("90일", None, None)]

    def collect_page(
        page_num: int,
        _page_size: int,
        _start_date: str | None,
        _end_date: str | None,
    ) -> list[dict[str, str]]:
        requests.append(page_num)
        if page_num > 55:
            return []
        return [{"ip_address": f"8.8.8.{page_num}"}]

    def record_performance(
        _collected_data: list[dict[str, str]],
        _strategies: list[tuple[str, str | None, str | None]],
        _duration: float,
    ) -> None:
        return None

    def post_process(data: list[dict[str, str]]) -> list[dict[str, str]]:
        return data

    monkeypatch.setattr(collector, "_generate_date_strategies", date_strategies)
    monkeypatch.setattr(collector, "_collect_single_page", collect_page)
    monkeypatch.setattr(collector, "_record_collection_performance", record_performance)
    monkeypatch.setattr(collector, "_post_process_collected_data", post_process)

    result = collector.collect_blacklist_data(
        page_size=REGTECH_PAGE_SIZE,
        max_pages=None,
    )

    assert requests == list(range(1, 57))
    assert len(result) == 55

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

from core.exceptions import ValidationError


MAX_EXPORT_ROWS: Final = 10_000
FORMULA_PREFIXES: Final = ("=", "+", "-", "@")


def parse_export_limit(value: str | None) -> int:
    if value is None:
        return MAX_EXPORT_ROWS
    try:
        limit = int(value)
    except ValueError:
        raise ValidationError(message="Export limit must be an integer", field="limit") from None
    if limit < 1 or limit > MAX_EXPORT_ROWS:
        raise ValidationError(
            message=f"Export limit must be between 1 and {MAX_EXPORT_ROWS}",
            field="limit",
        )
    return limit


def neutralize_csv_cell(value: str | int | float | bool | None) -> str | int | float | bool | None:
    if isinstance(value, str) and value.lstrip().startswith(FORMULA_PREFIXES):
        return f"'{value}"
    return value


def neutralize_csv_row(values: Iterable[str | int | float | bool | None]) -> list[str | int | float | bool | None]:
    return [neutralize_csv_cell(value) for value in values]

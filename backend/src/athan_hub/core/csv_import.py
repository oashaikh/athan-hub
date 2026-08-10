import csv
import datetime as dt
import io
import re
from typing import Any

from .time_utils import ALL_PRAYERS


ALIASES = {
    "sunrise": "shurooq",
    "zuhr": "dhuhr",
    "zohar": "dhuhr",
    "fajar": "fajr",
}


def _normalise_row(row: dict[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in row.items():
        clean = (key or "").strip().lower().replace(" ", "_")
        clean = ALIASES.get(clean, clean)
        result[clean] = (value or "").strip()
    return result


def parse_csv(content: bytes) -> list[dict[str, Any]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 encoded") from exc
    rows = [_normalise_row(row) for row in csv.DictReader(io.StringIO(text))]
    output = []
    seen_dates: set[str] = set()
    for line_number, row in enumerate(rows, start=2):
        date = row.get("date")
        if not date:
            continue
        try:
            dt.date.fromisoformat(date)
        except ValueError as exc:
            raise ValueError(f"Line {line_number}: date must use YYYY-MM-DD") from exc
        if date in seen_dates:
            raise ValueError(f"Line {line_number}: duplicate date {date}")
        seen_dates.add(date)
        prayers: dict[str, str | None] = {}
        for name in ALL_PRAYERS:
            value = row.get(name) or None
            if value and not re.fullmatch(r"(?:[01]?\d|2[0-3]):[0-5]\d", value):
                raise ValueError(f"Line {line_number}: invalid {name} time {value!r}")
            if value:
                hours, minutes = value.split(":")
                value = f"{int(hours):02d}:{minutes}"
            prayers[name] = value
        if not any(prayers.values()):
            raise ValueError(f"Line {line_number}: include at least one prayer time")
        output.append({"date": date, **prayers})
        if len(output) > 4000:
            raise ValueError("CSV contains more than 4,000 timetable rows")
    if not output:
        raise ValueError("CSV must include a date column and at least one data row")
    return output

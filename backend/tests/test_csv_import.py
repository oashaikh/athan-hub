import pytest

from athan_hub.core.csv_import import parse_csv


def test_normalises_aliases_and_times() -> None:
    rows = parse_csv(b"date,fajar,sunrise,zuhr,asr,maghrib,isha\n2026-01-01,5:30,07:10,12:15,15:20,17:01,18:30\n")
    assert rows == [{
        "date": "2026-01-01",
        "fajr": "05:30",
        "shurooq": "07:10",
        "dhuhr": "12:15",
        "asr": "15:20",
        "maghrib": "17:01",
        "isha": "18:30",
    }]


@pytest.mark.parametrize("content, message", [
    (b"date,fajr\n01/02/2026,05:00\n", "YYYY-MM-DD"),
    (b"date,fajr\n2026-01-01,25:00\n", "invalid fajr"),
    (b"date,fajr\n2026-01-01,05:00\n2026-01-01,05:01\n", "duplicate date"),
    (b"date,fajr\n2026-01-01,\n", "at least one prayer"),
])
def test_rejects_invalid_rows(content: bytes, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_csv(content)

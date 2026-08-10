import datetime as dt

from dateutil import parser
from zoneinfo import ZoneInfo

from .config import get_settings


PRAYER_ORDER = ["fajr", "dhuhr", "asr", "maghrib", "isha"]
ALL_PRAYERS = ["fajr", "shurooq", "dhuhr", "asr", "maghrib", "isha"]


def configured_timezone() -> str:
    settings = get_settings()
    timezone_file = settings.data_dir / "timezone"
    if timezone_file.is_file():
        value = timezone_file.read_text(encoding="utf-8").strip()
        if value:
            try:
                ZoneInfo(value)
                return value
            except (ValueError, KeyError):
                pass
    return settings.timezone


def now_local() -> dt.datetime:
    return dt.datetime.now(ZoneInfo(configured_timezone()))


def parse_date(value: str) -> dt.date:
    return parser.parse(value, dayfirst=False).date()


def combine_date_time(date_str: str, hhmm: str | None) -> dt.datetime | None:
    if not hhmm:
        return None
    value = dt.datetime.strptime(f"{date_str} {hhmm.strip()}", "%Y-%m-%d %H:%M")
    return value.replace(tzinfo=ZoneInfo(configured_timezone()))

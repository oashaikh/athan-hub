from typing import Any
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from ..db import models
from ..core.config import get_settings


ALLOWED_SETTINGS = {
    "timezone", "grace_seconds", "echo_mac", "pre_connect_seconds",
    "connect_retry_seconds", "sink_volume_percent", "disconnect_after_play",
    "dashboard_background",
}


def all_settings(db: Session) -> dict[str, str]:
    return {row.key: row.value for row in db.query(models.Setting).all()}


def update_settings(db: Session, payload: dict[str, Any]) -> None:
    for key, value in payload.items():
        if value is None or key not in ALLOWED_SETTINGS:
            continue
        if key == "timezone":
            try:
                ZoneInfo(str(value))
            except (ZoneInfoNotFoundError, ValueError) as exc:
                raise ValueError(f"Unknown IANA timezone: {value}") from exc
            timezone_file = get_settings().data_dir / "timezone"
            timezone_file.write_text(str(value).strip() + "\n", encoding="utf-8")
        if key == "dashboard_background":
            value = Path(str(value)).name
        if isinstance(value, bool):
            value = "1" if value else "0"
        db.merge(models.Setting(key=key, value=str(value)))
    db.commit()

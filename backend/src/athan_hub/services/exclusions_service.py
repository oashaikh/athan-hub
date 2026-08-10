import datetime as dt
from typing import Any

from sqlalchemy.orm import Session

from ..db import models


def is_excluded(db: Session, date_str: str, prayer: str) -> bool:
    rows = db.query(models.Exclusion).filter(models.Exclusion.enabled == 1).all()
    date_value = dt.date.fromisoformat(date_str)
    for row in rows:
        prayer_matches = not row.prayer_name or row.prayer_name == prayer
        if row.kind == "date":
            value_matches = row.value == date_str
        elif row.kind == "weekday":
            value_matches = row.value.lower() in {date_value.strftime("%A").lower(), str(date_value.weekday())}
        elif row.kind == "date_range":
            start, separator, end = row.value.partition("..")
            value_matches = bool(separator) and start <= date_str <= end
        else:
            value_matches = False
        if prayer_matches and value_matches:
            return True
    return False


def list_exclusions(db: Session) -> list[dict[str, Any]]:
    return [{"id": row.id, "kind": row.kind, "value": row.value, "date": row.value if row.kind == "date" else None, "prayer_name": row.prayer_name, "enabled": bool(row.enabled), "created_at": row.created_at} for row in db.query(models.Exclusion).all()]

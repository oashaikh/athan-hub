import json
from typing import Any

from sqlalchemy.orm import Session

from ..core.time_utils import now_local
from ..db import models


def add_entry(db: Session, level: str, message: str, details: Any = None) -> None:
    db.add(models.AuditLog(
        ts=now_local().isoformat(),
        level=level,
        message=message,
        details_json=json.dumps(details, default=str) if details is not None else None,
    ))
    db.commit()


def list_entries(db: Session, limit: int = 100) -> list[dict[str, Any]]:
    rows = db.query(models.AuditLog).order_by(models.AuditLog.id.desc()).limit(limit).all()
    return [{"id": row.id, "ts": row.ts, "level": row.level, "message": row.message, "details": row.details_json} for row in rows]

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


class QuranResources:
    """Verified, read-only access to the packaged QUL resource snapshot."""

    def __init__(self, path: Path, manifest_path: Path) -> None:
        self.path = Path(path)
        self.manifest_path = Path(manifest_path)
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        expected = manifest["database"]["sha256"]
        actual = hashlib.sha256(self.path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("Quran resource database checksum does not match its manifest")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        return [dict(row) for row in rows]

    def list_surahs(self, query: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM surahs"
        parameters: tuple[Any, ...] = ()
        if query and query.strip():
            sql += " WHERE name_simple LIKE ? COLLATE NOCASE OR translated_name LIKE ? COLLATE NOCASE"
            pattern = f"%{query.strip()}%"
            parameters = (pattern, pattern)
        sql += " ORDER BY id"
        with self._connect() as connection:
            return self._dicts(connection.execute(sql, parameters).fetchall())

    def verses(self, surah_id: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM ayahs WHERE surah_id = ? ORDER BY ayah_number", (surah_id,)
            ).fetchall()
        return self._dicts(rows)

    def list_recitations(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM recitations ORDER BY name COLLATE NOCASE, id").fetchall()
        return self._dicts(rows)

    def recitation(self, recitation_id: int) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM recitations WHERE id = ?", (recitation_id,)).fetchone()
        return dict(row) if row else None

    def audio_object(self, recitation_id: int, content_key: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM audio_objects WHERE recitation_id = ? AND content_key = ?",
                (recitation_id, content_key),
            ).fetchone()
        return dict(row) if row else None

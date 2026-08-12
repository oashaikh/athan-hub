#!/usr/bin/env python3
"""Build Athan Hub's deterministic, read-only Quran snapshot from QUL."""

from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sqlite3
import tempfile
from typing import Any
import urllib.request


BASE_URL = "https://qul.tarteel.ai"
QUL_COMMIT = "334206a60f8d99af13bab483a2e9c29cdec49d08"
CHAPTERS_URL = f"{BASE_URL}/api/v1/chapters"
VERSES_URL = (
    f"{BASE_URL}/api/v1/chapters/{{surah_id}}/verses"
    "?fields=text_qpc_hafs&translations=20&per_page=286"
)
TRANSLITERATION_URL = (
    "https://static-cdn.tarteel.ai/qul/data/transliterations/en.transliteration.json"
)
RECITATION_RESOURCE_URL = f"{BASE_URL}/api/v1/resources/recitations"
AYAH_RECITATIONS_URL = f"{BASE_URL}/api/v1/audio/ayah_recitations"
SURAH_RECITATIONS_URL = f"{BASE_URL}/api/v1/audio/surah_recitations"
USER_AGENT = "Athan-Hub-QUL-Importer/1.0 (+https://github.com/oashaikh/athan-hub)"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(html.unescape(value or ""))
    return re.sub(r"\s+", " ", "".join(parser.parts)).strip()


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        if response.geturl().split(":", 1)[0] != "https":
            raise ValueError(f"Refusing non-HTTPS resource: {response.geturl()}")
        return response.read()


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def fetch_json(url: str, source_hashes: dict[str, str]) -> Any:
    payload = download(url)
    source_hashes[url] = sha256(payload)
    return json.loads(payload)


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def display_name(row: dict[str, Any]) -> str:
    translated = row.get("translated_name") or {}
    return (row.get("name") or translated.get("name") or f"QUL recitation {row['id']}").strip()


def recommendation(name: str) -> str | None:
    lowered = name.casefold()
    if any(word in lowered for word in ("child", "children", "kids", "with kids")):
        return "kids_repeat"
    if any(word in lowered for word in ("muallim", "teacher", "repeat")):
        return "muallim"
    return None


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode=DELETE;
        PRAGMA foreign_keys=ON;
        CREATE TABLE surahs (
            id INTEGER PRIMARY KEY,
            name_simple TEXT NOT NULL,
            name_arabic TEXT NOT NULL,
            translated_name TEXT NOT NULL,
            ayah_count INTEGER NOT NULL CHECK (ayah_count > 0)
        );
        CREATE TABLE ayahs (
            verse_key TEXT PRIMARY KEY,
            surah_id INTEGER NOT NULL REFERENCES surahs(id),
            ayah_number INTEGER NOT NULL,
            arabic TEXT NOT NULL,
            translation TEXT NOT NULL,
            transliteration TEXT NOT NULL,
            UNIQUE (surah_id, ayah_number)
        );
        CREATE INDEX idx_ayahs_surah ON ayahs(surah_id, ayah_number);
        CREATE TABLE recitations (
            id INTEGER PRIMARY KEY,
            source_kind TEXT NOT NULL CHECK (source_kind IN ('ayah', 'surah')),
            source_id INTEGER NOT NULL,
            resource_id INTEGER,
            name TEXT NOT NULL,
            style TEXT,
            qirat TEXT,
            capability TEXT NOT NULL CHECK (capability IN ('ayah', 'segmented_surah', 'surah')),
            relative_path TEXT,
            recommended TEXT,
            detail_url TEXT NOT NULL,
            UNIQUE (source_kind, source_id)
        );
        """
    )


def insert_recitations(
    connection: sqlite3.Connection,
    rows: list[dict[str, Any]],
    resource_rows: list[dict[str, Any]],
    source_kind: str,
) -> None:
    resource_by_name: dict[str, int] = {}
    for resource in resource_rows:
        name = display_name(resource)
        if name:
            resource_by_name.setdefault(normalize_name(name), int(resource["id"]))

    for row in rows:
        name = display_name(row)
        source_id = int(row["id"])
        stable_id = (100_000 if source_kind == "ayah" else 200_000) + source_id
        if source_kind == "ayah":
            capability = "ayah"
            path = f"{AYAH_RECITATIONS_URL}/{source_id}"
        else:
            capability = "segmented_surah" if row.get("has_segments") else "surah"
            path = f"{SURAH_RECITATIONS_URL}/{source_id}"
        connection.execute(
            """
            INSERT INTO recitations (
                id, source_kind, source_id, resource_id, name, style, qirat,
                capability, relative_path, recommended, detail_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stable_id,
                source_kind,
                source_id,
                resource_by_name.get(normalize_name(name)),
                name,
                row.get("style"),
                row.get("qirat"),
                capability,
                row.get("relative_path") or "",
                recommendation(name),
                path,
            ),
        )


def build_database(output: Path) -> dict[str, Any]:
    source_hashes: dict[str, str] = {}
    chapters = fetch_json(CHAPTERS_URL, source_hashes)["chapters"]
    transliteration_rows = fetch_json(TRANSLITERATION_URL, source_hashes)
    transliterations = {
        f"{int(row['sura'])}:{int(row['aya'])}": plain_text(row["text"])
        for row in transliteration_rows
    }
    resource_rows = fetch_json(RECITATION_RESOURCE_URL, source_hashes)["recitations"]
    ayah_recitations = fetch_json(AYAH_RECITATIONS_URL, source_hashes)["recitations"]
    surah_recitations = fetch_json(SURAH_RECITATIONS_URL, source_hashes)["recitations"]

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".sqlite", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        connection = sqlite3.connect(temporary_path)
        create_schema(connection)
        for chapter in sorted(chapters, key=lambda item: int(item["id"])):
            connection.execute(
                "INSERT INTO surahs VALUES (?, ?, ?, ?, ?)",
                (
                    int(chapter["id"]),
                    chapter["name_simple"],
                    chapter["name_arabic"],
                    chapter["translated_name"]["name"],
                    int(chapter["verses_count"]),
                ),
            )

            url = VERSES_URL.format(surah_id=chapter["id"])
            verses = fetch_json(url, source_hashes)["verses"]
            if len(verses) != int(chapter["verses_count"]):
                raise ValueError(f"QUL returned an incomplete surah {chapter['id']}")
            for verse in verses:
                translations = verse.get("translations") or []
                key = verse["verse_key"]
                connection.execute(
                    "INSERT INTO ayahs VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        key,
                        int(chapter["id"]),
                        int(key.split(":", 1)[1]),
                        verse["text_qpc_hafs"].strip(),
                        plain_text(translations[0]["text"]) if translations else "",
                        transliterations.get(key, ""),
                    ),
                )

        insert_recitations(connection, ayah_recitations, resource_rows, "ayah")
        insert_recitations(connection, surah_recitations, resource_rows, "surah")
        counts = {
            "surahs": connection.execute("SELECT COUNT(*) FROM surahs").fetchone()[0],
            "ayahs": connection.execute("SELECT COUNT(*) FROM ayahs").fetchone()[0],
            "recitations": connection.execute("SELECT COUNT(*) FROM recitations").fetchone()[0],
        }
        missing = connection.execute(
            """SELECT COUNT(*) FROM ayahs
               WHERE arabic = '' OR translation = '' OR transliteration = ''"""
        ).fetchone()[0]
        if counts["surahs"] != 114 or counts["ayahs"] != 6236 or missing:
            raise ValueError(f"QUL snapshot failed completeness checks: {counts}, missing={missing}")
        capabilities = {
            row[0] for row in connection.execute("SELECT DISTINCT capability FROM recitations")
        }
        if capabilities != {"ayah", "segmented_surah", "surah"}:
            raise ValueError(f"QUL recitation capability set is incomplete: {capabilities}")
        connection.commit()
        connection.execute("VACUUM")
        connection.close()
        temporary_path.replace(output)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise

    return {"source_hashes": source_hashes, "counts": counts}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("resources/quran/quran.sqlite"))
    parser.add_argument("--manifest", type=Path, default=Path("resources/quran/manifest.json"))
    args = parser.parse_args()

    result = build_database(args.output)
    manifest = {
        "schema_version": 1,
        "qul_commit": QUL_COMMIT,
        "qul_repository": "https://github.com/TarteelAI/quranic-universal-library",
        "database": {
            "filename": args.output.name,
            "sha256": sha256(args.output.read_bytes()),
            **result["counts"],
        },
        "datasets": [
            {
                "name": "QUL QPC Hafs ayah script (resource 86), Quran structure, and Saheeh International (resource 20)",
                "urls": [CHAPTERS_URL, VERSES_URL],
                "sha256_by_url": {
                    key: value
                    for key, value in sorted(result["source_hashes"].items())
                    if "/chapters" in key
                },
                "notice": "See NOTICE.md",
            },
            {
                "name": "QUL English ayah transliteration (resource 72)",
                "urls": [TRANSLITERATION_URL],
                "sha256_by_url": {
                    TRANSLITERATION_URL: result["source_hashes"][TRANSLITERATION_URL]
                },
                "notice": "See NOTICE.md",
            },
            {
                "name": "QUL recitation catalogue",
                "urls": [RECITATION_RESOURCE_URL, AYAH_RECITATIONS_URL, SURAH_RECITATIONS_URL],
                "sha256_by_url": {
                    key: result["source_hashes"][key]
                    for key in (RECITATION_RESOURCE_URL, AYAH_RECITATIONS_URL, SURAH_RECITATIONS_URL)
                },
                "notice": "Audio remains hosted by its respective providers and is cached on demand.",
            },
        ],
        "audio_hosts": [
            "audio.qurancdn.com",
            "audio-cdn.tarteel.ai",
            "download.quranicaudio.com",
            "everyayah.com",
            "versebyversequran.com",
        ],
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

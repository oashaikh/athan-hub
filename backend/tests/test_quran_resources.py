import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from athan_hub.core.quran_resources import QuranResources


@pytest.fixture()
def resource_files(tmp_path):
    database = tmp_path / "quran.sqlite"
    connection = sqlite3.connect(database)
    connection.executescript(
        """
        CREATE TABLE surahs (
            id INTEGER PRIMARY KEY,
            name_simple TEXT NOT NULL,
            name_arabic TEXT NOT NULL,
            translated_name TEXT NOT NULL,
            ayah_count INTEGER NOT NULL
        );
        CREATE TABLE ayahs (
            verse_key TEXT PRIMARY KEY,
            surah_id INTEGER NOT NULL,
            ayah_number INTEGER NOT NULL,
            arabic TEXT NOT NULL,
            translation TEXT NOT NULL,
            transliteration TEXT NOT NULL
        );
        CREATE TABLE recitations (
            id INTEGER PRIMARY KEY,
            source_kind TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            resource_id INTEGER,
            name TEXT NOT NULL,
            style TEXT,
            qirat TEXT,
            capability TEXT NOT NULL,
            relative_path TEXT,
            recommended TEXT,
            detail_url TEXT NOT NULL
        );
        CREATE TABLE audio_objects (
            recitation_id INTEGER NOT NULL,
            content_key TEXT NOT NULL,
            audio_url TEXT NOT NULL,
            duration REAL,
            byte_count INTEGER,
            PRIMARY KEY (recitation_id, content_key)
        );
        """
    )
    for surah_id in range(1, 115):
        ayah_count = 7 if surah_id == 1 else (6236 - 7 if surah_id == 2 else 0)
        connection.execute(
            "INSERT INTO surahs VALUES (?, ?, ?, ?, ?)",
            (surah_id, f"Surah {surah_id}", f"سورة {surah_id}", f"Chapter {surah_id}", ayah_count),
        )
    connection.execute(
        "INSERT INTO ayahs VALUES (?, ?, ?, ?, ?, ?)",
        ("1:1", 1, 1, "بِسْمِ اللَّهِ", "In the name of Allah", "Bismi Allahi"),
    )
    capabilities = ("ayah", "segmented_surah", "surah")
    for index, capability in enumerate(capabilities, start=1):
        connection.execute(
            "INSERT INTO recitations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                index,
                "ayah" if capability == "ayah" else "surah",
                index,
                index,
                f"Reciter {index}",
                "Murattal",
                "Hafs",
                capability,
                "",
                None,
                f"https://qul.tarteel.ai/api/v1/audio/recitations/{index}",
            ),
        )
    connection.commit()
    connection.execute(
        "INSERT INTO audio_objects VALUES (?, ?, ?, ?, ?)",
        (1, "1:1", "https://audio.qurancdn.com/test.mp3", 4.0, 1000),
    )
    connection.commit()
    connection.close()

    digest = hashlib.sha256(database.read_bytes()).hexdigest()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"database": {"filename": database.name, "sha256": digest}}),
        encoding="utf-8",
    )
    return database, manifest


def test_resources_return_complete_quran(resource_files):
    database, manifest = resource_files
    resources = QuranResources(database, manifest)

    surahs = resources.list_surahs()
    assert len(surahs) == 114
    assert sum(row["ayah_count"] for row in surahs) == 6236
    assert resources.verses(1)[0]["verse_key"] == "1:1"
    assert resources.list_surahs("surah 11")[0]["id"] == 11


def test_recitation_catalogue_has_truthful_capabilities(resource_files):
    database, manifest = resource_files
    resources = QuranResources(database, manifest)

    rows = resources.list_recitations()
    assert {"ayah", "segmented_surah", "surah"} <= {row["capability"] for row in rows}
    assert resources.recitation(2)["capability"] == "segmented_surah"
    assert resources.recitation(999) is None


def test_manifest_hash_must_match_database(resource_files):
    database, manifest = resource_files
    database.write_bytes(database.read_bytes() + b"tampered")

    with pytest.raises(ValueError, match="checksum"):
        QuranResources(database, manifest)


def test_audio_source_url_is_pinned_in_snapshot(resource_files):
    database, manifest = resource_files
    resources = QuranResources(database, manifest)
    row = resources.audio_object(1, "1:1")
    assert row["audio_url"] == "https://audio.qurancdn.com/test.mp3"
    assert resources.audio_object(1, "2:1") is None


def test_packaged_snapshot_is_complete_and_verified():
    repository = Path(__file__).resolve().parents[2]
    resources = QuranResources(
        repository / "resources/quran/quran.sqlite",
        repository / "resources/quran/manifest.json",
    )
    surahs = resources.list_surahs()
    assert len(surahs) == 114
    assert sum(row["ayah_count"] for row in surahs) == 6236
    assert len(resources.list_recitations()) == 139
    assert resources.audio_object(100016, "1:1")["audio_url"].startswith("https://")

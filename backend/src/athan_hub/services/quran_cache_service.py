from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlencode, urlparse
import urllib.request

from filelock import FileLock
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..core.time_utils import now_local
from ..db import models
from . import quran_service


class CacheSourceError(ValueError):
    pass


class CacheQuotaError(RuntimeError):
    pass


_STREAMING_PATHS: set[Path] = set()


def mark_streaming(path: Path) -> None:
    _STREAMING_PATHS.add(Path(path))


def release_streaming(path: Path) -> None:
    _STREAMING_PATHS.discard(Path(path))


class QuranCacheService:
    def __init__(
        self,
        cache_dir: Path,
        allowed_hosts: set[str],
        cache_limit_bytes: int,
        opener=None,
        max_object_bytes: int = 256 * 1024 * 1024,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.allowed_hosts = {host.casefold() for host in allowed_hosts}
        self.cache_limit_bytes = cache_limit_bytes
        self.max_object_bytes = min(max_object_bytes, cache_limit_bytes)
        self.opener = opener or urllib.request.build_opener()

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.hostname.casefold() not in self.allowed_hosts:
            raise CacheSourceError("Audio source is outside the HTTPS host allowlist")

    @staticmethod
    def _looks_like_audio(payload: bytes) -> bool:
        return (
            payload.startswith(b"ID3")
            or (len(payload) >= 2 and payload[0] == 0xFF and payload[1] & 0xE0 == 0xE0)
            or (len(payload) >= 12 and payload[:4] == b"RIFF" and payload[8:12] == b"WAVE")
            or payload.startswith(b"OggS")
        )

    def _current_size(self, db: Session) -> int:
        return int(db.query(func.coalesce(func.sum(models.QuranAudioCache.byte_count), 0)).scalar() or 0)

    def evict_to_limit(self, db: Session, required_bytes: int = 0) -> int:
        size = self._current_size(db)
        target = self.cache_limit_bytes - required_bytes
        removed = 0
        for row in (
            db.query(models.QuranAudioCache)
            .filter_by(pinned=0)
            .order_by(models.QuranAudioCache.last_accessed_at, models.QuranAudioCache.id)
        ):
            if size <= target:
                break
            path = Path(row.local_path)
            if path in _STREAMING_PATHS:
                continue
            if path.exists():
                path.unlink()
            size -= row.byte_count
            removed += row.byte_count
            db.delete(row)
        db.commit()
        if size > target:
            raise CacheQuotaError("Pinned Quran audio prevents cache eviction")
        return removed

    def cache_url(self, db: Session, recitation_id: int, content_key: str, url: str) -> Path:
        existing = db.query(models.QuranAudioCache).filter_by(
            recitation_id=recitation_id, content_key=content_key
        ).one_or_none()
        if existing and Path(existing.local_path).is_file():
            existing.last_accessed_at = now_local().isoformat()
            db.commit()
            return Path(existing.local_path)

        self._validate_url(url)
        safe_key = content_key.replace(":", "-")
        target = self.cache_dir / f"{recitation_id}-{safe_key}.mp3"
        lock = FileLock(str(target) + ".lock", timeout=180)
        with lock:
            existing = db.query(models.QuranAudioCache).filter_by(
                recitation_id=recitation_id, content_key=content_key
            ).one_or_none()
            if existing and Path(existing.local_path).is_file():
                return Path(existing.local_path)

            request = urllib.request.Request(url, headers={"User-Agent": "Athan-Hub-Quran-Audio/1.0"})
            with self.opener.open(request, timeout=120) as response:
                self._validate_url(response.geturl())
                content_type = (response.headers.get("Content-Type") or "").split(";", 1)[0].strip().casefold()
                if content_type and not (content_type.startswith("audio/") or content_type in {"application/octet-stream", "binary/octet-stream"}):
                    raise CacheSourceError("Downloaded object has an invalid audio content type")
                declared = int(response.headers.get("Content-Length") or 0)
                if declared > self.max_object_bytes:
                    raise CacheQuotaError("Quran audio object exceeds the size limit")
                payload = response.read(self.max_object_bytes + 1)
            if len(payload) > self.max_object_bytes:
                raise CacheQuotaError("Quran audio object exceeds the size limit")
            if not self._looks_like_audio(payload):
                raise CacheSourceError("Downloaded object has an invalid audio signature")

            self.evict_to_limit(db, required_bytes=len(payload))
            with tempfile.NamedTemporaryFile(dir=self.cache_dir, delete=False) as temporary:
                temporary.write(payload)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            try:
                os.replace(temporary_path, target)
            finally:
                temporary_path.unlink(missing_ok=True)

            now = now_local().isoformat()
            if existing is None:
                existing = models.QuranAudioCache(recitation_id=recitation_id, content_key=content_key)
                db.add(existing)
            existing.local_path = str(target)
            existing.source_url = url
            existing.byte_count = len(payload)
            existing.sha256 = hashlib.sha256(payload).hexdigest()
            existing.created_at = existing.created_at or now
            existing.last_accessed_at = now
            db.commit()
            return target

    def cache_summary(self, db: Session) -> dict:
        rows = db.query(models.QuranAudioCache).order_by(
            models.QuranAudioCache.last_accessed_at.desc(), models.QuranAudioCache.id.desc()
        ).all()
        recitations = {row["id"]: row["name"] for row in quran_service.resources().list_recitations()}
        grouped: dict[int, dict] = {}
        for row in rows:
            entry = grouped.setdefault(row.recitation_id, {
                "recitation_id": row.recitation_id,
                "name": recitations.get(row.recitation_id, f"Recitation {row.recitation_id}"),
                "byte_count": 0,
                "object_count": 0,
                "pinned_count": 0,
            })
            entry["byte_count"] += row.byte_count
            entry["object_count"] += 1
            entry["pinned_count"] += int(bool(row.pinned))
        return {
            "byte_count": sum(row.byte_count for row in rows),
            "limit_bytes": self.cache_limit_bytes,
            "object_count": len(rows),
            "pinned_count": sum(1 for row in rows if row.pinned),
            "by_reciter": sorted(grouped.values(), key=lambda item: item["name"].casefold()),
            "items": [
                {
                    "id": row.id,
                    "recitation_id": row.recitation_id,
                    "content_key": row.content_key,
                    "byte_count": row.byte_count,
                    "pinned": bool(row.pinned),
                    "last_accessed_at": row.last_accessed_at,
                }
                for row in rows
            ],
        }

    @staticmethod
    def set_pinned(db: Session, cache_id: int, pinned: bool) -> bool:
        row = db.get(models.QuranAudioCache, cache_id)
        if row is None:
            return False
        row.pinned = int(pinned)
        db.commit()
        return True


def default_cache_service(db: Session) -> QuranCacheService:
    settings = get_settings()
    values = {row.key: row.value for row in db.query(models.Setting)}
    manifest = json.loads(settings.quran_manifest_path.read_text(encoding="utf-8"))
    return QuranCacheService(
        settings.quran_cache_dir,
        set(manifest["audio_hosts"]),
        int(values.get("quran_cache_limit_bytes", 5 * 1024 * 1024 * 1024)),
    )


def audio_source(recitation: dict, verse_key: str | None, surah_id: int) -> tuple[str, str]:
    if recitation["source_kind"] == "ayah":
        if not verse_key:
            raise CacheSourceError("Ayah recitations require a verse key")
        content_key = verse_key
    else:
        content_key = str(surah_id)
    row = quran_service.resources().audio_object(recitation["id"], content_key)
    if not row:
        raise CacheSourceError("Selected recitation has no audio for this selection")
    return content_key, row["audio_url"]


def segment_manifest(
    recitation: dict,
    surah_id: int,
    start_ayah: int,
    end_ayah: int,
    cache_dir: Path | None = None,
) -> dict:
    if recitation["source_kind"] != "surah":
        raise CacheSourceError("Selected recitation does not provide verse timing")
    cache_path = None
    if cache_dir is not None:
        segment_dir = Path(cache_dir) / "segments"
        segment_dir.mkdir(parents=True, exist_ok=True)
        cache_path = segment_dir / f"{recitation['id']}-{surah_id}.json"
        if cache_path.is_file():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                if isinstance(cached.get("segments"), dict):
                    return cached
            except (OSError, ValueError, AttributeError):
                cache_path.unlink(missing_ok=True)
    query = urlencode({"surah": surah_id, "from": start_ayah, "to": end_ayah, "per_page": 286})
    url = f"https://qul.tarteel.ai/api/v1/audio/surah_segments/{recitation['source_id']}?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "Athan-Hub-Quran-Catalogue/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.load(response)
    if not isinstance(result.get("segments"), dict):
        raise CacheSourceError("QUL returned invalid verse timing data")
    if cache_path is not None:
        with tempfile.NamedTemporaryFile("w", dir=cache_path.parent, encoding="utf-8", delete=False) as temporary:
            json.dump(result, temporary, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        try:
            os.replace(temporary_path, cache_path)
        finally:
            temporary_path.unlink(missing_ok=True)
    return result


def resolve_audio(db: Session, recitation_id: int, verse_key: str | None, surah_id: int) -> Path:
    recitation = quran_service.resources().recitation(recitation_id)
    if recitation is None:
        raise CacheSourceError("Unknown QUL recitation")
    content_key, url = audio_source(recitation, verse_key, surah_id)
    return default_cache_service(db).cache_url(db, recitation_id, content_key, url)

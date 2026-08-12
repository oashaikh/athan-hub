import io
import uuid

import pytest
from sqlalchemy import delete

from athan_hub.db import models
from athan_hub.db.migrations import init_db
from athan_hub.db.session import SessionLocal
from athan_hub.services.quran_cache_service import CacheSourceError, QuranCacheService


class FakeResponse:
    def __init__(self, url: str, payload: bytes):
        self._url = url
        self._stream = io.BytesIO(payload)
        self.headers = {"Content-Type": "audio/mpeg", "Content-Length": str(len(payload))}

    def geturl(self):
        return self._url

    def read(self, size=-1):
        return self._stream.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeOpener:
    def __init__(self, response):
        self.response = response
        self.request_count = 0

    def open(self, request, timeout=0):
        del request, timeout
        self.request_count += 1
        return self.response


def test_uncached_audio_downloads_once(tmp_path):
    init_db()
    payload = b"ID3" + b"\x00" * 100
    opener = FakeOpener(FakeResponse("https://allowed.test/001001.mp3", payload))
    service = QuranCacheService(
        cache_dir=tmp_path,
        allowed_hosts={"allowed.test"},
        cache_limit_bytes=1024 * 1024,
        opener=opener,
    )
    with SessionLocal() as db:
        recitation_id = 900_000 + int(uuid.uuid4().hex[:5], 16)
        first = service.cache_url(db, recitation_id, "1:1", "https://allowed.test/001001.mp3")
        second = service.cache_url(db, recitation_id, "1:1", "https://allowed.test/001001.mp3")
        assert first == second
        assert first.read_bytes() == payload
        assert opener.request_count == 1


def test_redirect_to_unlisted_host_is_rejected(tmp_path):
    opener = FakeOpener(FakeResponse("https://evil.test/audio.mp3", b"ID3bad"))
    service = QuranCacheService(
        cache_dir=tmp_path,
        allowed_hosts={"allowed.test"},
        cache_limit_bytes=1024,
        opener=opener,
    )
    with SessionLocal() as db, pytest.raises(CacheSourceError, match="allowlist"):
        service.cache_url(db, 999_991, "1:1", "https://allowed.test/redirect")


def test_invalid_audio_cannot_replace_cache(tmp_path):
    opener = FakeOpener(FakeResponse("https://allowed.test/not-audio", b"plain text"))
    service = QuranCacheService(
        cache_dir=tmp_path,
        allowed_hosts={"allowed.test"},
        cache_limit_bytes=1024,
        opener=opener,
    )
    with SessionLocal() as db, pytest.raises(CacheSourceError, match="signature"):
        service.cache_url(db, 999_992, "1:1", "https://allowed.test/not-audio")
    assert not list(tmp_path.glob("*.mp3"))


def test_lru_eviction_preserves_pinned_objects(tmp_path):
    init_db()
    with SessionLocal() as db:
        db.execute(delete(models.QuranAudioCache))
        db.commit()
        pinned = tmp_path / "pinned.mp3"
        old = tmp_path / "old.mp3"
        pinned.write_bytes(b"ID3" + b"p" * 20)
        old.write_bytes(b"ID3" + b"o" * 20)
        old_size = old.stat().st_size
        db.add_all(
            [
                models.QuranAudioCache(
                    recitation_id=999_993,
                    content_key="1:1",
                    local_path=str(pinned),
                    source_url="https://allowed.test/pinned.mp3",
                    byte_count=pinned.stat().st_size,
                    sha256="x",
                    pinned=1,
                    created_at="2026-01-01T00:00:00+00:00",
                    last_accessed_at="2026-01-01T00:00:00+00:00",
                ),
                models.QuranAudioCache(
                    recitation_id=999_993,
                    content_key="1:2",
                    local_path=str(old),
                    source_url="https://allowed.test/old.mp3",
                    byte_count=old.stat().st_size,
                    sha256="y",
                    pinned=0,
                    created_at="2026-01-02T00:00:00+00:00",
                    last_accessed_at="2026-01-02T00:00:00+00:00",
                ),
            ]
        )
        db.commit()
        service = QuranCacheService(tmp_path, {"allowed.test"}, cache_limit_bytes=30)
        assert service.evict_to_limit(db) == old_size
        assert pinned.exists()
        assert not old.exists()

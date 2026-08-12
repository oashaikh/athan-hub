import os
import shutil
import tempfile
from pathlib import Path


TEST_ROOT = Path(tempfile.mkdtemp(prefix="athan-hub-tests-"))
os.environ.update({
    "ATHAN_DATA_DIR": str(TEST_ROOT / "data"),
    "ATHAN_LOG_DIR": str(TEST_ROOT / "logs"),
    "ATHAN_UPLOAD_DIR": str(TEST_ROOT / "uploads"),
    "ATHAN_AUDIO_DIR": str(TEST_ROOT / "audio"),
    "ATHAN_BACKGROUND_DIR": str(TEST_ROOT / "backgrounds"),
    "ATHAN_QURAN_CACHE_DIR": str(TEST_ROOT / "quran-cache"),
    "ATHAN_PLAYBACK_STATE_PATH": str(TEST_ROOT / "run" / "athan-active.json"),
    "ATHAN_DB_PATH": str(TEST_ROOT / "data" / "athan.db"),
    "ATHAN_TIMEZONE": "Europe/London",
    "ATHAN_PIN": "",
    "ATHAN_TIMETABLE_UPLOAD_LIMIT": "1048576",
    "ATHAN_AUDIO_UPLOAD_LIMIT": "1024",
    "ATHAN_BACKGROUND_UPLOAD_LIMIT": "1024",
})


def pytest_sessionfinish(session, exitstatus) -> None:
    del session, exitstatus
    shutil.rmtree(TEST_ROOT, ignore_errors=True)

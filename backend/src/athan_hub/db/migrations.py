from . import models
from .session import Base, SessionLocal, engine
from ..core.config import get_settings
from ..core.audio_metadata import mp3_duration
from pathlib import Path


DEFAULT_SETTINGS = {
    "pre_connect_seconds": "10",
    "connect_retry_seconds": "20",
    "grace_seconds": "120",
    "disconnect_after_play": "0",
    "echo_mac": "",
    "sink_volume_percent": "100",
    "dashboard_background": "bg.png",
    "quran_cache_limit_bytes": str(5 * 1024 * 1024 * 1024),
    "leaderboard_enabled": "0",
    "leaderboard_repetitions": "1",
    "leaderboard_daily_practice": "1",
    "leaderboard_memorised": "1",
    "leaderboard_surahs": "1",
}


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(audio_profiles)")}
        if "duration_seconds" not in columns:
            connection.exec_driver_sql("ALTER TABLE audio_profiles ADD COLUMN duration_seconds FLOAT")
    app_settings = get_settings()
    defaults = {"timezone": app_settings.timezone, **DEFAULT_SETTINGS}
    with SessionLocal() as db:
        for key, value in defaults.items():
            if db.get(models.Setting, key) is None:
                db.add(models.Setting(key=key, value=value))
        for profile in db.query(models.AudioProfile).filter(models.AudioProfile.duration_seconds.is_(None)):
            try:
                profile.duration_seconds = mp3_duration(Path(profile.file_path))
            except ValueError:
                profile.enabled = 0
        db.commit()
    timezone_file = app_settings.data_dir / "timezone"
    if not timezone_file.exists():
        timezone_file.write_text(app_settings.timezone + "\n", encoding="utf-8")

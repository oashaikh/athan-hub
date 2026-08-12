import os
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[4]


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ATHAN_", case_sensitive=False)

    data_dir: Path = Path(os.environ.get("ATHAN_DATA_DIR", "/var/lib/athan-hub"))
    log_dir: Path = Path(os.environ.get("ATHAN_LOG_DIR", "/var/log/athan-hub"))
    upload_dir: Path = Path(os.environ.get("ATHAN_UPLOAD_DIR", "/var/lib/athan-hub/uploads"))
    audio_dir: Path = Path(os.environ.get("ATHAN_AUDIO_DIR", "/var/lib/athan-hub/audio"))
    background_dir: Path = Path(os.environ.get("ATHAN_BACKGROUND_DIR", "/var/lib/athan-hub/backgrounds"))
    quran_cache_dir: Path = Path(os.environ.get("ATHAN_QURAN_CACHE_DIR", "/var/lib/athan-hub/quran-cache"))
    quran_resource_db: Path = Path(os.environ.get("ATHAN_QURAN_RESOURCE_DB", str(PROJECT_ROOT / "resources/quran/quran.sqlite")))
    quran_manifest_path: Path = Path(os.environ.get("ATHAN_QURAN_MANIFEST_PATH", str(PROJECT_ROOT / "resources/quran/manifest.json")))
    db_path: Path = Path(os.environ.get("ATHAN_DB_PATH", "/var/lib/athan-hub/athan.db"))
    timezone: str = os.environ.get("ATHAN_TIMEZONE", "Europe/London")
    api_host: str = os.environ.get("ATHAN_API_HOST", "127.0.0.1")
    api_port: int = int(os.environ.get("ATHAN_API_PORT", "9000"))
    log_to_file: bool = os.environ.get("ATHAN_LOG_TO_FILE", "0") == "1"
    log_level: str = os.environ.get("ATHAN_LOG_LEVEL", "INFO")
    pin: str = os.environ.get("ATHAN_PIN", "")
    pin_secret: str = Field(default_factory=lambda: secrets.token_hex(32))
    timetable_upload_limit: int = int(os.environ.get("ATHAN_TIMETABLE_UPLOAD_LIMIT", str(5 * 1024 * 1024)))
    audio_upload_limit: int = int(os.environ.get("ATHAN_AUDIO_UPLOAD_LIMIT", str(100 * 1024 * 1024)))
    background_upload_limit: int = int(os.environ.get("ATHAN_BACKGROUND_UPLOAD_LIMIT", str(20 * 1024 * 1024)))

    def ensure_directories(self) -> None:
        for path in [self.data_dir, self.log_dir, self.upload_dir, self.audio_dir, self.background_dir, self.quran_cache_dir, self.db_path.parent]:
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    settings = AppSettings()
    settings.ensure_directories()
    return settings

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    grace_seconds: int | None = Field(default=None, ge=0, le=3600)
    echo_mac: str | None = Field(default=None, pattern=r"^$|^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
    pre_connect_seconds: int | None = Field(default=None, ge=0, le=120)
    connect_retry_seconds: int | None = Field(default=None, ge=1, le=300)
    sink_volume_percent: int | None = Field(default=None, ge=0, le=150)
    disconnect_after_play: bool | None = None
    dashboard_background: str | None = Field(default=None, max_length=255)


class ManualUpdate(BaseModel):
    prayers: dict[str, dict[str, Any]]


class TestPlayRequest(BaseModel):
    prayer_name: str = "fajr"


class PinRequest(BaseModel):
    pin: str = Field(min_length=1, max_length=128)


class BluetoothPairRequest(BaseModel):
    mac: str = Field(pattern=r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


Theme = Literal["night_explorer", "garden_light", "classic_mushaf"]
LearningState = Literal["learning", "needs_practice", "memorised"]


class PracticeStateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recitation_id: int | None = Field(default=None, ge=1)
    surah_id: int = Field(ge=1, le=114)
    start_ayah: int = Field(ge=1)
    end_ayah: int = Field(ge=1)
    repetitions: Literal[1, 3, 5, 10] = 3
    playback_speed: float = Field(default=1.0, ge=0.75, le=1.25)
    show_arabic: bool = True
    show_translation: bool = True
    show_transliteration: bool = False
    recall_mode: bool = False


class ProgressUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: LearningState
    completed_repetitions: int = Field(default=0, ge=0, le=10000)


class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    surah_id: int = Field(ge=1, le=114)
    start_ayah: int = Field(ge=1)
    end_ayah: int = Field(ge=1)
    recitation_id: int | None = Field(default=None, ge=1)


class SessionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    repetitions: int = Field(default=0, ge=0, le=10000)
    practice_seconds: int = Field(default=0, ge=0, le=86400)
    completed: bool = False


class AdminProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)
    gender: Literal["boy", "girl"] | None = None
    theme: Theme | None = None


class AdminProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=80)
    gender: Literal["boy", "girl"] | None = None
    theme: Theme | None = None


class LeaderboardSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool
    repetitions: bool = True
    daily_practice: bool = True
    memorised: bool = True
    surahs: bool = True


class QuranCacheUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pinned: bool


class QuranPrefetchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recitation_id: int = Field(ge=1)
    surah_id: int | None = Field(default=None, ge=1, le=114)


class QuranSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quran_cache_limit_bytes: int = Field(ge=64 * 1024 * 1024, le=1024 * 1024 * 1024 * 1024)

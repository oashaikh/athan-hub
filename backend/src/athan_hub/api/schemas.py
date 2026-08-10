from typing import Any

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

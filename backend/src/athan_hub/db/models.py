from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .session import Base


class PrayerTime(Base):
    __tablename__ = "prayer_times"
    date: Mapped[str] = mapped_column(String, primary_key=True)
    fajr: Mapped[str | None] = mapped_column(String, nullable=True)
    shurooq: Mapped[str | None] = mapped_column(String, nullable=True)
    dhuhr: Mapped[str | None] = mapped_column(String, nullable=True)
    asr: Mapped[str | None] = mapped_column(String, nullable=True)
    maghrib: Mapped[str | None] = mapped_column(String, nullable=True)
    isha: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String)


class ManualOverride(Base):
    __tablename__ = "manual_overrides"
    __table_args__ = (UniqueConstraint("date", "prayer_name"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String)
    prayer_name: Mapped[str] = mapped_column(String)
    time_hhmm: Mapped[str | None] = mapped_column(String, nullable=True)
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[str] = mapped_column(String)


class Exclusion(Base):
    __tablename__ = "exclusions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(String)
    prayer_name: Mapped[str | None] = mapped_column(String, nullable=True)
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String)


class AudioProfile(Base):
    __tablename__ = "audio_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String)
    file_path: Mapped[str] = mapped_column(String)
    sha256: Mapped[str] = mapped_column(String)
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String)


class PrayerAudioMap(Base):
    __tablename__ = "prayer_audio_map"
    prayer_name: Mapped[str] = mapped_column(String, primary_key=True)
    audio_profile_id: Mapped[int] = mapped_column(ForeignKey("audio_profiles.id"), nullable=False)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class PlaybackState(Base):
    __tablename__ = "playback_state"
    date: Mapped[str] = mapped_column(String, primary_key=True)
    prayer_name: Mapped[str] = mapped_column(String, primary_key=True)
    time_hhmm: Mapped[str] = mapped_column(String, primary_key=True)
    played_at: Mapped[str] = mapped_column(String)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[str] = mapped_column(String)
    level: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)

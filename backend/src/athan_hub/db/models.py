from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
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
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
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


class ChildProfile(Base):
    __tablename__ = "child_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String)
    slug: Mapped[str] = mapped_column(String, unique=True)
    gender: Mapped[str | None] = mapped_column(String, nullable=True)
    theme: Mapped[str] = mapped_column(String, default="classic_mushaf")
    preferred_recitation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_surah_id: Mapped[int] = mapped_column(Integer, default=1)
    start_ayah: Mapped[int] = mapped_column(Integer, default=1)
    end_ayah: Mapped[int] = mapped_column(Integer, default=1)
    repetitions: Mapped[int] = mapped_column(Integer, default=3)
    playback_speed: Mapped[float] = mapped_column(Float, default=1.0)
    show_arabic: Mapped[int] = mapped_column(Integer, default=1)
    show_translation: Mapped[int] = mapped_column(Integer, default=1)
    show_transliteration: Mapped[int] = mapped_column(Integer, default=0)
    recall_mode: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String)


class QuranProgress(Base):
    __tablename__ = "quran_progress"
    __table_args__ = (UniqueConstraint("profile_id", "verse_key"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("child_profiles.id", ondelete="CASCADE"))
    verse_key: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String, default="learning")
    completed_repetitions: Mapped[int] = mapped_column(Integer, default=0)
    first_practised_at: Mapped[str | None] = mapped_column(String, nullable=True)
    last_practised_at: Mapped[str | None] = mapped_column(String, nullable=True)
    first_memorised_at: Mapped[str | None] = mapped_column(String, nullable=True)


class QuranSession(Base):
    __tablename__ = "quran_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("child_profiles.id", ondelete="CASCADE"))
    surah_id: Mapped[int] = mapped_column(Integer)
    start_ayah: Mapped[int] = mapped_column(Integer)
    end_ayah: Mapped[int] = mapped_column(Integer)
    recitation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    practice_seconds: Mapped[int] = mapped_column(Integer, default=0)
    completed: Mapped[int] = mapped_column(Integer, default=0)
    points_awarded: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[str] = mapped_column(String)
    ended_at: Mapped[str | None] = mapped_column(String, nullable=True)


class RewardEvent(Base):
    __tablename__ = "reward_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("child_profiles.id", ondelete="CASCADE"))
    event_key: Mapped[str] = mapped_column(String, unique=True)
    category: Mapped[str] = mapped_column(String)
    points: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(String)


class ProfileBadge(Base):
    __tablename__ = "profile_badges"
    __table_args__ = (UniqueConstraint("profile_id", "badge_key"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("child_profiles.id", ondelete="CASCADE"))
    badge_key: Mapped[str] = mapped_column(String)
    awarded_at: Mapped[str] = mapped_column(String)


class QuranAudioCache(Base):
    __tablename__ = "quran_audio_cache"
    __table_args__ = (UniqueConstraint("recitation_id", "content_key"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    recitation_id: Mapped[int] = mapped_column(Integer)
    content_key: Mapped[str] = mapped_column(String)
    local_path: Mapped[str] = mapped_column(String)
    source_url: Mapped[str] = mapped_column(Text)
    byte_count: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String)
    pinned: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String)
    last_accessed_at: Mapped[str] = mapped_column(String)

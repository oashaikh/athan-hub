import logging
import math
import time
from pathlib import Path

from .logging import configure_logging
from .playback import play_once, prepare_output
from . import playback_state
from .time_utils import now_local
from ..db.migrations import init_db
from ..db.session import SessionLocal
from ..services import audio_service, audit_service, bluetooth_service, timetable_service


logger = logging.getLogger(__name__)
_prepared_occurrences: set[tuple[str, str, str]] = set()


def _occurrence_key(date_str: str, prayer: str, event_time) -> tuple[str, str, str]:
    return date_str, prayer, event_time.strftime("%H:%M")


def _next_tick_delay(events, now, takeover_lead_seconds: int) -> float:
    milestones: list[float] = []
    for _date_str, _prayer, event_time in events:
        until_event = (event_time - now).total_seconds()
        until_takeover = until_event - takeover_lead_seconds
        if until_takeover > 0:
            milestones.append(until_takeover)
        if until_event > 0:
            milestones.append(until_event)
    return max(0.1, min(10.0, min(milestones, default=10.0)))


def tick() -> float:
    with SessionLocal() as db:
        events = timetable_service.upcoming_events(db)
        now = now_local()
        upcoming = [event for event in events if event[2] >= now]
        if upcoming:
            logger.info("Next prayer", extra={"next": upcoming[0][1], "at": upcoming[0][2].isoformat()})
        takeover_lead = bluetooth_service._get_int(
            db,
            "pre_connect_seconds",
            bluetooth_service.DEFAULTS["pre_connect_seconds"],
        )
        connect_retry = bluetooth_service._get_int(
            db,
            "connect_retry_seconds",
            bluetooth_service.DEFAULTS["connect_retry_seconds"],
        )
        sink_volume = bluetooth_service._get_int(
            db,
            "sink_volume_percent",
            bluetooth_service.DEFAULTS["sink_volume_percent"],
        )
        active_keys = {_occurrence_key(*event) for event in events}
        _prepared_occurrences.intersection_update(active_keys)

        if takeover_lead > 0:
            for date_str, prayer, event_time in events:
                seconds_until = (event_time - now).total_seconds()
                key = _occurrence_key(date_str, prayer, event_time)
                if not 0 < seconds_until <= takeover_lead or key in _prepared_occurrences:
                    continue
                if timetable_service.has_played(db, *key):
                    continue
                profile = audio_service.profile_for_prayer(db, prayer)
                mac = bluetooth_service.get_echo_mac(db)
                if not profile or not profile.duration_seconds or not mac:
                    continue
                try:
                    result = prepare_output(
                        mac,
                        timeout_seconds=max(1, math.ceil(seconds_until)),
                        sink_volume_percent=sink_volume,
                        connect_retry_seconds=connect_retry,
                    )
                    _prepared_occurrences.add(key)
                    audit_service.add_entry(db, "INFO", f"Prepared speaker for {prayer}", result)
                except Exception as exc:
                    logger.warning("Early speaker takeover failed for %s: %s", prayer, exc)
                    audit_service.add_entry(
                        db,
                        "WARNING",
                        f"Speaker takeover failed for {prayer}",
                        {"error": str(exc)},
                    )

        now = now_local()
        grace = bluetooth_service._get_int(db, "grace_seconds", bluetooth_service.DEFAULTS["grace_seconds"])
        for date_str, prayer, event_time in events:
            delta = (now - event_time).total_seconds()
            hhmm = event_time.strftime("%H:%M")
            if delta < 0 or delta > grace or timetable_service.has_played(db, date_str, prayer, hhmm):
                continue
            profile = audio_service.profile_for_prayer(db, prayer)
            mac = bluetooth_service.get_echo_mac(db)
            if not profile or not mac:
                logger.warning("Prayer due but audio profile or Echo MAC is missing")
                continue
            if not profile.duration_seconds:
                logger.error("Prayer due but audio profile has no measured duration")
                audit_service.add_entry(db, "ERROR", f"Playback disabled for {prayer}", {"error": "Audio duration unavailable"})
                continue
            try:
                playback_state.write_active(prayer, profile.id, profile.duration_seconds, now_local())
                try:
                    result = play_once(
                        mac,
                        Path(profile.file_path),
                        pre_connect_seconds=takeover_lead,
                        connect_retry_seconds=connect_retry,
                        disconnect_after_play=bluetooth_service._get_bool(db, "disconnect_after_play", False),
                        sink_volume_percent=sink_volume,
                    )
                finally:
                    playback_state.clear_active()
                timetable_service.record_playback(db, date_str, prayer, hhmm)
                audit_service.add_entry(db, "INFO", f"Played {prayer}", result)
            except Exception as exc:
                logger.exception("Playback failed")
                audit_service.add_entry(db, "ERROR", f"Playback failed for {prayer}", {"error": str(exc)})
        return _next_tick_delay(events, now, takeover_lead)


def main() -> None:
    configure_logging()
    init_db()
    logger.info("Athan scheduler started")
    while True:
        try:
            delay = tick()
        except Exception:
            logger.exception("Scheduler tick failed")
            delay = 10
        time.sleep(delay)


if __name__ == "__main__":
    main()

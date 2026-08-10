import logging
import time
from pathlib import Path

from .logging import configure_logging
from .playback import play_once
from .time_utils import now_local
from ..db.migrations import init_db
from ..db.session import SessionLocal
from ..services import audio_service, audit_service, bluetooth_service, timetable_service


logger = logging.getLogger(__name__)


def tick() -> None:
    with SessionLocal() as db:
        events = timetable_service.upcoming_events(db)
        now = now_local()
        upcoming = [event for event in events if event[2] >= now]
        if upcoming:
            logger.info("Next prayer", extra={"next": upcoming[0][1], "at": upcoming[0][2].isoformat()})
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
            try:
                result = play_once(
                    mac,
                    Path(profile.file_path),
                    pre_connect_seconds=bluetooth_service._get_int(db, "pre_connect_seconds", 10),
                    connect_retry_seconds=bluetooth_service._get_int(db, "connect_retry_seconds", 20),
                    disconnect_after_play=bluetooth_service._get_bool(db, "disconnect_after_play", True),
                    sink_volume_percent=bluetooth_service._get_int(db, "sink_volume_percent", 140),
                )
                timetable_service.record_playback(db, date_str, prayer, hhmm)
                audit_service.add_entry(db, "INFO", f"Played {prayer}", result)
            except Exception as exc:
                logger.exception("Playback failed")
                audit_service.add_entry(db, "ERROR", f"Playback failed for {prayer}", {"error": str(exc)})


def main() -> None:
    configure_logging()
    init_db()
    logger.info("Athan scheduler started")
    while True:
        try:
            tick()
        except Exception:
            logger.exception("Scheduler tick failed")
        time.sleep(10)


if __name__ == "__main__":
    main()


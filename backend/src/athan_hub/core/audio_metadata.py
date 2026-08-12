from pathlib import Path

from mutagen import MutagenError
from mutagen.mp3 import MP3


def mp3_duration(path: Path) -> float:
    try:
        duration = float(MP3(path).info.length)
    except (MutagenError, OSError, ValueError) as exc:
        raise ValueError("MP3 duration could not be measured") from exc
    if duration <= 0:
        raise ValueError("MP3 duration could not be measured")
    return duration

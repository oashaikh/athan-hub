import json
import time
import urllib.request
from typing import Any, Dict
from xml.sax.saxutils import quoteattr

from .config import get_settings


def enabled() -> bool:
    settings = get_settings()
    return bool(settings.ha_token and settings.ha_notify_service and settings.ha_audio_url)


def play(duration_seconds: float, timeout_seconds: int = 20) -> Dict[str, Any]:
    """Ask Home Assistant's Alexa Media Player to play the hosted athan, then wait for it to finish.

    Amazon fetches the audio itself, so ha_audio_url must be public HTTPS in Alexa's
    MP3 format (48 kbps, 24 kHz, at most 240 seconds).
    """
    # ponytail: one hosted URL for every prayer; map per audio profile if prayers need different athans.
    settings = get_settings()
    body = json.dumps({"message": f"<audio src={quoteattr(settings.ha_audio_url)}/>", "data": {"type": "tts"}}).encode()
    request = urllib.request.Request(
        f"{settings.ha_url.rstrip('/')}/api/services/notify/{settings.ha_notify_service}",
        data=body,
        headers={"Authorization": f"Bearer {settings.ha_token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        status = response.status
    time.sleep(max(0.0, duration_seconds))
    return {"status": "played", "output": "home_assistant", "service": settings.ha_notify_service, "http_status": status}

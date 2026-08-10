import hashlib
import hmac
import time

from fastapi import Request

COOKIE_NAME = "athan_pin"
COOKIE_AGE = 30 * 24 * 60 * 60


def _token(pin: str, secret: str, bucket: int) -> str:
    return hmac.new(secret.encode(), f"{pin}:{bucket}".encode(), hashlib.sha256).hexdigest()


def issue_token(settings) -> str:
    return _token(settings.pin, settings.pin_secret, int(time.time()) // COOKIE_AGE)


def is_protected_host(host: str, settings) -> bool:
    return bool(settings.pin)


def is_pin_valid(request: Request, settings) -> bool:
    supplied = request.cookies.get(COOKIE_NAME, "")
    bucket = int(time.time()) // COOKIE_AGE
    return any(hmac.compare_digest(supplied, _token(settings.pin, settings.pin_secret, b)) for b in (bucket, bucket - 1))


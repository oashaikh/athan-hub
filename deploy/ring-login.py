#!/usr/bin/env python3
"""Sign go2rtc in to Ring so the Cameras page can talk through a Ring doorbell.

Ring blocks the old password sign-in that go2rtc's own Ring page uses (it
answers 406 Not Acceptable), so this signs in the way the Ring app does
(OAuth v2 with PKCE), then hands the refresh token to go2rtc and adds each
Ring camera as a go2rtc stream named after it ("Front Door" -> front_door).

Run on the Hub: python3 /opt/athan-hub/deploy/ring-login.py
It asks for the Ring email, password and the 2FA code Ring sends. Nothing is
stored except the token inside go2rtc's config. Then rerun
setup-home-assistant.sh --dashboard-only to put the Talk button on the card.
"""
import base64
import getpass
import hashlib
import http.cookiejar
import json
import re
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

OAUTH = "https://oauth.ring.com"
CLIENT_ID = "ring_official_android"
REDIRECT_URI = "https://ring.com/signin/callback"
USER_AGENT = "android:com.ringapp"
GO2RTC = "http://127.0.0.1:1984"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # read each Location ourselves


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def stream_name(description):
    return re.sub(r"[^a-z0-9]+", "_", description.lower()).strip("_")


class RingLogin:
    def __init__(self):
        self.hardware_id = str(uuid.uuid4())
        self.verifier = b64url(secrets.token_bytes(32))
        self.state = secrets.token_hex(16)
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies), NoRedirect)
        self.csrf = None

    def request(self, url, form=None, accept="text/html,application/json;q=0.9,*/*;q=0.8"):
        data = urllib.parse.urlencode(form).encode() if form is not None else None
        req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, "Accept": accept})
        if data is not None:
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with self.opener.open(req, timeout=30) as resp:
                return resp.status, resp.headers, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as err:
            return err.code, err.headers, err.read().decode("utf-8", "replace")

    def _find_csrf(self, html):
        for cookie in self.cookies:
            if cookie.name == "csrf-token":
                return urllib.parse.unquote(cookie.value)
        match = re.search(r"""["']csrf[-_]?token["']\s*[:=]\s*["']([^"']+)["']""", html, re.I)
        if match:
            return match.group(1)
        match = re.search(r"""name=["']csrf[-_]?token["'][^>]*value=["']([^"']+)["']""", html, re.I)
        return match.group(1) if match else None

    def _follow(self, url):
        """Follow redirects from url; return (status, headers, body, code-or-None)."""
        for _ in range(6):
            status, headers, body = self.request(url)
            location = headers.get("Location")
            if not (300 <= status < 400 and location):
                return status, headers, body, None
            url = urllib.parse.urljoin(OAUTH, location)
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            if "code" in query:
                if query.get("state", [None])[0] != self.state:
                    raise SystemExit("Ring answered with a different sign-in state; try again.")
                return status, headers, body, query["code"][0]
        raise SystemExit("Ring kept redirecting; try again later.")

    def open_authorize(self):
        params = {
            "client_id": CLIENT_ID, "response_type": "code", "scope": "client",
            "redirect_uri": REDIRECT_URI, "state": self.state, "prompt": "login",
            "code_challenge": b64url(hashlib.sha256(self.verifier.encode("ascii")).digest()),
            "code_challenge_method": "S256", "hardware_id": self.hardware_id,
            "app_brand": "ring", "device_model": "athan-hub",
        }
        status, _, body, _ = self._follow(f"{OAUTH}/oauth/v2/authorize?{urllib.parse.urlencode(params)}")
        self.csrf = self._find_csrf(body)
        if status >= 400 or not self.csrf:
            raise SystemExit(f"Ring's sign-in page did not load (HTTP {status}); try again later.")

    def sign_in(self, email, password):
        """Return True when Ring wants a 2FA code."""
        status, headers, body = self.request(f"{OAUTH}/oauth/v2/signin",
                                             {"username": email, "password": password, "csrf-token": self.csrf})
        try:
            data = json.loads(body)
        except ValueError:
            data = {}
        location = headers.get("Location") or ""
        if status == 412 or "tsv_state" in data or "next_time_in_secs" in data or "/2fa" in location:
            return True
        if status in (400, 401, 403):
            raise SystemExit("Ring did not accept that email and password.")
        if status >= 400:
            raise SystemExit(f"Ring refused the sign-in (HTTP {status}): {body[:200]}")
        return False

    def verify(self, code):
        status, _, body = self.request(f"{OAUTH}/oauth/v2/2fa/verify",
                                       {"2fa_code": code, "csrf-token": self.csrf, "remember_me": "false"})
        if status in (400, 401):
            raise SystemExit("Ring did not accept that code (wrong or expired). Run this again for a new one.")
        if status >= 400:
            raise SystemExit(f"Ring refused the code (HTTP {status}): {body[:200]}")

    def refresh_token(self):
        _, _, _, code = self._follow(f"{OAUTH}/oauth/v2/authorize")
        if not code:
            raise SystemExit("Ring signed in but sent no authorisation code; try again.")
        req = urllib.request.Request(
            f"{OAUTH}/oauth/token",
            data=urllib.parse.urlencode({
                "client_id": CLIENT_ID, "grant_type": "authorization_code", "code": code,
                "code_verifier": self.verifier, "redirect_uri": REDIRECT_URI,
            }).encode(),
            headers={"User-Agent": USER_AGENT, "Accept": "application/json", "hardware_id": self.hardware_id,
                     "Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            token = json.load(resp)["refresh_token"]
        # go2rtc's ring: source keeps the refresh token and hardware id together.
        return base64.b64encode(json.dumps({"rt": token, "hid": self.hardware_id}).encode()).decode()


def add_streams(token):
    query = urllib.parse.urlencode({"refresh_token": token})
    with urllib.request.urlopen(f"{GO2RTC}/api/ring?{query}", timeout=60) as resp:
        sources = json.load(resp).get("sources") or []
    added = []
    for source in sources:
        if source["url"].endswith("&snapshot"):
            continue
        name = stream_name(source["name"])
        put = urllib.request.Request(
            f"{GO2RTC}/api/streams?{urllib.parse.urlencode({'name': name, 'src': source['url']})}", method="PUT")
        urllib.request.urlopen(put, timeout=30).close()
        added.append(f"{source['name']} -> {name}")
    return added


def main():
    login = RingLogin()
    login.open_authorize()
    email = input("Ring email: ").strip()
    password = getpass.getpass("Ring password: ")
    if login.sign_in(email, password):
        login.verify(input("Code Ring just sent you: ").strip())
    token = login.refresh_token()
    added = add_streams(token)
    if not added:
        raise SystemExit("Signed in, but go2rtc found no Ring cameras on the account.")
    print("Added to go2rtc:\n  " + "\n  ".join(added))
    print("Now run: sudo bash /opt/athan-hub/deploy/setup-home-assistant.sh --dashboard-only")


if __name__ == "__main__":
    if "--check" in sys.argv:  # loads Ring's sign-in page only, no account needed
        login = RingLogin()
        login.open_authorize()
        assert stream_name("Front Door") == "front_door" and stream_name("Back  Garden 2") == "back_garden_2"
        print("Ring sign-in page reachable; csrf token found.")
    else:
        main()

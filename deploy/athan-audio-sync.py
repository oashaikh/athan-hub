#!/usr/bin/env python3
"""Publish athan recordings dropped into Home Assistant's media folders for the Echo.

Files uploaded through Home Assistant's Media panel to "athan/general" or
"athan/fajr" are converted to Alexa's MP3 format (48 kbps, 24 kHz), split at a
quiet moment when longer than Alexa's 240-second limit, published to Vercel (Amazon
fetches the audio itself, so it must be public HTTPS), and written into
/etc/athan-hub/athan-hub.env as the random choices for every prayer and for Fajr.

Needs ATHAN_VERCEL_TOKEN, ATHAN_VERCEL_TEAM and ATHAN_VERCEL_PROJECT in the env file.
Without them it does nothing, so the rest of Athan Hub is unaffected.
"""
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ENV_FILE = Path(os.environ.get("ATHAN_ENV_FILE", "/etc/athan-hub/athan-hub.env"))
MEDIA_ROOT = Path(os.environ.get("ATHAN_HA_MEDIA_ROOT", "/var/lib/homeassistant/media/athan"))
OUT_ROOT = Path(os.environ.get("ATHAN_ALEXA_AUDIO_DIR", "/var/lib/athan-hub/alexa-audio"))
AUDIO_SUFFIXES = {".mp3", ".m4a", ".aac", ".opus", ".ogg", ".oga", ".wav", ".flac", ".webm", ".mp4"}
ALEXA_LIMIT = 240.0
SPLIT_BEFORE = 236.0  # leave headroom under the limit for encoder padding


def log(message: str) -> None:
    print(f"athan-audio-sync: {message}", flush=True)


def read_env() -> dict[str, str]:
    values = {}
    for line in ENV_FILE.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value
    return values


def write_env(updates: dict[str, str]) -> bool:
    lines = ENV_FILE.read_text().splitlines()
    kept = [line for line in lines if line.split("=", 1)[0] not in updates]
    new = kept + [f"{key}={value}" for key, value in updates.items() if value]
    if new == lines:
        return False
    tmp = ENV_FILE.with_suffix(".tmp")
    tmp.write_text("\n".join(new) + "\n")
    os.chmod(tmp, ENV_FILE.stat().st_mode)
    os.chown(tmp, ENV_FILE.stat().st_uid, ENV_FILE.stat().st_gid)
    tmp.replace(ENV_FILE)
    return True


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def split_point(path: Path) -> float:
    """The start of the last silence before Alexa's limit, or a hard cut if there is none."""
    probe = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-af", "silencedetect=noise=-40dB:d=0.6", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    starts = [float(s) for s in re.findall(r"silence_start: ([0-9.]+)", probe)]
    ends = [float(e) for e in re.findall(r"silence_end: ([0-9.]+)", probe)]
    best = None
    for start, end in zip(starts, ends):
        middle = (start + end) / 2
        if 30 < middle < SPLIT_BEFORE:
            best = middle
    return best or SPLIT_BEFORE


def convert(source: Path, target_dir: Path) -> list[Path]:
    """Alexa-format MP3 parts for one source file, cached by the source's content hash."""
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
    stem = re.sub(r"[^a-z0-9]+", "-", source.stem.lower()).strip("-")[:40] or "athan"
    cached = sorted(target_dir.glob(f"{stem}-{digest}-*.mp3"))
    if cached:
        return cached
    total = duration(source)
    cuts = [0.0]
    while total - cuts[-1] > ALEXA_LIMIT:
        with tempfile.TemporaryDirectory() as tmp:
            rest = Path(tmp) / "rest.wav"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(cuts[-1]), "-i", str(source), str(rest)], check=True)
            cuts.append(cuts[-1] + split_point(rest))
    cuts.append(total)
    parts = []
    for index, (start, end) in enumerate(zip(cuts, cuts[1:])):
        part = target_dir / f"{stem}-{digest}-{index + 1}.mp3"
        subprocess.run([
            "ffmpeg", "-loglevel", "error", "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(source),
            "-map", "0:a", "-map_metadata", "-1", "-ac", "2", "-codec:a", "libmp3lame", "-b:a", "48k", "-ar", "24000",
            str(part),
        ], check=True)
        parts.append(part)
    log(f"converted {source.name} into {len(parts)} part(s)")
    return parts


def convert_full(source: Path, target_dir: Path) -> Path:
    """One full-length 128 kbps MP3 for the Alexa skill's AudioPlayer, which has no length limit."""
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
    stem = re.sub(r"[^a-z0-9]+", "-", source.stem.lower()).strip("-")[:40] or "athan"
    target = target_dir / f"{stem}-{digest}.mp3"
    if not target.exists():
        subprocess.run([
            "ffmpeg", "-loglevel", "error", "-y", "-i", str(source), "-map", "0:a", "-map_metadata", "-1",
            "-ac", "2", "-codec:a", "libmp3lame", "-b:a", "128k", "-ar", "44100", str(target),
        ], check=True)
    return target


def vercel(method: str, path: str, token: str, team: str, body: bytes | None = None, headers: dict | None = None) -> dict:
    request = urllib.request.Request(
        f"https://api.vercel.com{path}{'&' if '?' in path else '?'}slug={team}",
        data=body, method=method,
        headers={"Authorization": f"Bearer {token}", **(headers or {})},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        raw = response.read()
        return json.loads(raw) if raw else {}


def publish(files: dict[str, Path], token: str, team: str, project: str, extra: dict[str, bytes] | None = None) -> str:
    """Upload the files and deploy them to the project's production domain."""
    entries = []
    for name, path in files.items():
        data = path.read_bytes()
        sha = hashlib.sha1(data).hexdigest()
        vercel("POST", "/v2/files", token, team, data, {"Content-Type": "application/octet-stream", "x-vercel-digest": sha})
        entries.append({"file": name, "sha": sha, "size": len(data)})
    config = json.dumps({"headers": [{"source": "/a/(.*)\\.mp3", "headers": [
        {"key": "Content-Type", "value": "audio/mpeg"},
        {"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}]}]}).encode()
    generated = {"vercel.json": config, "index.html": b"<!doctype html><title>Athan audio</title>\n", **(extra or {})}
    for name, data in generated.items():
        sha = hashlib.sha1(data).hexdigest()
        vercel("POST", "/v2/files", token, team, data, {"Content-Type": "application/octet-stream", "x-vercel-digest": sha})
        entries.append({"file": name, "sha": sha, "size": len(data)})
    deployment = vercel("POST", "/v13/deployments", token, team, json.dumps({
        "name": project, "project": project, "target": "production", "files": entries,
        "projectSettings": {"framework": None},
    }).encode(), {"Content-Type": "application/json"})
    for _ in range(60):
        state = vercel("GET", f"/v13/deployments/{deployment['id']}", token, team)
        if state.get("readyState") == "READY":
            return state.get("alias", [f"{project}.vercel.app"])[0]
        if state.get("readyState") in ("ERROR", "CANCELED"):
            raise RuntimeError(f"Vercel deployment {state.get('readyState')}")
        time.sleep(5)
    raise RuntimeError("Vercel deployment did not finish in time")


def main() -> int:
    if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0:
        log("ffmpeg is not installed; run: sudo apt-get install -y ffmpeg")
        return 1
    env = read_env()
    token, team, project = env.get("ATHAN_VERCEL_TOKEN"), env.get("ATHAN_VERCEL_TEAM"), env.get("ATHAN_VERCEL_PROJECT")
    if not (token and team and project):
        log("ATHAN_VERCEL_TOKEN, ATHAN_VERCEL_TEAM and ATHAN_VERCEL_PROJECT are not set; nothing to do")
        return 0
    folder = env.get("ATHAN_AUDIO_PATH") or secrets.token_hex(8)  # an unguessable path, kept stable
    choices: dict[str, list[str]] = {"general": [], "fajr": []}
    full: dict[str, list[str]] = {"general": [], "fajr": []}
    files: dict[str, Path] = {}
    for group in choices:
        source_dir = MEDIA_ROOT / group
        target_dir = OUT_ROOT / group
        source_dir.mkdir(parents=True, exist_ok=True)
        target_dir.mkdir(parents=True, exist_ok=True)
        (OUT_ROOT / "full").mkdir(parents=True, exist_ok=True)
        for source in sorted(p for p in source_dir.iterdir() if p.suffix.lower() in AUDIO_SUFFIXES):
            parts = convert(source, target_dir)
            names = [f"a/{folder}/{group}/{part.name}" for part in parts]
            files.update(zip(names, parts))
            choices[group].append("+".join(names))
            whole = convert_full(source, OUT_ROOT / "full")
            full_name = f"a/{folder}/full/{whole.name}"
            files[full_name] = whole
            full[group].append(full_name)
    if not choices["general"]:
        log(f"no athans in {MEDIA_ROOT / 'general'} yet; leaving the current setup alone")
        return 0
    # The private Alexa skill (alexa/) streams full-length files from the same site.
    skill_id = env.get("ATHAN_ALEXA_SKILL_ID", "")
    skill_code = Path("/opt/athan-hub/alexa/api/alexa.js")
    base = f"https://{project}.vercel.app/"
    extra = {}
    if skill_id and skill_code.exists():
        manifest = {"skillId": skill_id, **{g: [base + n for n in names] for g, names in full.items()}}
        icons = skill_code.parent.parent / "icons"
        extra = {
            **{f"icons/{icon.name}": icon.read_bytes() for icon in sorted(icons.glob("*.png"))},
            "api/alexa.js": skill_code.read_bytes(),
            "api/_manifest.js": f"module.exports = {json.dumps(manifest)};\n".encode(),
        }
    signature = hashlib.sha256(json.dumps([sorted(files), skill_id, sorted(extra)]).encode()).hexdigest()
    if env.get("ATHAN_AUDIO_SIGNATURE") == signature:
        return 0
    domain = publish(files, token, team, project, extra)  # served at the stable project domain below
    changed = write_env({
        "ATHAN_AUDIO_PATH": folder,
        "ATHAN_AUDIO_SIGNATURE": signature,
        "ATHAN_HA_AUDIO_URL": ",".join("+".join(base + n for n in c.split("+")) for c in choices["general"]),
        "ATHAN_HA_AUDIO_URL_FAJR": ",".join("+".join(base + n for n in c.split("+")) for c in choices["fajr"]),
    })
    log(f"published {len(choices['general'])} general and {len(choices['fajr'])} Fajr athan(s) to {domain}")
    if changed:
        subprocess.run(["systemctl", "restart", "athan-hub-scheduler.service"], check=False)
        setup = Path("/opt/athan-hub/deploy/setup-home-assistant.sh")
        if setup.exists():  # point the on-demand "Play athan" script at the new files
            subprocess.run(["bash", str(setup), "--package-only"], check=False)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except urllib.error.HTTPError as exc:
        log(f"Vercel refused the request: {exc.code} {exc.read()[:300]!r}")
        sys.exit(1)

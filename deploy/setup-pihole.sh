#!/usr/bin/env bash
# Installs Pi-hole (Docker) on the Athan Hub machine as a network-wide DNS ad
# blocker and adds it to Home Assistant. Safe to rerun. Run as root after
# setup-home-assistant.sh (which installs Docker and Home Assistant).
#
# Pi-hole answers DNS on port 53 and serves its admin page on port 8081, since
# nginx already uses 80 and 8080. It blocks nothing until the router (or a
# device) uses this machine's address as its DNS server.
set -Eeuo pipefail

DATA_DIR=/var/lib/pihole
ENV_FILE=/etc/athan-hub/athan-hub.env
IMAGE=pihole/pihole:2026.10.0
WEB_PORT=8081

log() { printf '\n==> %s\n' "$*"; }
[[ "$(id -u)" == 0 ]] || { echo "Run as root" >&2; exit 1; }
command -v docker >/dev/null || { echo "Docker is missing; run setup-home-assistant.sh first" >&2; exit 1; }
command -v dig >/dev/null || apt-get install -y -qq dnsutils >/dev/null

install -d -m 0700 "$DATA_DIR"
[[ -s "$DATA_DIR/api-password" ]] || (umask 077; openssl rand -hex 16 > "$DATA_DIR/api-password")
password="$(cat "$DATA_DIR/api-password")"

if [[ "$(docker inspect -f '{{.Config.Image}}' pihole 2>/dev/null)" != "$IMAGE" ]]; then
  log "Starting Pi-hole ($IMAGE)"
  docker pull -q "$IMAGE" >/dev/null
  docker rm -f pihole >/dev/null 2>&1 || true
  docker run -d --name pihole --restart=unless-stopped --network=host \
    -e TZ="$(timedatectl show -p Timezone --value 2>/dev/null || echo Europe/London)" \
    -e FTLCONF_webserver_port="$WEB_PORT" \
    -e FTLCONF_webserver_api_password="$password" \
    -e FTLCONF_dns_upstreams='1.1.1.1;9.9.9.9' \
    -e FTLCONF_dns_listeningMode=local \
    -v "$DATA_DIR/etc:/etc/pihole" "$IMAGE" >/dev/null
fi

for _ in $(seq 1 60); do
  dig +short +time=2 +tries=1 @127.0.0.1 example.com >/dev/null 2>&1 && break
  sleep 3
done
if dig +short +time=2 +tries=1 @127.0.0.1 doubleclick.net | grep -q '^0\.0\.0\.0$'; then
  log "Pi-hole is answering and blocking ads"
else
  log "Pi-hole is running, but did not block the test domain yet (the blocklist may still be downloading)"
fi

token="$(grep -E '^ATHAN_HA_TOKEN=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
if [[ -z "$token" ]]; then
  log "No ATHAN_HA_TOKEN in $ENV_FILE; add Pi-hole in Home Assistant by hand (host 127.0.0.1, port $WEB_PORT)"
  exit 0
fi

# Add the Pi-hole integration through Home Assistant's config flow, unless it is there.
T="$token" P="$password" PORT="$WEB_PORT" python3 - <<'PY'
import json, os, urllib.request

def call(method, path, body=None):
    request = urllib.request.Request(
        "http://127.0.0.1:8123" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + os.environ["T"], "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)

if any(e["domain"] == "pi_hole" for e in call("GET", "/api/config/config_entries/entry")):
    print("Pi-hole is already in Home Assistant")
    raise SystemExit
flow = call("POST", "/api/config/config_entries/flow", {"handler": "pi_hole"})
known = {"host": "127.0.0.1", "port": int(os.environ["PORT"]), "name": "Pi-hole", "location": "admin",
         "api_key": os.environ["P"], "ssl": False, "verify_ssl": False}
answer = {f["name"]: known[f["name"]] for f in flow.get("data_schema", []) if f["name"] in known}
result = call("POST", "/api/config/config_entries/flow/" + flow["flow_id"], answer)
print("Home Assistant:", result.get("type"), result.get("title") or result.get("errors"))
PY

log "Pi-hole admin: http://$(hostname -I | awk '{print $1}'):$WEB_PORT/admin (password in $DATA_DIR/api-password)"

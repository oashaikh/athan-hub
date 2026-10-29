#!/usr/bin/env bash
# Installs Home Assistant (Docker) next to Athan Hub so prayers can play on an Echo
# through Alexa Media Player. Safe to rerun. Run as root on the Athan Hub machine.
#
# Before the first run: nothing. After it, sign in to Home Assistant at
# http://<host>:8123, add the Alexa Media Player integration, create a long-lived
# token and add the ATHAN_HA_ lines described in the README, then rerun this
# script to add the Home Assistant sensors, script and sidebar dashboard.
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR=/var/lib/homeassistant
ENV_FILE=/etc/athan-hub/athan-hub.env
IMAGE=ghcr.io/home-assistant/home-assistant:stable

log() { printf '\n==> %s\n' "$*"; }
[[ "$(id -u)" == 0 ]] || { echo "Run as root" >&2; exit 1; }

# Debian's docker.io (20.10) cannot unpack Home Assistant's zstd image layers.
if ! command -v docker >/dev/null || [[ "$(docker version -f '{{.Server.Version}}' 2>/dev/null | cut -d. -f1)" -lt 23 ]]; then
  log "Installing Docker from download.docker.com"
  apt-get remove -y docker.io >/dev/null 2>&1 || true
  . /etc/os-release
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL "https://download.docker.com/linux/$ID/gpg" | gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$ID $VERSION_CODENAME stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io
  systemctl enable --now docker
fi

install -d -m 0755 "$CONFIG_DIR/custom_components" "$CONFIG_DIR/packages" "$CONFIG_DIR/themes" "$CONFIG_DIR/www/community"

# Dashboard cards, pinned. card-mod is a frontend module so the theme can style every card.
fetch_card() {
  [[ -s "$CONFIG_DIR/www/community/$1" ]] || curl -fsSL -o "$CONFIG_DIR/www/community/$1" "$2"
}
fetch_card card-mod-4.2.1.js https://raw.githubusercontent.com/thomasloven/lovelace-card-mod/v4.2.1/card-mod.js
fetch_card layout-card-2.4.7.js https://raw.githubusercontent.com/thomasloven/lovelace-layout-card/v2.4.7/layout-card.js
fetch_card mushroom-5.2.3.js https://github.com/piitaya/lovelace-mushroom/releases/download/v5.2.3/mushroom.js
install -m 0644 "$SCRIPT_DIR/homeassistant/themes/athan_glass.yaml" "$CONFIG_DIR/themes/athan_glass.yaml"

if [[ ! -f "$CONFIG_DIR/custom_components/alexa_media/manifest.json" ]]; then
  log "Installing Alexa Media Player"
  tag="$(curl -fsSL https://api.github.com/repos/alandtse/alexa_media_player/releases/latest | python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"])')"
  tmp="$(mktemp -d)"
  curl -fsSL -o "$tmp/amp.zip" "https://github.com/alandtse/alexa_media_player/releases/download/$tag/alexa_media.zip"
  python3 -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' "$tmp/amp.zip" "$CONFIG_DIR/custom_components/alexa_media"
  rm -rf "$tmp"
fi

# Packages hold the Athan Hub additions so configuration.yaml stays the default.
if [[ -f "$CONFIG_DIR/configuration.yaml" ]] && ! grep -q '^  packages:' "$CONFIG_DIR/configuration.yaml"; then
  printf '\nhomeassistant:\n  packages: !include_dir_named packages\n' >> "$CONFIG_DIR/configuration.yaml"
fi
if [[ -f "$CONFIG_DIR/configuration.yaml" ]] && ! grep -q 'card-mod-4.2.1.js' "$CONFIG_DIR/configuration.yaml"; then
  sed -i '/^frontend:/a\  extra_module_url:\n    - /local/community/card-mod-4.2.1.js' "$CONFIG_DIR/configuration.yaml"
fi
# nginx proxies port 80 to Home Assistant when ATHAN_HA_FRONT_DOOR=1.
if [[ -f "$CONFIG_DIR/configuration.yaml" ]] && ! grep -q '^http:' "$CONFIG_DIR/configuration.yaml"; then
  printf '\nhttp:\n  use_x_forwarded_for: true\n  trusted_proxies:\n    - 127.0.0.1\n    - ::1\n' >> "$CONFIG_DIR/configuration.yaml"
fi

ha_value() { sed -n "s/^$1=//p" "$ENV_FILE" 2>/dev/null | head -n 1; }
notify_service="$(ha_value ATHAN_HA_NOTIFY_SERVICE)"
audio_url="$(ha_value ATHAN_HA_AUDIO_URL)"
{
  printf '# Written by athan-hub deploy/setup-home-assistant.sh; edits are overwritten.\n'
  printf 'rest:\n'
  printf '  - resource: http://127.0.0.1:9000/api/timetable/next\n'
  printf '    scan_interval: 60\n'
  printf '    sensor:\n'
  printf '      - name: Next prayer\n'
  printf '        unique_id: athan_hub_next_prayer\n'
  printf '        icon: mdi:mosque\n'
  printf '        value_template: "{{ value_json.next.prayer | title if value_json.next else none }}"\n'
  printf '      - name: Next prayer time\n'
  printf '        unique_id: athan_hub_next_prayer_time\n'
  printf '        device_class: timestamp\n'
  printf '        value_template: "{{ value_json.next.at if value_json.next else none }}"\n'
  printf '  - resource_template: "http://127.0.0.1:9000/api/timetable/day?date={{ now().date() }}"\n'
  printf '    scan_interval: 900\n'
  printf '    sensor:\n'
  printf '      - name: Prayer times today\n'
  printf '        unique_id: athan_hub_prayer_times_today\n'
  printf '        icon: mdi:calendar-clock\n'
  printf '        value_template: "{{ value_json.date }}"\n'
  printf '        json_attributes:\n'
  printf '          - prayers\n'
  if [[ -n "$notify_service" ]]; then
    # Mirror the Echo's next Alexa timer into a Home Assistant timer so the dashboard
    # can show a live, second-by-second countdown only while one is running.
    echo_slug="${notify_service#alexa_media_}"
    printf 'timer:\n'
    printf '  echo_timer:\n'
    printf '    name: Echo timer\n'
    printf '    icon: mdi:timer-outline\n'
    printf 'automation:\n'
    printf '  - id: athan_hub_mirror_echo_timer\n'
    printf '    alias: Mirror the Echo timer\n'
    printf '    mode: restart\n'
    printf '    triggers:\n'
    printf '      - trigger: state\n'
    printf '        entity_id: sensor.%s_next_timer\n' "$echo_slug"
    printf '      - trigger: homeassistant\n'
    printf '        event: start\n'
    printf '    actions:\n'
    printf '      - variables:\n'
    printf '          seconds: "{%% set t = states(%s) %%}{{ ((as_datetime(t) - now()).total_seconds() | int) if t not in [%s, %s] else 0 }}"\n' "'sensor.${echo_slug}_next_timer'" "'unknown'" "'unavailable'"
    printf '      - if: "{{ seconds | int > 0 }}"\n'
    printf '        then:\n'
    printf '          - action: timer.start\n'
    printf '            target:\n'
    printf '              entity_id: timer.echo_timer\n'
    printf '            data:\n'
    printf '              duration: "{{ seconds }}"\n'
    printf '        else:\n'
    printf '          - action: timer.cancel\n'
    printf '            target:\n'
    printf '              entity_id: timer.echo_timer\n'
  fi
  if [[ -n "$notify_service" && -n "$audio_url" ]]; then
    printf 'script:\n'
    printf '  play_athan_on_echo:\n'
    printf '    alias: Play athan on the Echo\n'
    printf '    icon: mdi:mosque\n'
    printf '    sequence:\n'
    printf '      - action: notify.%s\n' "$notify_service"
    printf '        data:\n'
    printf '          message: <audio src="%s"/>\n' "$audio_url"
    printf '          data:\n'
    printf '            type: tts\n'
  fi
} > "$CONFIG_DIR/packages/athan_hub.yaml"

# Home Assistant moved http settings from YAML into .storage/http; once migrated the
# YAML block is ignored, so set the proxy trust there too (with Home Assistant stopped).
if [[ -f "$CONFIG_DIR/.storage/http" ]]; then
  docker stop homeassistant >/dev/null 2>&1 || true
  python3 - "$CONFIG_DIR/.storage/http" <<'PY'
import json, sys
path = sys.argv[1]
with open(path) as handle:
    store = json.load(handle)
store["data"]["stable"].update({"use_x_forwarded_for": True, "trusted_proxies": ["127.0.0.1", "::1"]})
with open(path, "w") as handle:
    json.dump(store, handle, indent=2)
PY
fi

if ! docker inspect homeassistant >/dev/null 2>&1; then
  log "Starting Home Assistant"
  docker pull -q "$IMAGE"
  docker run -d --name homeassistant --restart=unless-stopped --privileged --network=host \
    -e TZ="$(timedatectl show -p Timezone --value 2>/dev/null || echo Europe/London)" \
    -v "$CONFIG_DIR:/config" -v /run/dbus:/run/dbus:ro "$IMAGE" >/dev/null
else
  docker restart homeassistant >/dev/null
fi

for _ in $(seq 1 60); do
  curl -fsS -o /dev/null http://127.0.0.1:8123/ && break
  sleep 5
done

token="$(ha_value ATHAN_HA_TOKEN)"
if [[ -n "$token" ]]; then
  log "Adding the Home and Athan Hub dashboards"
  web_port=80
  [[ "$(ha_value ATHAN_HA_FRONT_DOOR)" == 1 ]] && web_port=8080
  docker cp "$SCRIPT_DIR/homeassistant/home-dashboard.json" homeassistant:/tmp/home-dashboard.json
  docker exec -i -e T="$token" -e URL="http://$(hostname).local:$web_port/" homeassistant python3 - <<'PY'
import asyncio, json, os, aiohttp

async def main():
    async with aiohttp.ClientSession() as session, session.ws_connect("http://127.0.0.1:8123/api/websocket") as ws:
        await ws.receive_json()
        await ws.send_json({"type": "auth", "access_token": os.environ["T"]})
        if (await ws.receive_json())["type"] != "auth_ok":
            raise SystemExit("Home Assistant rejected ATHAN_HA_TOKEN")
        ids = iter(range(1, 100))

        async def call(message):
            message["id"] = next(ids)
            await ws.send_json(message)
            while True:
                reply = await ws.receive_json()
                if reply.get("id") == message["id"]:
                    return reply

        await call({"type": "config/core/update", "unit_system": "metric"})
        wanted = {
            "/local/community/layout-card-2.4.7.js": "module",
            "/local/community/mushroom-5.2.3.js": "module",
            "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap": "css",
        }
        have = {r["url"] for r in (await call({"type": "lovelace/resources"}))["result"]}
        for url, res_type in wanted.items():
            if url not in have:
                await call({"type": "lovelace/resources/create", "url": url, "res_type": res_type})
        await call({"type": "call_service", "domain": "frontend", "service": "reload_themes"})
        await call({"type": "call_service", "domain": "frontend", "service": "set_theme",
                    "service_data": {"name": "Athan Glass", "mode": "light"}})
        await call({"type": "call_service", "domain": "frontend", "service": "set_theme",
                    "service_data": {"name": "Athan Glass", "mode": "dark"}})
        existing = {d["url_path"] for d in (await call({"type": "lovelace/dashboards/list"}))["result"]}
        dashboards = {
            "home-dashboard": ("Home", "mdi:home-variant", json.load(open("/tmp/home-dashboard.json"))),
            "athan-hub": ("Athan Hub", "mdi:mosque", {"views": [{
                "title": "Athan Hub", "path": "athan-hub", "type": "panel",
                "cards": [{"type": "iframe", "url": os.environ["URL"], "aspect_ratio": "100%"}]}]}),
        }
        for url_path, (title, icon, config) in dashboards.items():
            if url_path not in existing:
                await call({"type": "lovelace/dashboards/create", "url_path": url_path, "title": title,
                            "icon": icon, "show_in_sidebar": True, "require_admin": False, "mode": "storage"})
            await call({"type": "lovelace/config/save", "url_path": url_path, "config": config})

        # Keep Home Assistant uncluttered: drop onboarding's empty example areas and Map
        # dashboard, and show only the Home and Athan Hub dashboards in the sidebar.
        devices = (await call({"type": "config/device_registry/list"}))["result"]
        used_areas = {d["area_id"] for d in devices if d["area_id"]}
        for area in (await call({"type": "config/area_registry/list"}))["result"]:
            if area["area_id"] in {"living_room", "kitchen", "bedroom"} and area["area_id"] not in used_areas:
                await call({"type": "config/area_registry/delete", "area_id": area["area_id"]})
        for dashboard in (await call({"type": "lovelace/dashboards/list"}))["result"]:
            if dashboard["url_path"] == "map":
                await call({"type": "lovelace/dashboards/delete", "dashboard_id": dashboard["id"]})
        hidden = ["lovelace", "energy", "history", "logbook", "map", "media-browser", "todo",
                  "climate", "light", "security", "maintenance", "home"]
        await call({"type": "frontend/set_user_data", "key": "sidebar",
                    "value": {"panelOrder": ["home-dashboard", "athan-hub"], "hiddenPanels": hidden}})
        await call({"type": "frontend/set_user_data", "key": "core", "value": {"default_panel": "home-dashboard"}})

asyncio.run(main())
PY
else
  log "Next: sign in at http://$(hostname -I | awk '{print $1}'):8123, add Alexa Media Player, then set the ATHAN_HA_ lines and rerun"
fi

log "Home Assistant is ready at http://$(hostname -I | awk '{print $1}'):8123"

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
  # shellcheck source=/dev/null
  . /etc/os-release
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL "https://download.docker.com/linux/$ID/gpg" | gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$ID $VERSION_CODENAME stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io
  systemctl enable --now docker
fi

install -d -m 0755 "$CONFIG_DIR/custom_components" "$CONFIG_DIR/packages" "$CONFIG_DIR/themes" "$CONFIG_DIR/www/community" \
  "$CONFIG_DIR/media/athan/general" "$CONFIG_DIR/media/athan/fajr"

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
# The TV app cannot type a password with a remote, so a TV at ATHAN_HA_TV_IP is
# signed in as the owner without a login screen. Only that one address is trusted.
# trusted_networks must be listed first, or the frontend shows the login form anyway.
tv_ip="$(sed -n 's/^ATHAN_HA_TV_IP=//p' "$ENV_FILE" 2>/dev/null | head -n 1)"
if [[ -n "$tv_ip" && -f "$CONFIG_DIR/.storage/auth" ]] && ! grep -q 'trusted_networks' "$CONFIG_DIR/configuration.yaml"; then
  owner_id="$(python3 -c 'import json,sys; print(next(u["id"] for u in json.load(open(sys.argv[1]))["data"]["users"] if u.get("is_owner")))' "$CONFIG_DIR/.storage/auth")"
  sed -i "/^homeassistant:/a\\  auth_providers:\\n    - type: trusted_networks\\n      trusted_networks:\\n        - $tv_ip/32\\n      trusted_users:\\n        $tv_ip/32: $owner_id\\n      allow_bypass_login: true\\n    - type: homeassistant" "$CONFIG_DIR/configuration.yaml"
fi
# Athans are uploaded through Home Assistant's Media panel into media/athan/general
# and media/athan/fajr; athan-audio-sync publishes them for the Echo.
if [[ -f "$CONFIG_DIR/configuration.yaml" ]] && ! grep -q 'media_dirs:' "$CONFIG_DIR/configuration.yaml"; then
  sed -i '/^homeassistant:/a\  media_dirs:\n    local: /config/media' "$CONFIG_DIR/configuration.yaml"
fi
# nginx proxies port 80 to Home Assistant when ATHAN_HA_FRONT_DOOR=1.
if [[ -f "$CONFIG_DIR/configuration.yaml" ]] && ! grep -q '^http:' "$CONFIG_DIR/configuration.yaml"; then
  printf '\nhttp:\n  use_x_forwarded_for: true\n  trusted_proxies:\n    - 127.0.0.1\n    - ::1\n' >> "$CONFIG_DIR/configuration.yaml"
fi

ha_value() { sed -n "s/^$1=//p" "$ENV_FILE" 2>/dev/null | head -n 1; }
notify_service="$(ha_value ATHAN_HA_NOTIFY_SERVICE)"
audio_url="$(ha_value ATHAN_HA_AUDIO_URL)"
audio_url="${audio_url%%,*}"  # the on-demand script plays the first athan in the list
audio_url="${audio_url%%+*}"  # and only its first part
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
    # Mirror each running Alexa timer into its own Home Assistant timer so the
    # dashboard can show live, second-by-second countdowns only while they run.
    # ponytail: four slots; raise ECHO_TIMER_SLOTS if more timers ever run at once.
    echo_slug="${notify_service#alexa_media_}"
    slots=4
    printf 'timer:\n'
    for i in $(seq 1 "$slots"); do
      printf '  echo_timer_%s:\n    name: Timer %s\n    icon: mdi:timer-outline\n' "$i" "$i"
    done
    printf 'automation:\n'
    printf '  - id: athan_hub_mirror_echo_timers\n'
    printf '    alias: Mirror the Echo timers\n'
    printf '    mode: restart\n'
    printf '    triggers:\n'
    printf '      - trigger: state\n'
    printf '        entity_id: sensor.%s_next_timer\n' "$echo_slug"
    printf '      - trigger: homeassistant\n'
    printf '        event: start\n'
    printf '    actions:\n'
    printf '      - variables:\n'
    printf '          ends: >-\n'
    printf "            {%% set ns = namespace(out=[]) %%}{%% for t in state_attr('sensor.%s_next_timer', 'sorted_active') or [] %%}{%% set left = (t.triggerTime / 1000 - as_timestamp(now())) | int %%}{%% if left > 0 %%}{%% set ns.out = ns.out + [left] %%}{%% endif %%}{%% endfor %%}{{ ns.out | sort }}\n" "$echo_slug"
    printf '      - repeat:\n'
    printf '          for_each: %s\n' "$(seq -s, 1 "$slots" | sed 's/^/[/; s/$/]/')"
    printf '          sequence:\n'
    printf '            - if: "{{ ends | count >= repeat.item }}"\n'
    printf '              then:\n'
    printf '                - action: timer.start\n'
    printf '                  target:\n'
    printf '                    entity_id: "timer.echo_timer_{{ repeat.item }}"\n'
    printf '                  data:\n'
    printf '                    duration: "{{ ends[repeat.item - 1] }}"\n'
    printf '              else:\n'
    printf '                - action: timer.cancel\n'
    printf '                  target:\n'
    printf '                    entity_id: "timer.echo_timer_{{ repeat.item }}"\n'
  fi
  # LG Developer Mode sessions expire after about 1000 hours and delete sideloaded
  # apps such as the Athan Hub TV app. Renew daily with the session token stored in
  # secrets.yaml (see tv/webos/README.md), and raise a notification if LG refuses.
  if grep -q '^lg_devmode_reset_url:' "$CONFIG_DIR/secrets.yaml" 2>/dev/null; then
    printf 'rest_command:\n'
    printf '  lg_devmode_reset:\n'
    printf '    url: !secret lg_devmode_reset_url\n'
    printf '    method: get\n'
    printf '    timeout: 30\n'
    printf 'automation lg_devmode:\n'
    printf '  - id: athan_hub_renew_lg_devmode\n'
    printf '    alias: Renew the LG Developer Mode session\n'
    printf '    triggers:\n'
    printf '      - trigger: time\n'
    printf '        at: "03:30:00"\n'
    printf '    actions:\n'
    printf '      - action: rest_command.lg_devmode_reset\n'
    printf '        response_variable: reset\n'
    # LG answers with a text/html content type, so the JSON arrives as a string.
    printf '      - if: "{{ reset.status != 200 or %s not in (reset.content | string) }}"\n' "'success'"
    printf '        then:\n'
    printf '          - action: persistent_notification.create\n'
    printf '            data:\n'
    printf '              title: LG Developer Mode renewal failed\n'
    printf '              message: "Open Developer Mode on the TV and press Extend, or the Athan Hub TV app will be removed. LG said: {{ reset.content }}"\n'
  fi
  tv_entity="$(ha_value ATHAN_HA_TV_ENTITY)"
  if [[ -n "$tv_entity" ]]; then
    # At each prayer, if the TV is on: show who is calling, mute it for the athan, unmute.
    tv_notify="${tv_entity#media_player.}"
    printf 'automation athan_tv:\n'
    printf '  - id: athan_hub_tv_prayer_alert\n'
    printf '    alias: Mute the TV for the athan\n'
    printf '    mode: single\n'
    printf '    triggers:\n'
    printf '      - trigger: time\n'
    printf '        at: sensor.next_prayer_time\n'
    printf '    conditions:\n'
    printf '      - condition: state\n'
    printf '        entity_id: %s\n' "$tv_entity"
    printf '        state: "on"\n'
    printf '    actions:\n'
    printf '      - variables:\n'
    printf "          prayer: \"{{ states('sensor.next_prayer') }}\"\n"
    printf '      - action: notify.%s\n' "$tv_notify"
    printf '        data:\n'
    printf '          message: "{{ prayer }}: athan is playing"\n'
    printf '      - action: media_player.volume_mute\n'
    printf '        target:\n'
    printf '          entity_id: %s\n' "$tv_entity"
    printf '        data:\n'
    printf '          is_volume_muted: true\n'
    printf '      - delay: "00:03:40"\n'
    printf '      - action: media_player.volume_mute\n'
    printf '        target:\n'
    printf '          entity_id: %s\n' "$tv_entity"
    printf '        data:\n'
    printf '          is_volume_muted: false\n'
  fi
  if [[ -n "$notify_service" && -n "$audio_url" ]]; then
    printf 'automation athan_voice:\n'
    printf '  - id: athan_hub_voice_trigger\n'
    printf '    alias: Play the athan when asked\n'
    printf '    mode: single\n'
    printf '    triggers:\n'
    printf '      - trigger: state\n'
    printf '        entity_id: media_player.%s\n' "${notify_service#alexa_media_}"
    printf '        attribute: last_called_summary\n'
    printf '    conditions:\n'
    printf "      - condition: template\n"
    printf "        value_template: \"{{ trigger.to_state.attributes.last_called_summary | lower | regex_search('athan|adhan|azan|adan') }}\"\n"
    printf '    actions:\n'
    printf '      - action: script.play_athan_on_echo\n'
    printf 'script:\n'
    printf '  play_athan_on_echo:\n'
    printf '    alias: Play athan on the Echo\n'
    printf '    icon: mdi:mosque\n'
    printf '    sequence:\n'
    if [[ "$(ha_value ATHAN_HA_PLAYBACK)" == "skill" ]]; then
      # The private Alexa skill streams a random full-length athan (see alexa/README.md).
      printf '      - action: media_player.play_media\n'
      printf '        target:\n'
      printf '          entity_id: media_player.%s\n' "${notify_service#alexa_media_}"
      printf '        data:\n'
      printf '          media_content_id: ask call to prayer to play the athan\n'
      printf '          media_content_type: custom\n'
    else
      printf '      - action: notify.%s\n' "$notify_service"
      printf '        data:\n'
      printf '          message: <audio src="%s"/>\n' "$audio_url"
      printf '          data:\n'
      printf '            type: tts\n'
    fi
  fi
} > "$CONFIG_DIR/packages/athan_hub.yaml"

# --package-only: athan-audio-sync changed the athan URLs; reload the package's
# scripts and automations without restarting Home Assistant.
if [[ "${1:-}" == "--package-only" ]]; then
  token="$(ha_value ATHAN_HA_TOKEN)"
  for domain in script automation; do
    curl -fsS -o /dev/null -H "Authorization: Bearer $token" -X POST "http://127.0.0.1:8123/api/services/$domain/reload" || true
  done
  exit 0
fi

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
        hidden = ["lovelace", "energy", "history", "logbook", "map", "todo",
                  "climate", "light", "security", "maintenance", "home", "calendar"]
        await call({"type": "frontend/set_user_data", "key": "sidebar",
                    "value": {"panelOrder": ["home-dashboard", "athan-hub", "media-browser"], "hiddenPanels": hidden}})
        await call({"type": "frontend/set_user_data", "key": "core", "value": {"default_panel": "home-dashboard"}})

asyncio.run(main())
PY
else
  log "Next: sign in at http://$(hostname -I | awk '{print $1}'):8123, add Alexa Media Player, then set the ATHAN_HA_ lines and rerun"
fi

log "Home Assistant is ready at http://$(hostname -I | awk '{print $1}'):8123"

# Athan Hub

Athan Hub turns a headless Ubuntu or Debian computer into a local prayer-time dashboard and scheduled Bluetooth Athan player. It is designed for small computers such as Raspberry Pi, Radxa ROCK boards, mini PCs, and repurposed x86 hardware.

The dashboard works entirely on the local network. After installation, upload your own timetable CSV and Athan MP3, pair a Bluetooth speaker, create child profiles, and use the built-in Quran memorisation workspace.

## Features

- Responsive prayer dashboard with a real-time SVG sunrise/sunset cycle
- CSV timetable preview, import, daily overrides, and exclusions
- Multiple user-supplied MP3 profiles and per-prayer mapping
- Headless Bluetooth discovery, pairing, connection, and test playback
- Automatic scheduled playback with retry and grace-window controls
- Local PIN protection with a unique signing secret per installation
- Child profiles with independent progress, reciter, rewards, streaks, and themes
- A complete offline Quran text snapshot with Arabic, Saheeh International, and transliteration
- 139 selectable QUL recitations with safe on-demand local audio caching
- Exact verse repetition where a recitation provides ayah audio or verse timings
- Scheduled Athan pre-emption that stops Quran playback and locks child interaction
- mDNS discovery at `http://athan.local` by default
- Idempotent one-shot installer, update, backup, diagnostics, and uninstall tools
- No cloud account, telemetry, bundled timetable, or bundled recitation audio

## Supported systems

- Ubuntu 22.04 LTS or newer
- Debian 12 or newer
- Raspberry Pi OS Bookworm or newer
- `amd64` and `arm64`; other Debian architectures work when the locked Python packages provide wheels or can compile locally

The machine needs a working network connection for initial installation, plus a Bluetooth adapter for speaker playback. A display, keyboard, and mouse are not required.

## One-shot installation

From an SSH session on a clean supported system:

```bash
curl -fsSL https://raw.githubusercontent.com/oashaikh/athan-hub/main/install.sh | sudo bash
```

On a fresh installation, the hostname becomes `athan`, making the dashboard available at:

```text
http://athan.local
```

The installer generates a six-digit dashboard PIN and prints it once. Existing installs preserve their hostname, PIN, signing secret, timetable, audio, background images, history, and settings when the installer is rerun.

Common options:

```bash
sudo ./install.sh --hostname prayer-room --timezone Europe/London
sudo ./install.sh --pin 246810
sudo ./install.sh --no-pin
sudo ./install.sh --keep-hostname
```

### Playing on an Echo through Home Assistant

Some Echo speakers will not hold a Bluetooth connection to a Linux device. Athan Hub can instead ask Home Assistant's Alexa Media Player integration to play the athan:

1. Convert the athan to Alexa's format (MP3, 48 kbps, 24 kHz, at most 240 seconds), for example `ffmpeg -i athan.mp3 -map 0:a -ac 2 -b:a 48k -ar 24000 alexa-athan.mp3`, and host it at a public HTTPS URL. Amazon fetches the file itself.
2. Create a long-lived access token in Home Assistant (Profile, then Security).
3. Add these lines to `/etc/athan-hub/athan-hub.env` and restart `athan-hub-scheduler`:

```text
ATHAN_HA_URL=http://127.0.0.1:8123
ATHAN_HA_TOKEN=<long-lived token>
ATHAN_HA_NOTIFY_SERVICE=alexa_media_<echo name>
ATHAN_HA_AUDIO_URL=https://example.com/athan.mp3
```

Optional extras: `ATHAN_HA_VOLUME=60` sets the Echo to 60% for the athan and restores the previous volume afterwards, and `ATHAN_HA_AUDIO_URL_FAJR` (or `_DHUHR`, `_ASR`, `_MAGHRIB`, `_ISHA`) plays a different hosted athan for that prayer. Either setting can list several athans separated by commas, and one is picked at random each time. An athan longer than Alexa's 240-second limit can be split into parts joined with `+`, which play back to back. Do Not Disturb on the Echo is switched off for the athan and back on afterwards, because it otherwise silences the Echo without any error.

Set `ATHAN_HA_TV_ENTITY` to an LG webOS TV's media player (for example `media_player.lg_webos_tv_65un85006la`) and the setup script adds an automation that shows the prayer on screen and mutes the TV for the athan when it is on. Saying "Alexa, athan" to the Echo plays the athan straight away. For the LG TV app, see [tv/webos/README.md](tv/webos/README.md); `ATHAN_HA_TV_IP` lets the TV open Home Assistant without a login screen.

When all of these are set, prayers play through Home Assistant. If Home Assistant or the Echo is unavailable for 90 seconds, Athan Hub falls back to Bluetooth when a speaker is paired. The installer keeps `ATHAN_HA_` lines on updates.

Add `ATHAN_HA_FRONT_DOOR=1` to make `http://athan.local` open Home Assistant. The Athan Hub dashboard then moves to `http://athan.local:8080`, and Home Assistant shows it as a sidebar page. The change applies the next time the installer or updater runs.

`sudo bash /opt/athan-hub/deploy/setup-home-assistant.sh` installs Home Assistant in Docker with Alexa Media Player. Once the lines above are set, rerunning it adds next-prayer sensors, a "Play athan on the Echo" script and an Athan Hub sidebar page to Home Assistant. See [docs/ROCK4SE-RECOVERY.md](docs/ROCK4SE-RECOVERY.md) for a full rebuild from a blank SD card.

`sudo bash /opt/athan-hub/deploy/setup-pihole.sh` adds Pi-hole, a network-wide DNS ad blocker, in Docker and connects it to Home Assistant. Its admin page is on port 8081, and the password is in `/var/lib/pihole/api-password`. It blocks ads once your router hands out this machine's address as the DNS server.

### Uploading athans

Upload recordings in Home Assistant under **Media → My media → athan**: put general athans in `general` and Fajr athans in `fajr`. Any common audio format works. Within a few seconds `athan-audio-sync` converts each file to Alexa's format, splits anything longer than 240 seconds at a quiet moment, publishes the files to Vercel (Amazon fetches the audio itself, so it has to be public HTTPS) and makes them the random choices for every prayer, with the `fajr` folder used for Fajr. Deleting a file removes it from the rotation.

It needs a Vercel access token in `/etc/athan-hub/athan-hub.env`:

```text
ATHAN_VERCEL_TOKEN=<token from Vercel, Account Settings, Tokens>
ATHAN_VERCEL_TEAM=<team slug>
ATHAN_VERCEL_PROJECT=athan-audio
```

Without these lines the sync does nothing. Run `sudo athan-audio-sync` to publish straight away.

### Wi-Fi on a headless machine

The safest approach is to configure Wi-Fi in the Ubuntu installer, cloud-init, or imaging tool before first boot. Ethernet and existing Wi-Fi configuration are never replaced by Athan Hub.

If NetworkManager is already installed, the one-shot installer can add a Wi-Fi connection without placing the password in the repository:

```bash
read -r -p "Wi-Fi SSID: " ATHAN_WIFI_SSID
read -r -s -p "Wi-Fi password: " ATHAN_WIFI_PASSWORD; echo
export ATHAN_WIFI_SSID ATHAN_WIFI_PASSWORD
curl -fsSL https://raw.githubusercontent.com/oashaikh/athan-hub/main/install.sh | sudo --preserve-env=ATHAN_WIFI_SSID,ATHAN_WIFI_PASSWORD bash
unset ATHAN_WIFI_SSID ATHAN_WIFI_PASSWORD
```

## First-run setup

1. Open `http://athan.local`, select the lock, and enter the generated admin PIN.
2. Open **Prayer system → Timetable**, upload your CSV, review the preview, and select **Import timetable**.
3. Open **Prayer system → Audio**, upload your MP3 and map it to the desired prayers.
4. Put your speaker into pairing mode.
5. Open **Prayer system → Bluetooth & speaker**, scan, pair, and run a test playback.
6. Open **Child profiles** and create each household profile. Children can then switch profiles without the PIN.

Quran text, translation, transliteration, and progress work offline. The first play of a recitation object requires internet access; it is then kept in the local cache for later offline use.

The accepted CSV columns are:

```text
date,fajr,shurooq,dhuhr,asr,maghrib,isha
```

Dates use `YYYY-MM-DD`; times use 24-hour `HH:MM`. `sunrise`, `fajar`, `zuhr`, and `zohar` are accepted aliases. See [the example timetable](examples/timetable-template.csv).

## Operations

```bash
# Health checks
sudo athan-hub-doctor

# Backup timetable, profiles, progress, Athan MP3s, settings, and history
sudo athan-hub-backup /path/to/backup/directory

# Check the configured branch now and deploy it when it changed
sudo athan-hub-update

# Follow updater activity (the timer checks every two minutes)
systemctl list-timers athan-hub-update.timer
sudo journalctl -u athan-hub-update.service -f

# Restart services
sudo systemctl restart athan-hub-api athan-hub-scheduler nginx

# View logs
sudo journalctl -u athan-hub-api -u athan-hub-scheduler -f

# Remove the application but preserve data
sudo athan-hub-uninstall

# Permanently remove the application and all user data
sudo athan-hub-uninstall --purge
```

Detailed guidance is in [Installation](docs/INSTALL.md) and [Troubleshooting](docs/TROUBLESHOOTING.md).

### Automatic deployments

The installer enables `athan-hub-update.timer`. It fetches the configured public
GitHub branch over HTTPS, deploys only a new commit, and verifies both services
and HTTP health before recording success. It postpones an update while Athan or
Quran audio is playing. Before changing the application it takes a private
rollback snapshot of the application, configuration, and persistent data; a
failed health check automatically restores that snapshot. The five most recent
pre-update data backups are retained under `/var/backups/athan-hub`.

The default tracked branch is the branch passed to the installer (`main` when
omitted). To use a protected integration branch, edit the root-owned file:

```bash
sudoedit /etc/athan-hub/updater.env
# ATHAN_UPDATE_REPOSITORY=https://github.com/oashaikh/athan-hub.git
# ATHAN_UPDATE_BRANCH=dev
sudo systemctl start athan-hub-update.service
```

No GitHub token or SSH key is stored on the appliance. Development happens in a
separate clone; the appliance only receives commits that are already public.

## Home Assistant integration

`custom_components/athan_hub` is a small Home Assistant integration that reads prayer times from a running Athan Hub server. It does not calculate anything itself. Athan Hub stays in charge of the timetable, overrides, exclusions and Bluetooth playback, and Home Assistant gets entities to automate with.

To install it by hand on Home Assistant Container, copy the `custom_components/athan_hub` folder into `/config/custom_components/` and restart Home Assistant. You can also add this repository to HACS as a custom repository of type Integration. Then go to Settings, Devices & services, Add integration, search for Athan Hub and enter the server address. The default is `http://athan.local`. If Home Assistant runs on the Athan Hub machine itself with host networking, `http://127.0.0.1:9000` also works.

The integration polls the server every 60 seconds and creates one device with these entities. Names follow the Mawaqit integration where that was easy, so most Mawaqit automations need only the entity IDs changing.

- `sensor.athan_hub_fajr`, `_shuruq`, `_dhuhr`, `_asr`, `_maghrib` and `_isha` hold today's times as timestamps. An `excluded` attribute shows when Athan Hub will skip the athan for that prayer. A prayer switched off by an override reads `unknown`.
- `sensor.athan_hub_next_prayer` (for example `Maghrib`) and `sensor.athan_hub_next_prayer_time`.
- `calendar.athan_hub_prayer_times` lists each prayer for the next seven days as a 15 minute event.
- `event.athan_hub_prayer` fires at each prayer time, including Shuruq. Its event type is the prayer key, such as `fajr` or `shurooq`, so an automation can filter on it. The integration sets a timer for the exact minute, so the event does not wait for the next poll. If Home Assistant is down at that moment the event is missed.
- `binary_sensor.athan_hub_athan_playing` is on while the server is playing the athan. It can lag by up to a minute.

The `athan_hub.play_athan` action plays an athan on any media player through `media_player.play_media`. Set the audio URL in the integration's options, or pass `media_content_id` in the call. The speaker has to be able to reach that URL. With no URL set, the action fails with an error that says so. Alexa Echo devices cannot play arbitrary URLs this way, and Athan Hub's built-in Home Assistant mode remains the route for them.

```yaml
action: athan_hub.play_athan
data:
  media_player: media_player.kitchen
  announce: true
```

The integration tests use `pytest-homeassistant-custom-component` in a separate virtual environment:

```bash
python3.14 -m venv .venv-ha
.venv-ha/bin/pip install pytest-homeassistant-custom-component
.venv-ha/bin/python -m pytest tests
```

## Development

Backend:

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
pytest
```

Frontend:

```bash
cd frontend
npm ci
npm test
npm run build
```

The compiled frontend is committed intentionally so the installer does not need Node.js on the target device. Fonts and icons are bundled locally for offline runtime use.

The Quran resource snapshot records its exact upstream revision, payload hashes, and source-specific notices. A scheduled public mirror of QUL is maintained at [oashaikh/quranic-universal-library](https://github.com/oashaikh/quranic-universal-library); the canonical upstream remains [TarteelAI/quranic-universal-library](https://github.com/TarteelAI/quranic-universal-library).

## Security and privacy

- Do not expose port 80 directly to the public internet.
- The installer creates a root-owned environment file at `/etc/athan-hub/athan-hub.env` with mode `0640`.
- User MP3s, uploaded timetables, databases, logs, Wi-Fi credentials, and PINs are excluded from Git.
- Quran resource provenance and checksums are committed in `resources/quran/manifest.json`; recitation audio is never committed.
- See [SECURITY.md](SECURITY.md) for the support policy and private reporting instructions.

## License

Athan Hub is free and open-source software licensed under the [GNU Affero General Public License v3.0](LICENSE). You may use, modify, distribute, and sell it under the license terms. Modified versions offered over a network must make their corresponding source available to users under the same license.

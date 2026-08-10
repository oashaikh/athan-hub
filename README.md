# Athan Hub

Athan Hub turns a headless Ubuntu or Debian computer into a local prayer-time dashboard and scheduled Bluetooth Athan player. It is designed for small computers such as Raspberry Pi, Radxa ROCK boards, mini PCs, and repurposed x86 hardware.

The dashboard works entirely on the local network. After installation, upload your own timetable CSV and MP3 recording, scan for a Bluetooth speaker, and choose which recording should play for each prayer.

## Features

- Responsive prayer dashboard with a real-time SVG sunrise/sunset cycle
- CSV timetable preview, import, daily overrides, and exclusions
- Multiple user-supplied MP3 profiles and per-prayer mapping
- Headless Bluetooth discovery, pairing, connection, and test playback
- Automatic scheduled playback with retry and grace-window controls
- Local PIN protection with a unique signing secret per installation
- mDNS discovery at `http://athan.local` by default
- Idempotent one-shot installer, update, backup, diagnostics, and uninstall tools
- No cloud service, telemetry, bundled timetable, bundled audio, or runtime internet dependency

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

1. Open `http://athan.local` and enter the generated PIN.
2. Open **Settings → Timetable**, upload your CSV, review the preview, and select **Import timetable**.
3. Open **Settings → Audio**, upload your MP3 and map it to the desired prayers.
4. Put your speaker into pairing mode.
5. Open **Settings → Bluetooth & speaker**, scan, pair, and run a test playback.

The accepted CSV columns are:

```text
date,fajr,shurooq,dhuhr,asr,maghrib,isha
```

Dates use `YYYY-MM-DD`; times use 24-hour `HH:MM`. `sunrise`, `fajar`, `zuhr`, and `zohar` are accepted aliases. See [the example timetable](examples/timetable-template.csv).

## Operations

```bash
# Health checks
sudo athan-hub-doctor

# Backup timetable, MP3s, settings, and history
sudo athan-hub-backup /path/to/backup/directory

# Install the latest main branch without deleting user data
sudo athan-hub-update

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
npm run build
```

The compiled frontend is committed intentionally so the installer does not need Node.js on the target device. Fonts and icons are bundled locally for offline runtime use.

## Security and privacy

- Do not expose port 80 directly to the public internet.
- The installer creates a root-owned environment file at `/etc/athan-hub/athan-hub.env` with mode `0640`.
- User MP3s, uploaded timetables, databases, logs, Wi-Fi credentials, and PINs are excluded from Git.
- See [SECURITY.md](SECURITY.md) for the support policy and private reporting instructions.

This repository is publicly visible but does not currently grant an open-source license. All rights are reserved unless a license is added later.

# Installation details

## What the installer changes

The installer is idempotent and may be safely rerun. It:

- installs required Debian packages;
- creates or reuses the dedicated `athan` service account;
- stores application code in `/opt/athan-hub`;
- stores persistent data in `/var/lib/athan-hub`;
- stores root-managed configuration in `/etc/athan-hub`;
- installs two hardened systemd services;
- configures Nginx on port 80;
- enables Avahi for `.local` discovery;
- starts a persistent user audio session for PipeWire or PulseAudio;
- enables Bluetooth, the API, the scheduler, Nginx, and Avahi at boot.

It does not upload a timetable, install an MP3, configure a speaker, expose the device to the internet, or replace existing network configuration.

## Local checkout

```bash
git clone https://github.com/oashaikh/athan-hub.git
cd athan-hub
sudo ./install.sh --timezone Europe/London
```

## Environment and paths

Runtime configuration is stored in `/etc/athan-hub/athan-hub.env`. Persistent user data remains outside `/opt`, so application upgrades do not delete it.

| Path | Purpose |
| --- | --- |
| `/opt/athan-hub` | Installed application and Python virtual environment |
| `/var/lib/athan-hub/athan.db` | SQLite database |
| `/var/lib/athan-hub/audio` | Uploaded MP3 files |
| `/var/lib/athan-hub/uploads` | Most recently uploaded timetable |
| `/var/lib/athan-hub/backgrounds` | Dashboard background images |
| `/var/lib/athan-hub/quran-cache` | Downloaded Quran recitation audio (excluded from backups) |
| `/var/log/athan-hub` | Optional application logs |
| `/etc/athan-hub/athan-hub.env` | Root-managed configuration and PIN secret |

## Network behavior

The API listens only on `127.0.0.1:9000`. Nginx is the only network-facing process and listens on TCP port 80. Avahi advertises the operating-system hostname over mDNS.

If UFW is active, the installer opens TCP 80 and UDP 5353. It does not enable UFW when the firewall is inactive.

## Non-default repository or branch

```bash
sudo env ATHAN_REPOSITORY=owner/fork ./install.sh --branch release-branch
```

The update command respects `ATHAN_REPOSITORY` and `ATHAN_BRANCH` environment variables.

## Quran resources and offline use

The installer verifies the packaged Quran SQLite database against its checked-in SHA-256 manifest before starting the services. Text, translation, transliteration, profiles, and progress do not require internet access at runtime.

Recitation audio downloads on first play from the HTTPS source recorded by QUL and is then served from `/var/lib/athan-hub/quran-cache`. The default cache limit is 5 GB. The admin centre shows cache use and source notices.

During a scheduled Athan, the scheduler publishes the measured playback window under `/run/athan-hub`. Public child pages immediately stop Quran audio, become non-interactive for that window, and never resume audio automatically.

# Rebuilding the ROCK 4SE

How the live device was rebuilt in October 2026 after its SD card failed. Follow this to get from a blank card to athan playing on the Echo.

## What failed, so it does not happen again

- The original SD card silently stopped saving writes on 15 Oct 2026. It still read fine, so the device ran on a frozen, partly blank filesystem. A replacement Canvas Select Plus card died a few minutes after boot when the weekly `fstrim` hung it. Use an endurance-rated card or an eMMC module. The installer masks `fstrim.timer` on `mmcblk` roots.
- The Echo Pop would not keep a Bluetooth pairing with the ROCK, even after the Bluetooth fixes. Prayers now play on the Echo through Home Assistant and Alexa Media Player.
- Keep backups of `/var/lib/athan-hub` and `/var/lib/bluetooth` outside `/tmp` on the machine doing the recovery.

## 1. Flash a fresh image

1. Write the Radxa image `rock-4se_bookworm_kde_r4.output_512.img.xz` to the card.
2. Replace `before.txt` on the card's small `config` partition with `deploy/rock4se/before.txt`, after replacing `RANDOM_PASSWORD_LOCKED_ON_FIRST_BOOT` with any random string. This creates the `athan` user and stops the default `radxa`/`rock` logins being created.
3. Copy the first-boot files into the root partition (on macOS, use `debugfs -w` from e2fsprogs):
   - `deploy/rock4se/athan-firstboot.sh` to `/usr/local/sbin/athan-firstboot.sh` (mode 0755)
   - `deploy/rock4se/athan-firstboot.service` to `/etc/systemd/system/`, enabled through a `multi-user.target.wants` symlink
   - your SSH public key, `deploy/rock4se/90-athan-sudoers` and `deploy/rock4se/99-athan-ssh.conf` to `/usr/local/share/athan/`, with the key named `authorized_keys`
   - optionally, the old `/etc/ssh/ssh_host_*` keys, so SSH clients keep trusting the host

First boot sets up key-only SSH for `athan`, locks its password, and masks the trim timer.

## 2. Install Athan Hub

```sh
curl -fsSL https://raw.githubusercontent.com/oashaikh/athan-hub/dev/install.sh -o install.sh
sudo bash install.sh --branch dev --timezone Europe/London --keep-hostname
sudo athan-hub-doctor
```

Restore `/var/lib/athan-hub` (database, audio, uploads, backgrounds) from the backup before or after the install. The installer keeps existing data.

## 3. Home Assistant and the Echo

1. Run `sudo bash /opt/athan-hub/deploy/setup-home-assistant.sh`.
2. Open `http://<rock>:8123`, create the owner account, then add the Alexa Media Player integration. Use `amazon.co.uk` and the 2FA app key from Amazon's "add authenticator app" page.
3. In Home Assistant, create a long-lived access token (Profile, then Security).
4. Add to `/etc/athan-hub/athan-hub.env`:

```text
ATHAN_HA_URL=http://127.0.0.1:8123
ATHAN_HA_TOKEN=<token>
ATHAN_HA_NOTIFY_SERVICE=alexa_media_hallway_echo_pop
ATHAN_HA_AUDIO_URL=<public Alexa-format MP3 URL>
```

5. Rerun `setup-home-assistant.sh`. It adds the next-prayer sensors, a "Play athan on the Echo" script and an Athan Hub sidebar page. Then run `sudo systemctl restart athan-hub-scheduler`.

The athan MP3 is hosted on the Vercel project `athan-audio` in "Osama Ashaikh's projects". Amazon needs MP3 at 48 kbps and 24 kHz, at most 240 seconds long:

```sh
ffmpeg -i athan.mp3 -map 0:a -map_metadata -1 -ac 2 -codec:a libmp3lame -b:a 48k -ar 24000 alexa-athan.mp3
```

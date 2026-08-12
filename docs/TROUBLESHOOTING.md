# Troubleshooting

Start with:

```bash
sudo athan-hub-doctor
```

## `athan.local` does not resolve

Confirm the client and Athan Hub are on the same LAN, then check:

```bash
systemctl status avahi-daemon
hostname -I
```

Open `http://DEVICE_IP` if the client does not support mDNS.

## Dashboard does not open

```bash
systemctl status nginx athan-hub-api
curl -v http://127.0.0.1:9000/api/health
journalctl -u athan-hub-api -n 100 --no-pager
```

## Bluetooth scan finds nothing

Put the speaker back into pairing mode, keep it nearby, and check:

```bash
rfkill list bluetooth
sudo rfkill unblock bluetooth
bluetoothctl show
sudo athan-pair-speaker --scan
```

Some speakers stop advertising after a short interval. Restart pairing mode immediately before scanning.

## Speaker pairs but audio does not play

```bash
sudo athan-hub-doctor
sudo -u athan env XDG_RUNTIME_DIR=/run/user/$(id -u athan) pactl list short sinks
journalctl -u athan-hub-scheduler -n 100 --no-pager
```

Confirm an MP3 profile is enabled and mapped to the prayer being tested. If the device uses a service account other than `athan`, substitute that account in the command.

If an older Athan profile is shown as disabled after an update, its MP3 duration could not be measured safely. Upload the original recording again from **Admin → Prayer system → Athan audio**.

## Quran text appears but a recitation will not play

The first play must download the selected audio object. Check internet access and the cache:

```bash
curl -I https://audio.qurancdn.com
sudo du -sh /var/lib/athan-hub/quran-cache
journalctl -u athan-hub-api -n 100 --no-pager
```

Try another reciter if the original source is temporarily unavailable. Already cached recordings and all text/progress features remain usable offline.

## Quran playback did not stop for the Athan

Confirm the uploaded Athan has a measured duration and inspect the public state while testing:

```bash
curl http://127.0.0.1:9000/api/playback/status
ls -l /run/athan-hub/athan-active.json
journalctl -u athan-hub-scheduler -n 100 --no-pager
```

The browser polls once per second. Leave the child page open during the test; audio will not resume automatically after the lock clears.

## Recover the dashboard PIN

```bash
sudo sed -n 's/^ATHAN_PIN=//p' /etc/athan-hub/athan-hub.env
```

To disable PIN protection, rerun:

```bash
curl -fsSL https://raw.githubusercontent.com/oashaikh/athan-hub/main/install.sh | sudo bash -s -- --no-pin --keep-hostname
```

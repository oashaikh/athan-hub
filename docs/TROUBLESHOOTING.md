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

## Recover the dashboard PIN

```bash
sudo sed -n 's/^ATHAN_PIN=//p' /etc/athan-hub/athan-hub.env
```

To disable PIN protection, rerun:

```bash
curl -fsSL https://raw.githubusercontent.com/oashaikh/athan-hub/main/install.sh | sudo bash -s -- --no-pin --keep-hostname
```

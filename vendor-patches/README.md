# go2rtc fork for CAM720 (JA-A12) over DTLS

Local patch set against upstream [AlexxIT/go2rtc](https://github.com/AlexxIT/go2rtc)
v1.9.15 (`7c05066`). What this does and why is written up in
[../docs/CAM720.md](../docs/CAM720.md). The TL;DR:

- Adds `pkg/cam720/` (client + producer) and `internal/cam720/` (scheme
  registration) so go2rtc understands
  `cam720://<ip>/<uid>?token=<device_pwd>`.
- Simplifies `pkg/tutk/dtls/auth.go`'s PSK derivation to plain SHA256
  (CAM720 does not truncate at the first NULL byte like Wyze does).
- Pins the DTLS cipher to `TLS_PSK_WITH_AES_128_CBC_SHA256` in
  `pkg/tutk/dtls/dtls.go`, which is the only suite CAM720 advertises.
- Fixes `(*DTLSConn).WriteIOCtrl` in `pkg/tutk/dtls/conn_dtls.go` so it
  writes through the DTLS tunnel instead of the raw UDPConn (the raw path
  needs a dialed socket, which the discovery flow does not give it).
- Adds `(*DTLSConn).WriteIOCtrlStd(ctrlType, body)` for the standard
  Session16 IOCTRL framing CAM720 expects.
- Registers `cam720` beside `wyze` in `main.go`.

## Current state

- DTLS session comes up, `AV LOGIN SUCCESS, two-way: true`.
- `WriteIOCtrlStd(0x1FF, …)` reaches the camera (ACKs seen). The camera
  does not push video frames in response — the exact pattern the Jooan
  firmware wants (resolution/quality/support-stream pre-queries, or a
  vendor IOCtrl like 66338 `GetStreamCtrl`, or a parameter inside
  `SMsgAVIoctrlAVStream` beyond `(channel=0, option=0)`) is still open.
- Backchannel audio is scaffolded (`StartIntercom` sends 0x350 then
  `AVServStart`) but CAM720 does not use the Wyze reverse-DTLS pattern,
  so the right port is to swap `AVSendAudioData` for a Session16-style
  frame on the main channel.

## Rebuild

```sh
cd ~/Downloads/cam720-apk/go2rtc-src/AlexxIT-go2rtc-7c05066
GOOS=linux GOARCH=arm64 go build -ldflags="-s -w" .
```

## Files

```
pkg_cam720_client.go     -> pkg/cam720/client.go
pkg_cam720_producer.go   -> pkg/cam720/producer.go
internal_cam720_cam720.go -> internal/cam720/cam720.go
pkg_tutk_dtls_auth.go    -> pkg/tutk/dtls/auth.go (modified)
pkg_tutk_dtls_dtls.go    -> pkg/tutk/dtls/dtls.go (modified)
pkg_tutk_dtls_conn_dtls.go -> pkg/tutk/dtls/conn_dtls.go (modified)
main.go                   -> main.go (modified: adds cam720 Init)
```

## cmd/mitm — DTLS man-in-the-middle for CAM720

`cmd/mitm/main.go` (shipped here as `cmd_mitm_main.go`) wraps the local build
as a DTLS proxy for reversing the Jooan phone/desktop app's AV protocol.
Deployment lives in [`deploy/cam720-dtls-mitm.sh`](../deploy/cam720-dtls-mitm.sh)
on the Hub: it brings up a dedicated Wi-Fi (`Athan-capture`), redirects UDP
32761 from that subnet to a local DTLS proxy on `10.77.0.1:33000`, and the
proxy terminates with the PSK derived from `device_pwd` on both sides.

Point the phone at Athan-capture, open the camera in CAM720, and the proxy
logs the plaintext of every TUTK AV packet in both directions
(`journalctl -u dtls-mitm`). That's the trace the next session needs to pin
down the exact IPCAM_START payload CAM720 wants.

## Trace discoveries

In session 2026-11-03 we captured the real CAM720 phone-app ↔ camera traffic
on the Hub's isolated Wi-Fi (`Athan-capture`). Both `live.pcap` captures
(not committed; they live in `~/scratchpad/`) confirmed the real protocol:

- **The transport is `TUTK Session16 scramble + DTLS inside`**. The outer
  envelope is 28 bytes starting with `04 02 1d 0b | body-size | seq |
  07 04 21 00 | sid16`, with the first 16 bytes Kalay-scrambled, and the
  DTLS 1.2 record follows at offset 28. Upstream go2rtc's `msgTxData`
  hardcodes version `0x1a` (Wyze) — patched to `0x1d` for CAM720.
- **The handshake uses `TLS_PSK_WITH_AES_128_CBC_SHA256` with EMS**.
  Identity is `AUTHPWD_admin`, PSK is `SHA256(device_pwd)`. Confirmed in
  the ServerHello extensions (`0x0017`).
- **Live-view AV data is sent as DTLS application records (type 23) at
  epoch 1**, 624-byte records (16-byte IV + 608-byte ciphertext).
- `traces/decrypt_cam.py` and `traces/decrypt_ems.py` are the local Python
  decoders that read a `.pcap`, run every UDP payload back through
  `tutk.ReverseTransCode`, extract DTLS records, derive the master
  secret from the known PSK plus the recorded handshake randoms, and
  attempt to decrypt the AV frames. They currently extract correct
  handshake bytes but the EMS-derived keys do not open the application
  records — the PRF implementation needs a cross-check against pion/dtls
  before plaintext can be read. That's the one remaining blocker.

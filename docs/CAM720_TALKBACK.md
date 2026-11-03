# CAM720 (Jooan JA-A12) talk-back: complete firmware trace

Full reverse-engineering of the camera-side talk-back (speaker) path, read
end to end from the extracted firmware binary `jooanipc` (MIPS32, in
`firmware/sqfs2_ex/run/jooanipc`, Ghidra project in the session scratchpad).
Every address and offset below is from decompiled firmware, not inference.

## The one confirmed bug

The app starts talk-back with **IOCtrl `0x351` (849)**, not `0x350` (848).

The IOCtrl→handler dispatch table lives at vaddr `0x93bb98`. Entries are
`{handler_ptr, ioctl_type}`:

| IOCtrl | Handler | Meaning |
|---|---|---|
| `0x350` (848) | `FUN_00427198` | clears `session+0x22` (a different speaker mode) |
| `0x351` (849) | `FUN_0042af54` = `handle_DP_TalkBack_Start` | **talk-back START** |
| `0x352` (850) | `FUN_004273bc` | talk-back STOP (clears `session+0x23`) |
| `0x354` (852) | `FUN_00427408` = `handle_DP_VideoCall_Start` | two-way video call |

Our fork sent 848 for the whole night. Fixed to 849 in
`OpenSpeakerCAM720WithChan` (`pkg/tutk/dtls/conn_dtls.go`). This is the
IOCtrl the standard TUTK header calls `SPEAKERSTOP`, but Jooan's firmware
repurposes the 848/849/850 block as speaker-mode / talk-start / talk-stop.

## The full chain (all firmware addresses)

1. **`handle_DP_TalkBack_Start` (`FUN_0042af54`)**, IOCtrl 849 handler:
   - `session = get_session_by_sid(sid)` (`FUN_00426f20`; 3 static session
     slots at `DAT_0098a82c + {0, 0x180, 0x300}`, each 0x180 bytes, matched
     by SID).
   - Guard: `if (session->iPlayBackStatus (+0x58) == 1)` → refuse, logs
     *"APP is playbacking, you dont speaker"*. `+0x58` is set to 1 **only**
     by `IPC_Media_Enable_playBack` (`FUN_004501a4`) when **SD-card
     playback** is running. Normal live view leaves it 0. So this guard does
     **not** block LAN talk-back during live view. (Ruled out as a blocker.)
   - Otherwise: `session->speakerFlag (+0x23) = 1`,
     `session->speakerCh (+0x2a) = payload[0]`, then call
     `IPC_Media_Switch_Speaker`.

2. **`IPC_Media_Switch_Speaker` (`FUN_0044fb1c`)**:
   - Raw branch logic (from disasm at 0x44fbb8): if `speakerFlag (+0x23) != 0`
     **and** `threadRunning (+0x5c) != 1`, `pthread_create` of
     `IPC_Media_SpeakerThread` (entry `LAB_0044e7ac`), passing the SID.

3. **`IPC_Media_SpeakerThread` (`FUN_0044e7ac`)**:
   - `avIndex = session->avIndex (+0x4)` — **the existing client AV session's
     avIndex**, NOT a new one. (`speakerCh` from the IOCtrl payload is only
     used in log lines, never in the read.) This means talk-back does **not**
     need a second `avClientStart`/IOTC channel — the camera reads our audio
     from the same AV session video+audio flow.
   - Loop: `avRecvAudioData(avIndex, buf[0x500], frameInfoBuf[0x10])`
     (`FUN_0041d150` → `FUN_0061dac8` → vtable `+0x1c`). **frameInfo is 16
     bytes** (confirms audio FRAMEINFO = 16, not the 40 video uses; our
     `n+40` trailer commit was wrong and was reverted to `n+16`).
   - On data: `FUN_0044d194(3, buf, len)`.

4. **`FUN_0044d194`** (receive→speaker): accumulates the received bytes into
   **320-byte (`0x140`) chunks** and calls `SHM_AudioWriteFrame(profile=3,
   chunk, 320)` (`FUN_005bf6b8`, `src/shm_write.cpp`). The received bytes are
   written to shared-memory audio profile 3 **raw** — there is no codec
   decode in this path. The SHM consumer (Ingenic audio-out media process)
   plays profile 3.

5. **Audio hardware**: `AE_engine_init` (`FUN_00485a04`) at boot calls
   `AE_talkback_init(1)` (`FUN_00484be0`) → **16 kHz**, 16-bit PCM, via
   `IMP_AO`. (`AE_talkback_init(0)` would be 8 kHz; the camera uses mode 1.)
   Speaker amp on GPIO 63 (`"SpeakGpio":63` in config).

## Session struct offsets (slot = 0x180 bytes, base `DAT_0098a82c`)

| Offset | Meaning |
|---|---|
| +0x04 | avIndex of the client AV session (talk audio is read here) |
| +0x22 | speaker-mode flag (IOCtrl 848 path) |
| +0x23 | speakerFlag (talk-back on) — set by 849, cleared by 850 |
| +0x2a | speakerCh (payload[0] of IOCtrl 849; log-only) |
| +0x48 | SpeakerThread pthread_t |
| +0x4c | playbackThread pthread_t |
| +0x58 | iPlayBackStatus (1 = SD playback active; the talk-back guard) |
| +0x5c | SpeakerThread running flag |
| +0x60 | SpeakerThread stop signal |

## What is ruled out (by code, not guessing)

- **Wrong IOCtrl** — was 848, must be 849. Fixed.
- **Needs a second AV session / IOTC channel** — no; SpeakerThread reads
  `session+0x4`, the existing session.
- **The `+0x58` playback guard** — only blocks during SD-card playback.
- **Codec decode in the recv path** — none; raw bytes go to SHM profile 3,
  so the camera expects raw 16 kHz 16-bit mono PCM (not G.711 / SPEEX / AAC)
  on the talk-back path.
- **frameInfo size** — 16 bytes (not 40).

## The AVFrame "ODUA" trailer (firmware-confirmed)

The TUTK frame builder `FUN_00627f84` writes the frame trailer as:

```
"ODUA" (0x4155444f, 4 bytes) | frameInfoLen uint32-LE (4) | frameInfo (frameInfoLen)
```

(`puVar6[0] = 0x4155444f; puVar6[1] = param_6; memcpy(puVar6+2, frameInfo, param_6)`.)

go2rtc's `SendFrameData` hardcodes `"ODUA\x20\x00\x00\x00"` — a declared
frameInfo length of **0x20 (32)**, which is the **video** frameInfo size.
`avRecvAudioData` reads a **16-byte** frameInfo, so the **audio** trailer
must declare **0x10 (16)**: `dataSize = n + 8 + 16`, marker
`"ODUA\x10\x00\x00\x00"`, then 16 bytes of frameInfo
(`codecID uint16 | flags byte | ... | timestamp uint32 @ +12`).

Our `SendAudioCAM720` had copied the video's `0x20` length while writing
only 16 bytes — a length/content mismatch the camera cannot parse. Now
fixed to declare `0x10`. This, plus IOCtrl 849 and 16 kHz PCM, is the fully
firmware-grounded configuration. It had never been tested as a whole (848
vs 849, and 0x20 vs 0x10 trailer, were only ever varied one at a time).

## The one remaining unknown (needs the camera's live log)

With IOCtrl fixed to 849 and 16 kHz raw PCM sent, there was still no audible
output. The three remaining possibilities are indistinguishable by static
analysis because they live in the TUTK AV library internals and in runtime
state:

1. Our `SendAudioCAM720` frame is not dequeued as *audio* by the camera's
   `avRecvAudioData` (AVFrame media-type / channel tag mismatch at the TUTK
   AV layer).
2. `IPC_Media_SpeakerThread` never started (e.g. the camera-side session the
   IOCtrl SID resolves to is not the one holding our live avIndex).
3. The SHM audio-out profile-3 pipe expects a different sample rate/width
   than 16 kHz/16-bit.

`IPC_Media_SpeakerThread` logs all of this to `/tmp/message.log` via syslogd:
`"avClientStartEx success avIndex[%d] SID[%d] speakerCh[%d]"` on start,
`"Audio LOST[%d]"` / `"avRecvAudioData ... error"` on bad frames,
`"imediaSpeakerThread_stop==1. Exit"` on stop. Reading that log while we send
a frame resolves all three at once.

### Getting the live log (staged, non-persistent)

The firmware `upgrade.sh` dispatches by file extension; a `.backup` file runs
`backup_cmd.sh` as root. A squashfs with `backup_cmd.sh` = `telnetd -p 2323
-l /bin/sh` is built and on the SD card (`/tmp/jooan_A12_telnet.backup`).
Insert the SD, trigger
`http://192.168.1.144/goform/upgradeFW?userid=admin&userkey=md5(adminpw)&filename=/mnt/sd_card/jooan_A12.backup`,
then `telnet 192.168.1.144 2323` for a root shell →
`tail -f /tmp/message.log` while sending a talk-back frame. Non-persistent
(dies on reboot), nothing is flashed.

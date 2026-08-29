# Speaker Takeover and Settings Save Design

## Goal

Make Athan Hub begin claiming its configured Bluetooth speaker 30 seconds before
an enabled prayer, without playing the athan early, and fix the speaker settings
form so it saves only the settings owned by that screen.

## Constraints

- The speaker may already be connected to a phone. Bluetooth does not provide a
  safe command that lets Athan Hub disconnect that remote phone directly.
- Athan Hub must never delete a Bluetooth bond automatically. Removing a bond
  can make the speaker unusable until it is placed in pairing mode again.
- The athan must start at the timetable time, not during the takeover window.
- Existing exact-time retry and grace-period behaviour must remain available if
  the speaker cannot be claimed before the prayer.
- Pi-hole and the other services on the host must remain uninterrupted.

## Selected approach

Use the existing `pre_connect_seconds` setting as the takeover lead time and set
its default and deployed value to 30 seconds. On each scheduler tick, find the
next enabled, playable prayer. When it enters the lead-time window, run a
connection-only preparation step. That step claims the configured speaker,
waits for its PipeWire sink, selects the sink, and applies the configured volume,
but never starts media playback.

At the timetable time, the existing playback path runs normally. If preparation
succeeded, playback uses the ready connection. If preparation failed because the
phone still owned the speaker, exact-time playback continues retrying within the
configured grace period.

Bluetooth connection operations will be serialized so the scheduler, admin
Connect button, and test playback cannot issue overlapping `bluetoothctl connect`
commands. A timed-out command will be followed by state polling before another
command is launched, avoiding the observed `Operation already in progress`
failure loop.

## Alternatives considered

### Keep the speaker connected continuously

This would reduce prayer-time connection risk but would prevent normal household
phone use of the speaker throughout the day. It does not match the requested
prayer-time takeover behaviour.

### Remove and recreate the Bluetooth bond after a failed takeover

This can recover a stale local bond only while the speaker is in pairing mode.
Doing it automatically is destructive and can leave the speaker unavailable, so
it is explicitly excluded.

## Scheduler behaviour

For each enabled prayer with an audio mapping and a configured speaker:

1. Before the lead window, only report the next prayer.
2. From T-30 seconds to T-1 second, prepare the speaker once per scheduler
   process for that prayer occurrence.
3. If preparation succeeds, leave the connection ready and wait.
4. At T, play the mapped athan and preserve existing playback-state locking,
   duration handling, audit logging, and post-play connection preference.
5. If preparation fails, record a concise warning and allow normal due-time
   retries; do not mark the prayer as played.
6. A scheduler restart during the window may prepare again. Connection
   preparation is idempotent, and serialization prevents overlap.

The occurrence key is the timetable date, prayer name, and effective HH:MM time.
This avoids suppressing a manual override or a later prayer while preventing a
successful preparation from being repeated every ten seconds.

## Settings API and interface

The settings endpoint retains `extra="forbid"` validation. The combined admin
page currently loads the full settings document, including Quran cache and
leaderboard keys, then sends that whole reactive object to `/api/settings`.
Those Quran settings belong to dedicated admin endpoints and are therefore
correctly rejected by the general settings schema.

The fix is to build an explicit payload for the general/speaker endpoint:

- `timezone`
- `grace_seconds`
- `echo_mac`
- `pre_connect_seconds`
- `connect_retry_seconds`
- `sink_volume_percent`
- `disconnect_after_play`
- `dashboard_background`

This preserves strict backend validation and prevents future settings added to
the GET response from leaking into unrelated update calls. The label and help
text will describe `pre_connect_seconds` as the number of seconds before prayer
when speaker takeover begins. The deployed value will be 30.

Validation error notifications will extract a short field-specific message from
FastAPI's structured `detail` array instead of rendering the entire JSON payload
over the mobile screen.

## Failure handling and observability

- A failed early takeover produces an audit/log warning with the prayer and
  failure reason, but does not block exact-time playback.
- A successful early takeover produces one preparation audit entry for that
  occurrence.
- Connection locking has a bounded wait and cannot deadlock the scheduler.
- Pairing and bond removal remain manual admin actions.
- No Wi-Fi, DNS, Pi-hole, timetable, or audio files are modified by this change.

## Verification

Automated coverage will include:

- no preparation before the 30-second window;
- connection-only preparation inside the window;
- no early media playback;
- one successful preparation per prayer occurrence;
- due-time playback still runs after preparation failure;
- connection attempts are serialized and a pending attempt is polled;
- the admin speaker/general save payload excludes Quran and leaderboard keys;
- structured validation errors render as a concise message;
- existing backend and frontend test suites and production builds continue to
  pass.

After deployment, verify on `athan.local` that the configured speaker begins
connecting 30 seconds before a temporary prayer-time override, the athan begins
at the exact override time, the settings form saves successfully on mobile, and
Pi-hole remains active.

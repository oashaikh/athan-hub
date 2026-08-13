# Quran memorisation and child-safe administration design

**Status:** Approved design  
**Date:** 2026-08-12  
**Application:** Athan Hub  
**Primary data source:** [Quranic Universal Library (QUL)](https://github.com/TarteelAI/quranic-universal-library)

## Purpose

Athan Hub will become a child-safe household prayer and Quran memorisation application while preserving its existing scheduled Athan behaviour.

The public experience will let children:

- View the current prayer dashboard without changing prayer-system settings.
- Select an existing child profile.
- Practise any surah and verse range.
- Choose any recitation available in the pinned QUL catalogue.
- Listen, repeat, hide and reveal text, and record memorisation progress.
- Earn personal rewards and optionally participate in a sibling leaderboard.

The PIN-protected `/admin` experience will be the only place that can:

- Create, rename, archive, restore, or permanently delete profiles.
- Correct a child's progress.
- Configure rewards and leaderboard visibility.
- Manage Quran audio downloads and cache limits.
- Change the timetable, Athan audio, Bluetooth speaker, exclusions, background, or system settings.

## Scope boundaries

This release provides listen-and-repeat memorisation with self-recorded progress. It does not provide microphone capture, speech recognition, tajweed grading, or automatic mistake detection.

Quran playback runs in the child's browser. Scheduled Athan playback continues through the server's configured Bluetooth sink. These audio paths remain separate except that an active Athan always stops and locks the child experience.

The existing Vue, Vite, Bulma, FastAPI, SQLAlchemy, SQLite, nginx, systemd, and installer stack remains in place. The implementation will not run the QUL Rails CMS, introduce a second frontend framework, or add a queue, Redis, or a separate authentication system.

## Approved visual direction

### Child prayer dashboard

The existing full-width cinematic dashboard remains the public home at `/`. It retains:

- The current and next prayer presentation.
- The live countdown.
- The solar arc and time-of-day ambience.
- The six prayer cards.
- The current background image.

A compact top navigation adds `Prayer times` and `Quran practice`. The active child profile appears at the right. A small lock icon links to `/admin`; it does not expose any settings.

### Quran practice workspace

`/quran` is a dedicated desktop workspace rather than a card added to the prayer dashboard. It contains:

- A searchable surah list.
- A central Arabic verse reader with optional translation.
- Previous and next verse controls.
- Recitation playback and repetition progress.
- A practice setup panel for reciter, verse range, repetition count, text visibility, and playback speed.
- Current-range mastery progress.
- The same prayer/Quran navigation and profile selector as `/`.

The approved desktop composition adapts to tablet and mobile without changing the information hierarchy. Mobile uses a compact header, a slide-over surah picker, a full-width reader, and a collapsible practice panel.

### Admin control centre

`/admin` first displays a dedicated six-digit PIN gate. A valid PIN opens a desktop control centre with these sections:

- Overview
- Child profiles
- Timetable
- Bluetooth and speaker
- Activity
- Exclusions
- Athan audio
- General
- Quran downloads and cache
- Quran sources and licences

The admin sidebar includes a clear return to the child dashboard. Existing settings content is reused inside the new admin shell rather than rewritten.

## Routes and access boundaries

### Frontend routes

| Route | Access | Purpose |
| --- | --- | --- |
| `/` | Public LAN | Read-only prayer dashboard |
| `/quran` | Public LAN | Quran memorisation workspace |
| `/admin` | PIN required | Admin overview |
| `/admin/profiles` | PIN required | Profile administration |
| `/admin/timetable` | PIN required | Timetable import and overrides |
| `/admin/bluetooth` | PIN required | Speaker pairing and testing |
| `/admin/activity` | PIN required | Audit history |
| `/admin/exclusions` | PIN required | Prayer exclusions |
| `/admin/audio` | PIN required | Athan audio uploads and mappings |
| `/admin/quran-cache` | PIN required | Quran audio cache and provenance |
| `/admin/general` | PIN required | General settings and background |

The legacy `/settings` route redirects to `/admin/timetable` so old bookmarks do not break.

### Server enforcement

The current PIN cookie and HMAC token mechanism remains. Protection moves from an all-or-nothing host gate to explicit route classification:

- Public read endpoints stay available without a PIN.
- Practice-only writes are limited to progress and preferences for existing active profiles.
- All `/api/admin/*` endpoints require a valid PIN cookie.
- Existing settings, uploads, timetable mutations, Bluetooth commands, exclusions, logs, and audio mutations require a valid PIN cookie regardless of frontend route.
- Full settings are no longer returned publicly. The dashboard receives only a small public display configuration containing timezone and background name.

Hiding a menu is not considered authorization. Direct unauthenticated requests to protected endpoints must return `401 PIN_REQUIRED`.

## Child profiles

Only an administrator can create or manage profiles. Children may freely switch between existing active profiles from `/` or `/quran` without a PIN.

Each profile stores:

- Name and stable slug.
- Optional gender value: boy, girl, or unset.
- Assigned theme.
- Preferred QUL recitation.
- Last surah and verse range.
- Repetition count and playback speed.
- Arabic, translation, transliteration, and recall visibility preferences.
- Per-verse learning state.
- Practice sessions, time, repetitions, stars, badges, and streak.
- Active or archived state.

The most recently selected profile is stored locally in the browser for convenience. The server remains authoritative for profile state and progress.

Archiving is the default removal action because it preserves progress. Permanent deletion is available only in admin after an explicit confirmation and removes the profile's progress, sessions, rewards, and preferences in one transaction.

## Memorisation session

1. The child selects an existing profile.
2. The child searches for and selects a surah.
3. The child chooses a verse range.
4. The child selects any QUL recitation.
5. The child chooses 1, 3, 5, or 10 repetitions and a playback speed.
6. The child chooses Arabic, English translation, transliteration, or recall mode.
7. Playback repeats each selected verse before advancing.
8. The child marks verses as `learning`, `needs_practice`, or `memorised`.
9. Progress and preferences save after every completed repetition and status change.
10. The next visit resumes at the saved surah, range, reciter, and display state.

Recall mode hides Arabic after the configured listening repetitions. The child can reveal the verse without changing progress. Playback never marks a verse memorised automatically.

## Quran resources

### Packaged data

A generated, read-only SQLite resource database ships with Athan Hub. It contains:

- QUL QPC Hafs ayah-by-ayah script resource 86.
- Quran structural metadata for 114 surahs and 6,236 ayahs.
- QUL Saheeh International English translation resource 20.
- QUL English ayah transliteration resource 72, including its source and licence notice.
- The complete QUL recitation catalogue and capability metadata.
- Source URLs, source names, attribution text, licence text, QUL upstream commit SHA, import timestamp, schema version, and file checksums.

The resource database is separate from the writable Athan Hub application database. Upgrading packaged Quran data cannot overwrite household profiles or progress.

Arabic and interface fonts are bundled locally. The public reader has no runtime font or text dependency on QUL.

### Recitation capabilities

Every recitation in the pinned QUL catalogue is selectable and labelled by what it supports:

- `ayah`: one audio object per verse; exact verse and range repetition.
- `segmented_surah`: one surah object with verse timestamps; exact verse and range repetition.
- `surah`: whole-surah playback only when verse timing is unavailable.
- `muallim`: highlighted as recommended for memorisation.
- `kids_repeat`: highlighted as recommended for younger children.

The interface explains capability limits before practice starts. It does not pretend a whole-surah recording can perform exact verse looping.

## Quran audio cache

Recitation audio is not committed to the Athan Hub repository or bundled in the installer.

The backend downloads an audio object the first time it is requested, verifies it, writes it atomically, and serves the local file. Later requests reuse the cached file.

Download rules:

- Only HTTPS URLs from source hosts present in the checked-in resource manifest are accepted.
- Redirects are revalidated against the same allowlist.
- Content type and file signature must indicate supported audio.
- Per-object and total-cache size limits are enforced.
- A failed or partial download cannot replace an existing valid file.
- Cache metadata records source URL, byte count, checksum, created time, and last access time.
- Concurrent requests for the same object share a filesystem lock and produce one file.
- The default cache limit is 5 GB and is configurable in admin.
- Least-recently-used objects are eligible for eviction; currently playing and admin-pinned objects are not.

Admin can view cache size by reciter, pre-download a reciter or surah, pin favourites, remove cached objects, retry failures, and view the associated source notice.

If internet is unavailable and the requested object is not cached, the child sees a retryable message. Text, progress, and cached recordings continue to work.

## Scheduled Athan pre-emption

The scheduler measures and stores each uploaded Athan MP3's duration. The pure-Python `mutagen` package is the only new backend dependency required for reliable MP3 duration metadata.

`audio_profiles.duration_seconds` stores the measured value. New uploads are rejected when their duration cannot be read. The database migration backfills existing profiles; a legacy file that cannot be measured is disabled and surfaced in admin rather than scheduled with an unsafe guessed duration.

Immediately before `mpg123` begins prayer playback, the scheduler atomically writes `/run/athan-hub/athan-active.json` with:

- Prayer name.
- Playback start time.
- Audio profile ID.
- Measured duration.
- Expected finish time.

The file is removed when the playback process exits. A stale file expires after its expected finish plus the existing playback grace window.

`GET /api/playback/status` exposes the safe public state. Child pages poll once per second. When active playback is detected, the frontend:

- Pauses Quran audio.
- Clears the audio source so it cannot continue in the background.
- Sets the public application content to `inert`.
- Displays a full-page accessible overlay with prayer name and remaining time.
- Blocks pointer, touch, keyboard, profile switching, navigation, and practice updates.

The child page unlocks only after the expected duration has elapsed and the runtime state file is gone or stale. Quran audio does not resume automatically. Admin pages remain available for diagnostics and recovery.

## Rewards and leaderboard

Rewards encourage consistency without punishing missed days.

### Personal rewards

- Ten stars for the first completed practice session of a day.
- Twenty-five stars at 10 memorised ayahs, 100 at 50, and 250 at 100.
- One star per ayah the first time every verse in a surah is memorised.
- After that completion, changing an ayah away from memorised subtracts its star; marking it memorised again restores the star.
- Individual ayahs and repetitions update progress but never award stars.
- Practice streaks count distinct local calendar days with a completed session.
- Ending a streak never removes stars, badges, or mastered progress.

Initial badges cover:

- First practice session.
- Three-, seven-, and thirty-day streaks.
- Ten, fifty, and one hundred memorised ayahs.
- First completed surah.
- One, five, and ten cumulative practice hours.

Reward events use unique semantic keys such as `memorised-milestone:PROFILE:THRESHOLD`. Repeated requests, retries, status toggling, or session updates cannot award the same one-time reward twice.

### Optional sibling leaderboard

Admin can enable or disable the leaderboard. It is disabled by default on new installations.

When enabled, the child experience shows weekly stars for active profiles. Admin can include or exclude these categories:

- Daily practice.
- Memorisation milestones.
- Completed surahs.

Personal progress remains available whether or not the leaderboard is enabled.

## Themes

Gender chooses an initial theme only. It does not change content, expectations, rewards, difficulty, or permissions. Admin can assign any theme to any profile.

Approved themes:

- `night_explorer`: default for boy profiles; deep navy, emerald, and warm gold with celestial reward motifs.
- `garden_light`: default for girl profiles; plum, muted rose, botanical green, and warm gold with garden reward motifs.
- `classic_mushaf`: default when gender is unset; parchment, green, and antique gold.

All themes use the same semantic components, accessible contrast targets, visible focus states, reduced-motion behaviour, and layout. Theme choice changes tokens and decorative motifs, not markup or logic.

## Persistence model

The existing application SQLite database gains these focused tables:

### `child_profiles`

Profile identity, active state, gender, theme, preferred recitation, last practice selection, playback preferences, text visibility preferences, and timestamps.

### `quran_progress`

One row per profile and verse key with learning state, completed repetitions, first/last practice timestamps, and first memorised timestamp. A unique constraint on `(profile_id, verse_key)` prevents duplicate progress rows.

### `quran_sessions`

Session start/end, profile, surah, verse range, recitation, repetitions, practice seconds, completion state, and points awarded.

### `reward_events`

Append-only reward ledger with profile, semantic event key, category, points, and timestamp. A unique constraint on the semantic key makes reward calculation idempotent.

### `profile_badges`

Profile, badge key, and award timestamp with a unique constraint on `(profile_id, badge_key)`.

### `quran_audio_cache`

Recitation and verse/surah identity, local path, source URL, size, checksum, pin state, created time, and last access time.

Foreign keys cascade only for a confirmed permanent profile deletion. Archive does not delete related rows.

## API shape

### Public and practice endpoints

- `GET /api/public/config`
- `GET /api/playback/status`
- Existing read-only timetable day and next-prayer endpoints
- `GET /api/quran/profiles`
- `GET /api/quran/profiles/{profile_id}/state`
- `PUT /api/quran/profiles/{profile_id}/state`
- `GET /api/quran/surahs`
- `GET /api/quran/surahs/{surah_id}/verses`
- `GET /api/quran/recitations`
- `GET /api/quran/audio/{recitation_id}/{verse_key}`
- `POST /api/quran/profiles/{profile_id}/sessions`
- `PUT /api/quran/profiles/{profile_id}/sessions/{session_id}`
- `PUT /api/quran/profiles/{profile_id}/verses/{verse_key}`
- `GET /api/quran/leaderboard`

Practice payloads use typed schemas and reject profile identity, name, gender, theme assignment, active state, reward totals, and any prayer-system setting.

### Admin endpoints

- `GET /api/admin/profiles`
- `POST /api/admin/profiles`
- `PUT /api/admin/profiles/{profile_id}`
- `POST /api/admin/profiles/{profile_id}/archive`
- `POST /api/admin/profiles/{profile_id}/restore`
- `DELETE /api/admin/profiles/{profile_id}`
- `PUT /api/admin/profiles/{profile_id}/progress/{verse_key}`
- `GET /api/admin/quran/settings`
- `PUT /api/admin/quran/settings`
- `GET /api/admin/quran/cache`
- `POST /api/admin/quran/cache/prefetch`
- `DELETE /api/admin/quran/cache/{cache_id}`

Existing system endpoint paths remain stable but receive server-side PIN enforcement for protected reads and every mutation.

## QUL fork and provenance

A public fork will be created at `https://github.com/oashaikh/quranic-universal-library`.

The fork receives a GitHub Actions workflow that:

- Runs daily and on manual dispatch.
- Uses GitHub's merge-upstream API with the repository-scoped `GITHUB_TOKEN`.
- Requests only `contents: write` and `issues: write` permissions.
- Synchronises the upstream default branch into the fork.
- Creates or updates a visible issue if automatic synchronisation fails.
- Contains no personal access token or repository secret.

The fork is preservation infrastructure, not Athan Hub's live runtime API. Athan Hub updates its pinned resource snapshot only through an explicit import command and reviewed commit. This prevents an upstream schema or content change from silently affecting installed devices.

## Licensing and attribution

QUL application code is MIT licensed, but QUL states that many resources are community-created and may have dataset-specific terms. Athan Hub therefore:

- Preserves QUL's MIT notice for reused code or tooling.
- Includes source and licence metadata for every packaged dataset and cached recording.
- Displays a sources and licences page in admin.
- Includes required notices in `NOTICE` and the installed documentation.
- Does not claim QUL, Tarteel, reciters, Quran.com, EveryAyah, QuranicAudio, Tanzil, King Fahd Quran Printing Complex, or translation contributors endorse Athan Hub.
- Does not package a dataset until its specific redistribution terms have been recorded and satisfied.

## Installer, update, backup, and recovery

- The one-shot installer creates the Quran audio cache directory and runtime state path with the existing service user ownership.
- Database creation remains idempotent through SQLAlchemy migrations.
- Existing installations receive new tables and nullable audio-duration fields without replacing prayer data, settings, MP3s, profiles, or history.
- The packaged Quran resource database is versioned with the application and replaced atomically during update.
- The writable application database includes profiles, progress, rewards, and Quran settings and remains part of normal backups.
- Downloaded Quran audio is excluded from backups by default because it is reproducible and may be large.
- The doctor command checks the resource database, cache permissions, duration metadata, runtime state path, and free storage.
- Uninstall without `--purge` preserves profiles and progress; purge removes them after the existing explicit confirmation path.

## Error handling

- Missing timetable data keeps the existing empty state and does not block Quran practice.
- Missing or corrupt Quran resources disable practice with a direct admin diagnostic message.
- Invalid profile IDs return `404`; archived profiles cannot start sessions.
- Invalid verse ranges, repetition counts, statuses, or recitation IDs return typed `400` responses.
- Uncached offline audio returns a retryable `503` without changing progress.
- Cache quota errors return `507` and point admin to cache management.
- Download timeouts and checksum failures leave existing cache entries untouched.
- Athan status polling failure defaults to safe Quran playback pause only when a previously active Athan has not yet reached its stale deadline.
- A stale runtime state cannot lock the child interface indefinitely.
- Admin PIN failures do not reveal whether a profile or protected resource exists.

## Testing and verification

### Backend

- Public prayer and Quran reads work without a PIN.
- Every protected existing and new endpoint rejects an invalid or absent PIN.
- Practice endpoints cannot mutate admin-owned profile fields.
- Profile create, archive, restore, delete, and progress correction behave transactionally.
- Progress remains isolated between profiles.
- Session and reward updates are idempotent under retries.
- Streaks use the configured local timezone.
- Leaderboard category and visibility settings are enforced.
- Reciter capability mapping covers ayah, segmented-surah, whole-surah, Muallim, and kids-repeat resources.
- Cache allowlisting, redirects, size limits, atomic writes, locking, eviction, and offline failures are covered.
- Audio duration metadata and runtime Athan state expiry are covered.
- Existing timetable, audio, scheduler, and Bluetooth tests remain green.

### Frontend

- Child navigation exposes no settings controls.
- Profile switching preserves independent state.
- Desktop, tablet, and mobile prayer and practice views render correctly.
- Keyboard navigation, focus states, screen-reader labels, reduced motion, and contrast are verified.
- Athan activation stops audio, locks all child interaction, announces status, and never auto-resumes.
- Offline, loading, empty, unavailable-reciter, cache-full, and server-error states render inline.
- Themes change only visual tokens and remain accessible.
- Admin route and protected API failures show the PIN gate.

### Installer and live device

- Fresh install on a clean supported Ubuntu/Debian environment.
- Upgrade from the current production database without data loss.
- Re-run installer idempotently.
- Verify API and scheduler services, nginx routing, mDNS, and cache permissions.
- Create multiple profiles and prove that children cannot create profiles.
- Exercise at least one ayah, one segmented-surah, and one whole-surah reciter.
- Disconnect internet and verify text, progress, and cached audio.
- Trigger a scheduled Athan while Quran audio is playing and verify stop, lock, countdown, unlock, and no auto-resume.
- Verify the paired speaker and scheduled Athan still work after the integration.
- Verify the QUL fork exists publicly and its manual upstream-sync workflow succeeds.

## Acceptance criteria

The feature is complete only when all of the following are true:

1. `/` is a read-only child prayer dashboard and `/quran` is a child memorisation workspace.
2. Children can switch existing profiles but cannot create or administer them.
3. `/admin` and all protected APIs require the existing PIN.
4. Each profile has independent reciter, practice preferences, progress, rewards, badges, and streak.
5. Every pinned QUL recitation is selectable with truthful capability labels.
6. Quran text and metadata work offline; audio is cached locally on demand.
7. The approved three-theme system works and admin can override the gender default.
8. Personal rewards work and the sibling leaderboard can be enabled or disabled by admin.
9. An active Athan stops Quran audio and blocks every child interaction for the measured playback duration without auto-resuming.
10. Existing scheduled Athan, Bluetooth, timetable, exclusions, and audio functionality remains operational.
11. The public QUL fork exists under `oashaikh`, synchronises from upstream, and contains no secret.
12. Source commit, checksums, attribution, and dataset-specific licence notices are recorded.
13. Fresh install, upgrade, backup, doctor, and uninstall paths account for the new data safely.
14. Automated tests and live `athan.local` verification prove the behaviours above.

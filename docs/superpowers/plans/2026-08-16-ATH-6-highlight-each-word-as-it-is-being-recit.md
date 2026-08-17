# ATH-6: Highlight each word as it is being recited

> Machine-generated plan (model `sonnet`, effort `high`) for
> http://oashaikh.local:9999/local-development/projects/181b85cd-639e-4e1c-be36-ca3b24b87f8b/issues/490528c1-0e33-44dd-816d-2065b73859e9. Progress below is written by the orchestrator; the
> database copy is authoritative — editing this file does not change execution.

## Assumptions

- Word boundaries are approximated by whitespace-splitting the stored Uthmani `arabic` text field; the packaged SQLite schema (backend/src/athan_hub/core/quran_resources.py) has no per-word ID/segmentation data.
- The currently implemented QUL segment endpoint (backend/src/athan_hub/services/quran_cache_service.py, test fixtures in backend/tests/test_quran_cache.py) only returns verse-level time_from/time_to, not verified per-word timestamps, so exact audio-synced word timing is not achievable without a backend/data contract change.
- No network access was available during planning to confirm whether the live (non-mocked) QUL surah_segments response nests per-word timing; the plan intentionally does not depend on that being true.

## Out of scope

- True audio-verified per-word timestamps (would require a new backend data contract, not established in this codebase today)
- Word highlighting for 'surah' whole-recording recitations (verse boundaries unknown, same restriction the existing verse-highlight already has)
- Any change to backend quran_cache_service.py or quran_routes.py

## Tasks

- [x] **Task 1: Emit per-word playback progress from QuranPlayer**
  - Intent: Add a new `word-progress` emit ({verseKey, fraction}) computed purely from data QuranPlayer already has (audio.currentTime/duration for 'ayah'; segmentMap time_from/time_to for 'segmented_surah'), emitting null for 'surah' capability and whenever paused/ended, mirroring the existing verse-highlight null-on-pause pattern.
  - Files: `frontend/src/components/QuranPlayer.vue`, `frontend/src/components/__tests__/QuranPlayer.test.ts`
  - [x] Triggering timeupdate on a mocked 'ayah' recitation with overridden currentTime/duration emits word-progress with the expected fraction
  - [x] Triggering timeupdate on a mocked 'segmented_surah' recitation inside a segment window emits the expected fraction using the same time_from/time_to already loaded for auto-advance
  - [x] 'surah' capability never emits a non-null word-progress (matches existing verse-highlight restriction)
  - [x] Pausing emits word-progress null, same as the existing verse-highlight pause test
  - [x] npm --prefix frontend test passes including existing QuranPlayer tests
  - [x] No backend files touched, no new dependency added
  - Risk: jsdom's HTMLMediaElement.duration/currentTime are getter-only in real browsers; tests must override them per element instance the same way frontend/src/test/setup.ts already stubs play/pause/load. Guard divide-by-zero when duration or segment span is 0.
  - Commit: (none — no code change for this task)

- [x] **Task 2: Highlight the active word inside the rendered Arabic verse** (after 1)
  - Intent: Consume @word-progress in QuranPractice.vue, split each verse's arabic field on whitespace into words, render them as spans, and mark the word at floor(fraction * words.length) active (clamped) only for the verse currently matching .verse.playing, using the existing --quran-accent theme color.
  - Files: `frontend/src/pages/QuranPractice.vue`, `frontend/src/components/__tests__/QuranPractice.test.ts`, `frontend/src/styles/bulma.scss`
  - [x] New test with a multi-word Arabic verse fixture: play + timeupdate marks the expected word span active and a different word is not active
  - [x] word-progress null (e.g. on pause) removes the active-word class from every word
  - [x] Existing 'scrolls the ayah being recited' test still passes unmodified
  - [x] Verses that are not the currently playing one never render an active word
  - [x] npm --prefix frontend test and npm --prefix frontend run build both succeed
  - Risk: Mark the fraction-based word estimate with a `ponytail:` comment noting it's a linear-interpolation approximation (real word durations vary), not a true per-word audio timestamp, since the committed segment contract only exposes verse-level time_from/time_to today.
  - Commit: `c0017c03d322`

- [ ] **Task 3: Rebuild and commit the synchronized frontend production bundle** (after 1, 2)
  - Intent: Repository convention requires frontend/dist stay in sync with frontend/src since the deployed appliance has no Node.js build step at runtime; regenerate it after the word-highlight UI change lands.
  - Files: `frontend/dist/**`
  - [ ] npm --prefix frontend run build produces a dist reflecting tasks 1-2, committed alongside the src change
  - [ ] dist diff contains only output affected by this feature (no unrelated churn)
  - [ ] backend/venv/bin/python -m pytest backend/tests, npm --prefix frontend test, and the shellcheck lint remain green

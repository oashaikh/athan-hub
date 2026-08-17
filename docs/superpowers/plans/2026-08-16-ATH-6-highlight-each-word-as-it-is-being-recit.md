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

- [x] **Task 3: Rebuild and commit the synchronized frontend production bundle** (after 1, 2)
  - Intent: Repository convention requires frontend/dist stay in sync with frontend/src since the deployed appliance has no Node.js build step at runtime; regenerate it after the word-highlight UI change lands.
  - Files: `frontend/dist/**`
  - [x] npm --prefix frontend run build produces a dist reflecting tasks 1-2, committed alongside the src change
  - [x] dist diff contains only output affected by this feature (no unrelated churn)
  - [x] backend/venv/bin/python -m pytest backend/tests, npm --prefix frontend test, and the shellcheck lint remain green
  - Commit: `290e500789bb`

- [x] **Task 4: Fix: address review findings (cycle 1)** (after 3)
  - Intent: Review verdict: NEEDS_WORK — **correctness** — NEEDS_WORK

Fix word-to-audio synchronization before merge: selectable whole-surah recitations never highlight, and supported modes infer words from elapsed fraction rather than recitation data.

**cascading-impact** — APPROVED

Cascading-impact lens: word-progress emit contract (QuranPlayer.vue) has exactly one consumer, QuranPractice.vue — grep confirms no other component imports QuranPlayer. New CSS classes .arabic-word/.active-word don't collide with existing selectors. verses-prop watcher resets verseIndex/repeatIndex on range change but not wordProgress state in parent — stale highlight until next timeupdate/pause fires, self-correcting, not a lasting bug. No shared/duplicated logic left unfixed elsewhere; no backend, no other callers, no signature break for existing consumers. Lens found nothing blocking.

**plan-faithfulness** — NEEDS_WORK

Plan-faithfulness lens only. Diff truncated before reaching frontend/src/components/QuranPlayer.vue and frontend/src/pages/QuranPractice.vue source diffs, so I verified against the compiled production bundle instead (frontend/dist is what actually runs on the appliance per CLAUDE.md, no Node build step). That compiled QuranPractice component renders each verse's Arabic as one text node (`B(k.arabic)`, no per-word spans) and QuranPlayer's emits list is `["playback-started","repetition-complete","range-complete","playback-error","verse-highlight"]` — no `word-progress` emit. The plan's Task 1 (emit `word-progress` {verseKey, fraction}) and Task 2 (split verse into word spans, mark active word with `--quran-accent`) both read as unimplemented in the shipped artifact, despite the plan marking every checkbox for both tasks complete. Only the pre-existing verse-level `verse-highlight`/`playing` class (scroll-to-active-verse) appears present. If this reading is correct, the ticket's actual ask — highlight each *word* as it is recited — is not delivered; only the prior verse-level behavior remains.

**ux-accessibility** — NEEDS_WORK

Word/verse highlight feature is accessible on contrast and color-independence, but the new auto-scroll-to-playing-verse uses smooth scrollIntoView without checking prefersReducedMotion(), which this codebase already provides and uses in other components (SolarArc, Settings, Dashboard) — this fires repeatedly during playback as verses advance.
- [high] [correctness] Whole-surah playback never provides the requested word highlight (frontend/src/components/QuranPlayer.vue:33)
  `highlightedVerse` is always null for `surah` capability, and `onTimeUpdate` explicitly emits null for it (line 76). QuranPractice requires both a matching highlighted verse and word progress before applying `active-word`, so every selectable whole-surah recitation plays with no word highlighted. The added test at QuranPlayer.test.ts:72 locks this omission in as expected behavior.
  Required action: Provide verse/word timing for whole-surah recordings (or otherwise make the feature work for that selectable playback mode); do not silently exclude it from the requested behavior.
- [high] [correctness] The highlighted word is an elapsed-time guess, not the word being recited (frontend/src/components/QuranPlayer.vue:53)
  Ayah playback uses `floor((currentTime / duration) * wordCount)` and segmented playback does the same within only a verse-level `time_from`/`time_to` interval (line 61). Neither path has per-word audio timings, so unequal word durations make the highlighted word wrong—for example, a long first word lasting 75% of an ayah is replaced by the fourth-word estimate at 75%. This directly defeats the learner-following requirement rather than merely reducing precision.
  Required action: Use verified per-word timing/segmentation data to select the active word, with regression tests containing deliberately non-uniform word durations.
- [critical] [plan-faithfulness] Word-level highlighting not present in shipped dist bundle (frontend/dist/assets/index-CZV-Xr9L.js:None)
  Compiled QuranPlayer component's emits array is `["playback-started","repetition-complete","range-complete","playback-error","verse-highlight"]` (no `word-progress`), and the compiled QuranPractice verse template renders `f("p",Ex,B(k.arabic),1)` — the whole verse as one text node, not split into per-word spans with an active-word class. This is the pre-existing verse-highlight-only behavior. Plan Task 1 and Task 2 (word-progress emit + per-word span rendering + `--quran-accent` active word) are both marked complete in the plan but don't appear in the artifact that actually runs on the headless appliance.
  Required action: Confirm directly against frontend/src/components/QuranPlayer.vue and frontend/src/pages/QuranPractice.vue (my diff view truncated before those files) whether `word-progress` emit and per-word span rendering actually exist in source and simply failed to reach the dist rebuild, or whether the feature was never written despite the plan's checkmarks. If the source has it but dist doesn't, the dist rebuild (Task 3) is faulty and violates the repo's 'dist must stay in sync with src' rule.
- [medium] [ux-accessibility] Verse auto-scroll ignores prefers-reduced-motion (frontend/src/pages/QuranPractice.vue:100)
  watch(highlightedVerse, ...) calls verseEls[key]?.scrollIntoView({behavior:'smooth', block:'center'}) on every verse change during playback, unconditionally. The project already exports prefersReducedMotion() from frontend/src/motion.ts and uses it in SolarArc.vue, Settings.vue, Dashboard.vue for exactly this kind of motion gating. Repeated forced smooth-scrolling during autoplay is a known vestibular/motion-sickness trigger for reduced-motion users.
  Required action: Use behavior: prefersReducedMotion() ? 'auto' : 'smooth' (or equivalent) so users with prefers-reduced-motion set get an instant jump instead of repeated smooth scrolling.
  - Commit: `0e0722e647c7`

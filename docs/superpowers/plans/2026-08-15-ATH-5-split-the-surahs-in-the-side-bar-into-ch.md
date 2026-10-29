# ATH-5: Split the surahs in the side bar into chapters

> Machine-generated plan (model `sonnet`, effort `high`) for
> http://oashaikh.local:9999/local-development/projects/181b85cd-639e-4e1c-be36-ca3b24b87f8b/issues/5c44fa25-0d98-46a2-b984-d5bef829af14. Progress below is written by the orchestrator; the
> database copy is authoritative — editing this file does not change execution.

## Assumptions

- The ticket title's 'chapters' is interpreted as the traditional 30-Juz (Para) grouping of the sidebar surah list, since that is the only chapter-like grouping the existing data (backend/src/athan_hub/core/quran_resources.py surahs table) can support without a schema/data change, and it's the standard convention in Quran memorisation apps. If the requester actually meant something else (e.g. Meccan/Medinan split, alphabetical sections), that needs new data not currently packaged in resources/quran/quran.sqlite.
- A surah that spans multiple Juz is grouped once, under the Juz in which it begins — matching how other Quran apps group a surah-list view.

## Out of scope

- Backend/API changes — no new endpoint or DB column needed for Juz-start grouping
- Meccan/Medinan revelation-place grouping (data not available)
- Any change to verse reading, playback, mastery tracking, or practice-panel behaviour
- Collapsible/expandable Juz sections (plain grouped headers only, unless the user asks for more)

## Tasks

- [x] **Task 1: Add Juz grouping helper module with self-test**
  - Intent: Sidebar currently renders all 114 surahs as one flat button list in `.surah-rail nav` (frontend/src/pages/QuranPractice.vue:12-16). 'Chapters' here means the standard 30-Juz (Para) division used by Quran apps — the only grouping scheme the data actually supports, since backend/src/athan_hub/core/quran_resources.py's `surahs` table has only id/name_simple/name_arabic/translated_name/ayah_count (no juz or revelation_place column, confirmed via `sqlite3 resources/quran/quran.sqlite .schema surahs`). Add a static, well-known 30-entry Juz-start boundary table (surah id + ayah where each Juz begins — public factual data, no new dependency) and a pure `groupSurahsByJuz(surahs)` helper that buckets each surah under the Juz its first ayah falls in. Pure frontend, no backend/API change needed.
  - Files: `frontend/src/quranJuz.ts`, `frontend/src/quranJuz.test.ts`
  - [x] frontend/src/quranJuz.ts exports a 30-entry Juz boundary table and `groupSurahsByJuz(surahs: {id:number}[])` returning surahs bucketed in ascending Juz order, every input surah appearing exactly once
  - [x] frontend/src/quranJuz.test.ts asserts surah 1 (Al-Fatihah) is in Juz 1, surah 2 (Al-Baqarah) starts Juz 1 (not its own group), and a late surah (e.g. 114) lands in Juz 30
  - [x] `npm --prefix frontend test` passes including the new test file
  - Risk: Juz boundaries are fixed, universally-agreed values (not user data or copyrighted text) — safe to hardcode. Grouping a surah under the Juz where it starts (not every Juz it spans) is the convention other Quran apps use for a surah-list view; call this out to the user as the assumption if they expected something else.
  - Commit: (none — no code change for this task)

- [x] **Task 2: Group the sidebar surah list by Juz with section headers** (after 1)
  - Intent: Wire the new helper into the sidebar so `.surah-rail nav` in frontend/src/pages/QuranPractice.vue renders a 'Juz N' header above each group instead of one flat list, while keeping current search/select/active/keyboard behaviour identical (`filteredSurahs`, `selectSurah`, `surah.id === surahId` active state all still work per-button).
  - Files: `frontend/src/pages/QuranPractice.vue`
  - [x] surah-rail nav renders a group heading per non-empty Juz bucket, in Juz order, using groupSurahsByJuz(filteredSurahs.value)
  - [x] searching (the existing search input) still filters surahs and hides any Juz group left with zero matches
  - [x] clicking a surah button still calls selectSurah(id) and closes the mobile panel exactly as before
  - [x] the currently selected surah's button still gets the active class
  - [x] `npm --prefix frontend run build` (vue-tsc + vite build) succeeds with no new type errors
  - Risk: Keep the change scoped to the nav markup/script — do not touch verse-reader or practice-panel sections in the same file.
  - Commit: `1d7c96a038d2`

- [x] **Task 3: Style the Juz group headers** (after 2)
  - Intent: The new group headers need visual treatment consistent with the existing `.surah-rail` panel (see frontend/src/styles/bulma.scss:562-572 for the panel's existing look: muted ink colors, quran-accent highlights, compact spacing). Add a small, scoped CSS rule for the group heading so it reads as a section label, not another surah button.
  - Files: `frontend/src/styles/bulma.scss`
  - [x] new selector (e.g. .surah-rail nav h3 or the exact class used in task 2) is added near the existing surah-rail rules (bulma.scss:562-572), using the same --quran-* CSS custom properties for colors rather than hardcoded values
  - [x] no existing .surah-rail selectors are modified or removed
  - [x] visually distinct from surah buttons (smaller, muted, non-interactive) when checked with npm --prefix frontend run dev or by reading the rendered output
  - Risk: Low risk, additive CSS only.
  - Commit: `390be6906776`

- [x] **Task 4: Sync committed frontend/dist and run full project checks** (after 3)
  - Intent: Repo principle: committed frontend/dist must stay in sync with frontend/src since the deployment target has no Node build step. Rebuild and re-commit dist, then run every project check to confirm nothing regressed.
  - Files: `frontend/dist/**`
  - [x] npm --prefix frontend run build run and its output copied into the committed frontend/dist so dist matches the new src
  - [x] npm --prefix frontend test passes
  - [x] backend/venv/bin/python -m pytest backend/tests passes unchanged (no backend files touched by this ticket)
  - [x] shellcheck install.sh uninstall.sh deploy/backup.sh deploy/doctor.sh deploy/pair-speaker.sh deploy/update.sh passes unchanged
  - Risk: frontend/dist is a large generated tree; only commit the files vite actually changes, don't hand-edit dist.
  - Commit: `1ee97345abf8`

- [x] **Task 5: Fix: address review findings (cycle 1)** (after 4)
  - Intent: Review verdict: NEEDS_WORK — **correctness** — APPROVED

Correctness-only review: juzForSurah/groupSurahsByJuz logic verified by hand against known Juz boundaries (surah 1, 2, 3, 4, 9, 15, 114) — all correct, single-pass grouping under the surah's starting Juz. QuranPractice.vue sidebar integration preserves existing selectSurah/active-state/search behavior, only wraps rendering in Juz groups. Tests cover heading order and hidden-empty-group-on-search cases. This lens found nothing.

**cascading-impact** — APPROVED

Cascading-impact lens: no downstream breakage found. groupSurahsByJuz is a new pure module; only consumer is QuranPractice.vue's new juzGroups computed. selectSurah, active-class check, filteredSurahs signatures untouched, no other caller in the file duplicates the old flat-list logic left unfixed. No other file in repo references quranJuz.ts or the surah-rail markup.

**plan-faithfulness** — APPROVED

Plan-faithfulness lens found nothing to block. Diff isolated to ATH-5 scope: frontend/src/quranJuz.ts (30-Juz boundary table + groupSurahsByJuz), QuranPractice.vue sidebar nav wiring, additive bulma.scss rule, dist rebuild, and new/relocated Juz tests. Isolating true ATH-5 diff via `git diff 5b01929..fd7d46c` (pre-merge branch tip) confirms no backend, auth, playback, or reward files touched by this ticket's own commits — the backend/QuranPlayer/reward files appearing in a naive dev-branch diff are stale-local-dev artifacts from already-merged ATH-1..ATH-4, not new ATH-5 work. Checked a suspicious lead: the ATH-4 auto-center feature (verseEls/setVerseEl/scrollIntoView) and its regression test at components/__tests__/QuranPractice.test.ts both survive intact in the final merge commit f25d812 — false alarm, not a regression.

**ux-accessibility** — NEEDS_WORK

Juz grouping in sidebar works and mostly preserves existing accessibility patterns (touch targets, contrast tokens, keyboard reach unchanged), but two lens-scoped gaps found: mobile horizontal-scroll nav layout not adapted for the new group headers, and group labels aren't exposed as programmatic headings for screen-reader users.
- [medium] [ux-accessibility] Mobile horizontal nav not adapted for Juz group headers (frontend/src/styles/bulma.scss:608)
  Existing mobile rule `.surah-rail nav{display:flex;...overflow-x:auto}` (unchanged by this diff, line 608) turns the surah list into a horizontally scrolling row of buttons. The new `.juz-heading` <p> elements (QuranPractice.vue) are inserted into that same flex flow with no mobile-specific handling, so on phones the 'Juz N' labels become inline items interleaved with surah buttons in a horizontal scroll strip instead of a clear section break. This muddles the visual grouping the ticket asked for, specifically on the mobile breakpoint.
  Required action: Add a mobile rule (e.g. flex-basis:100% or display:block on .juz-heading inside the max-width:720px query) so group labels break the row instead of sitting inline with buttons.
- [low] [ux-accessibility] Juz group labels aren't exposed as headings for screen readers (frontend/src/pages/QuranPractice.vue:12)
  `<p class="juz-heading">Juz {{ group.juz }}</p>` is plain text, not a heading (h3) or aria-labelledby'd group. Sighted users see the visual section break; screen-reader users navigating the `nav aria-label="Surahs"` region by headings or landmarks get no equivalent grouping cue — the whole list still reads as one flat sequence of buttons with occasional unannounced text nodes.
  Required action: Use a heading element (e.g. h3) or wrap each group in a labelled region/group role so assistive tech exposes the same grouping sighted users get.
  - Commit: `9f09a38c19a7`

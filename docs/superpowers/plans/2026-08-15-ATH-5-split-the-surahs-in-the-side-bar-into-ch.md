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

- [ ] **Task 1: Add Juz grouping helper module with self-test**
  - Intent: Sidebar currently renders all 114 surahs as one flat button list in `.surah-rail nav` (frontend/src/pages/QuranPractice.vue:12-16). 'Chapters' here means the standard 30-Juz (Para) division used by Quran apps — the only grouping scheme the data actually supports, since backend/src/athan_hub/core/quran_resources.py's `surahs` table has only id/name_simple/name_arabic/translated_name/ayah_count (no juz or revelation_place column, confirmed via `sqlite3 resources/quran/quran.sqlite .schema surahs`). Add a static, well-known 30-entry Juz-start boundary table (surah id + ayah where each Juz begins — public factual data, no new dependency) and a pure `groupSurahsByJuz(surahs)` helper that buckets each surah under the Juz its first ayah falls in. Pure frontend, no backend/API change needed.
  - Files: `frontend/src/quranJuz.ts`, `frontend/src/quranJuz.test.ts`
  - [ ] frontend/src/quranJuz.ts exports a 30-entry Juz boundary table and `groupSurahsByJuz(surahs: {id:number}[])` returning surahs bucketed in ascending Juz order, every input surah appearing exactly once
  - [ ] frontend/src/quranJuz.test.ts asserts surah 1 (Al-Fatihah) is in Juz 1, surah 2 (Al-Baqarah) starts Juz 1 (not its own group), and a late surah (e.g. 114) lands in Juz 30
  - [ ] `npm --prefix frontend test` passes including the new test file
  - Risk: Juz boundaries are fixed, universally-agreed values (not user data or copyrighted text) — safe to hardcode. Grouping a surah under the Juz where it starts (not every Juz it spans) is the convention other Quran apps use for a surah-list view; call this out to the user as the assumption if they expected something else.

- [ ] **Task 2: Group the sidebar surah list by Juz with section headers** (after 1)
  - Intent: Wire the new helper into the sidebar so `.surah-rail nav` in frontend/src/pages/QuranPractice.vue renders a 'Juz N' header above each group instead of one flat list, while keeping current search/select/active/keyboard behaviour identical (`filteredSurahs`, `selectSurah`, `surah.id === surahId` active state all still work per-button).
  - Files: `frontend/src/pages/QuranPractice.vue`
  - [ ] surah-rail nav renders a group heading per non-empty Juz bucket, in Juz order, using groupSurahsByJuz(filteredSurahs.value)
  - [ ] searching (the existing search input) still filters surahs and hides any Juz group left with zero matches
  - [ ] clicking a surah button still calls selectSurah(id) and closes the mobile panel exactly as before
  - [ ] the currently selected surah's button still gets the active class
  - [ ] `npm --prefix frontend run build` (vue-tsc + vite build) succeeds with no new type errors
  - Risk: Keep the change scoped to the nav markup/script — do not touch verse-reader or practice-panel sections in the same file.

- [ ] **Task 3: Style the Juz group headers** (after 2)
  - Intent: The new group headers need visual treatment consistent with the existing `.surah-rail` panel (see frontend/src/styles/bulma.scss:562-572 for the panel's existing look: muted ink colors, quran-accent highlights, compact spacing). Add a small, scoped CSS rule for the group heading so it reads as a section label, not another surah button.
  - Files: `frontend/src/styles/bulma.scss`
  - [ ] new selector (e.g. .surah-rail nav h3 or the exact class used in task 2) is added near the existing surah-rail rules (bulma.scss:562-572), using the same --quran-* CSS custom properties for colors rather than hardcoded values
  - [ ] no existing .surah-rail selectors are modified or removed
  - [ ] visually distinct from surah buttons (smaller, muted, non-interactive) when checked with npm --prefix frontend run dev or by reading the rendered output
  - Risk: Low risk, additive CSS only.

- [ ] **Task 4: Sync committed frontend/dist and run full project checks** (after 3)
  - Intent: Repo principle: committed frontend/dist must stay in sync with frontend/src since the deployment target has no Node build step. Rebuild and re-commit dist, then run every project check to confirm nothing regressed.
  - Files: `frontend/dist/**`
  - [ ] npm --prefix frontend run build run and its output copied into the committed frontend/dist so dist matches the new src
  - [ ] npm --prefix frontend test passes
  - [ ] backend/venv/bin/python -m pytest backend/tests passes unchanged (no backend files touched by this ticket)
  - [ ] shellcheck install.sh uninstall.sh deploy/backup.sh deploy/doctor.sh deploy/pair-speaker.sh deploy/update.sh passes unchanged
  - Risk: frontend/dist is a large generated tree; only commit the files vite actually changes, don't hand-edit dist.

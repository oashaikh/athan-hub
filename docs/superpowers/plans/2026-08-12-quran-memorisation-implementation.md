# Child-Safe Quran Memorisation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only child prayer dashboard, profile-based Quran memorisation with every pinned QUL reciter, rewards and themes, a PIN-protected admin centre, and reliable Quran-audio interruption during scheduled Athan playback.

**Architecture:** Keep the existing Vue/FastAPI/SQLAlchemy/SQLite application. Ship a generated read-only QUL resource database, keep household state in the existing writable database, cache recitation audio under `/var/lib/athan-hub`, and expose separate public/practice and PIN-protected admin APIs. Reuse the current scheduler, PIN cookie, audit log, installer, and settings UI rather than adding services or frameworks.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic 2, SQLAlchemy 2, SQLite, filelock, mutagen, Vue 3, Vue Router 4, TypeScript, Vite, Bulma/Sass, Vitest, pytest, nginx, systemd, GitHub Actions.

## Global Constraints

- Preserve scheduled Athan, Bluetooth, timetable, exclusions, uploads, backgrounds, installer idempotency, and existing user data.
- `/` and `/quran` work without a PIN; every admin/system mutation is enforced server-side with `401 PIN_REQUIRED`.
- Only admin can create, rename, archive, restore, or delete profiles; children can switch existing active profiles.
- QUL text, structural metadata, translation, transliteration, catalogue provenance, and licences are pinned locally; recitation audio is cached on demand.
- An active Athan stops Quran audio, blocks all child interaction for measured media duration, and never automatically resumes Quran playback.
- Gender selects an initial theme only; admin can assign any theme; rewards and learning behaviour are identical.
- The sibling leaderboard is optional and disabled by default.
- No second CMS, frontend framework, authentication system, queue, Redis, or external runtime API.
- Use input validation, atomic file writes, HTTPS host allowlisting, cache quotas, checksum tracking, accessible focus/lock states, and dataset-specific attribution.

---

## File Structure

### Backend files to create

- `backend/src/athan_hub/core/audio_metadata.py` — MP3 duration inspection.
- `backend/src/athan_hub/core/playback_state.py` — atomic runtime Athan state and stale expiry.
- `backend/src/athan_hub/core/quran_resources.py` — read-only resource DB queries and manifest verification.
- `backend/src/athan_hub/services/quran_service.py` — profiles, preferences, progress, sessions, and public serialization.
- `backend/src/athan_hub/services/reward_service.py` — idempotent stars, badges, streaks, and leaderboard.
- `backend/src/athan_hub/services/quran_cache_service.py` — validated, locked, quota-aware audio caching.
- `backend/src/athan_hub/api/quran_routes.py` — public/practice Quran endpoints.
- `backend/src/athan_hub/api/admin_routes.py` — protected profile, Quran, and cache administration.
- `backend/tests/test_admin_auth.py` — authorization regression matrix.
- `backend/tests/test_quran_profiles.py` — profile isolation and practice state.
- `backend/tests/test_rewards.py` — idempotency, streaks, and leaderboard.
- `backend/tests/test_quran_cache.py` — download and eviction boundaries.
- `backend/tests/test_playback_state.py` — duration and Athan runtime state.
- `scripts/import_qul_resources.py` — deterministic QUL-to-SQLite importer.
- `resources/quran/manifest.json` — pinned QUL commit, URLs, hashes, hosts, and notices.
- `resources/quran/quran.sqlite` — generated, read-only Quran dataset.
- `resources/quran/NOTICE.md` — resource-specific attribution.

### Frontend files to create

- `frontend/src/stores/profile.ts` — selected profile and persisted ID.
- `frontend/src/stores/playback.ts` — Athan status polling and lock state.
- `frontend/src/components/ChildHeader.vue` — prayer/Quran navigation, profile picker, admin link.
- `frontend/src/components/AthanLock.vue` — accessible full-page interaction lock.
- `frontend/src/components/ProfilePicker.vue` — active-profile switcher only.
- `frontend/src/components/RewardSummary.vue` — stars, streak, badges, optional leaderboard.
- `frontend/src/components/QuranPlayer.vue` — one browser audio element and repeat state machine.
- `frontend/src/pages/QuranPractice.vue` — responsive practice workspace.
- `frontend/src/pages/AdminLayout.vue` — protected sidebar shell.
- `frontend/src/pages/AdminProfiles.vue` — admin-only profile management.
- `frontend/src/pages/AdminQuranCache.vue` — cache and provenance controls.
- `frontend/src/styles/themes.scss` — three profile theme token sets.
- `frontend/src/test/setup.ts` — DOM/audio test setup.
- `frontend/src/components/__tests__/AthanLock.test.ts`
- `frontend/src/components/__tests__/QuranPlayer.test.ts`
- `frontend/src/pages/__tests__/AdminProfiles.test.ts`

### Existing files to modify

- Backend: `pyproject.toml`, `requirements.lock`, `models.py`, `migrations.py`, `config.py`, `schemas.py`, `pin_auth.py`, `routes.py`, `main.py`, `audio_service.py`, `playback.py`, `scheduler.py`, existing tests.
- Frontend: `package.json`, lockfile, `main.ts`, `App.vue`, `Dashboard.vue`, `Settings.vue`, `FloatingMenu.vue`, `api.ts`, `bulma.scss`.
- Operations: `install.sh`, `deploy/backup.sh`, `deploy/doctor.sh`, systemd templates, README, INSTALL, TROUBLESHOOTING, NOTICE, VERSION, CHANGELOG, committed `frontend/dist`.

---

### Task 1: Public/Admin Authorization Boundary

**Files:**
- Modify: `backend/src/athan_hub/core/pin_auth.py`
- Modify: `backend/src/athan_hub/main.py`
- Modify: `backend/src/athan_hub/api/routes.py`
- Modify: `backend/src/athan_hub/api/schemas.py`
- Create: `backend/tests/test_admin_auth.py`
- Modify: `backend/tests/test_api.py`

**Interfaces:**
- Produces: `pin_auth.requires_admin(method: str, path: str) -> bool`
- Produces: `pin_auth.require_admin(request: Request) -> None`
- Produces: `GET /api/public/config`
- Preserves: `GET /api/pin/status`, `POST /api/pin/verify`, timetable public reads.

- [ ] **Step 1: Write the authorization matrix tests**

```python
@pytest.mark.parametrize("method,path", [
    ("PUT", "/api/settings"),
    ("POST", "/api/timetable/import"),
    ("POST", "/api/bluetooth/connect"),
    ("GET", "/api/logs"),
])
def test_protected_api_requires_pin(client_with_pin, method, path):
    assert client_with_pin.request(method, path).status_code == 401

def test_child_reads_remain_public(client_with_pin):
    assert client_with_pin.get("/api/public/config").status_code == 200
    assert client_with_pin.get("/api/timetable/next").status_code == 200
```

- [ ] **Step 2: Run the focused tests and confirm the old whole-host middleware fails them**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_admin_auth.py -q`

Expected: public reads return `401` before the route classification exists.

- [ ] **Step 3: Implement explicit protection and public config**

```python
PUBLIC_PATHS = {
    "/api/health", "/api/public/config", "/api/pin/status", "/api/pin/verify",
    "/api/timetable/day", "/api/timetable/next", "/api/playback/status",
}

def requires_admin(method: str, path: str) -> bool:
    if path.startswith("/api/admin/"):
        return True
    if method == "GET" and path in PUBLIC_PATHS:
        return False
    return path.startswith("/api/") and not path.startswith("/api/quran/")
```

Middleware calls this predicate and returns the existing `{"detail":"PIN_REQUIRED"}` response. `GET /api/public/config` returns only timezone and background filename.

- [ ] **Step 4: Run authorization and existing API tests**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_admin_auth.py backend/tests/test_api.py -q`

Expected: PASS; tests authenticate before old settings/upload mutations.

- [ ] **Step 5: Commit**

```bash
git add backend/src/athan_hub backend/tests
git commit -m "Enforce child and admin API boundaries"
```

### Task 2: Household Persistence and Migrations

**Files:**
- Modify: `backend/src/athan_hub/db/models.py`
- Modify: `backend/src/athan_hub/db/migrations.py`
- Modify: `backend/src/athan_hub/api/schemas.py`
- Create: `backend/tests/test_quran_profiles.py`

**Interfaces:**
- Produces SQLAlchemy models: `ChildProfile`, `QuranProgress`, `QuranSession`, `RewardEvent`, `ProfileBadge`, `QuranAudioCache`.
- Produces Pydantic schemas: `PracticeStateUpdate`, `ProgressUpdate`, `SessionCreate`, `SessionUpdate`, `AdminProfileCreate`, `AdminProfileUpdate`.
- Produces settings defaults: `quran_cache_limit_bytes=5368709120`, `leaderboard_enabled=0`, four leaderboard category flags.

- [ ] **Step 1: Write migration and constraint tests**

```python
def test_profile_tables_and_unique_progress(db):
    profile = models.ChildProfile(name="Yusuf", slug="yusuf", theme="night_explorer", active=1)
    db.add(profile); db.commit()
    db.add(models.QuranProgress(profile_id=profile.id, verse_key="1:1", state="learning"))
    db.commit()
    db.add(models.QuranProgress(profile_id=profile.id, verse_key="1:1", state="memorised"))
    with pytest.raises(IntegrityError):
        db.commit()
```

- [ ] **Step 2: Run the test and confirm missing models fail**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_quran_profiles.py::test_profile_tables_and_unique_progress -q`

Expected: FAIL because `ChildProfile` is absent.

- [ ] **Step 3: Add the six models and safe column migration helper**

Use composite unique constraints exactly as specified. Add `duration_seconds: float | None` to `AudioProfile`. Since `create_all()` does not add columns, add an idempotent `PRAGMA table_info`/`ALTER TABLE audio_profiles ADD COLUMN duration_seconds FLOAT` migration.

- [ ] **Step 4: Add strict enums/validators in Pydantic schemas**

```python
Theme = Literal["night_explorer", "garden_light", "classic_mushaf"]
LearningState = Literal["learning", "needs_practice", "memorised"]

class PracticeStateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recitation_id: int | None = Field(default=None, ge=1)
    surah_id: int = Field(ge=1, le=114)
    start_ayah: int = Field(ge=1)
    end_ayah: int = Field(ge=1)
    repetitions: Literal[1, 3, 5, 10] = 3
    playback_speed: float = Field(default=1.0, ge=0.75, le=1.25)
```

- [ ] **Step 5: Run model and migration tests**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_quran_profiles.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/athan_hub/db backend/src/athan_hub/api/schemas.py backend/tests/test_quran_profiles.py
git commit -m "Add Quran profile and progress persistence"
```

### Task 3: Deterministic QUL Resource Snapshot

**Files:**
- Create: `scripts/import_qul_resources.py`
- Create: `resources/quran/manifest.json`
- Create: `resources/quran/quran.sqlite`
- Create: `resources/quran/NOTICE.md`
- Create: `backend/src/athan_hub/core/quran_resources.py`
- Create: `backend/tests/test_quran_resources.py`
- Modify: `.gitattributes`

**Interfaces:**
- Produces: `QuranResources(path: Path, manifest_path: Path)`.
- Produces: `list_surahs(query: str | None) -> list[dict]`.
- Produces: `verses(surah_id: int) -> list[dict]`.
- Produces: `list_recitations() -> list[dict]`.
- Produces: `recitation(recitation_id: int) -> dict | None`.
- Manifest includes `qul_commit`, datasets with URL/SHA-256/licence, and `audio_hosts`.

- [ ] **Step 1: Write fixture-DB query and manifest hash tests**

```python
def test_resources_return_complete_quran(resource_db):
    resources = QuranResources(resource_db, manifest_path)
    assert len(resources.list_surahs()) == 114
    assert sum(row["ayah_count"] for row in resources.list_surahs()) == 6236
    assert resources.verses(1)[0]["verse_key"] == "1:1"

def test_recitation_catalogue_has_quran_capabilities(resources):
    rows = resources.list_recitations()
    assert rows
    assert {"ayah", "segmented_surah", "surah"} <= {row["capability"] for row in rows}
```

- [ ] **Step 2: Run tests and confirm the resource adapter is absent**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_quran_resources.py -q`

Expected: import failure.

- [ ] **Step 3: Implement the importer with Python stdlib**

The script accepts pinned input URLs and `--output`, downloads with `urllib.request`, calculates SHA-256, maps QUL resource 86, translation 20, transliteration 72, structural metadata, and all recitation resource records into normalized SQLite tables, and rejects any run that does not yield 114 surahs, 6,236 ayahs, Arabic text, translation, and at least one recitation.

```python
def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Athan-Hub-QUL-Importer/1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()

def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
```

- [ ] **Step 4: Generate the checked-in database, manifest, and notices**

Run: `python3 scripts/import_qul_resources.py --output resources/quran`

Expected: importer prints the pinned QUL SHA, `114 surahs`, `6236 ayahs`, the recitation count, and all file hashes.

- [ ] **Step 5: Implement read-only queries and verify the manifest**

Open SQLite with URI `mode=ro`; validate the database SHA against `manifest.json` once at app startup.

- [ ] **Step 6: Run tests and inspect provenance**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_quran_resources.py -q && sqlite3 resources/quran/quran.sqlite 'select count(*) from verses; select count(*) from recitations;'`

Expected: PASS and counts match the manifest.

- [ ] **Step 7: Commit**

```bash
git add scripts/import_qul_resources.py resources/quran backend/src/athan_hub/core/quran_resources.py backend/tests/test_quran_resources.py .gitattributes
git commit -m "Pin Quranic Universal Library resources"
```

### Task 4: Profiles, Practice State, and Admin CRUD

**Files:**
- Create: `backend/src/athan_hub/services/quran_service.py`
- Create: `backend/src/athan_hub/api/quran_routes.py`
- Create: `backend/src/athan_hub/api/admin_routes.py`
- Modify: `backend/src/athan_hub/main.py`
- Modify: `backend/tests/test_quran_profiles.py`
- Modify: `backend/tests/test_admin_auth.py`

**Interfaces:**
- Produces: `profile_summary(db, profile) -> dict`.
- Produces: `update_practice_state(db, profile_id, payload) -> dict`.
- Produces: `update_progress(db, profile_id, verse_key, payload) -> dict`.
- Produces public `/api/quran/*` and protected `/api/admin/profiles*` routes from the spec.

- [ ] **Step 1: Write public/admin profile tests**

```python
def test_only_admin_can_create_profile(public_client, admin_client):
    payload = {"name": "Maryam", "gender": "girl"}
    assert public_client.post("/api/admin/profiles", json=payload).status_code == 401
    created = admin_client.post("/api/admin/profiles", json=payload)
    assert created.status_code == 201
    assert created.json()["theme"] == "garden_light"

def test_child_state_update_cannot_change_profile_identity(client, profile):
    response = client.put(f"/api/quran/profiles/{profile.id}/state", json={"name": "Changed"})
    assert response.status_code == 422
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_quran_profiles.py backend/tests/test_admin_auth.py -q`

Expected: 404/import failures for the new endpoints.

- [ ] **Step 3: Implement service transactions and route modules**

Default themes map `{boy: night_explorer, girl: garden_light, None: classic_mushaf}`. Slugs use a normalized name plus numeric suffix. Archived profiles are excluded publicly and return `404` for new practice writes. Permanent deletion relies on model cascades and one transaction.

- [ ] **Step 4: Validate verse range and recitation against QUL resources**

`end_ayah >= start_ayah`, both are at most the selected surah's `ayah_count`, and the recitation ID must exist.

- [ ] **Step 5: Run profile/auth tests**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_quran_profiles.py backend/tests/test_admin_auth.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/athan_hub/services/quran_service.py backend/src/athan_hub/api backend/src/athan_hub/main.py backend/tests
git commit -m "Add child profiles and Quran practice APIs"
```

### Task 5: Idempotent Rewards and Optional Leaderboard

**Files:**
- Create: `backend/src/athan_hub/services/reward_service.py`
- Create: `backend/tests/test_rewards.py`
- Modify: `backend/src/athan_hub/services/quran_service.py`
- Modify: `backend/src/athan_hub/api/quran_routes.py`
- Modify: `backend/src/athan_hub/api/admin_routes.py`

**Interfaces:**
- Produces: `award(db, profile_id: int, key: str, category: str, points: int) -> bool`.
- Produces: `complete_session(db, session, payload) -> dict`.
- Produces: `profile_rewards(db, profile_id) -> dict`.
- Produces: `leaderboard(db, week_start: date) -> dict`.

- [ ] **Step 1: Write idempotency, streak, badge, and leaderboard tests**

```python
def test_memorised_reward_is_awarded_once(db, profile):
    assert award(db, profile.id, f"memorised:{profile.id}:1:1", "memorised", 25)
    assert not award(db, profile.id, f"memorised:{profile.id}:1:1", "memorised", 25)
    assert sum(row.points for row in db.query(models.RewardEvent).all()) == 25

def test_leaderboard_disabled_returns_hidden(client):
    assert client.get("/api/quran/leaderboard").json() == {"enabled": False, "entries": []}
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_rewards.py -q`

Expected: missing service/import failure.

- [ ] **Step 3: Implement the reward ledger and badge evaluation**

Use the exact point rules and semantic keys from the design. Count streaks from completed session local dates using `now_local()` timezone. Badge keys are fixed constants; unique constraints absorb retry races.

- [ ] **Step 4: Wire session/progress endpoints and leaderboard settings**

Only a transition from non-memorised to memorised may request the one-time verse reward. Admin settings control leaderboard visibility and included categories.

- [ ] **Step 5: Run reward and profile tests**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_rewards.py backend/tests/test_quran_profiles.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/athan_hub/services backend/src/athan_hub/api backend/tests/test_rewards.py
git commit -m "Add Quran practice rewards and leaderboard"
```

### Task 6: Validated Quran Audio Cache

**Files:**
- Modify: `backend/src/athan_hub/core/config.py`
- Create: `backend/src/athan_hub/services/quran_cache_service.py`
- Create: `backend/tests/test_quran_cache.py`
- Modify: `backend/src/athan_hub/api/quran_routes.py`
- Modify: `backend/src/athan_hub/api/admin_routes.py`

**Interfaces:**
- Produces: `resolve_audio(db, recitation_id: int, verse_key: str | None, surah_id: int) -> Path`.
- Produces: `cache_summary(db) -> dict`.
- Produces: `evict_to_limit(db, required_bytes: int = 0) -> int`.
- Adds settings paths: `quran_cache_dir`, `quran_resource_db`, `quran_manifest_path`.

- [ ] **Step 1: Write local HTTP fixture tests for allowlist and atomic cache**

```python
def test_uncached_audio_downloads_once(cache_service, http_server):
    first = cache_service.resolve_audio(db, recitation_id=112, verse_key="1:1", surah_id=1)
    second = cache_service.resolve_audio(db, recitation_id=112, verse_key="1:1", surah_id=1)
    assert first == second
    assert http_server.request_count == 1

def test_redirect_to_unlisted_host_is_rejected(cache_service):
    with pytest.raises(CacheSourceError):
        cache_service.download("https://allowed.test/redirect-to-evil")
```

- [ ] **Step 2: Run cache tests and verify failure**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_quran_cache.py -q`

Expected: missing service.

- [ ] **Step 3: Implement stdlib HTTPS download, filelock, and atomic replace**

Use `urllib.request`, `FileLock`, a temporary file in the target directory, `os.fsync`, and `os.replace`. Verify redirects, response size, audio signature, and available quota before replacement.

- [ ] **Step 4: Implement LRU eviction and protected files**

Order unpinned, non-playing rows by `last_accessed_at`; delete database row only after filesystem deletion succeeds. Raise `HTTPException(507)` when pinned content prevents enough eviction.

- [ ] **Step 5: Add public streaming and admin cache routes**

Return `FileResponse` from local storage. Convert uncached network failures to `503`, quota failures to `507`, and invalid capabilities/ranges to `400`.

- [ ] **Step 6: Run cache tests**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_quran_cache.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/athan_hub/core/config.py backend/src/athan_hub/services/quran_cache_service.py backend/src/athan_hub/api backend/tests/test_quran_cache.py
git commit -m "Cache Quran recitation audio safely"
```

### Task 7: Athan Duration and Runtime Playback State

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/requirements.lock`
- Create: `backend/src/athan_hub/core/audio_metadata.py`
- Create: `backend/src/athan_hub/core/playback_state.py`
- Modify: `backend/src/athan_hub/services/audio_service.py`
- Modify: `backend/src/athan_hub/core/playback.py`
- Modify: `backend/src/athan_hub/core/scheduler.py`
- Modify: `backend/src/athan_hub/api/routes.py`
- Create: `backend/tests/test_playback_state.py`
- Modify: `backend/tests/test_api.py`

**Interfaces:**
- Produces: `mp3_duration(path: Path) -> float`.
- Produces: `write_active(prayer: str, profile_id: int, duration_seconds: float, started_at: datetime) -> None`.
- Produces: `clear_active() -> None`.
- Produces: `read_active(now: datetime | None = None, grace_seconds: int = 120) -> dict | None`.
- Produces: `GET /api/playback/status`.

- [ ] **Step 1: Add `mutagen` and regenerate the exact lock**

Run: `backend/.venv/bin/pip install 'mutagen>=1.47,<2' && backend/.venv/bin/pip freeze | LC_ALL=C sort > backend/requirements.lock`

Confirm `mutagen` is also in `pyproject.toml`.

- [ ] **Step 2: Write duration, state lifecycle, and upload rejection tests**

```python
def test_runtime_state_expires_and_is_removed(tmp_path, monkeypatch):
    write_active("fajr", 1, 2.0, started_at)
    assert read_active(started_at + timedelta(seconds=1))["prayer"] == "fajr"
    assert read_active(started_at + timedelta(seconds=123), grace_seconds=120) is None

def test_invalid_mp3_duration_rejects_upload(client):
    response = client.post("/api/audio/upload", data={"name":"bad"}, files={"file":("bad.mp3", b"ID3bad", "audio/mpeg")})
    assert response.status_code == 400
```

- [ ] **Step 3: Run tests and confirm failure**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_playback_state.py backend/tests/test_api.py -q`

Expected: missing helpers and fake MP3 upload expectations fail.

- [ ] **Step 4: Measure upload duration and backfill legacy profiles**

Write uploads to a temporary file, call `mutagen.mp3.MP3`, reject unreadable files, then atomically move and persist `duration_seconds`. Migration scans enabled legacy files and disables only unreadable profiles.

- [ ] **Step 5: Wrap scheduled playback state in `try/finally`**

```python
write_active(prayer, profile.id, profile.duration_seconds, now)
try:
    result = play_once(...)
finally:
    clear_active()
```

Write state immediately before invoking `mpg123`, not while Bluetooth is connecting.

- [ ] **Step 6: Add public status route and run tests**

Run: `backend/.venv/bin/python -m pytest backend/tests/test_playback_state.py backend/tests/test_api.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend
git commit -m "Publish measured Athan playback state"
```

### Task 8: Child Shell, Profiles, Themes, and Athan Lock

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/src/main.ts`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/api.ts`
- Create: `frontend/src/stores/profile.ts`
- Create: `frontend/src/stores/playback.ts`
- Create: `frontend/src/components/ChildHeader.vue`
- Create: `frontend/src/components/ProfilePicker.vue`
- Create: `frontend/src/components/AthanLock.vue`
- Create: `frontend/src/styles/themes.scss`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/components/__tests__/AthanLock.test.ts`
- Modify: `frontend/src/pages/Dashboard.vue`
- Remove: `frontend/src/components/FloatingMenu.vue`

**Interfaces:**
- Produces composable singleton `useProfileStore()` with `profiles`, `selected`, `select(id)`, `load()`.
- Produces singleton `usePlaybackStore()` with `active`, `remaining`, `start()`, `stop()`.
- `AthanLock` emits no events; it renders from playback store and applies `inert` to `#child-application`.

- [ ] **Step 1: Add Vitest and Vue Test Utils**

Run: `cd frontend && npm install -D vitest@^3 @vue/test-utils@^2 jsdom@^26`

Add `"test": "vitest run"` and Vite test setup.

- [ ] **Step 2: Write the Athan lock test**

```ts
it('pauses every audio element and makes child content inert', async () => {
  document.body.innerHTML = '<main id="child-application"><audio></audio></main>'
  const pause = vi.spyOn(HTMLMediaElement.prototype, 'pause')
  playback.active.value = { prayer: 'fajr', remaining_seconds: 30 }
  mount(AthanLock)
  expect(pause).toHaveBeenCalled()
  expect(document.querySelector('#child-application')).toHaveAttribute('inert')
})
```

- [ ] **Step 3: Run the test and confirm missing component failure**

Run: `cd frontend && npm test -- AthanLock.test.ts`

Expected: import failure.

- [ ] **Step 4: Implement the two stores and child shell**

Poll `/api/playback/status` every second. On activation, pause all `audio`, remove `src`, call `load()`, and render an `aria-live="assertive"` overlay. Clear `inert` only after inactive status. Persist selected active profile ID in `localStorage`.

- [ ] **Step 5: Implement approved themes as CSS custom properties**

Use `data-profile-theme` on the child root and the exact three approved token groups. Respect `prefers-reduced-motion` and maintain existing focus styles.

- [ ] **Step 6: Replace floating settings menu with approved top navigation**

Dashboard remains visually intact; add `Prayer times`, `Quran practice`, profile picker, and lock link. Public empty-state settings link points to `/admin/timetable`.

- [ ] **Step 7: Run frontend tests and build**

Run: `cd frontend && npm test && npm run build`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend
git commit -m "Add child shell profiles and Athan lock"
```

### Task 9: Quran Practice Reader and Reward UI

**Files:**
- Create: `frontend/src/components/QuranPlayer.vue`
- Create: `frontend/src/components/RewardSummary.vue`
- Create: `frontend/src/pages/QuranPractice.vue`
- Create: `frontend/src/components/__tests__/QuranPlayer.test.ts`
- Modify: `frontend/src/main.ts`
- Modify: `frontend/src/styles/bulma.scss`

**Interfaces:**
- `QuranPlayer` props: `profileId`, `recitation`, `verses`, `repetitions`, `playbackSpeed`.
- Emits: `repetition-complete(verseKey: string)`, `range-complete()`.
- `QuranPractice` consumes QUL/profile APIs and owns selection/display state.

- [ ] **Step 1: Write repeat-state and no-auto-resume tests**

```ts
it('repeats the verse before advancing', async () => {
  const wrapper = mount(QuranPlayer, { props: { verses: twoVerses, repetitions: 3, ...base } })
  await wrapper.get('audio').trigger('ended')
  await wrapper.get('audio').trigger('ended')
  expect(wrapper.emitted('repetition-complete')).toHaveLength(2)
  expect(wrapper.text()).toContain('Repeat 3 of 3')
})
```

- [ ] **Step 2: Run the test and confirm missing component failure**

Run: `cd frontend && npm test -- QuranPlayer.test.ts`

Expected: import failure.

- [ ] **Step 3: Implement one native `<audio>` repeat state machine**

Use native playback rate, `ended`, and explicit `play()` calls. Capability labels control whether URL selection is verse or surah based. Athan lock resets playback and never calls `play()` after unlock.

- [ ] **Step 4: Build the approved responsive practice page**

Desktop: surah rail, central reader/player, practice side panel. Tablet/mobile: slide-over surah picker, reader, collapsible settings. Add loading skeletons and inline offline/cache-full/capability errors.

- [ ] **Step 5: Add progress controls, recall mode, rewards, and optional leaderboard**

Status buttons send typed progress updates. Recall mode hides Arabic after listening count but leaves a reveal button. Reward summary uses server totals; it never computes authoritative points in the browser.

- [ ] **Step 6: Run tests and production build**

Run: `cd frontend && npm test && npm run build`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend
git commit -m "Build Quran memorisation workspace"
```

### Task 10: Protected Admin Centre

**Files:**
- Create: `frontend/src/pages/AdminLayout.vue`
- Create: `frontend/src/pages/AdminProfiles.vue`
- Create: `frontend/src/pages/AdminQuranCache.vue`
- Create: `frontend/src/pages/__tests__/AdminProfiles.test.ts`
- Modify: `frontend/src/pages/Settings.vue`
- Modify: `frontend/src/main.ts`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/api.ts`

**Interfaces:**
- `AdminLayout` owns PIN status/gate and nested navigation.
- `Settings.vue` receives `forcedTab?: string` and remains the implementation of existing system settings.
- Router maps `/admin/:section?` to admin children; `/settings` redirects.

- [ ] **Step 1: Write profile-management visibility and API tests**

```ts
it('creates profiles only from the admin screen', async () => {
  mock.onPost('/admin/profiles').reply(201, { id: 1, name: 'Maryam', theme: 'garden_light' })
  const wrapper = mount(AdminProfiles)
  await wrapper.get('[data-test=create-profile]').trigger('click')
  expect(mock.history.post).toHaveLength(1)
})
```

- [ ] **Step 2: Run the test and confirm missing page failure**

Run: `cd frontend && npm test -- AdminProfiles.test.ts`

Expected: import failure.

- [ ] **Step 3: Implement the approved admin shell and PIN gate**

Reuse `PinGate`; scope it to admin. Sidebar contains profile, existing prayer settings, cache, and source pages. Successful verification reloads the requested admin child.

- [ ] **Step 4: Reuse existing settings panels under admin routes**

Map sections to the current query-tab implementation; do not duplicate Bluetooth, timetable, audio, activity, exclusions, or general forms. Replace public menu links and redirect `/settings`.

- [ ] **Step 5: Implement profile cards/forms and cache/provenance panels**

Use native form controls, explicit archive/delete confirmation, storage totals, prefetch/remove actions, and checked-in manifest/source notices.

- [ ] **Step 6: Run frontend tests and build**

Run: `cd frontend && npm test && npm run build`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend
git commit -m "Move administration behind the PIN"
```

### Task 11: Installer, Backup, Diagnostics, and Documentation

**Files:**
- Modify: `install.sh`
- Modify: `deploy/backup.sh`
- Modify: `deploy/doctor.sh`
- Modify: `deploy/systemd/athan-hub-api.service.in`
- Modify: `deploy/systemd/athan-hub-scheduler.service.in`
- Modify: `README.md`
- Modify: `docs/INSTALL.md`
- Modify: `docs/TROUBLESHOOTING.md`
- Modify: `NOTICE`
- Modify: `VERSION`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Installer creates `/var/lib/athan-hub/quran-audio` and deploys `/opt/athan-hub/resources/quran` read-only.
- Backup includes writable DB/profile progress, not reproducible Quran audio.
- Doctor verifies QUL database/hash, cache/runtime permissions, duration metadata, storage, API, and services.

- [ ] **Step 1: Add installer contract checks**

Run: `bash -n install.sh deploy/backup.sh deploy/doctor.sh && shellcheck install.sh deploy/*.sh`

Record current output; install shellcheck locally only if absent from the development Mac, never add it as target dependency.

- [ ] **Step 2: Extend paths, environment, and systemd write access**

Create the cache directory with `0750`, set `ATHAN_QURAN_CACHE_DIR`, `ATHAN_QURAN_RESOURCE_DB`, and `ATHAN_QURAN_MANIFEST_PATH`, and keep `/run/athan-hub` writable to scheduler/API. Do not expose home directories.

- [ ] **Step 3: Extend backup and doctor**

Backup the application DB, timezone, uploaded Athan audio, timetable uploads, and backgrounds. Explicitly report Quran audio as excluded. Doctor uses Python to open resource SQLite read-only, recompute SHA-256, inspect audio duration nulls, and check free bytes against cache limit.

- [ ] **Step 4: Update documentation and notices**

Document child/admin routes, profile ownership, QUL provenance, cache behaviour, offline limits, Athan lock, fork, upgrade, backup, and recovery. Add dataset contributors and no-endorsement language. Increment to version `2.0.0`.

- [ ] **Step 5: Run shell, backend, and frontend verification**

Run: `bash -n install.sh deploy/*.sh uninstall.sh && backend/.venv/bin/python -m pytest backend/tests -q && cd frontend && npm test && npm run build`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add install.sh deploy README.md docs NOTICE VERSION CHANGELOG.md frontend/dist
git commit -m "Ship Quran memorisation installation support"
```

### Task 12: Preserve QUL in GitHub and Verify Production

**Files:**
- Create in fork: `.github/workflows/sync-upstream.yml`
- Modify only if verification finds defects: files from Tasks 1-11.

**Interfaces:**
- Public fork: `https://github.com/oashaikh/quranic-universal-library`.
- Workflow events: daily cron and `workflow_dispatch`.
- Workflow permissions: `contents: write`, `issues: write`.

- [ ] **Step 1: Verify GitHub authentication and fork state**

Run: `gh auth status && gh repo view oashaikh/quranic-universal-library --json isFork,parent,url,visibility`

Expected: authenticated; create the fork only if the repository does not exist.

- [ ] **Step 2: Create the public fork without secrets**

Run: `gh repo fork TarteelAI/quranic-universal-library --org '' --clone=false`

Verify parent is `TarteelAI/quranic-universal-library` and visibility is public.

- [ ] **Step 3: Add the upstream-sync workflow on a short-lived clone**

Workflow body:

```yaml
name: Sync upstream
on:
  schedule:
    - cron: '23 3 * * *'
  workflow_dispatch:
permissions:
  contents: write
  issues: write
jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - name: Sync default branch
        env:
          GH_TOKEN: ${{ github.token }}
        run: gh api --method POST "repos/${GITHUB_REPOSITORY}/merge-upstream" -f branch="${GITHUB_REF_NAME:-main}"
```

Add a failure step using `gh issue create` or `gh issue edit` to maintain one `upstream-sync-failed` issue. Push to the fork; do not add a PAT or secret.

- [ ] **Step 4: Trigger and verify the workflow**

Run: `gh workflow run sync-upstream.yml -R oashaikh/quranic-universal-library && gh run watch -R oashaikh/quranic-universal-library --exit-status`

Expected: success and fork default-branch SHA matches or contains upstream.

- [ ] **Step 5: Run the full local completion audit**

Run:

```bash
git diff --check
backend/.venv/bin/python -m pytest backend/tests -q
cd frontend && npm ci && npm test && npm run build
cd ..
bash -n install.sh deploy/*.sh uninstall.sh
git status --short
```

Expected: all tests/builds pass; only intentional committed build output changes remain before final commit.

- [ ] **Step 6: Deploy to `athan.local` using the normal update path**

Push the integration branch/main as appropriate, then run over SSH:

```bash
ssh athan.local 'sudo athan-hub-backup /var/lib/athan-hub/pre-quran-upgrade && sudo athan-hub-update && sudo athan-hub-doctor'
```

Expected: backup exists, update succeeds, services are active/enabled, resource hash passes, and current timetable/audio data remains.

- [ ] **Step 7: Perform live acceptance checks**

Create two profiles through `/admin`, verify public creation is rejected, select different reciters/progress, test cached and offline audio, enable/disable leaderboard, inspect all themes, and trigger a temporary scheduled Athan while Quran audio is playing. Confirm Quran stops, all child interaction locks, countdown follows measured duration, unlock occurs, audio does not resume, and Bluetooth Athan completes.

- [ ] **Step 8: Remove temporary overrides and inspect production state**

Delete any temporary timetable override through admin/API, verify next prayer is genuine, inspect scheduler audit log, confirm Echo remains connected, and verify no test profile/data remains unless explicitly retained.

- [ ] **Step 9: Commit any verification fixes and push**

```bash
git add -A
git commit -m "Complete child-safe Quran memorisation"
git push origin main
git status --short
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

Expected: clean worktree and local/remote SHAs match.


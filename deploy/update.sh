#!/usr/bin/env bash
set -Eeuo pipefail

readonly INSTALL_ROOT="/opt/athan-hub"
readonly CONFIG_ROOT="/etc/athan-hub"
readonly STATE_ROOT="/var/lib/athan-hub-updater"
readonly CACHE_ROOT="/var/cache/athan-hub-updater"
readonly REPO_ROOT="$CACHE_ROOT/repository"
readonly ROLLBACK_ROOT="$STATE_ROOT/rollback"
readonly BACKUP_ROOT="/var/backups/athan-hub"
readonly LOCK_FILE="/run/lock/athan-hub-update.lock"

repository="${ATHAN_UPDATE_REPOSITORY:-https://github.com/oashaikh/athan-hub.git}"
branch="${ATHAN_UPDATE_BRANCH:-main}"
candidate=""
previous=""
rollback_ready=false
service_user="athan"

log() { printf '%s athan-hub-update: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
fail() { log "ERROR: $*" >&2; return 1; }

restore_previous_release() {
  local original_status="$?"
  trap - ERR
  if [[ "$rollback_ready" != true ]]; then
    exit "$original_status"
  fi

  log "Deployment failed; restoring the previous application release"
  systemctl stop athan-hub-api.service athan-hub-scheduler.service || true
  rsync -a --delete --exclude 'backend/venv' "$ROLLBACK_ROOT/app/" "$INSTALL_ROOT/" || true
  tar -xzf "$ROLLBACK_ROOT/system.tar.gz" -C / || true
  if [[ -f "$ROLLBACK_ROOT/data.tar.gz" ]]; then
    tar -xzf "$ROLLBACK_ROOT/data.tar.gz" -C / || true
  fi

  if [[ -x "$INSTALL_ROOT/backend/venv/bin/pip" && -f "$INSTALL_ROOT/backend/requirements.lock" ]]; then
    runuser -u "$service_user" -- "$INSTALL_ROOT/backend/venv/bin/pip" install \
      --disable-pip-version-check -r "$INSTALL_ROOT/backend/requirements.lock" || true
    runuser -u "$service_user" -- "$INSTALL_ROOT/backend/venv/bin/pip" install \
      --disable-pip-version-check --no-deps "$INSTALL_ROOT/backend" || true
  fi
  systemctl daemon-reload || true
  nginx -t || true
  systemctl restart athan-hub-api.service athan-hub-scheduler.service nginx.service || true
  printf '%s\n' "${previous:-unknown}" > "$STATE_ROOT/last-failed-rollback"
  log "Rollback finished; the failed candidate was ${candidate:-unknown}"
  exit "$original_status"
}

[[ $EUID -eq 0 ]] || fail "Run as root"
[[ "$repository" =~ ^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.git$ ]] || fail "Updater repository must be an HTTPS GitHub URL"
[[ "$branch" =~ ^[A-Za-z0-9._/-]+$ ]] || fail "Invalid update branch"

service_user="$(sed -n 's/^service_user=//p' "$CONFIG_ROOT/installed" 2>/dev/null | head -n 1)"
service_user="${service_user:-athan}"
id "$service_user" >/dev/null 2>&1 || fail "Configured service user does not exist"

install -d -m 0700 "$STATE_ROOT" "$CACHE_ROOT"
install -d -m 0750 "$BACKUP_ROOT"
exec 9>"$LOCK_FILE"
flock -n 9 || { log "Another update check is already running"; exit 0; }

if [[ ! -d "$REPO_ROOT/.git" ]]; then
  log "Creating the read-only deployment checkout"
  rm -rf -- "$REPO_ROOT"
  git clone --quiet --no-tags --filter=blob:none "$repository" "$REPO_ROOT"
else
  current_remote="$(git -C "$REPO_ROOT" remote get-url origin)"
  [[ "$current_remote" == "$repository" ]] || fail "Cached repository remote does not match updater configuration"
fi

git -C "$REPO_ROOT" fetch --quiet --prune --no-tags origin "+refs/heads/$branch:refs/remotes/origin/$branch"
candidate="$(git -C "$REPO_ROOT" rev-parse --verify "refs/remotes/origin/$branch^{commit}")"
previous="$(cat "$STATE_ROOT/deployed-commit" 2>/dev/null || true)"

if [[ "$candidate" == "$previous" ]]; then
  log "Already running ${candidate:0:12} from $branch"
  exit 0
fi

git -C "$REPO_ROOT" checkout --quiet --detach "$candidate"
git -C "$REPO_ROOT" reset --quiet --hard "$candidate"
git -C "$REPO_ROOT" clean -qfdx

[[ ! -e "$REPO_ROOT/.gitmodules" ]] || fail "Submodules are not permitted in automatic deployments"
[[ -f "$REPO_ROOT/backend/pyproject.toml" ]] || fail "Candidate is missing backend/pyproject.toml"
[[ -f "$REPO_ROOT/backend/requirements.lock" ]] || fail "Candidate is missing backend/requirements.lock"
[[ -f "$REPO_ROOT/frontend/dist/index.html" ]] || fail "Candidate is missing the prebuilt frontend"
[[ -f "$REPO_ROOT/resources/quran/quran.sqlite" ]] || fail "Candidate is missing Quran resources"
bash -n "$REPO_ROOT/install.sh" "$REPO_ROOT/deploy/update.sh"
python3 - "$REPO_ROOT/backend/src" <<'PY'
import pathlib
import sys

for source_path in pathlib.Path(sys.argv[1]).rglob("*.py"):
    compile(source_path.read_bytes(), str(source_path), "exec")
PY

if pgrep -x mpg123 >/dev/null 2>&1 || python3 - /run/athan-hub/athan-active.json <<'PY'
import datetime as dt
import json
import pathlib
import sys

try:
    payload = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    finish = dt.datetime.fromisoformat(payload["expected_finish_at"])
    now = dt.datetime.now(finish.tzinfo or dt.timezone.utc)
except (OSError, ValueError, KeyError, json.JSONDecodeError):
    raise SystemExit(1)
raise SystemExit(0 if now < finish else 1)
PY
then
  log "Audio is currently playing; postponing deployment until the next check"
  exit 0
fi

log "Preparing rollback snapshot before deploying ${candidate:0:12}"
rm -rf -- "$ROLLBACK_ROOT"
install -d -m 0700 "$ROLLBACK_ROOT/app"
rsync -a --delete --exclude 'backend/venv' "$INSTALL_ROOT/" "$ROLLBACK_ROOT/app/"
tar -C / -czf "$ROLLBACK_ROOT/system.tar.gz" \
  etc/athan-hub \
  etc/systemd/system/athan-hub-api.service \
  etc/systemd/system/athan-hub-scheduler.service \
  etc/nginx/sites-available/athan-hub \
  usr/local/bin/athan-hub-backup \
  usr/local/bin/athan-hub-doctor \
  usr/local/bin/athan-hub-update

rollback_ready=true
trap restore_previous_release ERR
systemctl stop athan-hub-api.service athan-hub-scheduler.service
tar -C / --exclude='var/lib/athan-hub/quran-cache' -czf "$ROLLBACK_ROOT/data.tar.gz" var/lib/athan-hub
cp -a "$ROLLBACK_ROOT/data.tar.gz" "$BACKUP_ROOT/athan-hub-pre-update-${candidate:0:12}.tar.gz"

ATHAN_REPOSITORY="${repository#https://github.com/}"
ATHAN_REPOSITORY="${ATHAN_REPOSITORY%.git}"
export ATHAN_REPOSITORY
bash "$REPO_ROOT/install.sh" \
  --source-dir "$REPO_ROOT" \
  --branch "$branch" \
  --keep-hostname \
  --skip-system-packages

systemctl is-active --quiet athan-hub-api.service
systemctl is-active --quiet athan-hub-scheduler.service
curl --max-time 15 -fsS http://127.0.0.1:9000/api/health >/dev/null
curl --max-time 15 -fsS http://127.0.0.1/ >/dev/null

trap - ERR
rollback_ready=false
printf '%s\n' "$candidate" > "$STATE_ROOT/deployed-commit"
printf '%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$STATE_ROOT/deployed-at"
find "$BACKUP_ROOT" -maxdepth 1 -type f -name 'athan-hub-pre-update-*.tar.gz' -print0 \
  | xargs -0 ls -1t 2>/dev/null \
  | tail -n +6 \
  | xargs -r rm -f --
log "Successfully deployed ${candidate:0:12} from $branch"

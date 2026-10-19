#!/usr/bin/env bash
# Execute on the staging host. Reads the public main branch without GitHub/AWS keys.
set -euo pipefail
umask 077
export GIT_TERMINAL_PROMPT=0
ROOT=/opt/socratia
MIRROR=/opt/socratia-git
STATE=/opt/socratia-deployment
REMOTE=https://github.com/BrayanJoelRamosVargas1/SOCRATIA_SW1.git
mkdir -p "$STATE" "$ROOT/backups"
exec 9>"$STATE/deploy.lock"
flock -n 9 || exit 0
if [[ ! -d "$MIRROR" ]]; then
  git init --bare "$MIRROR"
  git --git-dir="$MIRROR" remote add origin "$REMOTE"
fi
git -c credential.helper= --git-dir="$MIRROR" fetch --no-tags origin main
TARGET=$(git --git-dir="$MIRROR" rev-parse FETCH_HEAD)
PREVIOUS=$(cat "$STATE/deployed-commit" 2>/dev/null || true)
[[ "$TARGET" != "$PREVIOUS" ]] || exit 0
# Do not repeatedly build a known failed commit every polling interval.
[[ ! -f "$STATE/failed-commit" || "$(cat "$STATE/failed-commit")" != "$TARGET" ]] || exit 1
if [[ -n "$PREVIOUS" ]]; then
  git --git-dir="$MIRROR" merge-base --is-ancestor "$PREVIOUS" "$TARGET"
fi
cd "$ROOT"
COMPOSE=(sudo docker compose --env-file .env.staging -f compose.staging.yaml)
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
# Snapshot the database to the same encrypted disk; this is not off-host disaster recovery.
"${COMPOSE[@]}" exec -T db pg_dump -U socratia -d socratia --no-owner | gzip > "$ROOT/backups/pre-deploy-$STAMP.sql.gz"
gzip -t "$ROOT/backups/pre-deploy-$STAMP.sql.gz"
sudo docker image tag socratia-staging-backend socratia-staging-backend:previous
sudo docker image tag socratia-staging-frontend socratia-staging-frontend:previous
printf '%s\n' "$TARGET" > "$STATE/building-commit"
finish_failed() {
  printf '%s\n' "$TARGET" > "$STATE/failed-commit"
  printf 'FAILED %s; inspect journal and backups before retrying\n' "$TARGET" >&2
}
trap finish_failed ERR
# Environment, uploads and runtime volumes are not tracked in Git and are preserved.
git --git-dir="$MIRROR" archive "$TARGET" | tar -x -C "$ROOT"
"${COMPOSE[@]}" config --quiet
"${COMPOSE[@]}" build backend
"${COMPOSE[@]}" build frontend
# Workers must finish or be marked interrupted, never replay an uncertain AI request.
"${COMPOSE[@]}" stop -t 180 preparation-worker 2>/dev/null || true
"${COMPOSE[@]}" up -d --no-deps backend
for attempt in $(seq 1 40); do
  if curl --fail --silent --max-time 4 http://localhost:80/health >/dev/null; then break; fi
  [[ "$attempt" != 40 ]] || exit 1
  sleep 3
done
"${COMPOSE[@]}" up -d --no-deps frontend preparation-worker proxy
curl --fail --silent --retry 6 --retry-delay 3 --max-time 15 https://socratia.34.204.9.87.sslip.io/login >/dev/null
curl --fail --silent --max-time 10 https://socratia.34.204.9.87.sslip.io/health >/dev/null
printf '%s\n' "$TARGET" > "$STATE/deployed-commit"
printf '{"commit":"%s","deployed_at":"%s","source":"public GitHub main"}\n' "$TARGET" "$(date -u +%FT%TZ)" > "$ROOT/RELEASE.json"
trap - ERR
printf 'DEPLOYED %s\n' "$TARGET"

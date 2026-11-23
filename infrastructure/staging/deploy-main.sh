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
BUILD_BACKEND=true
BUILD_FRONTEND=true
COMPOSE_CHANGED=false
[[ "$TARGET" != "$PREVIOUS" ]] || exit 0
# Do not repeatedly build a known failed commit every polling interval.
[[ ! -f "$STATE/failed-commit" || "$(cat "$STATE/failed-commit")" != "$TARGET" ]] || exit 1
if [[ -n "$PREVIOUS" ]]; then
  git --git-dir="$MIRROR" merge-base --is-ancestor "$PREVIOUS" "$TARGET"
  if git --git-dir="$MIRROR" diff --quiet "$PREVIOUS" "$TARGET" -- backend; then
    BUILD_BACKEND=false
  fi
  if git --git-dir="$MIRROR" diff --quiet "$PREVIOUS" "$TARGET" -- frontend; then
    BUILD_FRONTEND=false
  fi
  if ! git --git-dir="$MIRROR" diff --quiet "$PREVIOUS" "$TARGET" -- compose.staging.yaml; then
    COMPOSE_CHANGED=true
  fi
  # Documentation and test-only commits do not consume another production build.
  if git --git-dir="$MIRROR" diff --quiet "$PREVIOUS" "$TARGET" -- \
      backend/app backend/migrations backend/requirements.txt backend/requirements-local-voice.txt backend/Dockerfile backend/.dockerignore backend/alembic.ini \
      frontend/src frontend/public frontend/package.json frontend/package-lock.json frontend/next.config.ts \
      frontend/Dockerfile frontend/.dockerignore frontend/tsconfig.json frontend/postcss.config.mjs \
      frontend/scripts/copy-standalone.mjs compose.staging.yaml infrastructure/staging/Caddyfile; then
    printf '%s\n' "$TARGET" > "$STATE/deployed-commit"
    printf '{"commit":"%s","runtime_unchanged_from":"%s","source":"public GitHub main"}\n' "$TARGET" "$PREVIOUS" > "$ROOT/RELEASE.json"
    printf 'METADATA_ONLY %s\n' "$TARGET"
    exit 0
  fi
fi
cd "$ROOT"
COMPOSE=(sudo docker compose --env-file .env.staging -f compose.staging.yaml)
# Runtime mounts, limits and environment do not change an image. Compare the
# resolved build definitions separately so only changed build args/context/target
# require a new image. Both Compose files reside beside the same environment.
build_signature() {
  sudo docker compose --env-file "$ROOT/.env.staging" -f "$1" config --format json |
    python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["services"][sys.argv[1]].get("build"),sort_keys=True))' "$2"
}
if [[ "$COMPOSE_CHANGED" == true ]]; then
  PREVIOUS_COMPOSE=$(mktemp "$ROOT/.previous-compose.XXXXXX.yaml")
  git --git-dir="$MIRROR" show "$PREVIOUS:compose.staging.yaml" > "$PREVIOUS_COMPOSE"
  OLD_BACKEND_BUILD=$(build_signature "$PREVIOUS_COMPOSE" backend)
  OLD_FRONTEND_BUILD=$(build_signature "$PREVIOUS_COMPOSE" frontend)
  rm -f "$PREVIOUS_COMPOSE"
fi
PUBLIC_DOMAIN=$("${COMPOSE[@]}" config --format json | python3 -c '
import json,re,sys
domain=json.load(sys.stdin)["services"]["proxy"]["environment"]["PUBLIC_DOMAIN"]
if not re.fullmatch(r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}",domain):
    raise SystemExit("Invalid PUBLIC_DOMAIN; deployment stopped")
print(domain)
')
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
# Snapshot the database to the same encrypted disk; this is not off-host disaster recovery.
"${COMPOSE[@]}" exec -T db pg_dump -U socratia -d socratia --no-owner | gzip > "$ROOT/backups/pre-deploy-$STAMP.sql.gz"
gzip -t "$ROOT/backups/pre-deploy-$STAMP.sql.gz"
# Preserve images actually running, including after a previous build failed.
LIVE_BACKEND=$(sudo docker inspect --format '{{.Image}}' "$("${COMPOSE[@]}" ps -q backend)")
LIVE_FRONTEND_CONTAINER=$("${COMPOSE[@]}" ps -q frontend)
LIVE_FRONTEND=$(sudo docker inspect --format '{{.Image}}' "$LIVE_FRONTEND_CONTAINER")
sudo docker image tag "$LIVE_BACKEND" socratia-staging-backend:previous
if sudo docker image inspect "$LIVE_FRONTEND" >/dev/null 2>&1; then
  sudo docker image tag "$LIVE_FRONTEND" socratia-staging-frontend:previous
else
  # Loading a prebuilt tag can remove old image metadata in containerd's image
  # store while its container still runs. Preserve that running frontend before
  # replacing it. Never use this fallback for the backend: its runtime environment
  # contains private credentials. This snapshot remains only on the encrypted host.
  printf 'SNAPSHOT_RUNNING_FRONTEND %s\n' "$LIVE_FRONTEND_CONTAINER"
  sudo docker commit --pause=false "$LIVE_FRONTEND_CONTAINER" socratia-staging-frontend:previous >/dev/null
fi
printf '%s\n' "$TARGET" > "$STATE/building-commit"
finish_failed() {
  printf '%s\n' "$TARGET" > "$STATE/failed-commit"
  printf 'FAILED %s; inspect journal and backups before retrying\n' "$TARGET" >&2
}
trap finish_failed ERR
# Environment, uploads and runtime volumes are not tracked in Git and are preserved.
git --git-dir="$MIRROR" archive "$TARGET" | tar -x -C "$ROOT"
"${COMPOSE[@]}" config --quiet
if [[ "$COMPOSE_CHANGED" == true ]]; then
  [[ "$OLD_BACKEND_BUILD" == "$(build_signature "$ROOT/compose.staging.yaml" backend)" ]] || BUILD_BACKEND=true
  [[ "$OLD_FRONTEND_BUILD" == "$(build_signature "$ROOT/compose.staging.yaml" frontend)" ]] || BUILD_FRONTEND=true
fi
printf 'IMAGE_BUILD backend=%s frontend=%s\n' "$BUILD_BACKEND" "$BUILD_FRONTEND"
# Operators may preload an image built off-host. Accept it only for this exact
# source commit; an older or unlabelled image must never silently skip a build.
image_matches_target() {
  [[ "$(sudo docker image inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$1" 2>/dev/null || true)" == "$TARGET" ]]
}
if [[ "$BUILD_BACKEND" == true ]]; then
  if image_matches_target socratia-staging-backend:latest; then
    printf 'PREBUILT backend=%s\n' "$TARGET"
  else "${COMPOSE[@]}" build backend; fi
fi
if [[ "$BUILD_FRONTEND" == true ]]; then
  if image_matches_target socratia-staging-frontend:latest; then
    printf 'PREBUILT frontend=%s\n' "$TARGET"
  else "${COMPOSE[@]}" build frontend; fi
fi
# Workers must finish or be marked interrupted, never replay an uncertain AI request.
if "${COMPOSE[@]}" config --services | grep -qx qwen; then
  "${COMPOSE[@]}" up -d --no-deps qwen
fi
"${COMPOSE[@]}" stop -t 180 preparation-worker 2>/dev/null || true
"${COMPOSE[@]}" up -d --no-deps backend
for attempt in $(seq 1 40); do
  if curl --fail --silent --max-time 4 http://localhost:80/health >/dev/null; then break; fi
  [[ "$attempt" != 40 ]] || exit 1
  sleep 3
done
"${COMPOSE[@]}" up -d --no-deps frontend preparation-worker proxy
curl --fail --silent --retry 8 --retry-all-errors --retry-delay 3 --retry-max-time 90 --max-time 15 "https://$PUBLIC_DOMAIN/login" >/dev/null
curl --fail --silent --retry 8 --retry-all-errors --retry-delay 3 --retry-max-time 90 --max-time 10 "https://$PUBLIC_DOMAIN/health" >/dev/null
printf '%s\n' "$TARGET" > "$STATE/deployed-commit"
printf '{"commit":"%s","deployed_at":"%s","source":"public GitHub main"}\n' "$TARGET" "$(date -u +%FT%TZ)" > "$ROOT/RELEASE.json"
trap - ERR
printf 'DEPLOYED %s\n' "$TARGET"

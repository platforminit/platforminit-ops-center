#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

log() { printf '[bootstrap-dev] %s\n' "$*"; }
warn() { printf '[bootstrap-dev][WARN] %s\n' "$*" >&2; }
fail() { printf '[bootstrap-dev][FAIL] %s\n' "$*" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

[[ -f "backend/pyproject.toml" ]] || fail "backend/pyproject.toml not found. Run from the platforminit-ops-center repository."
[[ -f "frontend/package.json" ]] || fail "frontend/package.json not found. Frontend skeleton is missing."

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

log "Checking required local tooling"
need_cmd git
need_cmd python3
need_cmd uv
need_cmd node
need_cmd pnpm

log "Tool versions"
git --version
python3 --version
uv --version
node --version
pnpm --version

CHECK_HTTP_BIN="${CHECK_HTTP_BIN:-/usr/lib/nagios/plugins/check_http}"
CHECK_DISK_BIN="${CHECK_DISK_BIN:-/usr/lib/nagios/plugins/check_disk}"

[[ -x "${CHECK_HTTP_BIN}" ]] || fail "Nagios check_http not executable at ${CHECK_HTTP_BIN}"
[[ -x "${CHECK_DISK_BIN}" ]] || fail "Nagios check_disk not executable at ${CHECK_DISK_BIN}"

if command -v podman >/dev/null 2>&1; then
  log "Podman detected"
  podman --version
else
  warn "Podman not found. Local container build/run checks will be skipped."
fi

log "Bootstrapping backend Python environment"
(
  cd backend
  uv sync --extra dev
)

log "Bootstrapping frontend dependencies"
(
  cd frontend
  pnpm install
)

log "Running lightweight smoke checks"
"${CHECK_HTTP_BIN}" -H example.com >/dev/null
"${CHECK_DISK_BIN}" -w 20% -c 10% -p / >/dev/null

log "Bootstrap completed successfully"

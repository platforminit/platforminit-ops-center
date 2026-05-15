#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

log() { printf '[verify-dev] %s\n' "$*"; }
warn() { printf '[verify-dev][WARN] %s\n' "$*" >&2; }
fail() { printf '[verify-dev][FAIL] %s\n' "$*" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

[[ -f "backend/pyproject.toml" ]] || fail "backend/pyproject.toml not found."
[[ -f "frontend/package.json" ]] || fail "frontend/package.json not found."

CHECK_HTTP_BIN="${CHECK_HTTP_BIN:-/usr/lib/nagios/plugins/check_http}"
CHECK_DISK_BIN="${CHECK_DISK_BIN:-/usr/lib/nagios/plugins/check_disk}"

[[ -x "${CHECK_HTTP_BIN}" ]] || fail "Nagios check_http not executable at ${CHECK_HTTP_BIN}"
[[ -x "${CHECK_DISK_BIN}" ]] || fail "Nagios check_disk not executable at ${CHECK_DISK_BIN}"

log "Running backend tests"
(
  cd backend
  uv run pytest -q
)

log "Running backend lint"
(
  cd backend
  uv run ruff check .
)

log "Running frontend lint"
(
  cd frontend
  pnpm lint
)

log "Running frontend production build"
(
  cd frontend
  pnpm build
)

log "Running Nagios plugin smoke checks"
"${CHECK_HTTP_BIN}" -H example.com
"${CHECK_DISK_BIN}" -w 20% -c 10% -p /

if [[ -f "backend/app/runner/nagios.py" ]]; then
  log "Running Nagios runner integration smoke"
  (
    cd backend
    uv run python - <<'PY'
from app.runner.models import CheckStatus
from app.runner.nagios import run_nagios_plugin

result = run_nagios_plugin(
    ["/usr/lib/nagios/plugins/check_http", "-H", "example.com"],
    timeout_seconds=10,
)

assert result.status == CheckStatus.OK, result
assert result.exit_code == 0, result
assert "HTTP OK" in result.output, result
print("runner-smoke=OK")
PY
  )
else
  warn "backend/app/runner/nagios.py not found; runner integration smoke skipped."
fi

if command -v podman >/dev/null 2>&1; then
  log "Checking Podman availability"
  podman --version
else
  warn "Podman not found; container runtime check skipped."
fi

log "Verification completed successfully"

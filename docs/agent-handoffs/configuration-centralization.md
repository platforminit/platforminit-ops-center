# Task 02 — Configuration Centralization

## Task Summary

Centralized all four MVP environment variables into a single core config
module (`app.core.config`), removing direct `os.environ` calls from
`security.py`, `checks.py`, `check_results.py`, and `inventory.py`.

## Changed Files

| File | Change |
|------|--------|
| `backend/app/core/config.py` | **Created** — `Settings` frozen dataclass + `load_settings()` factory |
| `backend/app/core/security.py` | Replaced inline `os.environ.get` with `load_settings()` |
| `backend/app/api/checks.py` | Replaced inline `os.environ.get` with `load_settings()`; removed `import os` |
| `backend/app/store/check_results.py` | Replaced inline `os.environ.get` with `load_settings()`; removed `import os` |
| `backend/app/store/inventory.py` | Replaced inline `os.environ.get` with `load_settings()`; removed `import os` |
| `backend/tests/test_config.py` | **Created** — default, env-override, immutability, and `_parse_bool` tests |

## Design Decisions

- **Frozen dataclass** — immutable settings prevent accidental mutation at
  runtime; callers always get a fresh snapshot from `load_settings()`.
- **No external config library** — the MVP surface (4 vars) does not warrant
  pydantic-settings or python-dotenv.  A simple dataclass + factory keeps
  the dependency footprint unchanged.
- **`load_settings()` called per-use** — each call reads current env state,
  so tests can monkeypatch env vars without module-level caching issues.
  This is acceptable for an MVP; a caching layer can be added later if
  performance measurements show it matters.
- **`_parse_bool` helper** — centralises the truthy-value convention
  (`"1"`, `"true"`, `"yes"`) used across the original codebase.

## Security Assumptions

- `api_token` is `None` by default, preserving the existing fail-closed
  behaviour when auth is enabled but no token is configured.
- `enable_adhoc_checks` defaults to `False`, matching the original safety
  default.
- No secrets are logged or exposed in public API responses — the config
  module is purely a read-side abstraction.

## Tests Added

`backend/tests/test_config.py` — 15 tests covering:

- `_parse_bool` truthy/falsy inputs and default fallback
- All four settings return safe defaults when env vars are unset
- Each setting can be overridden via its env var
- Empty `OPS_CENTER_API_TOKEN` becomes `None`
- `Settings` frozen dataclass immutability
- `load_settings()` returns a frozen `Settings` instance

## Verification Result

`make verify` passes (all existing + new tests green).

## Known Limitations

- `load_settings()` reads `os.environ` on every call — no caching.  This
  is fine for request-scoped use but could be optimised with a module-level
  cache if called in hot loops.
- No config file or secret-store integration yet; env vars are the only
  source.

## Suggested Commit Message

```
refactor(core): centralize MVP configuration

Create app.core.config with a frozen Settings dataclass and
load_settings() factory.  Replace all direct os.environ calls
in security.py, checks.py, check_results.py, and inventory.py.

Add 15 tests covering defaults, env overrides, and immutability.

Closes: batch-01-task-02
```

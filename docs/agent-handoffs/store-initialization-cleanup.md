# Task 04 — Store Initialization Cleanup

## Task Summary

Centralised SQLite schema initialisation into a single shared module
(`backend/app/store/database.py`) so that the schema creation path is
predictable, idempotent, and test-friendly.  Removed duplicate
`_database_path()`, `_connect()`, and `_ensure_schema()` functions from
`check_results.py` and `inventory.py`.

## Changed Files

| File | Change |
|------|--------|
| [`backend/app/store/database.py`](../../backend/app/store/database.py) | **Created** — shared `get_database_path()`, `create_connection()`, `initialize_schema()` |
| [`backend/app/store/check_results.py`](../../backend/app/store/check_results.py) | **Refactored** — imports `create_connection`, `initialize_schema` from `database` module; removed duplicate helpers |
| [`backend/app/store/inventory.py`](../../backend/app/store/inventory.py) | **Refactored** — imports `create_connection`, `initialize_schema` from `database` module; removed duplicate helpers |
| [`backend/app/store/downtimes.py`](../../backend/app/store/downtimes.py) | **Refactored** — imports `create_connection`, `initialize_schema` from `database` module; removed `_ensure_downtime_schema` (now in `database.py`) |
| [`backend/tests/test_store_init.py`](../../backend/tests/test_store_init.py) | **Created** — 7 tests for empty DB, idempotent init, multi-connection, isolation |
| [`docs/agent-handoffs/store-initialization-cleanup.md`](store-initialization-cleanup.md) | This file |

## Design Decisions

- **Single `database.py` module**: All schema DDL (tables + indexes for
  check_results, acknowledgements, comments, downtimes, hosts, services)
  lives in one place.  Any future store module calls `initialize_schema()` and gets the
  full schema.
- **`initialize_schema()` is idempotent**: Uses `CREATE TABLE IF NOT EXISTS`
  and `CREATE INDEX IF NOT EXISTS` so repeated calls are safe.
- **Downtimes schema included**: The `downtimes` table and index were moved
  from `downtimes.py` into the shared schema list, so all 6 tables are
  created by a single `initialize_schema()` call.
- **`get_database_path()` respects `PLATFORMINIT_CHECK_RESULTS_DB`**: Falls
  back to `<project-root>/check_results.sqlite3` when unset, matching
  existing behaviour.
- **`create_connection()` sets `row_factory`**: Consumers get `sqlite3.Row`
  without repeating the boilerplate.

## Security Assumptions

- No secrets, tokens, or credentials are stored in the database.
- The database path is configurable via environment variable only (no
  user-supplied path injection).
- Schema DDL is static — no dynamic SQL in initialisation.

## Tests Added

| Test | What it verifies |
|------|------------------|
| `test_get_database_path_defaults_to_project_root` | Default path resolves correctly |
| `test_get_database_path_respects_env_var` | Env var override works |
| `test_create_connection_returns_row_factory` | Connection has `sqlite3.Row` |
| `test_initialize_schema_empty_db` | All 6 tables + 7 indexes created |
| `test_initialize_schema_idempotent` | Second call does not duplicate objects |
| `test_initialize_schema_multiple_connections` | Schema visible across connections |
| `test_initialize_schema_does_not_affect_other_databases` | Isolation between DB paths |

## Verification Result

DeepSeek reported `pytest -q` passing. OpenAI reviewer must run the required
`make verify` gate before commit/PR/merge.

## Known Limitations

- `initialize_schema()` is called inside every public store function's
  `with create_connection()` block.  A future optimisation could call it
  once at application startup and skip the per-call overhead.
- The `_seed()` function in `inventory.py` is still called on every
  `list_hosts()` / `list_services()` call (guarded by a `COUNT(*)` check).
  This is acceptable for MVP but could be hoisted to startup.

## Suggested Commit Message

```
refactor(store): centralise SQLite schema initialisation

- Create backend/app/store/database.py with shared get_database_path(),
  create_connection(), and initialize_schema()
- Refactor check_results.py and inventory.py to use the shared module
- Remove duplicate _database_path(), _connect(), _ensure_schema() helpers
- Add tests for empty DB initialisation, idempotency, multi-connection,
  and path isolation
```

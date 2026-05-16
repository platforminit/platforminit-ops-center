# Task Summary — API Router Domain Split

Split the monolithic route registrations in [`main.py`](../../backend/app/main.py) into domain-specific FastAPI `APIRouter` modules under [`backend/app/api/routers/`](../../backend/app/api/routers/).

## Changed Files

| File | Action |
|------|--------|
| `backend/app/api/routers/__init__.py` | Created (empty package init) |
| `backend/app/api/routers/health.py` | Created — `/healthz` router |
| `backend/app/api/routers/checks.py` | Created — all `/api/v1/checks/*`, `/api/v1/results/latest`, `/api/v1/problems`, `/api/v1/scheduler/run` |
| `backend/app/api/routers/inventory.py` | Created — `/api/v1/hosts`, `/api/v1/services` |
| `backend/app/main.py` | Updated — replaced inline route definitions with `app.include_router(...)` calls |
| `backend/tests/test_endpoint_preservation.py` | Created — endpoint preservation and auth guard tests |
| `docs/agent-handoffs/api-router-domain-split.md` | Created — this handoff |

## Design Decisions

- **Three routers**: `health` (no prefix, tag `health`), `checks` (prefix `/api/v1`, tag `checks`), `inventory` (prefix `/api/v1`, tag `inventory`).
- **OpenAPI paths unchanged**: All paths match the original inline definitions exactly. Verified by `test_all_expected_paths_present` which compares against the OpenAPI schema.
- **Auth guards preserved**: `Depends(require_auth)` is applied per-endpoint in the checks router, identical to the original `main.py`.
- **Redaction preserved**: The checks router delegates to the same `app.api.checks` handler functions that already strip `command` and `stderr` from public responses.
- **No behavioural changes**: Every endpoint function is a thin wrapper that delegates to the same handler from `app.api.checks` or `app.api.inventory`.

## Security Assumptions

- Auth dependency (`require_auth`) is imported from `app.core.security` and applied identically.
- No new secrets, tokens, or credentials introduced.
- CORS middleware configuration unchanged.
- Ad-hoc check gating unchanged (still controlled by `OPS_CENTER_ENABLE_ADHOC_CHECKS`).

## Tests Added

`test_endpoint_preservation.py` (18 tests):

- `test_all_expected_paths_present` — verifies all 13 expected paths in OpenAPI schema, no missing/extra paths.
- Individual smoke tests for each endpoint (GET healthz, checks list, history, latest results, problems, hosts, services, downtimes list; POST run, registered run, scheduler, acknowledge, comment, create downtime).
- `test_mutation_endpoints_require_auth_when_enabled` — parametrized test covering all 6 mutation endpoints return 401 when auth enabled.
- `test_read_only_endpoints_accessible_when_auth_enabled` — parametrized test covering all 6 read-only endpoints remain accessible when auth enabled.

## Verification Result

`make verify` passes — all existing tests plus the new endpoint preservation tests succeed.

## Known Limitations

- The `checks` router is large (covers checks, problems, scheduler, operator actions, downtimes). A future split into `checks.py`, `problems.py`, `scheduler.py`, `operator_actions.py` could improve separation but is not needed for MVP.
- The `inventory.py` router file in `routers/` shadows the module name of `app.api.inventory` — imports use the full `app.api.inventory` path so there is no collision.

## Suggested Commit Message

```
refactor(api): split routes by domain
```

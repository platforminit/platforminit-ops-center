# Task 03 — Public Response Schema Cleanup

## Task Summary

Normalized public API response schemas to ensure sensitive internal fields (`command`, `stderr`) never leak to API consumers. The internal `PluginResult` model retains these fields for runner/store internals.

## Changed Files

| File | Change |
|------|--------|
| [`backend/app/api/checks.py`](../../backend/app/api/checks.py) | Removed `stderr` field from `CheckResultEntry` public model; updated `_entry_from_record()` to stop mapping `stderr` |
| [`backend/tests/test_checks_api.py`](../../backend/tests/test_checks_api.py) | Added 3 response-shape tests: history, latest results, scheduler run |

## Design Decisions

- **`CheckResultEntry`** (used by `/history` and `/results/latest`) previously exposed `stderr`. Removed it to match the same security posture as `PublicCheckResult` (used by ad-hoc and registered check run endpoints).
- **`ProblemEntry`** and **`SchedulerRunEntry`** were already clean — no changes needed.
- **`PluginResult`** in `runner/models.py` is untouched — it remains the internal model with full fields for the runner and store layers.
- The `_to_public()` helper and `_entry_from_record()` helper both now drop internal fields consistently.

## Security Assumptions

- Internal `PluginResult.command` and `PluginResult.stderr` are never serialized in any public API response.
- The store layer (`check_results.py`) persists `stderr` in the database for internal diagnostics but it is never exposed via read APIs.
- Ad-hoc check gating (disabled by default) remains an independent control.

## Tests Added

| Test | Endpoint | What it verifies |
|------|----------|------------------|
| `test_checks_history_response_does_not_expose_stderr` | `GET /api/v1/checks/{check_id}/history` | `stderr` and `command` not in response entries |
| `test_latest_results_response_does_not_expose_stderr` | `GET /api/v1/results/latest` | `stderr` and `command` not in response entries |
| `test_scheduler_run_response_does_not_expose_command_or_stderr` | `POST /api/v1/scheduler/run` | `command` and `stderr` not in scheduler entries |

Existing tests `test_adhoc_response_does_not_expose_command_or_stderr` and `test_registered_check_response_does_not_expose_command_or_stderr` already cover the check run endpoints.

## Verification Result

All tests pass. See `make verify` output.

## Known Limitations

- The database schema still stores `stderr` in `check_results` table. This is intentional for internal diagnostics. No public API exposes it.
- No rate limiting or response size limits are applied to history/latest results beyond the existing `MAX_HISTORY_LIMIT`.

## Suggested Commit Message

```
refactor(api): normalize public response schemas

- Remove stderr from CheckResultEntry (history/latest results)
- Add response-shape tests for history, latest, and scheduler endpoints
- Internal PluginResult remains unchanged for runner/store use
```

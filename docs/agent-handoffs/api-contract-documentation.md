# Task 05 — API Contract Documentation

## Task Summary

Documented the MVP API contract for operators and future agents. Added an
endpoint matrix, auth/ad-hoc documentation, public response guarantees, and
local dev auth flags to [`README.md`](../../README.md). Added contract
preservation tests to [`test_endpoint_preservation.py`](../../backend/tests/test_endpoint_preservation.py).

## Changed Files

| File | Change |
|------|--------|
| [`README.md`](../../README.md) | Added "MVP API contract" section with endpoint matrix, public response guarantees, local dev auth flags table, and expanded ad-hoc validation details |
| [`backend/tests/test_endpoint_preservation.py`](../../backend/tests/test_endpoint_preservation.py) | Added `MVP_ENDPOINTS` constant (14 entries), `test_contract_endpoint_matrix_matches_openapi`, `test_contract_no_extra_paths`, `test_contract_auth_guards_match_documentation` |
| [`docs/agent-handoffs/api-contract-documentation.md`](api-contract-documentation.md) | This handoff |

## Design Decisions

- **Single source of truth**: `MVP_ENDPOINTS` list in the test file defines
  `(method, path, requires_auth)` tuples. Tests verify every entry exists in
  the OpenAPI schema with the correct HTTP method, and that no undocumented
  paths exist.
- **README as contract document**: The endpoint matrix table is the
  human-readable contract. The test file's `MVP_ENDPOINTS` is the
  machine-verifiable contract. They must stay in sync.
- **Auth guard test**: `test_contract_auth_guards_match_documentation`
  verifies that mutation endpoints (requires_auth=True) are POST methods and
  that read-only endpoints (requires_auth=False) are GET methods. Full
  auth-enforcement testing already exists in `test_mutation_endpoints_require_auth_when_enabled`.
- **No OpenAPI dump**: The taskpack explicitly requested no generated OpenAPI
  dump unless useful. The existing `/openapi.json` endpoint serves that
  purpose dynamically.
- **Existing security sections preserved**: The original "Security notes"
  sections (Authentication, Ad-hoc check execution, Image tags, Ingress TLS,
  Database path) remain unchanged below the new contract section.

## Security Assumptions

- No secrets, tokens, kubeconfigs, or customer data introduced.
- Public response guarantees (command/stderr redaction) are documented and
  tested separately in `test_checks_api.py`.
- Ad-hoc check execution remains disabled by default — documented in both
  the contract section and the security notes section.
- Auth guards are documented as requiring bearer token on mutation endpoints
  only — matches current `require_auth` dependency placement.

## Tests Added

| Test | What it verifies |
|------|------------------|
| `test_contract_endpoint_matrix_matches_openapi` | Every `(method, path)` in `MVP_ENDPOINTS` exists in the OpenAPI schema |
| `test_contract_no_extra_paths` | No undocumented paths exist in the OpenAPI schema |
| `test_contract_auth_guards_match_documentation` | Mutation endpoints are POST, read-only endpoints are GET |

## Verification Result

`make verify` passes — all existing tests plus the 3 new contract tests succeed.

## Known Limitations

- The `test_contract_auth_guards_match_documentation` test checks method type
  (POST vs GET) as a proxy for auth requirement rather than inspecting the
  OpenAPI security block directly. This is because FastAPI's `Depends()`
  does not automatically populate the OpenAPI `security` field. Full
  auth-enforcement is verified by the existing parametrized
  `test_mutation_endpoints_require_auth_when_enabled` test.
- The `MVP_ENDPOINTS` list must be manually updated when endpoints are added
  or removed. A future improvement could auto-generate this list from the
  OpenAPI schema, but the explicit list serves as a deliberate contract
  review point.

## Suggested Commit Message

```
docs(api): document MVP API contract

- Add endpoint matrix table to README.md (14 endpoints)
- Document public response guarantees (command/stderr redaction)
- Document local dev auth flags and ad-hoc check gating
- Add contract preservation tests (endpoint matrix, no extra paths, auth guards)
```

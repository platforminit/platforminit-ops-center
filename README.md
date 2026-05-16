# PlatformInit Ops Center

Standalone operations monitoring component for PlatformInit.

## Goals

- Nagios-compatible plugin runner
- CheckMK/Nagios-style host and service state model
- Operator-focused Problems view
- Native SSO support
- GitOps-friendly deployment
- Release artifact deployment to platforminit-dev-01

## MVP API contract

### Endpoint matrix

| Method | Path | Auth required | Purpose |
|--------|------|---------------|---------|
| `GET` | `/healthz` | No | Liveness probe |
| `GET` | `/api/v1/checks` | No | List registered checks (metadata only, no commands) |
| `GET` | `/api/v1/checks/{check_id}/history` | No | Check result history (newest first, capped by `limit`) |
| `GET` | `/api/v1/results/latest` | No | Latest result per registered check |
| `GET` | `/api/v1/problems` | No | Non-OK results sorted by severity then newest |
| `GET` | `/api/v1/hosts` | No | Seeded host inventory |
| `GET` | `/api/v1/services` | No | Seeded service inventory |
| `GET` | `/api/v1/checks/{check_id}/downtimes` | No | List downtimes for a check |
| `POST` | `/api/v1/checks/run` | Yes | Execute an ad-hoc Nagios plugin command |
| `POST` | `/api/v1/checks/{check_id}/run` | Yes | Execute a registered check by ID |
| `POST` | `/api/v1/scheduler/run` | Yes | Run all due registered checks |
| `POST` | `/api/v1/checks/{check_id}/acknowledge` | Yes | Acknowledge a problem |
| `POST` | `/api/v1/checks/{check_id}/comments` | Yes | Add a comment to a check |
| `POST` | `/api/v1/checks/{check_id}/downtimes` | Yes | Schedule a downtime window |

### Public response guarantees

- **`command`** and **`stderr`** are never included in any public API response.
  The internal `PluginResult` model retains these fields for runner/store
  internals only.
- **`CheckResultEntry`** (history, latest results) and **`PublicCheckResult`**
  (ad-hoc / registered run) both strip internal fields before serialization.
- **`ProblemEntry`** includes acknowledgement state (`acknowledged`,
  `acknowledged_by`, `acknowledged_at`, `acknowledged_reason`) and downtime
  state (`in_downtime`).

### Local development auth flags

| Env var | Default | Effect |
|---------|---------|--------|
| `OPS_CENTER_AUTH_ENABLED` | `false` | When `true`, mutation endpoints require `Authorization: Bearer <token>` |
| `OPS_CENTER_API_TOKEN` | unset | Expected bearer token value |
| `OPS_CENTER_ENABLE_ADHOC_CHECKS` | `false` | When `true`, `POST /api/v1/checks/run` is allowed |
| `PLATFORMINIT_CHECK_RESULTS_DB` | unset | Filesystem path for the SQLite database |

All four variables default to safe local-dev values so the API runs without
any environment configuration.

### Ad-hoc check execution

Ad-hoc plugin execution (`POST /api/v1/checks/run`) is **disabled by default**
(`OPS_CENTER_ENABLE_ADHOC_CHECKS=false`). Set to `"true"` to enable.
Registered check execution (`POST /api/v1/checks/{check_id}/run`) is
unaffected by this flag.

When enabled, ad-hoc commands are validated against a strict allow-list:
- The executable must reside under `/usr/lib/nagios/plugins/`.
- Path traversal (`..`) is rejected.
- Each argument is capped at 512 characters.
- The command list is capped at 20 elements.
- Shell strings are rejected (must be a JSON array of strings).
- Timeout is capped at 30 seconds.

## Local development

```bash
make test
make check-plugins
make dev-api
make dev-ui
```

## Container builds (Podman)

Build and run the backend API image:

```bash
podman build -t ops-center-api -f backend/Containerfile backend/
podman run -d --name ops-center-api -p 8000:8000 ops-center-api
```

Build and run the frontend UI image:

```bash
podman build -t ops-center-ui -f frontend/Containerfile frontend/
podman run -d --name ops-center-ui -p 8080:8080 ops-center-ui
```

Smoke-test the running containers:

```bash
curl -s http://localhost:8000/healthz
curl -s http://localhost:8080/
```

> **Note:** These builds do not require Docker Desktop. Only Podman (or an
> equivalent OCI-compatible runtime) is needed. No secrets are baked into the
> images.

## Helm chart

A Helm chart for deploying Ops Center to Kubernetes is available under
[`charts/platforminit-ops-center/`](charts/platforminit-ops-center/Chart.yaml).

### Lint the chart

```bash
helm lint charts/platforminit-ops-center/
```

### Render templates locally

```bash
helm template ops-center charts/platforminit-ops-center/ \
  --values deploy/dev/values.yaml \
  --namespace platforminit-ops-center-dev
```

### Deploy to dev (dry-run first)

```bash
helm upgrade --install ops-center charts/platforminit-ops-center/ \
  --values deploy/dev/values.yaml \
  --namespace platforminit-ops-center-dev \
  --create-namespace \
  --dry-run
```

> **Note:** Ingress is disabled by default. Enable it in
> [`deploy/dev/values.yaml`](deploy/dev/values.yaml) when a domain and TLS
> certificate are available for the dev environment. No real secrets are
> included in the chart — use external secret management (e.g. SealedSecrets,
> External Secrets Operator) for production.

## Security notes

### Authentication

The API supports a lightweight bearer-token authentication guard controlled by
two environment variables:

- `OPS_CENTER_AUTH_ENABLED` — set to `"true"` to require authentication on
  mutation endpoints (default: `"false"` for local development).
- `OPS_CENTER_API_TOKEN` — the expected bearer token value.

When enabled, the following endpoints require `Authorization: Bearer <token>`:
- `POST /api/v1/checks/run`
- `POST /api/v1/checks/{check_id}/run`
- `POST /api/v1/scheduler/run`
- `POST /api/v1/checks/{check_id}/acknowledge`
- `POST /api/v1/checks/{check_id}/comments`
- `POST /api/v1/checks/{check_id}/downtimes`

Read-only endpoints (`GET /healthz`, `GET /api/v1/checks`, etc.) remain
unauthenticated for MVP convenience.

### Ad-hoc check execution

Ad-hoc plugin execution (`POST /api/v1/checks/run`) is gated behind
`OPS_CENTER_ENABLE_ADHOC_CHECKS` (default: `"false"`). Set to `"true"` to
enable. Registered check execution (`POST /api/v1/checks/{check_id}/run`) is
unaffected.

### Image tags

Production deployments **must** use immutable version tags or digests instead
of mutable tags like `latest`. See [`deploy/dev/values.yaml`](deploy/dev/values.yaml)
for the dev defaults.

### Ingress TLS

When `ingress.enabled=true`, the Helm chart requires `ingress.tls` to be
configured with at least one host/secretName entry. The chart will fail to
render if TLS is missing.

### Database path

The backend reads the database path from the `PLATFORMINIT_CHECK_RESULTS_DB`
environment variable. The Helm chart has been updated to use this variable
(not `OPS_CENTER_DB_PATH`).

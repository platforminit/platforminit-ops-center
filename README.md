# PlatformInit Ops Center

Standalone operations monitoring component for PlatformInit.

## Goals

- Nagios-compatible plugin runner
- CheckMK/Nagios-style host and service state model
- Operator-focused Problems view
- Native SSO support
- GitOps-friendly deployment
- Release artifact deployment to platforminit-dev-01

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

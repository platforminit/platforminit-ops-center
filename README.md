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

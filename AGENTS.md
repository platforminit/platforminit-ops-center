# PlatformInit Ops Center Agent Rules

## Scope

This repository contains the standalone PlatformInit Ops Center product.

## Hard rules

- Do not introduce secrets, tokens, kubeconfigs, SSH keys, or real customer data.
- Do not push directly to main.
- Prefer small, reviewable branches.
- All plugin execution code is security-sensitive.
- Any subprocess/plugin runner change requires tests.
- Any auth/OIDC/RBAC change requires explicit security review.
- Keep repository changes minimal and targeted.

## Architecture baseline

- Backend: FastAPI.
- Frontend: React/Vite.
- MVP database: SQLite.
- Plugin compatibility target: Nagios Plugin API.
- Container runtime for local dev: rootless Podman.
- Deployment target: Kubernetes via Helm chart.

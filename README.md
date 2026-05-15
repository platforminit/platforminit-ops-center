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


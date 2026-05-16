---
name: platforminit-helm-container-release
description: Use when changing Containerfiles, Helm charts, deploy values, release smoke tests, or packaging documentation.
---

# PlatformInit Helm and Container Release Skill

## Repository boundary

Work only in:

`/mnt/d/SYSADMIN/platforminit-ops-center`

Never inspect or modify the parent `D:/SYSADMIN` workspace globally.

## Required WSL command wrapper

Use this exact pattern for Linux commands:

```bash
wsl -d Ubuntu-22.04 -- bash -lc 'source "$HOME/.nvm/nvm.sh" && nvm use --silent default && export UV_LINK_MODE=copy && cd /mnt/d/SYSADMIN/platforminit-ops-center && <COMMAND>'
```

Do not use plain Linux commands from PowerShell.

## Token discipline

- Read only files needed for the task.
- Do not paste full successful logs.
- If verification passes, report only the summary.
- If verification fails, include only the failing section.
- Prefer changed-files-only review unless this is an explicit OWASP/full-repo review.

## Purpose

Keep packaging and deployment safe for PlatformInit Ops Center MVP.

## Rules

- Do not add real secrets.
- Containers should run non-root where practical.
- Do not use mutable `latest` tags in dev values.
- Ingress must be disabled by default.
- If ingress is enabled, TLS must be required or fail clearly.
- Keep `PLATFORMINIT_CHECK_RESULTS_DB` aligned between backend and Helm.
- Do not run `kubectl`, `helm`, or deploy commands unless explicitly approved.
- Prefer template/lint/smoke documentation over real deployment in feature branches.

## Required checks

- `make verify`
- Container/Helm smoke only if safe make targets exist
- README updated for operator deployment assumptions

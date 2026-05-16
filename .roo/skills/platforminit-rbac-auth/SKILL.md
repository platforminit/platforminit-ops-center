---
name: platforminit-rbac-auth
description: Use when adding or modifying bearer-token auth, role guards, viewer/operator/admin authorization, or future SSO boundaries.
---

# PlatformInit Auth and RBAC Skill

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

Implement local-dev-safe auth and future-compatible RBAC.

## Rules

- Local dev may default auth disabled, but this must be explicit and documented.
- When auth is enabled, mutation routes must require authentication.
- Viewer/operator/admin responsibilities must remain clear.
- Ad-hoc execution requires admin and explicit feature flag.
- Do not implement full OIDC unless explicitly requested.
- Do not hardcode production secrets.

## Minimum permission model

- viewer: read checks/problems/history/inventory
- operator: run registered checks, acknowledge, comment, downtime
- admin: scheduler trigger, ad-hoc execution if feature flag enabled

## Required tests

- auth disabled behavior
- missing token
- invalid token
- valid token
- role denied
- role allowed

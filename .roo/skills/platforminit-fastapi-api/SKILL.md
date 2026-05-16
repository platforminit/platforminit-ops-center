---
name: platforminit-fastapi-api
description: Use when adding or modifying FastAPI endpoints, request/response models, validation, or API tests.
---

# PlatformInit FastAPI API Skill

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

Create small, maintainable FastAPI API changes for PlatformInit Ops Center.

## Rules

- Prefer domain-specific API modules under `backend/app/api/`.
- Keep `backend/app/main.py` focused on app assembly and route registration.
- Use Pydantic models for request and response validation.
- Never accept shell command strings.
- Keep public response models separate from internal/debug models when data may be sensitive.
- Add tests under `backend/tests/`.
- Do not introduce real secrets.
- Do not make unrelated frontend, Helm, or container changes.

## Verification

Run:

```bash
wsl -d Ubuntu-22.04 -- bash -lc 'source "$HOME/.nvm/nvm.sh" && nvm use --silent default && export UV_LINK_MODE=copy && cd /mnt/d/SYSADMIN/platforminit-ops-center && make verify'
```

## Final response

Keep under 40 lines:
- changed files
- API endpoints changed
- tests added
- verification result
- known limitations

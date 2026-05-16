---
name: platforminit-frontend-operator-ui
description: Use when adding React/Vite operator-facing pages such as Problems, Checks, Check detail, Inventory, or action forms.
---

# PlatformInit Frontend Operator UI Skill

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

Build simple, operator-first UI for monitoring workflows.

## Rules

- Use relative API paths by default through `import.meta.env.VITE_API_BASE ?? ""`.
- Do not hardcode `http://localhost`.
- Do not introduce secrets into frontend code.
- Do not use `dangerouslySetInnerHTML`.
- Show loading, empty, and error states.
- Keep UI simple and readable.
- Do not add large UI libraries without explicit approval.

## Expected pages

- Problems
- Checks
- Check detail/history
- Inventory
- Operator actions

## Verification

Frontend lint and build must pass through `make verify`.

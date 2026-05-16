---
name: platforminit-sqlite-state-store
description: Use when adding or modifying SQLite persistence, latest check state, history, problems, operator actions, inventory, or schema initialization.
---

# PlatformInit SQLite State Store Skill

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

Implement SQLite-backed MVP state safely and predictably.

## Rules

- Use parameterized SQL queries only.
- Keep DB path configurable through `PLATFORMINIT_CHECK_RESULTS_DB` unless a new config is explicitly approved.
- Do not create unbounded result queries.
- Use default limits and maximum limits for history/list endpoints.
- Do not store secrets.
- Store operational history and audit-friendly timestamps.
- Keep store code in `backend/app/store/`.

## Required tests

- empty state
- insert/read path
- latest state
- history limit and max limit
- unknown check IDs
- persistence behavior with temporary DB path

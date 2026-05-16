---
name: platforminit-operator-workflow
description: Use when implementing acknowledge, comments, downtime, problem lifecycle, audit fields, or operator actions.
---

# PlatformInit Operator Workflow Skill

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

Keep monitoring operator workflows clear and audit-friendly.

## Rules

- Acknowledge must not delete or hide the underlying problem.
- Downtime must mark or annotate problems, not erase check history.
- Comments and reasons must be non-empty and length-bounded.
- Operator fields must be validated even before full SSO exists.
- Store timestamps for every operator action.
- Read models should clearly show acknowledged and in_downtime state.

## Required tests

- acknowledge
- unacknowledge if implemented
- comment validation
- downtime create/list/cancel
- problem response includes action state
- invalid unknown check ID handling

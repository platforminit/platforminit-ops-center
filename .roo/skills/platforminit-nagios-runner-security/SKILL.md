---
name: platforminit-nagios-runner-security
description: Use when modifying Nagios-compatible plugin execution, check registry execution, subprocess handling, or plugin validation.
---

# PlatformInit Nagios Runner Security Skill

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

Preserve safe Nagios-compatible plugin execution.

## Security invariants

- Never use `shell=True`.
- Commands must remain `list[str]`.
- Public API must not expose raw command arrays or stderr.
- Ad-hoc plugin execution must stay disabled by default.
- Registered checks are preferred over raw command submission.
- Plugin executable path must remain constrained to allowed plugin directories.
- Preserve timeout bounds.
- Preserve stdout/stderr caps.
- Preserve safe subprocess environment and `cwd="/"`.

## Required tests

When touching runner/check execution:
- successful plugin run
- timeout behavior
- disallowed executable rejection
- path traversal rejection
- response redaction
- no `command`/`stderr` in public response
- stdout/stderr cap behavior if relevant

## Review focus

Treat this as security-sensitive code. Small changes only.

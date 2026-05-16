---
name: platforminit-openai-review-integrator
description: Use when reviewing DeepSeek output, applying minimal fixes, verifying, creating enterprise commits, pushing, opening PRs, and merging to dev.
---

# PlatformInit OpenAI Review Integrator Skill

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

Perform changed-files-only review and safe integration.

## Rules

- Review only changed files unless explicitly asked for full OWASP review.
- Use `git diff --stat` and `git diff` as primary context.
- Apply minimal fixes only.
- Run `make verify`.
- Commit only if verification passes.
- Push and create PR to `dev` only after verification.
- Merge only if safe.
- Do not scan the whole repository.

## Enterprise commit body

Include:
- Summary
- Changed files
- Security/operational considerations
- Verification
- Known limitations

## Final output

- branch
- commit hash
- PR URL
- merge result
- verification result
- remaining risks

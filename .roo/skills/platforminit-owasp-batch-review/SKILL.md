---
name: platforminit-owasp-batch-review
description: Use only after 5 merged feature cycles or before a release to perform full repository OWASP review.
---

# PlatformInit OWASP Batch Review Skill

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

Perform a full repository security review only at batch gates.

## Use only when

- after 5 feature merges
- before release
- explicitly requested by the human operator

## Standards

- OWASP Top 10
- OWASP API Security Top 10
- OWASP ASVS principles where applicable
- subprocess execution safety
- auth/RBAC readiness
- input validation
- output redaction
- secret handling
- supply-chain/container risk
- Helm/Kubernetes configuration safety
- frontend security

## Output

- Executive Summary
- Findings by severity
- OWASP mapping
- affected files
- risk
- minimal fix prompt
- positive observations
- recommended fix batch
- merge/release recommendation

Do not modify files in review mode.

# PlatformInit Roo Workspace Rules

Repository boundary:
- Work only in `/mnt/d/SYSADMIN/platforminit-ops-center`.
- Do not inspect or modify the parent `D:/SYSADMIN` workspace globally.
- Do not read unrelated repositories in the multi-root VS Code workspace.

Terminal rule:
- Linux commands must use WSL.
- Required command wrapper:
  `wsl -d Ubuntu-22.04 -- bash -lc 'source "$HOME/.nvm/nvm.sh" && nvm use --silent default && export UV_LINK_MODE=copy && cd /mnt/d/SYSADMIN/platforminit-ops-center && <COMMAND>'`

Token discipline:
- Changed-files-only review for feature reviews.
- Full repository OWASP review only after 5 feature merges or when explicitly requested.
- Do not paste full successful logs.
- If verification passes, summarize the result only.
- If verification fails, include only the failing section.
- DeepSeek final output must be under 40 lines.

Security:
- Never introduce secrets, tokens, kubeconfigs, SSH keys, or customer data.
- No `shell=True` for plugin execution.
- No raw command/stderr exposure in public API responses.
- Ad-hoc check execution remains disabled by default.

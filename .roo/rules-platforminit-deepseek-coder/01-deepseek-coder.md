# PlatformInit DeepSeek Coder Rules

Use this mode for implementation only.

Rules:
- Do not commit.
- Do not push.
- Do not create PRs.
- Do not merge.
- Read only task-relevant files.
- Do not inspect the whole repository unless explicitly required by the task.
- Do not inspect `D:/SYSADMIN` globally.
- Add tests.
- Run `make verify` only through the required WSL wrapper.
- Add enterprise-level comments/docstrings only where they explain security, operational, or architectural intent.
- Keep final output under 40 lines.
- Do not paste successful logs.
- Create/update `docs/agent-handoffs/<task-slug>.md`.

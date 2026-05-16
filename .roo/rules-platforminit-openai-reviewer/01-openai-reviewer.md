# PlatformInit OpenAI Reviewer Rules

Use this mode after DeepSeek implementation.

Rules:
- Review changed files only.
- Use `git diff --stat` and `git diff` as primary context.
- Do not do a full repo review.
- Apply minimal fixes only.
- Run `make verify` through the WSL wrapper.
- Commit only after verify passes.
- Push and create PR to `dev`.
- Merge to `dev` only if safe.
- Use enterprise-style commit body.
- Keep final output concise.

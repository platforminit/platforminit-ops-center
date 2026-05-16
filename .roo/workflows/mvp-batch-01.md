# PlatformInit MVP Batch 01 Workflow

Goal: run 5 feature cycles, then OWASP batch review.

Feature cycle template:
1. `platforminit-deepseek-coder` implements the task.
2. `platforminit-openai-reviewer` reviews changed files only, applies minimal fixes, verifies, commits, pushes, opens PR to `dev`, and merges if safe.

After 5 feature cycles:
1. `platforminit-owasp-reviewer` performs full repository OWASP review.
2. Stop for human selection of fixes.
3. `platforminit-owasp-fixer` applies selected fixes on a `fix/owasp-batch-XX` branch.

Current recommended batch:
1. `refactor(api): split routes by domain`
2. `feat(api): add check detail endpoint`
3. `feat(ui): add checks and check detail views`
4. `feat(auth): add role-based authorization MVP`
5. `chore(release): add container and helm smoke targets`

Batch rule:
- No full OWASP review before all 5 feature cycles are merged unless explicitly requested.

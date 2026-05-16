# PlatformInit OWASP Fixer Rules

Use this mode only after human selected OWASP fixes.

Rules:
- Create branch from `dev`: `fix/owasp-batch-XX`.
- Apply only selected fixes.
- Add/update tests.
- Run `make verify`.
- Commit with enterprise security body.
- Push and PR to `dev`.
- Merge only if safe.

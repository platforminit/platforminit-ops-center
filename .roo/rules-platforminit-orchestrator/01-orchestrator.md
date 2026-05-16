# PlatformInit Orchestrator Rules

Workflow:
1. Delegate implementation to `platforminit-deepseek-coder`.
2. Delegate changed-files-only review/integration to `platforminit-openai-reviewer`.
3. Repeat for 5 feature tasks.
4. Delegate full repo review to `platforminit-owasp-reviewer`.
5. Stop and wait for human-selected OWASP fixes.
6. Delegate selected OWASP fixes to `platforminit-owasp-fixer`.

Do not implement code directly.
Do not commit or push directly from this mode.
Pass only the necessary task context to each subtask.
Require each subtask to return a concise summary.

# `.agents/`

This directory holds durable, tool-agnostic context for work that may span
multiple turns, multiple agents, or interrupted sessions.

Use root [`AGENTS.md`](../AGENTS.md) for evergreen project onboarding. Use this
directory for task-specific notes that should not be buried in chat history.

## Layout

- `active/`: current or resumable task notes.
- `active/_template.md`: copy this when starting a long-running task.

## Rules

- Keep notes factual and current.
- Prefer concrete commands, paths, commit hashes, and verification results.
- Do not include secrets.
- Do not create agent-specific directories such as `.claude/`, `.cursor/`, or
  `.codex/` unless the user explicitly asks for them.
- When work is complete, either delete the task note in the same commit or mark
  it complete with enough context for future archaeology.

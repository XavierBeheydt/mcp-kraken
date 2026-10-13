# .agents — canonical agent assets

This directory is the canonical home for extra AI-agent assets: subagents,
slash commands, tool-specific settings.

- `AGENTS.md` (repo root) is the single source of truth for instructions.
- `CLAUDE.md` (repo root) is a symlink to `AGENTS.md` — do not edit it.
- Claude Code reads this directory through the committed symlink
  `.claude -> .agents`. Like `CLAUDE.md`, this symlink is part of the repo,
  so a fresh clone is ready to use by AI agents as-is.

Commit changes here (`.agents/`), never under `.claude/`.

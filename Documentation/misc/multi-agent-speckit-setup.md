# Multi-Agent Spec-Kit Setup

This project uses [Spec-Kit](https://github.com/github/spec-kit) with **both Claude Code and Gemini CLI** as interchangeable coding agents. Spec-Kit's out-of-the-box install assumes a single agent per project, so several adjustments were made to keep the two agents in sync and to remove behaviors we didn't want. This document records what was changed and why.

## Goals

1. Either agent can run any `/speckit.*` command and produce consistent results.
2. A single shared context file — `AGENTS.md` — so spec/plan references don't drift between agents.
3. No automatic git operations (branching, auto-commits) triggered by Spec-Kit commands.
4. The hook framework remains available for future user-defined hooks (e.g., docs updates after implementation).

## Canonical context file: `AGENTS.md`

`AGENTS.md` is the single source of truth for project-wide agent guidance.

- `CLAUDE.md` is a one-line forwarder: `@AGENTS.md` (Claude Code's native import syntax).
- `GEMINI.md` is a symlink to `AGENTS.md` (Gemini CLI does not auto-load `AGENTS.md` and has no import directive equivalent to Claude's `@`).
- `AGENTS.md` contains the `<!-- SPECKIT START --> ... <!-- SPECKIT END -->` marker block. `/speckit.plan` rewrites the content between those markers to point at the current feature's `plan.md`.

Both `/speckit.plan` implementations were edited to target `AGENTS.md` instead of their agent-specific file:
- `.claude/skills/speckit-plan/SKILL.md` — `CLAUDE.md` → `AGENTS.md`
- `.gemini/commands/speckit.plan.toml` — `GEMINI.md` → `AGENTS.md`

Net effect: regardless of which agent runs `/speckit.plan`, the marker block in `AGENTS.md` is updated and both agents see the new pointer.

## Git extension removal

Spec-Kit ships a `git` extension that registers mandatory and optional hooks for nearly every command (`before_specify` auto-creates a feature branch, `after_*` prompts to commit, etc.). We don't want Spec-Kit managing branches or commits — branching cadence is a human decision, and auto-commit prompts add noise.

Removed:
- `.claude/skills/speckit-git-feature/`, `-validate/`, `-remote/`, `-initialize/`, `-commit/` — the Claude-side slash commands.
- `.specify/extensions/git/` — the extension source directory used by the installer.
- The git entry in `.specify/extensions/.registry` (registry now holds `"extensions": {}`).
- All hook entries in `.specify/extensions.yml` (now `hooks: {}`).

The `/speckit.*` commands still run their "check for hooks" preamble — they just find an empty map and continue silently. No extra overhead, no prompts.

Side effect to note: `/speckit.specify` no longer auto-creates feature branches. It still creates numbered spec directories (`specs/NNN-name/`) because numbering reads `init-options.json.branch_numbering` directly, independent of git. Create feature branches manually when you want them.

## Can you still add custom hooks?

Yes. The hook framework is independent of the git extension.

The framework consists of:
- `.specify/extensions.yml` — the hook registry.
- Pre/post-hook check blocks embedded in every `/speckit.*` command file.

To add, for example, a "regenerate docs after implementation" hook:

1. Create the slash command for both agents:
   - `.claude/skills/speckit-docs-update/SKILL.md`
   - `.gemini/commands/speckit.docs.update.toml`
2. Register it in `.specify/extensions.yml`:
   ```yaml
   hooks:
     after_implement:
       - extension: docs
         command: speckit.docs.update
         enabled: true
         optional: true
         prompt: Regenerate documentation?
         description: Update docs after implementation
         condition: null
   ```
3. Optionally add a matching extension entry to `.specify/extensions/.registry`.

Both agents will pick up the new hook on their next `/speckit.implement` run.

## What `init-options.json` actually affects

Metadata-only at runtime — do not rely on these values to drive behavior.

Tested by grep: only one key, `branch_numbering`, is read at runtime (by `/speckit.specify` and previously by the git extension). The fields `ai`, `context_file`, `integration`, `preset`, `script`, `here`, `speckit_version` are recorded by the `specify` CLI at install time and used only when re-running `specify init` / upgrades. They do not influence how either agent executes commands.

We left `init-options.json` largely untouched. Its `"ai": "gemini"` / `"context_file": "GEMINI.md"` values are historical bookkeeping from the last `specify init` run and do not reflect the actual multi-agent setup.

## Re-running `specify init` will undo some of this

If you ever run `specify init` or a Spec-Kit CLI upgrade, the installer may:
- Reinstall the `git` extension (restoring `.specify/extensions/git/` and the agent-side slash commands).
- Repopulate `.specify/extensions.yml` with git hooks.
- Rewrite `/speckit.plan` to target `CLAUDE.md` or `GEMINI.md` again.

To recover, re-apply the changes documented above. Consider reviewing the installer output before accepting any reinstall.

## Files changed (summary)

| File | Change |
|---|---|
| `.specify/extensions.yml` | Cleared `installed` and `hooks` |
| `.specify/extensions/.registry` | Emptied `extensions` map |
| `.specify/extensions/git/` | Deleted |
| `.claude/skills/speckit-git-*` (5 dirs) | Deleted |
| `.claude/skills/speckit-plan/SKILL.md` | `CLAUDE.md` → `AGENTS.md` in agent-context update step |
| `.gemini/commands/speckit.plan.toml` | `GEMINI.md` → `AGENTS.md` in agent-context update step |
| `CLAUDE.md` | Reduced to `@AGENTS.md` |
| `GEMINI.md` | Replaced with symlink → `AGENTS.md` |
| `AGENTS.md` | Added `<!-- SPECKIT START/END -->` marker block |

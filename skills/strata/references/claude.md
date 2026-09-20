# Claude Code configuration

Read this reference only for Claude Code installation, routing, or troubleshooting.

## Recommended roles

| Agent | Model alias | Effort | Tools | Use |
|---|---|---|---|---|
| Default primary | `opus[1m]` | `xhigh` | session permissions | Goal ownership, integration |
| `haiku-scout` | `haiku` | inherited | `Read, Grep, Glob` | Locate paths and evidence |
| `sonnet-worker` | `sonnet` | `xhigh` | read/write/bash | Ordinary bounded implementation |
| `opus-worker` | `opus` | `xhigh` | read/write/bash | Complex/high-risk implementation |
| `opus-reviewer` | `opus` | `xhigh` | read-only tools | Consequential review |
| `fable-controller` | `fable` | `xhigh` | session permissions | Explicit highest-tier main session |
| `fable-worker` | `fable` | `xhigh` | read/write/bash | Exceptional long implementation |
| `fable-reviewer` | `fable` | `xhigh` | read-only tools | Exceptional high-consequence review |

Aliases resolve according to provider and can change. Pin full model IDs only when reproducibility and provider rollout require it.

## Concurrency and nesting

| Control | Mechanism | Default | Strata position |
|---|---|---|---|
| Concurrent subagents | `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` | 20 | Leave the client default; the policy budget of three active agents is the working limit |
| Spawn depth | `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | 3 layers below the main conversation | Set to `1` so the no-descendant invariant is enforced by the client, not only by instructions |

- Claude Code's cap is far above the default budget, so the budget is a deliberate policy choice about write safety and synthesis capacity rather than a client restriction. Raise it only by the checklist in [scaling.md](scaling.md).
- A spawn past the cap fails with `Concurrent subagent limit reached` and instructs no retry. Queue the packet into the next wave.
- Forks occupy a slot while running, and resuming a completed subagent takes a fresh slot without a limit check, so a resume-heavy plan can exceed the intended budget without any client error.
- Sessions running at the maximum effort level are exempt from the concurrent cap. There the stated budget is the only limit, so state the number before dispatching.
- Both variables take a positive whole number and belong in the `env` block of the settings file being merged. `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH = 1` disables nesting entirely.

## Files

- `../assets/templates/claude/settings-snippet.json`
- `../assets/templates/claude/CLAUDE-snippet.md`
- `../assets/templates/claude/agents/*.md`

Personal skills and agents live in `~/.claude/skills/` and `~/.claude/agents/`; project equivalents live in `.claude/skills/` and `.claude/agents/`.

## Merge notes

- User settings are `~/.claude/settings.json`; shared project settings are `.claude/settings.json`; personal project overrides are `.claude/settings.local.json`.
- Merge JSON keys. Never replace existing `permissions`, `plugins`, `hooks`, `env`, or organization-defined controls. Add `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` into the existing `env` object instead of replacing it, and leave an existing concurrency variable alone unless the user asked for a different ceiling.
- `effortLevel` accepts persistent values through `xhigh`; `max` is session-only. The templates deliberately use `xhigh` for the main session and all coding/review agents.
- Frontmatter `effort` overrides the session level unless an environment variable or managed control takes precedence.
- Some third-party providers currently resolve `sonnet` or `opus` aliases to 4.6-class models that do not support `xhigh`; Claude Code lowers the request to the highest supported level. Installation is complete only after `/status` or equivalent evidence confirms the resolved model and effort. Otherwise pin an organization-approved full model ID that supports `xhigh`, or report this invariant as unmet.
- Read-only agents list only `Read`, `Grep`, and `Glob`; workers list editing and Bash tools. Tool lists reduce accidental capability but do not grant permission beyond the parent session.
- If the agents directory did not exist when the session started, restart Claude Code after first installation. Environment changes in settings also require a new session.

## Fable

Fable requires a sufficiently recent Claude Code version and account/organization access. It is explicit rather than default because availability and billing behavior vary.

- Start the highest-tier main session with `claude --agent fable-controller`.
- Delegate `fable-worker` or `fable-reviewer` only after the user explicitly selected Fable or availability/approved usage credits are known.
- Interactive Claude Code can request consent before billing usage credits. Non-interactive print-mode and Agent SDK flows may bill without that prompt; do not select Fable there without prior authorization.
- Authentication, billing, rate-limit, request-size, and transport errors do not activate model fallback. If Fable is unavailable, stop the branch and return control without retry loops.

## Official sources

- <https://code.claude.com/docs/en/skills>
- <https://code.claude.com/docs/en/sub-agents>
- <https://code.claude.com/docs/en/env-vars>
- <https://code.claude.com/docs/en/model-config>
- <https://code.claude.com/docs/en/settings>

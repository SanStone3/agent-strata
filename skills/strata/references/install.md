# Installation workflow

Use this reference only when installing, upgrading, or changing scope.

## Scope map

| Client | Global | Project |
|---|---|---|
| Codex skill | `~/.agents/skills/strata/` | `<repo>/.agents/skills/strata/` |
| Codex config | `~/.codex/config.toml` | `<repo>/.codex/config.toml` |
| Codex agents | `~/.codex/agents/` | `<repo>/.codex/agents/` |
| Codex rules | `~/.codex/AGENTS.md` | `<repo>/AGENTS.md` |
| Claude skill | `~/.claude/skills/strata/` | `<repo>/.claude/skills/strata/` |
| Claude config | `~/.claude/settings.json` | `<repo>/.claude/settings.json` |
| Claude agents | `~/.claude/agents/` | `<repo>/.claude/agents/` |
| Claude rules | `~/.claude/CLAUDE.md` | `<repo>/CLAUDE.md` |

Codex's current official personal skill location is `~/.agents/skills/`. Existing environments may also expose legacy or installer-managed locations. Use the active client's discovery output rather than relocating a working install without need.

A shared personal package at `~/.agents/skills/strata/` can serve CLI and IDE instances on the same machine when both discover that location. Custom role definitions, config and bindings instead belong to each client's **actual** `CODEX_HOME`, which may differ from `~/.codex`. Confirm discovery through each matching client's `skills/list`; do not assume the VS Code extension uses the shell's home or executable. See [auth-context.md](auth-context.md).

## Safe merge procedure

1. Identify the home directory or repository root explicitly. Never use an unresolved variable as a destructive target.
2. Read every target file and list same-name Agent definitions.
3. Record client version and current model. For Claude, check whether Fable appears or can be selected only if the user wants Fable.
4. Create timestamped backups of existing files. Do not back up secrets into the repository.
5. Merge syntax-aware:
   - TOML: add or update only the requested keys/tables.
   - JSON: preserve every unrelated object and array, and add environment keys inside the existing `env` object.
   - Markdown rules: append or update one delimited `Layered Agent Orchestration` section.
   - Agent files: compare before replacement; preserve user customization or obtain direction.
6. For Codex, follow [model-routing.md](model-routing.md) to obtain the current catalog, preserve user pins, resolve and render all roles into a new staging directory. Merge the generated definitions and agent defaults, using the strongest eligible controller at `xhigh` unless explicitly pinned or preserved, while retaining context settings. Copy Claude templates independently. Never install bare Codex model-free source templates as resolved agents.
7. Configure the concurrency controls for the client:
   - Codex: pin `agents.max_concurrent_threads_per_session = 3` unless the user asked for a different ceiling, then verify the observed parallelism as described in [codex.md](codex.md).
   - Claude Code: set `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` to `1` so the no-descendant invariant is client-enforced, and leave the concurrent-subagent ceiling at the client default; see [claude.md](claude.md).
8. Parse all resulting files and run [validation.md](validation.md).
9. Inspect client status for the actually resolved model and effort. A requested `xhigh` is not sufficient evidence: if a Claude alias resolves to a model without `xhigh`, pin an organization-approved compatible full ID or report the invariant as unmet.
10. Report backups, changed paths, effective model/effort, effective concurrency cap and spawn depth, conflicts, and whether a new session is required.

## Boundaries

- Do not enable bypass permissions or widen tool allowlists.
- Do not raise a concurrency ceiling above the default budget unless the user asked for it, and never enable an unrelated feature flag to make a limit change take effect.
- Do not add API keys, usage credits, payment settings, or external bridge processes.
- Do not make Codex invoke Claude or Claude invoke Codex.
- Do not assume fallback handles authentication, billing, rate-limit, request-size, or transport errors.
- Do not commit global configuration. Project configuration may be committed only when the user requested shared project setup and project rules permit it.
- If a managed organization setting blocks a recommendation, report it as authoritative.

## AI-facing prompt

After installing this skill, a user can ask:

```text
Use strata to install Agent Strata for this client at global scope.
Inspect and back up the existing configuration, merge without overwriting unrelated settings,
keep coding workers at xhigh, keep the default concurrency budget, validate the result,
and do not configure cross-provider calls.
```

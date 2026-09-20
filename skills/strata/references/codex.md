# Codex configuration

Read this reference only for Codex installation, routing, or troubleshooting.

## Recommended roles

| Agent | Model | Effort | Mode | Use |
|---|---|---|---|---|
| Primary controller | `gpt-5.6-sol` | `xhigh` | inherited session | Goal ownership, decomposition, integration |
| `luna_scout` | `gpt-5.6-luna` | `medium` | read-only | Locate paths, dependencies, evidence |
| `luna_executor` | `gpt-5.6-luna` | `medium` | workspace-write | Exact mechanical operations only |
| `terra_worker` | `gpt-5.6-terra` | `xhigh` | workspace-write | Ordinary bounded implementation |
| `sol_worker` | `gpt-5.6-sol` | `xhigh` | workspace-write | Complex/high-risk implementation |
| `sol_reviewer` | `gpt-5.6-sol` | `xhigh` | read-only | Consequential final review |

The model family and effort values are verified against official documentation as of 2026-08-20. Recheck current docs when upgrading.

## Concurrency

`agents.max_concurrent_threads_per_session` caps concurrently open spawned-agent threads, excluding the primary. Left unset, Codex chooses its own default; the documented default is four threads including the root, so three spawned agents. That matches the Strata default budget, which is why the template pins `3` rather than relying on an unstated default.

Official sample configuration shows values such as `6`, and documented workflow examples use `6` and `8`, so higher values are supported. Raise the number only alongside the checklist in [scaling.md](scaling.md), because the client cap governs how many threads may open, not whether parallel writes are safe.

Verify the effective cap rather than the requested one:

1. Read the merged `[agents]` table in the configuration file actually being loaded, for the scope in use.
2. Dispatch a disposable read-only wave that requests one more agent than the intended budget and observe how many run at once.
3. If the observed parallelism does not match the configured key, the running build may resolve concurrency through its multi-agent v2 feature, where community reports place the honored key at `features.multi_agent_v2.max_concurrent_threads_per_session` and a legacy `agents.max_threads` is ignored. Confirm against the version's own documentation before changing feature tables, and never enable a feature flag merely to raise a limit.
4. Report the observed value as effective, and plan waves against it.

Codex resolves a wave by waiting until all requested results are available and then returning a consolidated response, so a wave's latency is its slowest packet. Keep packets in one wave comparable in size.

## Files

Recommended snippets and definitions:

- `../assets/templates/codex/config-snippet.toml`
- `../assets/templates/codex/AGENTS-snippet.md`
- `../assets/templates/codex/agents/*.toml`

Custom personal agents live in `~/.codex/agents/`; project agents live in `.codex/agents/`. Every file requires `name`, `description`, and `developer_instructions`.

## Merge notes

- `model_context_window = 1000000` and `model_auto_compact_token_limit = 900000` are an opinionated long-session baseline. Do not apply them when the selected model/account does not support that window.
- `max_concurrent_threads_per_session = 3` counts spawned threads, excluding the primary.
- The custom agent's model and reasoning values override defaults. Keep Worker and Reviewer files explicit so code/review remains `xhigh`.
- Subagents inherit current sandbox/approval policy and live runtime overrides. A custom agent's `sandbox_mode = "read-only"` is a useful default, not permission to ignore a broader parent override; the controller must still enforce read-only behavior.
- Project `.codex/` configuration loads only for trusted projects. Never mark a project trusted merely to complete installation without user intent.
- Current local Codex releases delegate after a direct request or applicable project/skill instruction. The installed skill and AGENTS rules provide that applicable instruction for suitable tasks.
- Codex has no documented switch that forbids descendant agents, so the no-descendant invariant rests on the agent definitions and the rules section. Keep both prohibitions present.

## Escalation

`terra_worker` stops and returns to the controller if the work crosses a public interface, security boundary, concurrency/lifecycle boundary, data migration, multiple subsystems, or otherwise needs Sol-level judgment. The controller rewrites the packet for `sol_worker`; it does not let Terra continue with expanded scope.

## Official sources

- <https://developers.openai.com/codex/subagents>
- <https://developers.openai.com/codex/config-basic>
- <https://developers.openai.com/codex/config-sample>
- <https://developers.openai.com/codex/skills>
- <https://developers.openai.com/api/docs/guides/latest-model>

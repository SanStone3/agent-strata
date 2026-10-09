# Codex configuration

Read this reference only for Codex installation, routing, or troubleshooting.

## Adaptive roles

Read [model-routing.md](model-routing.md) before resolving or dispatching models. The policy and live catalog produce concrete IDs; templates do not pin a generation.

| Agent | Capability tier | Effort | Mode | Use |
|---|---|---|---|---|
| Primary controller | GPT-6.1 Sol recommendation (user choice takes precedence) | `xhigh` | inherited session | Goal ownership, decomposition, integration |
| `scout` | efficient; GPT-6 Luna preferred | `medium` | read-only | Locate paths, dependencies, evidence |
| `executor` | efficient; GPT-6 Luna preferred | `medium` | workspace-write | Exact mechanical operations |
| `worker` | balanced | `xhigh` | workspace-write | Ordinary bounded implementation |
| `deep_worker` | balanced (Sol), deeper task packet | `xhigh` | workspace-write | Complex/high-risk implementation |
| `reviewer` | balanced (Sol), independent review | `xhigh` | read-only | Consequential final review |

Runtime model and effort overrides must follow the current native tool schema and fork restrictions. If overrides are unavailable, resolve and render definitions, merge them during installation/update, then verify client reload before dispatch. An unresolved role is not permission to lower effort or inherit an unknown model.

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

- Resolve the controller at the reviewed Sol tier and `xhigh`; honor explicit controller pins or `--preserve-primary`. Preserve context window and auto-compact settings. Model discovery does not prove context-window entitlement.
- `max_concurrent_threads_per_session = 3` counts spawned threads, excluding the primary.
- Rendered custom agents contain explicit model and reasoning values. Keep Workers and Reviewers at `xhigh`; do not copy unresolved source templates into a live installation.
- Subagents inherit current sandbox/approval policy and live runtime overrides. A custom agent's `sandbox_mode = "read-only"` is a useful default, not permission to ignore a broader parent override; the controller must still enforce read-only behavior.
- Project `.codex/` configuration loads only for trusted projects. Never mark a project trusted merely to complete installation without user intent.
- Current local Codex releases delegate after a direct request or applicable project/skill instruction. The installed skill and AGENTS rules provide that applicable instruction for suitable tasks.
- Codex has no documented switch that forbids descendant agents, so the no-descendant invariant rests on the agent definitions and the rules section. Keep both prohibitions present.

## Escalation

`worker` stops and returns to the controller if the work crosses a public interface, security boundary, concurrency/lifecycle boundary, data migration, multiple subsystems, or otherwise needs deep-worker judgment. The controller rewrites the packet for `deep_worker`; it does not let the ordinary worker continue with expanded scope.

## Official sources

- <https://developers.openai.com/codex/subagents>
- <https://developers.openai.com/codex/config-basic>
- <https://developers.openai.com/codex/config-sample>
- <https://developers.openai.com/codex/skills>
- <https://developers.openai.com/api/docs/guides/latest-model>

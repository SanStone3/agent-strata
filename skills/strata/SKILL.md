---
name: strata
description: Configure or run capability-tiered native subagent workflows for complex Codex or Claude Code tasks, with one controller, one writer by default, xhigh coding workers, an explicit concurrency budget with wave scheduling when more agents are genuinely needed, bounded task packets, and provider isolation. Use for multi-part work, noisy independent exploration, parallel write planning, high-risk review, or global/project installation of this orchestration pattern; do not use for small sequential or same-file tasks.
---

# Strata

Keep one primary controller responsible for the complete objective, authorization boundaries, project rules, conflict resolution, final validation, and delivery. Delegate only bounded work whose isolation or noise reduction justifies the coordination cost.

## Select the mode

- For installation or configuration, read [references/install.md](references/install.md), then read only the provider reference requested: [references/codex.md](references/codex.md) or [references/claude.md](references/claude.md).
- For live task orchestration, read [references/task-contract.md](references/task-contract.md).
- When one writer or three active agents are not enough, when a parallel wave must be planned, or when a client refuses a spawn, read [references/scaling.md](references/scaling.md).
- For an audit, upgrade, troubleshooting, or handoff, read [references/validation.md](references/validation.md).

When both providers are requested, configure them as two independent clients. Never create a Codex-to-Claude or Claude-to-Codex invocation path.

## Core invariants

1. Keep exactly one primary controller. It owns the user-facing result and does not delegate final accountability.
2. Default to a concurrency budget of at most three active subagents and one writer. The budget limits how many run at once, not how much work the task may contain; total packets are unbounded and scale by waves.
3. Raise the budget only by the checklist in [references/scaling.md](references/scaling.md): read-only fan-out, or one writer per verified disjoint write domain with frozen shared contracts, per-domain validation, and controller capacity to inspect every write. Otherwise serialize.
4. Keep scouts and reviewers read-only. A mechanical executor may write only when the transformation is exact and fully bounded.
5. Use `xhigh` for code implementation and consequential review. Lower effort is reserved for read-only scouting or purely mechanical execution.
6. Give each subagent one compact task packet with explicit scope, write domain, permissions, acceptance evidence, result budget, and stopping conditions.
7. Require structured, compressed results rather than raw logs or bulk file contents.
8. Project instructions and user authorization remain authoritative. Delegation does not broaden permission to edit, commit, push, deploy, spend credits, or contact external systems.
9. Subagents do not spawn subagents. Return missing authority, conflicts, or invalid assumptions to the controller. Where the client can enforce this mechanically, configure it rather than relying on instructions alone.
10. Do not use multiple agents for small, sequential, or same-file work where coordination overhead or write conflicts dominate.

## Route live work

Before delegating, classify the work:

- Fast read-only discovery -> `luna_scout` / `haiku-scout`.
- Exact mechanical operation -> `luna_executor` when using Codex; otherwise handle directly or use a tightly bounded worker.
- Ordinary bounded implementation -> `terra_worker` / `sonnet-worker` at `xhigh`.
- Cross-module, ambiguous, security-sensitive, concurrency-sensitive, lifecycle-sensitive, migration-sensitive, or expensive-to-rework implementation -> `sol_worker` / `opus-worker` at `xhigh`.
- Consequential final review -> `sol_reviewer` / `opus-reviewer` at `xhigh`.
- Exceptionally long, high-consequence Claude work -> `fable-worker`, with `fable-reviewer` for the final read-only pass, only when Fable is explicitly selected and availability or approved usage credits are confirmed. An explicit Fable main session starts as `claude --agent fable-controller`.

Do not delegate merely because a specialized agent exists. Continue locally when the task is small or when each step depends on the previous result.

## Run the workflow

1. Read applicable repository instructions and inspect current state before decomposing.
2. Identify independent workstreams, shared state, and required decision points, then partition writable paths into disjoint write domains and land any shared contract change in the controller first.
3. Assign only work that can be described with the task contract, and schedule the packets into waves that fit the budget.
4. Keep the controller productive on work that touches no domain while independent agents run; do not duplicate their assigned work.
5. At each wave gate, collect results, resolve contradictions against primary evidence, inspect all writes, and rewrite the next wave from the state that now exists.
6. Run only project-authorized validation, proportional to the risk: per domain during the waves, then across the combined change.
7. Deliver one coherent result with completed work, validation, residual risk, and any unresolved decision.

When a subagent discovers that its boundary is wrong, stop that packet and rewrite it. Do not let the subagent silently expand scope. When a wave gate shows the partition was wrong, stop the plan, not just the packet.

## Install or update configuration

Treat installation as a merge, not a copy operation:

1. Detect client, version, requested scope, account/model availability, existing configuration, rules, and agent definitions.
2. If scope is unspecified, infer global only from language such as “all projects” or “this computer”; otherwise use project scope when operating for one repository. Ask only when the choice remains materially ambiguous.
3. Back up each existing file before changing it.
4. Merge only the relevant keys and append a clearly delimited rules section. Preserve unrelated models, permissions, MCP servers, plugins, hooks, trust entries, and user customizations.
5. Install or update the provider-native agent files from `assets/templates/` after checking same-name conflicts.
6. Do not lower sandbox or permission controls, add credentials, or enable cross-provider execution.
7. Parse the resulting formats, run `scripts/validate.py` against the source or installed layout when possible, and confirm the client's actually resolved model, effort, and effective concurrency cap. If an alias resolves to a model that cannot run `xhigh`, pin an organization-approved compatible full ID or report that the coding-worker invariant remains unmet.
8. Report exact changes, effective rather than merely requested model/effort, the effective concurrency cap, and restart requirements.

The templates are opinionated recommendations, not authority to replace a user's selected model or incur paid usage. If a recommended model is unavailable, preserve the existing selection and report the gap.

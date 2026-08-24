---
name: layered-orchestration
description: Configure or run capability-tiered native subagent workflows for complex Codex or Claude Code tasks, with one controller, one writer by default, xhigh coding workers, bounded task packets, and provider isolation. Use for multi-part work, noisy independent exploration, high-risk review, or global/project installation of this orchestration pattern; do not use for small sequential or same-file tasks.
---

# Layered Orchestration

Keep one primary controller responsible for the complete objective, authorization boundaries, project rules, conflict resolution, final validation, and delivery. Delegate only bounded work whose isolation or noise reduction justifies the coordination cost.

## Select the mode

- For installation or configuration, read [references/install.md](references/install.md), then read only the provider reference requested: [references/codex.md](references/codex.md) or [references/claude.md](references/claude.md).
- For live task orchestration, read [references/task-contract.md](references/task-contract.md).
- For an audit, upgrade, troubleshooting, or handoff, read [references/validation.md](references/validation.md).

When both providers are requested, configure them as two independent clients. Never create a Codex-to-Claude or Claude-to-Codex invocation path.

## Core invariants

1. Keep exactly one primary controller. It owns the user-facing result and does not delegate final accountability.
2. Default to at most three active subagents and one writer. Parallelize read-heavy work first.
3. Keep scouts and reviewers read-only. A mechanical executor may write only when the transformation is exact and fully bounded.
4. Use `xhigh` for code implementation and consequential review. Lower effort is reserved for read-only scouting or purely mechanical execution.
5. Give each subagent one compact task packet with explicit scope, permissions, acceptance evidence, and stopping conditions.
6. Require structured, compressed results rather than raw logs or bulk file contents.
7. Project instructions and user authorization remain authoritative. Delegation does not broaden permission to edit, commit, push, deploy, spend credits, or contact external systems.
8. Subagents do not spawn subagents. Return missing authority, conflicts, or invalid assumptions to the controller.
9. Do not use multiple agents for small, sequential, or same-file work where coordination overhead or write conflicts dominate.

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
2. Identify independent workstreams, shared state, write ownership, and required decision points.
3. Assign only work that can be described with the task contract.
4. Keep the controller productive while independent agents run; do not duplicate their assigned work.
5. Collect results, resolve contradictions against primary evidence, and inspect all writes.
6. Run only project-authorized validation, proportional to the risk.
7. Deliver one coherent result with completed work, validation, residual risk, and any unresolved decision.

When a subagent discovers that its boundary is wrong, stop that packet and rewrite it. Do not let the subagent silently expand scope.

## Install or update configuration

Treat installation as a merge, not a copy operation:

1. Detect client, version, requested scope, account/model availability, existing configuration, rules, and agent definitions.
2. If scope is unspecified, infer global only from language such as “all projects” or “this computer”; otherwise use project scope when operating for one repository. Ask only when the choice remains materially ambiguous.
3. Back up each existing file before changing it.
4. Merge only the relevant keys and append a clearly delimited rules section. Preserve unrelated models, permissions, MCP servers, plugins, hooks, trust entries, and user customizations.
5. Install or update the provider-native agent files from `assets/templates/` after checking same-name conflicts.
6. Do not lower sandbox or permission controls, add credentials, or enable cross-provider execution.
7. Parse the resulting formats, run `scripts/validate.py` against the source or installed layout when possible, and confirm the client's actually resolved model and effort. If an alias resolves to a model that cannot run `xhigh`, pin an organization-approved compatible full ID or report that the coding-worker invariant remains unmet.
8. Report exact changes, effective rather than merely requested model/effort, and restart requirements.

The templates are opinionated recommendations, not authority to replace a user's selected model or incur paid usage. If a recommended model is unavailable, preserve the existing selection and report the gap.

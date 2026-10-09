---
name: strata
description: Configure or run cost-aware native subagent workflows for complex Codex or Claude Code tasks, with compact task packets, xhigh coding workers, an explicit concurrency budget, and provider isolation. Use for independent workstreams, scoped implementation, consequential review, or global/project setup; do not use for small sequential or same-file tasks.
---

# Strata

Keep one controller accountable for the objective, user choices, permissions, integration and final validation. Delegate only when specialization or isolated context saves more work than the handoff costs.

## Route work

Codex defaults to GPT-6.1 Sol for implementation and review, and GPT-6 Luna for simple discovery and mechanical execution. Do not automatically select GPT-5.6 Sol, Astra, legacy alternatives or unpriced successors. `automatic_models` in [assets/model-policy.json](assets/model-policy.json) is the reviewed automatic selection set; an explicitly user-approved pin is the exception, not an automatic fallback. See [references/cost-control.md](references/cost-control.md) for pricing and quality-preserving savings.

| Role | Default model | Effort | Scope |
|---|---|---|---|
| Main controller | user-selected; recommend GPT-6.1 Sol for a new chat | preserve selection | Plan, integrate, verify |
| `scout` | GPT-6 Luna | medium | Simple read-only evidence collection |
| `executor` | GPT-6 Luna | medium | Exact mechanical operations |
| `worker` | GPT-6.1 Sol | xhigh | Bounded implementation |
| `deep_worker` | GPT-6.1 Sol | xhigh | Ambiguous or high-risk implementation |
| `reviewer` | GPT-6.1 Sol | xhigh | Consequential independent read-only review |

Keep the model fixed for each existing Codex conversation/subagent. Do not try to change it during a turn, on resume, or by editing configuration. Select a model when creating a new child. If a packet exceeds its ability, return evidence and remaining scope to the controller; create a new bounded child if justified. Expensive-model escalation needs an explicit user choice; otherwise strengthen the evidence/validation or report the limit. Never claim equal capability across all models or guaranteed unchanged code quality.

Small, sequential or same-file tasks stay with the controller. Do not spawn a cheaper agent merely for a one-command task. For suitable independent work, autonomously choose the role and a compact packet; do not repeatedly ask whether to delegate.

## Fast path and context

When the current native tool exposes the installed role/model/effort and the task fits, dispatch directly. Do not re-read every guide, inspect helper source, run help or discover the entire catalog before each spawn. For missing/ambiguous bindings, use [references/model-routing.md](references/model-routing.md) and resolve once per execution context.

Keep the executing client's CODEX_HOME, executable, provider, profile, authentication and environment intact. Native children inherit that context. CLI ChatGPT login and IDE API-key login need separate bindings even with a shared skill package. For SSH, login differences or API compatibility errors, read [references/auth-context.md](references/auth-context.md). Never rotate credentials/providers to hide a failure.

## Execution and quality

1. Keep at most three active subagents and one writer by default. Three is a ceiling, not a target; additional packets run in waves. Raise the budget only with the disjoint-write-domain checklist in [references/scaling.md](references/scaling.md).
2. Give each child the goal, relevant file/symbol pointers, constraints, acceptance evidence, owned paths and a short result budget. Use [references/task-contract.md](references/task-contract.md) for writing or multi-workstream packets. Do not copy full chat history or whole-repository dumps. Include necessary contracts and evidence rather than truncating them to meet an arbitrary token cap.
3. Keep scouts/reviewers read-only. Freeze shared interfaces, schemas, manifests, lockfiles and generated artifacts before parallel writes. Subagents do not spawn descendants or independently commit, push, deploy, contact external parties or invoke another coding-agent provider.
4. Preserve xhigh for code and consequential review. Save tokens first through targeted reads, focused diffs, reused verified evidence and concise results. Run meaningful tests and inspect writes; do not remove acceptance checks to make a cheaper route look successful.
5. The controller stays productive on nonoverlapping work and does not duplicate a delegated search. Reuse a completed child's findings, not its entire transcript. Request follow-up only for a concrete gap or changed evidence.
6. Return findings/changes, paths, test outcomes and remaining risks. Include detailed logs only around a relevant failure. Use an independent reviewer when risk justifies it; avoid mandatory multi-agent review for trivial edits.
7. Report a short allocation and material progress/blocks. On conflicting writes or failed assumptions, inspect actual state and rewrite the packet; never blindly replay a writer or discard user work.

## Installation and maintenance

For installation read [references/install.md](references/install.md), then the requested provider reference: [references/codex.md](references/codex.md) or [references/claude.md](references/claude.md). Configure providers independently; Codex never invokes Claude and vice versa. Claude's native role/effort policy is unchanged by the Codex cost profile.

Back up and merge only relevant files. Share the skill at a user-discovered location, but render native definitions and save bindings in each actual CODEX_HOME. Preserve current main-session choice with `--preserve-primary`, context settings, credentials, endpoints, permissions and unrelated configuration. Defaults for future sessions do not change an active conversation.

Validate source and installed state with [references/validation.md](references/validation.md). Distinguish configured settings, live discovery and successful native inference. If model/effort capability is unverified or a required role is unresolved, report the gap rather than silently weakening the task.

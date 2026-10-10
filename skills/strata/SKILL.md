---
name: strata
description: Cost-aware native subagent orchestration for Codex or Claude Code, with bounded tasks, xhigh coding workers, a concurrency budget and provider isolation. Use for independent workstreams, implementation, review or setup; do not use for trivial sequential work.
---

# Strata

One controller owns quality, permissions, integration and delivery. Optimize total cost per accepted change, including rework; do not trade away necessary evidence or tests.

## Choose the smallest useful route

| Work | Codex route |
|---|---|
| Known file/symbol, literal search, trivial sequential task | Direct tools; no new agent |
| Bounded independent evidence collection | `scout`: GPT-6 Luna, medium, read-only |
| Exact mechanical operation | `executor`: GPT-6 Luna, medium |
| Implementation or complex analysis | `worker` / `deep_worker`: GPT-6.1 Sol, xhigh |
| Consequential independent review | `reviewer`: GPT-6.1 Sol, xhigh, read-only |

Read-only is not necessarily easy: architecture, security, concurrency and data invariants need Sol. Scouts report references, facts and uncertainties, not unsupported correctness judgments.

GPT-5.6 is removed: no selection, pin, custom-policy override, upgrade route or rendered role may invoke it. Automatic selection uses the reviewed Sol/Luna IDs in [assets/model-policy.json](assets/model-policy.json). Other expensive models require an explicit user-approved pin; availability alone is not approval.

## Execute efficiently

- Preserve the main model/effort chosen by the user. Recommend Sol for a new coding chat. Keep each conversation/subagent on its original model; escalation creates a new compact child, never a model switch on resume.
- Use verified native role/model/effort declarations directly. If a declared role still uses GPT-5.6, do not dispatch it. Resolve missing bindings once per context using [model-routing.md](references/model-routing.md); avoid repeated help, source audits or catalog discovery.
- Keep at most three active subagents and one writer by default. Three is a ceiling, not a target. Raise the budget only after the disjoint-write-domain checklist in [scaling.md](references/scaling.md).
- Give a compact packet: goal, relevant paths/contracts, constraints, owned write domain, acceptance checks and result budget. Reuse verified findings; do not duplicate another agent's search or copy full transcripts/logs. Details: [task-contract.md](references/task-contract.md).
- Keep scouts/reviewers read-only. Children do not spawn descendants, independently commit/push/deploy, expand scope or invoke another coding-agent provider. Preserve the current CODEX_HOME, auth, provider, profile and environment.
- Inspect returned changes and run meaningful validation. On a conflict or failed assumption, inspect actual state and rewrite the packet; do not blindly retry writers or erase user work. Announce allocation and material progress briefly.

## Read only the relevant guide

- Install/update: [install.md](references/install.md), then [Codex](references/codex.md) or [Claude](references/claude.md). Back up and merge; preserve unrelated settings and active main sessions with `--preserve-primary`. Configure providers independently.
- Separate logins, SSH, API summary/region failures: [auth-context.md](references/auth-context.md). Never copy credentials or switch providers to hide errors.
- Audit/verification: [validation.md](references/validation.md). Distinguish configuration, discovery and successful native inference; never dispatch unresolved roles.
- Price and context efficiency: [cost-control.md](references/cost-control.md). Claude's independent native policy is unchanged.

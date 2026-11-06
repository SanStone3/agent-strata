---
name: strata
description: Cost-aware native subagent orchestration for Codex or Claude Code. Choose models, task effort, parallelism and compact context for independent coding, research or review; do not use for trivial sequential work.
metadata:
  version: "2026.11.06"
---

# Strata

Optimize cost and elapsed time per accepted change, including context, retries and review. One controller owns integration and quality.

## Route by task

| Task | Codex starting point |
|---|---|
| Known path, short search, small sequential edit | Direct tools |
| Bounded extraction, search, summary or exact mechanical execution | Luna `low/medium`; `scout` read-only or `executor` |
| Coding and agent work with understood scope | Sol `medium`; `worker` |
| Readily checked scoped fix, supplied-material writing, vision or computer use | Terra `medium/high`; scoped `worker` |
| Cross-module diagnosis, architecture, security, concurrency or difficult implementation | Sol `high/xhigh`; `deep_worker` |
| Consequential independent review | Sol `high/xhigh`; `reviewer`, read-only |

These are starting points, not quality guarantees. Read-only work can need Sol. Terra's lower token price does not make Terra xhigh cheaper than Sol medium. Use [cost-control.md](references/cost-control.md) for dated evidence; retain required tests and evidence.

## Orchestrate

- The current CLI/App user selection owns the primary model and effort, including later user switches. Never restore a startup value or write primary settings during skill updates. Sol xhigh is a recommendation only. Children keep their creation model; escalation uses a new compact packet.
- Strata has no numeric agent cap. Choose useful parallelism from actual host capacity, resources, cost and synthesis capacity. Default to one writer; allow more only with disjoint paths, frozen contracts and independent checks. Queue excess work. See [scaling.md](references/scaling.md).
- Use the active native tool's verified model/effort list. Prefer explicit new-child overrides and history-free packets. Resolve missing bindings once through [model-routing.md](references/model-routing.md); avoid rediscovery on every task. Automatic choices: reviewed Sol, Terra and Luna; Astra needs an explicit approved pin. No GPT-5.6.
- Send goal, file/contract pointers, owned paths or read-only scope, constraints, checks, stop condition and a concise result budget. Reuse evidence; do not copy transcripts or duplicate searches. Return findings/changes, locations, tests and uncertainty. See [task-contract.md](references/task-contract.md) when boundaries are unclear.
- Scouts/reviewers are read-only. Children do not spawn descendants, expand scope, commit, push, deploy or invoke another coding-agent provider. Preserve CODEX_HOME, auth, provider and permissions. Inspect changes before integration; inspect partial state before retrying.

Read only what the task needs: [installation](references/install.md), [Codex](references/codex.md), [Claude](references/claude.md), [login/SSH failures](references/auth-context.md), [validation](references/validation.md).

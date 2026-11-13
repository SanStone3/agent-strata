---
name: strata
description: Delegate independent coding, research and review to native Codex or Claude Code subagents. In Codex, route focused evidence to Luna, ordinary coding to Terra and complex tasks to Sol; do not use for trivial sequential work.
metadata:
  version: "2026.11.13"
---

# Strata

Meet the code and engineering acceptance criteria first. Among routes that can meet them, balance delivery time, token use and agent allowance across the whole task, including retries and review. One controller owns integration and quality.

## Delegate and route by task

When native delegation is allowed, look for a self-contained implementation, evidence or verification packet that saves time on the critical path or adds needed independent evidence. Run it alongside the controller's work when useful. Batch related lookups and keep tiny sequential edits local.

| Task | Codex starting point |
|---|---|
| Known path, short search, small sequential edit | Direct tools |
| Bounded code or test discovery, log triage, extraction, summary or exact mechanical execution | Luna `low/medium` with `scout` (read-only) or `executor` |
| Ordinary feature, bug fix, refactor or test change with understood contracts and clear checks | Terra `medium` with `worker` |
| More involved work with stable contracts and clear checks, including writing, vision or computer use | Terra `medium/high` with `worker` |
| Difficult implementation or cross-module diagnosis | Sol `high` with `deep_worker` from the first pass |
| Ambiguous invariants, high-impact failure, conflicting evidence or consequential independent review | Sol `xhigh` with `deep_worker` or read-only `reviewer` |

Choose the capability floor from contract uncertainty, failure impact and strength of the checks. Use Sol for work that needs it from the start. For eligible options compare Intelligence Index against **cost, time and output tokens per task**, then account for local evidence, context and integration overhead. When a check exposes deeper uncertainty, inspect the partial result and hand off the remaining problem to Sol. Keep the required tests and review. See [cost-control.md](references/cost-control.md) for the benchmark and [claude.md](references/claude.md) for Claude's independent routing.

## Orchestrate

- The current CLI/App user selection owns the primary model and effort, including later user switches. Keep primary settings out of skill updates. Children keep their creation model. Escalation uses a new compact packet.
- Strata has no numeric agent cap. Choose useful parallelism from actual host capacity, resources, cost and synthesis capacity. Default to one writer; allow more only with disjoint paths, frozen contracts and independent checks. Queue excess work. See [scaling.md](references/scaling.md).
- Match the requested model and effort to the active native tool. Use a named role when its binding matches. If a named role pins a different model or effort, use a generic child with explicit overrides and the same task boundaries when supported. Use compact, history-free packets for explicit overrides. See [model-routing.md](references/model-routing.md) for fallback and resolution.
- Send goal, file/contract pointers, owned paths or read-only scope, constraints, checks, stop condition and a concise result budget. Reuse evidence; do not copy transcripts or duplicate searches. Return findings/changes, locations, tests and uncertainty. See [task-contract.md](references/task-contract.md) when boundaries are unclear.
- Scouts/reviewers are read-only. Children do not spawn descendants, expand scope, commit, push, deploy or invoke another coding-agent provider. Preserve CODEX_HOME, auth, provider and permissions. Inspect changes before integration; inspect partial state before retrying.

Read only what the task needs: [installation](references/install.md), [Codex](references/codex.md), [Claude](references/claude.md), [login/SSH failures](references/auth-context.md), [validation](references/validation.md).

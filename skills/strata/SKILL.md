---
name: strata
description: Delegate independent coding, research and review to native Codex or Claude Code subagents. In Codex, route focused evidence to Luna, ordinary coding to Terra and complex tasks to Sol; do not use for trivial sequential work.
metadata:
  version: "2026.11.12"
---

# Strata

Optimize cost and elapsed time per accepted change, including context, retries and review. One controller owns integration and quality.

## Delegate and route by task

When native delegation is allowed, delegate meaningful work with a self-contained brief and an independent check. At the start of multi-step work, look for a bounded implementation for Terra or a distinct evidence or verification task for Luna. One useful packet is enough. Run independent work alongside the controller's own work when possible. Keep one-off lookups and tiny sequential edits local.

| Task | Codex starting point |
|---|---|
| Known path, short search, small sequential edit | Direct tools |
| Bounded code or test discovery, log triage, extraction, summary or exact mechanical execution | Luna `low/medium` with `scout` (read-only) or `executor` |
| Ordinary feature, bug fix, refactor or test change with understood contracts and clear checks | Terra `medium` with `worker` |
| Harder bounded work, supplied-material writing, vision or computer use | Terra `medium/high` with `worker` |
| Cross-module diagnosis, architecture, security, concurrency or difficult implementation | Sol `high/xhigh`; `deep_worker` |
| Consequential independent review | Sol `high/xhigh`; `reviewer`, read-only |

Escalate to Sol when the packet requires cross-module root cause analysis, changes a high-risk contract, or fails an acceptance check that exposes deeper uncertainty. Inspect the partial result first and pass only the remaining problem. Keep required tests and evidence. See [cost-control.md](references/cost-control.md) for dated comparisons and [claude.md](references/claude.md) for Claude's independent routing.

## Orchestrate

- The current CLI/App user selection owns the primary model and effort, including later user switches. Keep primary settings out of skill updates. Children keep their creation model. Escalation uses a new compact packet.
- Strata has no numeric agent cap. Choose useful parallelism from actual host capacity, resources, cost and synthesis capacity. Default to one writer; allow more only with disjoint paths, frozen contracts and independent checks. Queue excess work. See [scaling.md](references/scaling.md).
- Match the requested model and effort to the active native tool. Use a named role when its binding matches. If a named role pins a different model or effort, use a generic child with explicit overrides and the same task boundaries when supported. Use compact, history-free packets for explicit overrides. See [model-routing.md](references/model-routing.md) for fallback and resolution.
- Send goal, file/contract pointers, owned paths or read-only scope, constraints, checks, stop condition and a concise result budget. Reuse evidence; do not copy transcripts or duplicate searches. Return findings/changes, locations, tests and uncertainty. See [task-contract.md](references/task-contract.md) when boundaries are unclear.
- Scouts/reviewers are read-only. Children do not spawn descendants, expand scope, commit, push, deploy or invoke another coding-agent provider. Preserve CODEX_HOME, auth, provider and permissions. Inspect changes before integration; inspect partial state before retrying.

Read only what the task needs: [installation](references/install.md), [Codex](references/codex.md), [Claude](references/claude.md), [login/SSH failures](references/auth-context.md), [validation](references/validation.md).

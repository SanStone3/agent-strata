<!-- BEGIN AGENT STRATA -->
## Layered Agent Orchestration

For complex work with independent workstreams or noisy bounded exploration, use the `strata` skill and native Codex subagents. Keep the current main session as the sole controller and final owner.

- Prefer the strongest eligible deep-tier primary controller at xhigh. Honor an explicit controller pin or preserve-primary choice. Resolve its recommendation at session start; apply global model changes only during an authorized setup/update, and never claim an active session switched because a file changed.
- Before the first delegation, use the Strata model-routing reference and resolver to bind stable roles to the current tool catalog. Honor model pins, pass resolved model/effort explicitly when supported, and refresh on host/account/tool changes or explicit model rejection. Otherwise use verified rendered agent definitions. Never dispatch unresolved or bare model-free templates.
- Do not delegate small, sequential, or same-file tasks.
- Keep at most three active subagents and one writer by default. The budget caps concurrency, not total work: additional packets run as further waves.
- Raise the budget only for read-only fan-out, or for writers holding disjoint write domains with frozen shared contracts, one validation command per domain, and capacity to inspect every write before the next wave. Otherwise serialize the writes.
- Land shared interface, schema, manifest, lockfile, and generated-artifact changes in the primary session before a parallel wave, then treat them as immutable for that wave.
- Use `scout` for read-only exploration and `executor` only for exact mechanical operations.
- Use `worker` at `xhigh` for ordinary bounded code changes.
- Escalate cross-module, ambiguous, security-, concurrency-, lifecycle-, migration-, or high-rework changes to `deep_worker` at `xhigh`.
- Use `reviewer` at `xhigh` for consequential read-only final review.
- Give every subagent one bounded task packet with an explicit write domain and result budget, and require concise evidence-based results.
- A wave returns only when its slowest packet returns, so keep packets in one wave comparable in size.
- Subagents do not spawn descendants, commit, push, deploy, expand scope, or invoke another coding-agent provider.
- Named custom roles use compact task packets or limited recent-turn forks. Never combine explicit custom type with full-history fork.
- Before delegating, state the planned agent split and wave plan; report briefly in the main thread when each subagent starts, blocks, and completes.
- On a write conflict, stop the wave, inspect the working tree, and serialize the remaining writers; never discard existing work to clear a conflict.
- Project-specific instructions, user authorization, and existing worktree changes remain authoritative.
<!-- END AGENT STRATA -->

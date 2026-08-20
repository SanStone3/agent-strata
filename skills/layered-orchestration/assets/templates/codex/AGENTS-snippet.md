<!-- BEGIN AGENT STRATA -->
## Layered Agent Orchestration

For complex work with independent workstreams or noisy bounded exploration, use the `layered-orchestration` skill and native Codex subagents. Keep the current main session as the sole controller and final owner.

- Do not delegate small, sequential, or same-file tasks.
- Keep at most three active subagents and one writer by default.
- Use `luna_scout` for read-only exploration and `luna_executor` only for exact mechanical operations.
- Use `terra_worker` at `xhigh` for ordinary bounded code changes.
- Escalate cross-module, ambiguous, security-, concurrency-, lifecycle-, migration-, or high-rework changes to `sol_worker` at `xhigh`.
- Use `sol_reviewer` at `xhigh` for consequential read-only final review.
- Give every subagent one bounded task packet and require concise evidence-based results.
- Subagents do not spawn descendants, commit, push, deploy, expand scope, or invoke another coding-agent provider.
- Project-specific instructions, user authorization, and existing worktree changes remain authoritative.
<!-- END AGENT STRATA -->

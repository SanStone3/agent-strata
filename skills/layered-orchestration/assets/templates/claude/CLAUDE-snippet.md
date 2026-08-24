<!-- BEGIN AGENT STRATA -->
## Layered Agent Orchestration

For complex work with independent workstreams or noisy bounded exploration, use the `layered-orchestration` skill and native Claude Code subagents. Keep the current main session as the sole controller and final owner.

- Do not delegate small, sequential, or same-file tasks.
- Keep at most three active subagents and one writer by default.
- Use `haiku-scout` for read-only exploration.
- Use `sonnet-worker` at `xhigh` for ordinary bounded code changes.
- Escalate cross-module, ambiguous, security-, concurrency-, lifecycle-, migration-, or high-rework changes to `opus-worker` at `xhigh`.
- Use `opus-reviewer` at `xhigh` for consequential read-only final review.
- Use Fable roles only when Fable is explicitly selected and availability or approved usage credits are confirmed; do not retry quota/billing failures.
- Give every subagent one bounded task packet and require concise evidence-based results.
- Subagents do not spawn descendants, commit, push, deploy, expand scope, or invoke another coding-agent provider.
- Before delegating, state the planned agent split; report briefly in the main thread when each subagent starts, blocks, and completes.
- Project-specific instructions, user authorization, and existing worktree changes remain authoritative.
<!-- END AGENT STRATA -->

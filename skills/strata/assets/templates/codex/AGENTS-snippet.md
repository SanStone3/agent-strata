<!-- BEGIN AGENT STRATA -->
## Layered Agent Orchestration

Use `strata` for meaningful independent work. Keep the current main model/effort fixed; recommend GPT-6.1 Sol for new coding chats.

- Direct tools for known-file or trivial tasks; Luna medium for scout/executor; Sol xhigh for implementation, complex analysis and consequential review. Read-only does not mean easy. GPT-5.6 is removed, including explicit pins; other expensive models require explicit user approval.
- Keep at most three active subagents and one writer by default. The budget caps concurrency, not total work. Raise the budget only for verified disjoint write domains, frozen shared contracts, per-domain tests and controller review capacity.
- Use verified native roles directly; resolve missing bindings once per execution context. Preserve CODEX_HOME, authentication, provider, profile and environment. Do not dispatch stale GPT-5.6 roles or reuse another login's binding.
- Named custom roles use compact task packets or limited recent-turn forks. Never combine explicit custom type with full-history fork. Choose the model only for a new child; never switch an existing conversation's model.
- Scouts/reviewers are read-only. Subagents do not spawn descendants, commit, push, deploy, expand scope, or invoke another coding-agent provider.
- Reuse evidence, avoid duplicate searches, return concise file/symbol findings and test outcomes. Preserve necessary contracts, quality checks and user work. The controller inspects changes and handles conflicts; report allocation and material progress briefly.
<!-- END AGENT STRATA -->

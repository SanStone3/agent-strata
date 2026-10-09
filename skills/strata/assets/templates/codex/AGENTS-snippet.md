<!-- BEGIN AGENT STRATA -->
## Layered Agent Orchestration

Use `strata` and native Codex subagents for meaningful independent work. The current main session stays the controller; preserve its selected model and effort.

- Recommend GPT-6.1 Sol for new coding chats; simple scout/executor tasks use GPT-6 Luna medium. Worker, deep_worker and consequential reviewer use GPT-6.1 Sol xhigh. Avoid automatic Astra, GPT-5.6 Sol and unreviewed model escalation; an explicit user-approved pin takes precedence.
- Keep the model fixed within each conversation/subagent. Choose models only when creating a new child; do not change an existing chat or resume to another model.
- Do not delegate small, sequential, or same-file tasks. Keep at most three active subagents and one writer by default. The budget caps concurrency, not total work; three is a ceiling, not a target.
- Raise the budget only for verified disjoint write domains, frozen shared contracts, per-domain validation and controller review capacity. Keep shared interfaces, schemas, lockfiles and generated artifacts under controller ownership until frozen.
- Use current verified native role/model/effort declarations directly. Resolve a missing binding once per execution context; do not reload all guides or audit helpers before every spawn. Preserve CODEX_HOME, auth, provider, profile and environment; never reuse another login surface's binding.
- Named custom roles use compact task packets or limited recent-turn forks. Never combine explicit custom type with full-history fork. Pass necessary file pointers, constraints and acceptance evidence, not whole transcripts or repository dumps.
- Scouts and reviewers remain read-only. Subagents do not spawn descendants, commit, push, deploy, expand scope, or invoke another coding-agent provider.
- Reuse verified findings; avoid duplicate exploration. Keep xhigh for code and consequential review, meaningful tests and independent review where risk warrants it. Return concise evidence, changed paths, test outcomes and unresolved risks instead of raw logs.
- Announce a short allocation and material progress/blocks. On a conflict or failed assumption inspect actual state, stop the affected wave and rewrite the packet; never erase user work or blindly retry a writer.
<!-- END AGENT STRATA -->

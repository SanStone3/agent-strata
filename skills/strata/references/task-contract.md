# Compact task contracts

Delegate when independent work shortens the critical path, isolates noisy exploration, or adds necessary independent review. Known-file, same-state or small sequential work stays local.

Each packet includes:

```text
Goal and acceptance checks:
Relevant file/symbol/contract pointers and verified facts:
Write domain: explicit paths, or read-only; everything else read-only
Constraints and stop conditions:
Result budget: concise findings/changes, evidence, tests, uncertainty
```

Add ordering and shared-contract information only when needed. Do not forward full conversations, bulk logs or irrelevant project history. Give the child enough evidence to avoid redoing a prior scout's work. Two simultaneous packets must not answer the same question or own the same change.

Choose the role, model and effort for the packet before creation. Prefer history-free mixed-model children. Keep a small controller ledger: owner, paths, model/effort, status and evidence pointers. Reuse a child for a related follow-up on the same model when context remains useful; unrelated work or a capability change gets a fresh compact packet. Stop idle/unneeded work through the host lifecycle. Never switch a child model on resume.

Results report `completed | partial | blocked`, concise findings/changes with locations, validation commands/results, uncertainty and any boundary needing revision. Reviewers return severity-ordered actionable findings, or state no material finding. Suggested budget: five findings or twenty lines, adjusted when completeness requires more.

The controller inspects evidence and diffs, reconciles contradictions and runs necessary final checks. Keep full logs in permitted local artifacts; return only failing excerpts and test receipts. Before context compaction preserve decisions, remaining work and evidence pointers, not the tool transcript. Keep this in session state unless the user requested a handoff file.

If a boundary fails, inspect partial state and rewrite the packet. Children do not widen scope or spawn descendants. Multiple-writer criteria: [scaling.md](scaling.md).

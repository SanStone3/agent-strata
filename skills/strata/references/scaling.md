# Parallelism and write ownership

Strata imposes no numeric subagent cap. The host cap, chosen active count, writer count and total packet count are separate. A host's three available slots do not become a global Strata rule.

```text
active = min(actual host slots, useful independent packets,
             resource capacity, synthesis capacity, explicit user/project budget)
writers = verified disjoint write domains   # default 1
```

Compare the delivery path with and without the child. Count overlapping work once for elapsed time and sum the usage of every branch. Include handoff, integration and required checks. Start with one useful child and add work when it shortens the delivery path or supplies required independent evidence. Batch related tiny lookups. Keep dependent work sequential. Count running forks and resumed children and queue excess packets against the actual host capacity.

Multiple writers require all of:

1. Explicit non-overlapping writable path lists; every other path is read-only.
2. Controller-owned shared contracts already landed and frozen: interfaces, types, schemas, manifests, lockfiles, generated files, shared fixtures and formatter configuration.
3. An independent validation command for each domain and a safe integration order.
4. Enough controller attention to inspect all writes and absorb concise results.

At each wave boundary, inspect the combined state, validate, then construct remaining packets from that state. Recompute useful concurrency; there is no fixed count to return to. A refusal is backpressure: queue, do not loop. On conflicts, stop affected writers, inspect and serialize; preserve user work.

Do not raise a host limit just to install Strata. Remove a known old Strata-imposed cap during an authorized upgrade; retain deliberate user/project limits. Configured capacity does not prove effective capacity. If a version ignores a key, verify its own docs/schema before changing it; do not enable unrelated features. Claude-specific controls remain in [claude.md](claude.md).

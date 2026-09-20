# Runtime task contract

Read this reference before delegating live work. For budgets, write domains, and wave planning, read [scaling.md](scaling.md).

## Decomposition test

Delegate only when at least one is true:

- independent workstreams can run without shared mutable state;
- read-heavy exploration, logs, or research would pollute the controller context;
- an independent high-risk review adds meaningful confidence;
- ownership can be bounded by paths, modules, interfaces, or output artifacts.

Continue in the primary when the task is small, sequential, same-file, or dependent on rapid back-and-forth judgment.

## Task packet

Every delegated packet must state:

```text
Objective:
Relevant context and evidence:
Write domain: owned writable paths, or read-only
Explicit exclusions:
Wave and merge order:
Permission mode and allowed commands:
Acceptance evidence:
Result budget:
Stop/escalation conditions:
Required return fields:
```

`Write domain` is a path list, not a module name, and every other path is read-only to that agent. A read-only packet says read-only and names no writable path. `Result budget` caps the returned volume, for example five findings or twenty lines, so that a whole wave still compresses into one coherent state.

Do not forward the full user conversation when a compact packet is sufficient. Include project instructions or facts the subagent cannot otherwise access.
Named custom roles use compact task packets or limited recent-turn forks. Never combine explicit custom type with full-history fork.

Two concurrent packets must not contain the same question or the same change. Duplicated exploration doubles cost and returns the same uncertainty.

## Write ownership

Default to one writer. Before allowing two or more writers in one wave, verify disjoint path lists, frozen shared contracts, independent per-domain validation, project permission, and safe integration order. If any condition is uncertain, serialize the writes. The full partition procedure and the conditions for raising the concurrency budget are in [scaling.md](scaling.md).

Shared contracts stay with the controller: public interfaces and type declarations, schemas and migrations, generated output, barrel and index files, lockfiles and manifests, formatter and lint configuration, and cross-domain fixtures. Land those changes first, then declare them immutable for the wave.

Scouts and reviewers never edit. A mechanical executor stops when semantic judgment appears.

## Required return

Scout and worker:

```text
status: completed | partial | blocked
summary:
findings_or_changes: concise, with file/symbol evidence
validation: command or check plus result
domain_boundary: respected | needed paths outside the domain
uncertainties:
residual_risks:
recommended_next_step:
```

Reviewer returns findings first, ordered by severity. Each finding contains location, trigger/failure mode, impact, evidence, and verification or mitigation. State explicitly when there is no material finding.

## Controller synthesis

The controller checks returned claims against primary evidence, inspects all writes, resolves contradictions, and runs allowed final validation. It never reports a subagent's unverified statement as completed work.

At a wave gate, inspect the combined state rather than the sum of the reports, then rewrite the next wave's packets from the state that now exists.

When a subagent discovers that its boundary is wrong, stop that packet and rewrite it. Do not let the subagent silently expand scope. When two agents disagree with confidence, treat it as a partition defect and re-cut the boundary rather than averaging the answers.

## Dispatch failures

- A refused spawn at the client cap is scheduling information, not an error to retry. Queue that packet into the next wave. Claude Code reports `Concurrent subagent limit reached` and instructs no retry.
- Forks occupy a concurrency slot, and resumes take a fresh slot without a limit check; count both against the intended budget.
- A write conflict stops the wave. Inspect the working tree and serialize the remaining writers; never discard user work to clear a conflict.
- A `blocked` return changes the plan, not the tier. Do not respawn an unchanged packet at a higher capability tier.

## Effort verification

A `sonnet`/`opus` alias that resolves to a 4.6-class model does not support `xhigh`; the client silently lowers the request to the highest supported level. A configured `xhigh` is not an effective `xhigh` until `/status` or equivalent evidence confirms the resolved model. Otherwise pin a full model ID that supports `xhigh`, or report the coding-worker invariant as unmet.

Fable authentication, billing, rate-limit, request-size, and transport errors do not trigger model fallback. Stop the branch and return control; do not retry.

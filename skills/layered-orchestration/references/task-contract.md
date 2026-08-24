# Runtime task contract

Read this reference before delegating live work.

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
Owned read/write paths or modules:
Explicit exclusions:
Permission mode and allowed commands:
Acceptance evidence:
Stop/escalation conditions:
Required return fields:
```

Do not forward the full user conversation when a compact packet is sufficient. Include project instructions or facts the subagent cannot otherwise access.
Named custom roles use compact task packets or limited recent-turn forks. Never combine explicit custom type with full-history fork.

## Write ownership

Default to one writer. Before allowing two writers, verify disjoint paths and state, fixed interface contracts, independent validation, project permission, and safe integration. If any condition is uncertain, serialize the writes.

Scouts and reviewers never edit. A mechanical executor stops when semantic judgment appears.

## Required return

Scout and worker:

```text
status: completed | partial | blocked
summary:
findings_or_changes: concise, with file/symbol evidence
validation: command or check plus result
uncertainties:
residual_risks:
recommended_next_step:
```

Reviewer returns findings first, ordered by severity. Each finding contains location, trigger/failure mode, impact, evidence, and verification or mitigation. State explicitly when there is no material finding.

## Controller synthesis

The controller checks returned claims against primary evidence, inspects all writes, resolves contradictions, and runs allowed final validation. It never reports a subagent's unverified statement as completed work.

When a subagent discovers that its boundary is wrong, stop that packet and rewrite it. Do not let the subagent silently expand scope.

## Effort verification

A `sonnet`/`opus` alias that resolves to a 4.6-class model does not support `xhigh`; the client silently lowers the request to the highest supported level. A configured `xhigh` is not an effective `xhigh` until `/status` or equivalent evidence confirms the resolved model. Otherwise pin a full model ID that supports `xhigh`, or report the coding-worker invariant as unmet.

Fable authentication, billing, rate-limit, request-size, and transport errors do not trigger model fallback. Stop the branch and return control; do not retry.

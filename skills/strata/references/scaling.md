# Concurrency and scaling

Read this reference when one writer and three active agents are not enough, when a wave of parallel work must be planned, when a client refuses a spawn, or when parallel writes collide.

## Keep four numbers separate

Conflating them produces either timid single-threaded work or unmanageable fan-out.

| Quantity | Meaning | Default |
|---|---|---|
| Client cap | Ceiling the client enforces mechanically | Codex: 3 spawned threads, 4 including the primary. Claude Code: 20 concurrent subagents |
| Concurrency budget | How many the controller chooses to keep active | 3 active, 1 writer |
| Write domains | Verified disjoint sets of writable paths | 1 |
| Packet count | Total delegated packets across the whole task | Unbounded |

Three is a concurrency default, not a quota on the task. Twelve packets are ordinary work: run four waves of three, not twelve open threads. Raising the budget is a decision about write safety and synthesis capacity, never a way to get more total work done.

## Budget formula

```text
concurrency_budget = min(client_cap, writers + readers)
writers = verified disjoint write domains            # default 1
readers = distinct read-only questions the controller
          can state in one sentence and absorb in one
          synthesis step                             # default 2
```

If a reader's question does not fit in one sentence, it is not separable yet: scout first, then split. If two writers cannot be handed non-overlapping path lists, `writers` stays 1. A budget above the client cap is not a plan; it is a queue.

## Partition write domains

A domain is a list of paths one agent may write, plus the explicit statement that everything else is read-only to it.

1. List candidate paths per workstream from actual evidence, not from module names.
2. Remove any path that appears in two lists. Shared paths belong to the controller or to a serialized follow-up packet.
3. Check the usual shared-state traps: public interface or type declaration files, schema and migration directories, generated or vendored output, barrel and index files, lockfiles, dependency manifests, formatter or lint configuration, snapshot fixtures, one test file asserting several domains, and anything a build step rewrites.
4. Freeze contracts before the wave. The controller lands the interface, signature, schema, or config key change first, in its own step, and tells every writer to treat it as fixed.
5. Require one independent validation command per domain. A domain whose correctness can only be judged after another domain lands is not independent; sequence it instead.
6. Keep a domain map in the controller's own notes: domain id, owner, paths, validation command, merge order.

If any step fails, the honest answer is fewer writers, not a larger budget.

## Plan waves

A wave is a set of packets that fit the budget and share no write domain. Between waves the controller closes the loop.

1. Assign each packet a domain id, a wave number, and a merge order inside the wave.
2. Start the wave. Keep working on controller-owned work that touches no domain.
3. At the integration gate: read every diff, run each domain's validation, reconcile contradictions against primary evidence, and inspect the combined state rather than the sum of the reports.
4. Rewrite the next wave's packets from the state that now exists. Never dispatch wave *n+1* packets written before wave *n* landed.
5. Stop the plan, not just the packet, when a gate reveals that the partition was wrong.

Read-only waves may be wide. Writing waves stay narrow, and a wave mixing readers and writers keeps the readers off the writers' paths.

## Raise the budget only when every condition holds

- Every packet in the wave is read-only, or every writer owns a domain verified by explicit path lists.
- All shared contracts are frozen or controller-owned.
- Each domain has its own validation command.
- Each packet returns within its result budget, so *n* results still compress into one coherent state.
- The controller has the capacity to inspect every write in the wave before the next wave starts.
- Each added agent removes work from the critical path instead of duplicating exploration.
- The extra token and credit spend is authorized, and the client cap allows the count without queueing.

Raise it in one step to a stated number, report that number, and return to the default once the wide wave closes.

## Never raise the budget for

- same-file or overlapping-path work, including two agents editing one large module;
- one migration, one schema, or one state machine, however many call sites it touches;
- a refactor that moves symbols other packets are reading;
- a boundary still being discovered: scout first, then decide;
- work with no per-domain validation;
- writers that would have to negotiate with each other mid-flight;
- review breadth. Reviewers are read-only and cheap to fan out, but the number of reviewers does not substitute for one accountable final review.

## Backpressure and failure

- Claude Code refuses a spawn past the cap with `Concurrent subagent limit reached` and instructs no retry. Treat the refusal as scheduling information: queue that packet into the next wave rather than retrying or lowering its scope.
- Forks occupy a concurrency slot while running, and resuming a completed subagent takes a fresh slot without a limit check. A resume-heavy plan can exceed the intended budget silently, so count resumes against your own budget.
- Sessions at maximum effort are exempt from the Claude Code cap, so the policy budget is the only remaining limit there. State the number before dispatching.
- On Codex, a raised `agents.max_concurrent_threads_per_session` may have no effect on builds where the multi-agent v2 feature owns concurrency; verify the observed parallelism and treat the observed value as effective. See [codex.md](codex.md).
- On a write conflict, stop the wave, inspect the working tree, and serialize the remaining writers. Never resolve a conflict by discarding a working tree or by destructive version-control cleanup.
- On `partial` or `blocked` returns, re-cut the boundary in the controller. Do not let the agent widen its own scope, and do not respawn the same packet at a higher tier without changing the packet.
- When results contradict each other, primary evidence decides. Two confident agents disagreeing is a partition defect, not a tie to average.

## Cost and latency

Parallel agents buy wall-clock, not tokens. Each concurrent agent adds full context and result cost, and every wave adds one synthesis round.

- Prefer one wide read-only wave over several narrow ones; scouting is the cheapest thing to parallelize and the easiest to compress.
- Do not parallelize to hide a missing decision. Two workers exploring the same uncertainty cost twice and still return the uncertainty.
- Keep result budgets explicit. Unbounded returns from a wide wave destroy the controller's context, which is the resource the whole pattern exists to protect.

## Worked example

Fifteen call sites to update across three modules, one shared interface change, one consequential review. Client cap 3.

| Wave | Active | Packets | Gate |
|---|---|---|---|
| 0 | 1 reader | Scout maps call sites, owners, tests | Controller confirms the three candidate domains and the shared interface |
| 1 | 3 readers | One scout per candidate domain, each answering one question about hidden coupling | Partition accepted or re-cut; overlapping paths pulled into controller scope |
| 2 | 0 | Controller lands the frozen interface change itself | Interface fixed and validated; writers told it is immutable |
| 3 | 2 writers, 1 reader | Domains A and B implemented; scout prepares domain C evidence | Both diffs inspected, both domain validations run |
| 4 | 1 writer | Domain C implemented | Combined validation across domains |
| 5 | 1 reviewer | Read-only final review of the whole change | Controller resolves findings and delivers |

Nine packets, never more than three active, one writer per domain, one accountable controller.

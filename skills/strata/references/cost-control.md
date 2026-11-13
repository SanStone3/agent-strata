# Cost, latency and context

Optimize accepted work: total billed usage across all children and retries, elapsed time, rework and defects. Parallel completion can be faster while costing more. A cheap token rate is not a cheap accepted change.

## Snapshot: 2026-11-06

Official Standard short-context API prices, USD per million tokens. Cached input is a separate bucket. These are not a custom gateway quote or a conversion of ChatGPT subscription allowance.

| Model | Input | Cached read | Output | API context / max output |
|---|---:|---:|---:|---|
| GPT-6.1 Sol | 2 | 0.10 | 10 | 1,050,000 / 128,000 |
| GPT-6.1 Terra | 1 | 0.05 | 5 | 1,050,000 / 128,000 |
| GPT-6 Luna | 0.10 | 0.01 | 0.50 | 1,050,000 / 128,000 |
| GPT-6 Astra, manual primary only | 10 | 1 | 50 | Verify model/client entitlement |

Sources: [pricing](https://developers.openai.com/api/docs/pricing), [Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol), [Terra](https://developers.openai.com/api/docs/models/gpt-6.1-terra), [Luna](https://developers.openai.com/api/docs/models/gpt-6-luna). API maximum context is not the active Codex context. Preserve client context/compaction settings. At more than 272K input, these GPT-6 request input/cache rates double and output rates rise 1.5x; cache writes, speed tiers and provider rates need separate accounting.

## Artificial Analysis snapshot, 2026-11-13

Intelligence Index v5.0.1 and its weighted per-task metrics. Output includes both reasoning and answer tokens. Time estimates use output tokens and measured generation speed. Provider speed measurements can change. Use the Index and relevant coding subtests as directional evidence. Repository acceptance, delivery time and actual plan usage come from comparable local tasks. [OpenAI model charts and methodology](https://artificialanalysis.ai/zh/models/creators/openai).

| Model | Effort | Index | USD/task | Minutes/task | Output tokens/task | Strata choice |
|---|---|---:|---:|---:|---:|---|
| [GPT-6 Luna](https://artificialanalysis.ai/models/releases/gpt-6-luna) | none | 9 | 0.0714 | 1.9 | 10.06k | Outside native routing |
| Luna | low | 10 | 0.0051 | 0.6 | 3.30k | Exact evidence, extraction or commands |
| Luna | medium | 18 | 0.0422 | 3.5 | 19.82k | Bounded synthesis or multi-file evidence |
| Luna | high | 21 | 0.0729 | 5.6 | 32.84k | Outside automatic routing |
| Luna | xhigh | 23 | 0.1041 | 7.3 | 43.89k | Outside automatic routing |
| Luna | max | 28 | 0.1520 | 11.8 | 75.30k | Outside automatic routing |
| [GPT-6.1 Terra](https://artificialanalysis.ai/models/releases/gpt-6-1-terra) | none | 31 | 0.2259 | 2.4 | 9.49k | Outside native routing |
| Terra | low | 29 | 0.0713 | 1.2 | 4.42k | Explicit pin for simple supported visual or text tasks |
| Terra | medium | 38 | 0.1688 | 2.9 | 10.88k | Scoped work with a known approach and quick checks |
| Terra | high | 42 | 0.2593 | 4.3 | 16.75k | Scoped work needing more depth |
| Terra | xhigh | 45 | 0.4007 | 6.6 | 26.20k | Explicit pin only |
| Terra | max | 51 | 0.9611 | 14.6 | 59.88k | Outside worker routing |
| [GPT-6.1 Sol](https://artificialanalysis.ai/models/releases/gpt-6-1-sol) | low | 35 | 0.1615 | 2.0 | 5.84k | Small code change with a known approach |
| Sol 6.1 | medium | 46 | 0.3594 | 4.5 | 13.52k | Default ordinary code diagnosis, edits and tests |
| Sol 6.1 | high | 50 | 0.5910 | 7.7 | 22.61k | Difficult implementation and cross-module diagnosis |
| Sol 6.1 | xhigh | 52 | 0.7640 | 10.5 | 30.24k | Uncertain invariants, high impact or consequential review |
| Sol 6.1 | max | 55 | 1.2721 | 23.3 | 67.82k | Explicit effort for exceptional deep work |
| [GPT-6 Astra](https://artificialanalysis.ai/models/releases/gpt-6-astra) | low | 43 | 1.4237 | 4.0 | 9.13k | User-selected primary only |
| Astra | medium | 52 | 2.7324 | 7.5 | 18.05k | User-selected primary only |
| Astra | high | 55 | 3.2386 | 9.6 | 23.13k | User-selected primary only |
| Astra | xhigh | 55 | 3.6589 | 11.7 | 26.72k | User-selected primary only |
| Astra | max | 57 | 6.2447 | 24.2 | 51.97k | User-selected primary only |
| [GPT-6 Sol](https://artificialanalysis.ai/models/releases/gpt-6-sol) | max | 44 | 2.4658 | 7.8 | 53.89k | Older model, outside automatic routing |

The model-family charts report weighted cost and output tokens. The snapshot rounds Index and time. Ultra is a client orchestration mode where supported. Keep it outside Strata child effort selection. API `none` on Luna/Terra does not imply native tool support. Use the actual client catalog for supported efforts. [OpenAI client models and effort](https://learn.chatgpt.com/docs/models) · [API effort support](https://developers.openai.com/api/docs/guides/latest-model).

Sol medium scores 48.0% on Terminal-Bench 4.0 and 62.6% on AutomationBench-AA. Terra medium scores 32.3% and 57.8%, respectively, and leads on FrontierCode-AA 2.0 at 34.5% versus 33.4%. Combined with observed slow fixes on Terra, this favors Sol medium for ordinary repo diagnosis, edits and tests. Terra high uses 16.7k output tokens versus Sol medium's 13.5k with similar benchmark task times. Sol low trades benchmark capability for faster bounded edits. [Medium comparison](https://artificialanalysis.ai/models/comparisons/gpt-6-1-terra-medium-vs-gpt-6-1-sol-medium) · [Terra high comparison](https://artificialanalysis.ai/models/comparisons/gpt-6-1-terra-high-vs-gpt-6-1-sol-medium).

## Apply all three comparisons

1. Set the capability floor from failure impact, uncertain contracts and available checks. Choose Sol high upfront for difficult engineering and Sol xhigh upfront when evidence conflicts, invariants are unclear or rollback is costly. Preserve required validation and independent review.
2. Compare cost, time and output tokens among routes that can meet that floor. Use Luna low for exact evidence and Sol low for small known edits. Start ordinary fixes on Sol medium. Reserve Terra medium/high for scoped packets with a known approach and quick checks. If Terra stalls, inspect its work and hand the remaining problem to Sol.
3. Compare the complete routes. For parallel work, estimate the longest dependency path plus handoff, integration and verification time. Sum input and output across the controller, children and retries. If a lower tier is likely to need a second pass, include that pass before choosing it. Delegate an independent task when overlap reduces the delivery time or when independent evidence adds required assurance.

For calibration, use comparable completed tasks and record first-pass acceptance, required checks, elapsed time, available input/output usage, agent usage and retries. Treat missing usage as unknown. Avoid mixing API dollars, plan allowance and gateway charges.

## Practical savings

- Known paths and small sequential changes stay with direct tools. Batch related lookups; avoid agents for single reads or duplicate investigations.
- Send compact packets and file pointers, not transcript forks. Read paths/symbols before relevant ranges; preserve necessary contracts and test evidence.
- Put conditional documentation in references. Keep global/project AGENTS sections as pointers to the shared skill; do not duplicate routing tables everywhere.
- Return concise findings and test receipts. Keep full logs out of the controller context. Reuse verified evidence until files or assumptions change.
- Keep stable instruction prefixes where caching is supported; do not retain irrelevant history for hypothetical cache hits. Compact session state before it becomes noisy.
- Use the lowest task effort that passes meaningful acceptance checks. Inspect failure before escalation; do not serially try every cheap model. New scope/capability needs a new bounded packet.
- Preserve user speed/provider settings. Fast/Ultrafast is not a token-saving switch. Never change billing/login to conceal failure.

Estimate cost from disjoint uncached input, cached input, separately billed cache writes, billed output including reasoning, and tool charges. Include every attempt. Do not double-count cached input already included in usage totals; missing usage means unknown cost. Keep API dollars and subscription credits separate. Measure completion quality and wall time as well as tokens; no guaranteed savings percentage is claimed.

# Cost, latency and context

Optimize accepted work: total billed usage across all children and retries, elapsed time, rework and defects. Parallel completion can be faster while costing more. A cheap token rate is not a cheap accepted change.

## Snapshot: 2026-11-06

Official Standard short-context API prices, USD per million tokens. Cached input is a separate bucket. These are not a custom gateway quote or a conversion of ChatGPT subscription allowance.

| Model | Input | Cached read | Output | API context / max output |
|---|---:|---:|---:|---|
| GPT-6.1 Sol | 2 | 0.10 | 10 | 1,050,000 / 128,000 |
| GPT-6.1 Terra | 1 | 0.05 | 5 | 1,050,000 / 128,000 |
| GPT-6 Luna | 0.10 | 0.01 | 0.50 | 1,050,000 / 128,000 |
| GPT-6 Astra, explicit evaluation only | 10 | 1 | 50 | Verify model/client entitlement |

Sources: [pricing](https://developers.openai.com/api/docs/pricing), [Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol), [Terra](https://developers.openai.com/api/docs/models/gpt-6.1-terra), [Luna](https://developers.openai.com/api/docs/models/gpt-6-luna). API maximum context is not the active Codex context. Preserve client context/compaction settings. At more than 272K input, these GPT-6 request input/cache rates double and output rates rise 1.5x; cache writes, speed tiers and provider rates need separate accounting.

## Artificial Analysis snapshot, 2026-11-13

Intelligence Index v5.0.1 and its weighted per-task metrics. Output includes both reasoning and answer tokens. Time estimates use output tokens and measured generation speed. Provider speed measurements can change. Use the Index and relevant coding subtests as directional evidence. Repository acceptance, delivery time and actual plan usage come from comparable local tasks. [OpenAI model charts and methodology](https://artificialanalysis.ai/zh/models/creators/openai).

| Model / effort | Index | USD/task | Minutes/task | Output tokens/task |
|---|---:|---:|---:|---:|
| [Luna low](https://artificialanalysis.ai/models/comparisons/claude-haiku-5-5-low-vs-gpt-6-luna-low) | 10 | 0.01 | 0.6 | 3.3k |
| [Luna medium](https://artificialanalysis.ai/models/comparisons/claude-haiku-5-5-medium-vs-gpt-6-luna-medium) | 18 | 0.04 | 3.5 | 19.8k |
| [Terra medium](https://artificialanalysis.ai/models/comparisons/gpt-6-1-terra-medium-vs-gpt-6-1-sol-medium) | 38 | 0.17 | 2.8 | 10.9k |
| [Terra high](https://artificialanalysis.ai/models/comparisons/gpt-6-1-terra-high-vs-gpt-6-1-sol-high) | 42 | 0.26 | 4.2 | 16.7k |
| [Sol medium](https://artificialanalysis.ai/models/comparisons/gpt-6-1-terra-medium-vs-gpt-6-1-sol-medium) | 46 | 0.36 | 4.3 | 13.5k |
| [Terra xhigh](https://artificialanalysis.ai/models/comparisons/gpt-6-1-terra-xhigh-vs-gpt-6-1-sol-medium) | 45 | 0.40 | 6.4 | 26.2k |
| [Sol high](https://artificialanalysis.ai/models/comparisons/gpt-6-1-sol-high-vs-gpt-6-1-sol-xhigh) | 50 | 0.59 | 7.4 | 22.6k |
| [Sol xhigh](https://artificialanalysis.ai/models/comparisons/gpt-6-1-sol-high-vs-gpt-6-1-sol-xhigh) | 52 | 0.76 | 9.9 | 30.2k |

## Apply all three comparisons

1. Set the capability floor from failure impact, uncertain contracts and available checks. Choose Sol high upfront for difficult engineering and Sol xhigh upfront when evidence conflicts, invariants are unclear or rollback is costly. Preserve required validation and independent review.
2. Compare cost, time and output tokens among routes that can meet that floor. Luna low fits exact extraction or commands. Luna medium fits synthesis within a bounded scout packet and can use more tokens and time than Terra medium even at lower dollar cost. Terra medium fits ordinary code with clear checks. Terra high fits longer bounded work. Sol medium is a same-effort worker fallback and scores higher than Terra xhigh with lower measured cost, time and output tokens.
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

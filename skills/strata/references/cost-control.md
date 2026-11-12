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

AA Intelligence Index **v5.0.1**, checked 2026-11-06. Values below come from the linked effort-specific pages, not older Sol or index versions.

| Model / effort | Index | USD/task | Minutes/task | Output tok/s | First answer token, seconds |
|---|---:|---:|---:|---:|---:|
| [Sol medium](https://artificialanalysis.ai/zh/models/gpt-6-1-sol-medium) | 46 | 0.36 | 4.2 | 54 | 6.80 |
| [Sol high](https://artificialanalysis.ai/zh/models/gpt-6-1-sol-high) | 50 | 0.59 | 7.1 | 53 | 46.36 |
| [Sol xhigh](https://artificialanalysis.ai/zh/models/gpt-6-1-sol-xhigh) | 52 | 0.76 | 9.8 | 52 | 79.16 |
| [Terra medium](https://artificialanalysis.ai/zh/models/gpt-6-1-terra-medium) | 38 | 0.17 | 2.6 | 70 | 5.04 |
| [Terra high](https://artificialanalysis.ai/zh/models/gpt-6-1-terra-high) | 42 | 0.26 | 4.0 | 70 | 12.63 |
| [Terra xhigh](https://artificialanalysis.ai/zh/models/gpt-6-1-terra-xhigh) | 45 | 0.40 | 6.1 | 71 | 38.22 |
| [Luna medium](https://artificialanalysis.ai/zh/models/gpt-6-luna-medium) | 18 | 0.04 | Unavailable | Unavailable | Unavailable |
| [Luna low](https://artificialanalysis.ai/zh/models/gpt-6-luna-low) | 10 | 0.01 | 0.6 | 90 | 2.72 |

AA costs/times are benchmark task averages, not repository completion predictions. First-answer latency includes reasoning; do not call it pure TTFT. Performance measurements are rolling snapshots; unavailable data stays unavailable. The AA pages round context to 1M. Do not mix snapshots, effort levels or index versions to imply measured coding success.

On 2026-11-12, the same-effort comparison put Terra medium at $0.17 and 2.7 minutes per task and Sol medium at $0.36 and 4.2 minutes. Use Terra medium as the starting point for ordinary coding with clear acceptance checks. The earlier snapshot shows why automatically raising Terra to xhigh can erase the savings. Use Luna low/medium for well-defined evidence and execution packets. Check acceptance, retries and total cost on comparable project tasks. [Artificial Analysis medium comparison](https://artificialanalysis.ai/models/comparisons/gpt-6-1-terra-medium-vs-gpt-6-1-sol-medium).

User-provided background: [KnightLi comparison](https://knightli.com/2026/09/10/openai-gpt-6-astra-gpt-5-6-model-comparison/), [LaoZhang comparison](https://blog.laozhang.ai/zh/posts/gpt-6-sol-vs-terra-vs-luna-vs-astra). Their historical measurements are not merged with this snapshot.

## Practical savings

- Known paths and small sequential changes stay with direct tools. Batch related lookups; avoid agents for single reads or duplicate investigations.
- Send compact packets and file pointers, not transcript forks. Read paths/symbols before relevant ranges; preserve necessary contracts and test evidence.
- Put conditional documentation in references. Keep global/project AGENTS sections as pointers to the shared skill; do not duplicate routing tables everywhere.
- Return concise findings and test receipts. Keep full logs out of the controller context. Reuse verified evidence until files or assumptions change.
- Keep stable instruction prefixes where caching is supported; do not retain irrelevant history for hypothetical cache hits. Compact session state before it becomes noisy.
- Use the lowest task effort that passes meaningful acceptance checks. Inspect failure before escalation; do not serially try every cheap model. New scope/capability needs a new bounded packet.
- Preserve user speed/provider settings. Fast/Ultrafast is not a token-saving switch. Never change billing/login to conceal failure.

Estimate cost from disjoint uncached input, cached input, separately billed cache writes, billed output including reasoning, and tool charges. Include every attempt. Do not double-count cached input already included in usage totals; missing usage means unknown cost. Keep API dollars and subscription credits separate. Measure completion quality and wall time as well as tokens; no guaranteed savings percentage is claimed.

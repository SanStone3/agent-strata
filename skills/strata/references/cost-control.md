# Cost control without skipping verification

Default routing uses GPT-6.1 Sol for code, complex tasks and independent review; GPT-6 Luna handles bounded simple tasks. Keep xhigh for implementation and consequential review. Do not claim a cheaper model has identical capability or that quality cannot regress: acceptance evidence, appropriate tests and observed outcomes decide whether a route is adequate.

## Price snapshot, checked 2026-10-09

Scope: general-purpose coding models present in the inspected Codex catalogs, not image/audio or specialist cybersecurity models. Values are **per 1 million tokens**, Standard speed and short-context pricing. Cached input is a separate input category, not an extra charge on the same tokens.

| Model | API input USD | API cached input USD | API output USD | Credits input / cached / output |
|---|---:|---:|---:|---|
| GPT-6.1 Sol | 2 | 0.10 | 10 | 50 / 2.5 / 250 |
| GPT-6 Luna | 0.10 | 0.01 | 0.50 | 2.5 / 0.25 / 12.5 |
| GPT-6 Sol | 2 | 0.20 | 10 | 50 / 5 / 250 |
| GPT-5.6 Sol | 4 | 0.40 | 20 | 100 / 10 / 500 |
| GPT-5.6 Terra | 2 | 0.20 | 12 | 50 / 5 / 300 |
| GPT-5.6 Luna | 0.20 | 0.02 | 1.20 | 5 / 0.5 / 30 |
| GPT-6 Astra | 10 | 1 | 50 | 250 / 25 / 1250 |
| GPT-5.5 | 5 | 0.50 | 30 | 125 / 12.5 / 750 |

Sources: [API pricing](https://developers.openai.com/api/docs/pricing), [Codex credits](https://learn.chatgpt.com/docs/pricing), [GPT-6 Sol](https://developers.openai.com/api/docs/models/gpt-6-sol), [GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra), [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna), [GPT-5.5](https://developers.openai.com/api/docs/models/gpt-5.5).

Use current official sources when refreshing this snapshot. These are not the rates of a custom API gateway, nor a conversion of subscription allowance into guaranteed task counts. Provider charges, caching behavior, long-context brackets and speed modes can differ. The quoted Astra input/output ratio is currently 5x Sol, while Luna is 0.05x; cached-token ratios differ. GPT-6.1 Sol has a lower cached-input rate than GPT-6 Sol despite matching ordinary input/output prices.

Estimate cost only from disjoint measured usage buckets: uncached input, cached input, any separately billed cache writes, and total billed output including reasoning. Do not add cached input twice when an API's input total already includes it. Include every attempt, child, tool charge and retry; missing usage is unknown. Keep API dollar and subscription-credit accounting separate. Public prices do not justify sending account requests through a different provider.

## Save work and context first

- Start with direct work or one bounded worker. Use parallelism for genuinely independent tasks, not multiple agents solving the same question. The concurrency ceiling is not a minimum team size.
- Read file names/symbols first, then relevant ranges. Reuse trustworthy findings until files or assumptions change. Avoid repeated directory scans, helper inspection, full logs and whole-repository dumps.
- Give new children compact packets: goal, file pointers, relevant contracts, owned paths, constraints, exact acceptance criteria and result budget. Never drop necessary evidence to satisfy a token target.
- Request concise findings and test receipts; keep full logs in local artifacts and quote only failing sections. Do not ask writers to re-explain unchanged background on every round.
- Reuse an existing child for a related follow-up **with the same model** when its context is useful. A new task or different capability needs a new compact child, not a model switch on resume. No in-conversation hot switching.
- Keep stable instructions stable where the provider supports caching. Avoid gratuitous timestamps and reordered boilerplate. Do not retain irrelevant bulk context merely to chase cache hits; long-context pricing and reasoning over noise can dominate.
- Prefer Standard speed for routine work. Do not enable Fast/Ultrafast solely as a token-saving measure. Do not automatically change the user's current speed or provider settings.
- Preserve meaningful tests, security/data invariants and independent review for risky changes. A cheap failed attempt plus rework can cost more than one properly scoped Sol task. Escalate from Luna by returning findings and spawning a new Sol packet; stronger expensive models require explicit approval/pinning.

## Policy and session stability

The user-supplied [ZiCode article](https://zicode.com/blog/codex-multi-agent-sol-luna/) motivates isolating noisy exploration from the controller and returning compact evidence. Adapt that method to current Sol/Luna rather than copying its older model IDs or rate assumptions. If the implementation boundary is unknown, use a narrow scout first, let the controller confirm the contract, then dispatch the writer; these dependent stages are not a parallel wave. Keep small work local and do not interpret “controller” as a prohibition on direct work.

Evaluate improvements on comparable real tasks: acceptance/test success, rework, defect severity, total billed tokens/cost across all children, elapsed time and controller-context growth. Faster parallel completion alone does not prove lower cost. Do not launch a paid benchmark merely to install this skill; use evidence from authorized work or a separately requested evaluation.

Only IDs in `automatic_models` enter automatic selection. An unavailable Sol does not automatically become Astra or GPT-5.6 Sol. New model discovery is still dynamic, but adding a new automatic candidate requires checking its price and role fit. User-approved pins are explicit exceptions and remain subject to runtime availability and effort checks.

Record the chosen model for each conversation/subagent and keep it fixed. Changing a role file affects future children after reload; it does not change a running child. Preserve the user's current main model/effort and recommend Sol for a new session rather than trying to change the active conversation.

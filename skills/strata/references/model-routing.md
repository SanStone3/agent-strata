# Codex routing

Use the active spawn tool's schema as authority for model IDs, effort, fork rules and capacity. A separate CLI/API catalog does not prove access from this client. Resolve once per host/login/provider/tool context; refresh on a relevant change or explicit unavailable-model rejection. Do not rediscover on every packet.

## Task and effort

`scout` and `executor` default to Luna medium. Use Luna low for exact lookups or mechanical steps with simple checks. `worker` defaults to Terra medium for ordinary coding and can use Terra high when the task still has a clear boundary. If Terra lacks the requested effort or modality, the resolver can use Sol at the same effort. Automatic worker selection at xhigh uses Sol. Use `deep_worker` or `reviewer` for complex implementation or consequential review with Sol high/xhigh. Those roles require the balanced tier or an eligible explicit pin. The automatic candidates are the reviewed Luna, Terra and Sol IDs in the model policy.

```bash
python3 scripts/resolve_models.py --catalog /path/to/current-catalog.json --role worker
python3 scripts/resolve_models.py --catalog /path/to/current-catalog.json \
  --effort worker=high --role worker
python3 scripts/resolve_models.py --catalog /path/to/current-catalog.json \
  --effort deep_worker=high --role deep_worker
```

`--pin ROLE=MODEL` honors an eligible explicit choice without silent fallback. `--effort ROLE=LEVEL` requires the requested effort within the role contract and the model's catalog support. A harder task receives a new, bounded Sol packet after the controller inspects completed work. `--task-kind coding` and `--task-kind scoped` remain accepted for compatibility and use the same worker policy.

Tool-derived catalog format:

```json
{"source":"active native spawn tool","models":[
  {"model":"gpt-6.1-sol","efforts":["low","medium","high","xhigh","max"]}
]}
```

Include every relevant model and actual supported effort. This example is not an access claim. Add timezone-aware `captured_at` if saved; dated catalogs expire after 24 hours. Unknown capability stays unclassified. New IDs require evidence-backed classification and price review before joining `automatic_models`; availability/version alone is insufficient. `--allowed-model` intersects a narrower calling-tool allowlist. Image tasks require verified modality metadata and `--require-modality image`.

If the active tool exposes no catalog, use matching-client read-only discovery:

```bash
python3 scripts/resolve_models.py --discover --codex /path/to/codex \
  --codex-home /path/to/home --cwd /path/to/project
```

Discovery uses initialize/model-list plus optional config/account reads and login status classification. It never starts inference or returns credentials. Preserve the executable, CODEX_HOME, provider, profile and process environment. Separate logins/SSH: [auth-context.md](auth-context.md).

## Primary selection and rendering

The primary follows the current user-selected CLI/App model and effort on every turn. Strata neither polls a hidden UI selection nor hot-switches the running model itself: client turn settings take effect when the host applies them. Never claim a file edit changed an active model. Do not restore a previously observed value after the user switches.

The resolver preserves primary settings by default. `--preserve-primary` remains a compatibility flag. Explicit `--role controller` or `--pin controller=MODEL` produces advisory information only; `--effort controller=LEVEL` can accompany explicit controller resolution. **Rendering never emits primary model/effort/context keys**, even with an advisory controller binding; validation never treats user primary changes as drift. A skill cannot alter host lifecycle/turn-setting support.

```bash
python3 scripts/resolve_models.py --catalog /path/to/current-catalog.json \
  --output-dir /path/to/new-staging-dir
```

The new directory contains resolved `agents/*.toml`, `config-snippet.toml`, `AGENTS-snippet.md`, and `model-bindings.json`. The `[agents]` default uses the worker binding. Merge the rendered files during an authorized installation. Use a named role when its effective model and effort match. For per-task overrides, use a generic child with explicit model and effort if a custom definition would override them. Include the same read-only or write scope in the packet. Use a history-free fork when required by the tool. See [Codex integration](codex.md) for reload and precedence.

Exit codes: 0 resolved requested roles; 2 valid catalog with unmet constraints; 1 invalid input/discovery/render failure. An unresolved role cannot be dispatched. Bindings capture policy/catalog/context fingerprints, selected task kind/efforts and `access_verified: false`. Verification recomputes them; do not edit manifests to hide drift.

## Recovery

For explicit unknown-model/unsupported-effort rejection before execution: refresh the same surface once, exclude the rejected model and retry at most once with a role-eligible alternative. Pins do not fall back. Scope/correctness failures require inspecting state and rewriting the task, not blind replay. Authentication, quota, rate limits, network or encrypted-region failures are not evidence that a cheaper model is needed; preserve the login and return the actual gap.

Legacy aliases: `luna_scout`→`scout`, `luna_executor`→`executor`, `terra_worker`→`worker`, `sol_worker`→`deep_worker`, `sol_reviewer`→`reviewer`. Migrate definitions and callers together; no alias implicitly changes a running child.

Sources: [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), [model selection](https://developers.openai.com/api/docs/guides/model-selection), [app-server models](https://learn.chatgpt.com/docs/app-server#models).

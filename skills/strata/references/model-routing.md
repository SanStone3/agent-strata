# Adaptive Codex model routing

Read this for Codex delegation, installation, model upgrades or unavailable-model failures. Claude keeps its independent native alias workflow in [claude.md](claude.md).

## Stable roles and authoritative inputs

The role names are `scout`, `executor`, `worker`, `deep_worker`, and `reviewer`. Their write boundaries and reasoning requirements do not change when models change. The separate `controller` binding defaults to the reviewed GPT-6.1 Sol model at `xhigh`. It configures the primary session, not a sixth subagent. Preserve context and auto-compact settings. This skill cannot switch an already-running primary model by editing a file.

Read the active native spawn tool's schema first. Its permitted model IDs, effort values, fork rules and host restrictions are authoritative for that call. A desktop app, CLI, API account and remote host can have different catalogs. Never assume API `/v1/models`, a local cache file, or a separate CLI process proves what the current spawn tool accepts.

For a tool that exposes a model/effort list, transcribe those exact values into a small catalog:

```json
{
  "source": "current native spawn tool on the target host",
  "models": [
    {"model": "gpt-6.1-sol", "efforts": ["low", "medium", "high", "xhigh"]}
  ]
}
```

This is an illustrative one-role catalog, not a default allowlist. Include every available model and its actual effort options. Add `captured_at` as an ISO timestamp with timezone when saving it. Tool-derived catalogs may omit modality metadata for text tasks; image requirements need explicit capability evidence.

If the current tool does not expose a catalog and the matching CLI is available, use the resolver's short-lived app-server discovery. It sends only `initialize`, `initialized` and paginated `model/list`, then exits. It never sends `thread/start` or `turn/start`, reads credentials directly, starts inference, or changes client configuration. Its catalog can be bundled/cached: access remains unverified until an authorized task successfully runs. Do not launch a second inference client to bypass a native tool restriction.

For account/API-key coexistence and remote shells, read [auth-context.md](auth-context.md). Discovery supports `--codex-home`, `--cwd`, `--profile`, `--expected-auth` and `--expected-provider`; keep each generated binding with its own target. Preserve the target process's existing proxy and provider-key environment without printing or copying credentials.

## Resolve before dispatch

Use Python 3.10+ (stdlib only; no API key or additional package required):

```bash
python3 scripts/resolve_models.py --catalog /path/to/models.json --role worker
python3 scripts/resolve_models.py --discover --role worker
```

Run from the installed skill directory, or prefix `scripts/` with its absolute path. `--codex /path/to/codex` selects the matching executable; `--timeout 20` bounds discovery including pagination. A model override requiring a compact packet/limited fork must not be combined with a full-history fork. Use the actual tool's parameter names: map `reasoning_effort` to `reasoning_effort`, `thinking`, or the documented equivalent; the JSON result is not itself a spawn request.

The resolver returns bindings, alternatives, unresolved roles, unclassified models, policy/catalog fingerprints, non-secret execution context and its fingerprint, capture time and `access_verified: false`. Exit codes: `0` means the requested role (or all roles when omitted) resolved; `2` means a valid catalog has unmet role constraints; `1` means invalid input, discovery failure, stale data or rendering failure. Never dispatch an unresolved role.

If combining a CLI catalog with a narrower calling-tool allowlist, repeat `--allowed-model MODEL` for the allowed IDs. Effort options must also agree: construct the input catalog from their intersection when the surfaces differ. `--require-modality image` requires explicit image metadata. An empty/failed discovery must not turn into an unconstrained allowlist.

Honor user-selected role models by passing `--pin ROLE=MODEL` (or putting them in a local policy's `pins`). Existing installation-specific model choices remain pinned unless the user has requested adaptive management of those roles. Pins never silently fall back and still require the role's effort and minimum capability. An explicit controller pin may choose a lower known tier because the user owns that choice; it must still support `xhigh`. To preserve a different primary effort too, use `--preserve-primary`. Unknown models require an evidence-backed classification before use. Missing constraints mean “unresolved”, not permission to guess.

Example of deliberately keeping a selected worker model:

```bash
python3 scripts/resolve_models.py --catalog /path/to/models.json \
  --pin worker=gpt-6-sol --role worker
```

## Task-sensitive cost preferences

The default `automatic_models` allowlist contains only `gpt-6.1-sol` and `gpt-6-luna`, whose pricing and role fit have been reviewed. Discovery can report other/newer models, but availability or a version number alone does not authorize automatic paid selection. Review price and capability before adding a new ID. An explicit user-approved pin bypasses the automatic list while retaining capability, effort, visibility and caller-allowlist checks. Missing approved models remain unresolved; never silently fall back to Astra or a legacy model.

`role_preferences` orders eligible candidates only; it cannot bypass `automatic_models`. The default prefers GPT-6 Luna for scout/executor and Sol for implementation/review. These roles describe tasks, not claims that all model tiers have identical capability. See [cost-control.md](cost-control.md).

## How adaptation works

[../assets/model-policy.json](../assets/model-policy.json) is a Strata policy, not a Codex configuration file. The reviewed families classify efficiency, balanced implementation and deep reasoning. Future minor versions within those reviewed families are eligible when the current catalog lists them with the required effort. Numeric version comparison happens only after family classification; arbitrary newer names are never assumed stronger.

Catalog `upgrade` links can carry a known role tier to a new successor name. Explicit policy classifications take precedence when a successor is already known. Cycles or conflicting inherited tiers stop resolution. After role-specific preferences, prefer the current reviewed lineage, newer numeric version and upgrade successor; use the catalog default as a tie-breaker. Hidden entries are eligible only through an explicit pin. Missing effort data does not prove support for `xhigh`.

The controller is resolved together with the five subagent roles. Use `--role controller` to inspect its recommendation, `--pin controller=MODEL` for an explicit primary choice, or `--preserve-primary` to exclude primary configuration from the output. A controller pin and preserve-primary are mutually exclusive. Existing model settings do not count as an intentional pin when the user requests the recommended setup; explicit user choices do. Primary and subagent catalogs can differ: resolve the controller against its own host/model-picker catalog before applying it.

Automatic alternatives stay in the same capability tier. This is a capability policy, not a live price estimator: no price or quota is inferred from the model name. Apply any organization budget/allowlist before resolution. A user may explicitly pin a stronger tier; automatic escalation to another tier is disabled. A new major family with no reliable upgrade link remains unclassified until reviewed.

To classify an organization-approved full ID or a newly reviewed family, copy the policy outside the installed package, change only the necessary entries, and pass `--policy /path/to/policy.json`. An exact model entry under `models` needs `tier`, integer `priority`, and `evidence` (official source or organization approval). Do not fabricate evidence, parse marketing text as executable policy, or change the five role contracts. The policy fingerprint makes changes visible to the validator.

Resolve once at first delegation, keep the binding stable for that session and refresh when the host/account/provider/tool changes, a model is explicitly unavailable, or the user requests an upgrade. Files older than 24 hours are rejected when capture time is present. Undated input is a caller-supplied snapshot that must be freshly obtained; no persistent cache is automatically reused. Do not schedule background updates or modify a running wave's assignments. Never change the model of an existing conversation/subagent; any escalation creates a new compact child packet.

## Dispatch and bounded recovery

When creating a new native child and the spawn tool accepts model and effort overrides, pass the binding explicitly along with the role's instructions and task packet. Supplying `sandbox_mode` in the binding describes the required boundary; apply it only through supported tool/config fields and keep read-only constraints in the packet. A result field never overrides the host's permissions.

When the tool only supports named agent definitions, use a rendered installation (below). A bare model-free template is not an adaptive installed agent: it would inherit an arbitrary parent/default. Do not claim runtime adaptation if the client cannot override the model or reload changed definitions. Regenerate the definitions at a session boundary, verify the active settings, and start a new session when needed. Full-history forks inherit the parent model when required by the tool; they cannot be used to implement mixed-model routing.

For an explicit unknown/unavailable-model or unsupported-effort rejection before execution: refresh the same surface once, add the rejected model with `--exclude MODEL`, resolve the same role again, and retry at most once using an eligible alternative. A pin stays unresolved rather than being replaced. No alternative means return the gap to the controller; it may complete the task locally if its existing model and permissions meet the task requirements.

Authentication, payment/quota, rate limits, transport failures and task/test failures are not model-unavailability evidence. Do not rotate models to bypass them. A task failure can justify a newly bounded `deep_worker` packet after the controller inspects evidence, not automatic replay of the old worker.

Encrypted reasoning or cross-region replay errors are also not model-unavailability evidence. Follow [auth-context.md](auth-context.md); if a history-free native child is already failing, surface the provider/client compatibility gap rather than cycling through models or declaring basic API connectivity equivalent to native delegation.

If a failed task may have edited files or called external services, inspect actual state before any retry. Pass completed work and remaining scope in the new packet. Never blindly replay a writer, reset user changes, or loop over the candidate list. Report selected model/effort, reason for any switch and validation evidence; successful discovery alone is not an inference test.

## Render and migrate installed definitions

```bash
python3 scripts/resolve_models.py --discover --output-dir /path/to/new-staging-dir
```

Or use `--catalog` when the active tool is the authority. The output directory must not exist. Rendering requires a resolved controller (unless `--preserve-primary`) and all five subagent roles, and produces `agents/*.toml`, `config-snippet.toml`, `AGENTS-snippet.md`, and `model-bindings.json`. It writes only that new directory and removes incomplete output on an error. It never installs into a live home or merges unrelated settings.

Follow [install.md](install.md) to back up and merge. Merge the generated top-level `model` and `model_reasoning_effort` for the controller, `default_subagent_model`, and explicit per-role models. With `--preserve-primary`, generated output omits primary keys. Preserve context window, permissions and unrelated settings. Keep `model-bindings.json` beside the merged configuration for inspection, but regenerate it from the current surface when validating a later upgrade. Do not commit host/account-specific catalogs or global configuration to the public repository.

Legacy names are migration aliases:

| Old name | Stable role |
|---|---|
| `luna_scout` | `scout` |
| `luna_executor` | `executor` |
| `terra_worker` | `worker` |
| `sol_worker` | `deep_worker` |
| `sol_reviewer` | `reviewer` |

The resolver accepts old names in `--role` and `--pin`. The validator accepts old installed filenames when the stable file is absent, and checks them against the corresponding new binding when supplied. This does not magically rebind old agents: merge the resolved model into the chosen definitions and update all routing references together. Preserve customized old files until the stable roles are verified; retire obsolete definitions only within the user's installation request. When both exist, validation checks the stable definition; do not dispatch stale legacy definitions.

```bash
python3 scripts/validate.py --codex-home /path/to/codex-home \
  --bindings /path/to/new-staging-dir/model-bindings.json
```

For project scope, add `--codex-rules /path/to/project/AGENTS.md`. If a local policy was used, pass the same `--model-policy /path/to/policy.json`. The validator recomputes the binding against its captured catalog and policy, checks target home/provider/profile and installed primary and subagent models/efforts against it, and rejects drift or stale snapshots. Without `--bindings`, installed validation reports that model compatibility is unverified. Neither mode proves account access, live tool compatibility, effective client precedence or inference success; verify those through the authorized native task.

## Sources

- [Model selection](https://developers.openai.com/api/docs/guides/model-selection)
- [Codex model/list](https://learn.chatgpt.com/docs/app-server#models)
- [Catalogs are not entitlement checks](https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server)

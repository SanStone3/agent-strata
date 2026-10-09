# Authentication and execution context

Use this for ChatGPT account login, API-key login, custom providers, IDE extensions, remote SSH or multiple Codex homes. Strata orchestrates the native client; it does not implement login or credential transport.

## Identify the actual client first

For each execution surface, record the executable and version, host, working directory, `CODEX_HOME`, selected profile, effective provider and authentication mode. Get effective configuration with the matching app-server's `config/read`, and authentication type with `account/read` without requesting a refresh. A matching `codex login status` can identify stored login mode when the account RPC is unavailable; it does not prove inference access. Never print its raw output because some versions include credential hints.

The VS Code extension can bundle a different Codex version and run under a different home/environment than the shell CLI. In Remote SSH, also determine whether the extension runs locally or on the remote host. Use its actual execution side; installing on a laptop does not install on a remote PC. Do not guess from the command name or share credentials between the two contexts.

| Surface | Skill package | Native roles/config/bindings |
|---|---|---|
| CLI, ChatGPT login | shared user-discovered skill directory | CLI's actual `CODEX_HOME` |
| IDE, API-key login | same package if the IDE discovers it | IDE backend's actual `CODEX_HOME` |
| Remote host | package installed on that host | remote client's actual `CODEX_HOME` |

Prefer `~/.agents/skills/strata/` for a shared personal package when both clients discover it. Also honor an already working `$CODEX_HOME/skills` installation. Verify each surface through its own `skills/list` instead of making duplicate installs that can shadow each other. Store generated `agents/*.toml`, `config.toml` changes and `strata/model-bindings.json` separately in each target home.

## Discover within one context

From the installed skill directory (replace executable, home and working directory with inspected values):

```bash
# Account-login CLI
python3 scripts/resolve_models.py --discover \
  --codex /path/to/cli/codex \
  --codex-home "$HOME/.codex" \
  --cwd /path/to/project --expected-auth chatgpt --expected-provider openai \
  --output-dir /path/to/new-cli-staging

# API-key IDE backend, using the already configured provider
python3 scripts/resolve_models.py --discover \
  --codex /path/to/extension/bin/codex \
  --codex-home "$HOME/.codex-ide" \
  --cwd /path/to/project --expected-auth api-key --expected-provider gateway \
  --output-dir /path/to/new-ide-staging
```

`gateway` is an example provider ID, not a provider to create. Use `openai` for direct OpenAI API access, or the existing custom provider ID. If the client uses a profile, add `--profile NAME`; do not silently retry without it when the profile is missing or unsupported. The current profile format is `<CODEX_HOME>/<NAME>.config.toml`; older client formats require explicit version adaptation. Provider/auth guards reject mismatches and unknown results.

The child process inherits the calling environment, with only a requested `CODEX_HOME` overridden. Run it from the same environment as the target client. In particular:

- An SSH shell may lack the proxy environment of a working desktop terminal; a timeout then is not evidence that account login is unsupported.
- An IDE may receive an API key from its launcher or credential store rather than the SSH shell. A shell-only key check does not establish whether the IDE can authenticate.
- Preserve existing environment-variable names and values for custom providers. Never read or print secrets to build model candidates, and never add a key to prompts, bindings, logs, repository files or generated Agent definitions.
- Do not copy `auth.json`, log out the account, add an API key, change `forced_login_method`, change endpoints, or bypass host permission controls merely to make discovery succeed.

The script itself reads metadata through the client, not credential files. It records a non-secret `context` and `context_sha256` alongside the catalog. Context includes executable, client version, home, host, cwd, profile, provider, auth mode and its evidence source; a provider endpoint may be represented only by a hash. Keep these machine-local artifacts outside the public repository. This fingerprint identifies a configuration context, not the API-key principal or authorization state. After credential rotation or account changes, discard old bindings and recheck access even if the fingerprint is unchanged.

## Keep discovery separate from access and execution

`model/list` can be a bundled/cached catalog. An API-key custom provider may return the same list as a ChatGPT session while supporting different models. Never treat that equality as proof of access. Public API `/v1/models` usually lacks complete reasoning/tool metadata; model names alone cannot satisfy the role contracts.

Verify progressively and report the achieved level:

1. **Discovery:** the target client discovers `strata` and returns a catalog.
2. **Binding:** the selected models support the required effort in that catalog and fit the target policy/allowlist.
3. **Inference:** a minimal authorized request succeeds through that exact client/provider. Account/key presence and an HTTP connection are weaker evidence.
4. **Native orchestration:** in a disposable workspace, the host uses its native spawn tool, the child completes, and the parent collects its result. Inspect actual tool evidence and effective model/effort; an agent saying it spawned a child is insufficient.

Smoke tests may consume the account's quota or API usage. When the user requests a working integration, keep them small and within that request: no business data, no persistent application edits, no deployment, and no unbounded retries. A successful test on one model does not validate every tier. Exercise the selected tiers proportionately or report those not exercised.

Keep the controller's authentication/provider inherited by its native children. A named Agent file must not override `model_provider` to a different provider. When the runtime supports model overrides, use the current binding and the exact native schema. When it exposes named roles only, render/merge those definitions and reload at a session boundary. Do not launch an independently authenticated CLI or provider API and call it a native subagent.

## Install and validate independently

Back up each target home before merging its own rendered configuration. Preserve provider tables, credential-store settings, account files, endpoint URLs, unrelated plugins, trust entries and context limits. Do not apply a controller/model recommendation unsupported by that provider; use an approved policy/pin or leave the role unresolved. Preserve the user's primary setting explicitly with `--preserve-primary` when needed.

Run one validation per home:

```bash
python3 scripts/validate.py --codex-home "$HOME/.codex" \
  --bindings /path/to/new-cli-staging/model-bindings.json
python3 scripts/validate.py --codex-home "$HOME/.codex-ide" \
  --bindings /path/to/new-ide-staging/model-bindings.json
```

For a profile add `--codex-profile NAME`. For project-level rules add `--codex-rules /path/to/project/AGENTS.md`. Pass `--runtime-context /path/to/fresh-discovery.json` (or a JSON context object) to compare the complete freshly observed context, not only the target home's configured provider/profile. Manual catalogs without provenance remain usable but cannot prove execution-context identity.

The validator refuses a binding from a different home/provider/profile, detects primary and role drift, and rejects role-specific provider overrides. Without `--runtime-context`, it explicitly warns that current auth/endpoint/executable identity remains unverified even when the saved binding carries provenance. Full context comparison requires a newly observed context from the target, not another copy of the saved binding. It does not prove live entitlement, effective session overrides or native spawn behavior. A currently running chat may retain its prior settings; report when a new session or extension reload is needed.

## Failure classification and autonomous behavior

For an API provider rejecting a parameter with an error such as `reasoning.summary is not supported`, inspect the exact target CODEX_HOME and back up its configuration. The compatibility settings belong at the TOML root, before the first table, not under `[agents]` or a provider table:

```toml
model_reasoning_summary = "none"
model_supports_reasoning_summaries = false
```

Apply these only for a matching error or a provider's documented requirement, to the API-key context that needs them. With separate CLI and IDE homes, the IDE file may be `<IDE_CODEX_HOME>/config.toml`, not `~/.codex/config.toml`. Preserve auth, endpoint, model and requested reasoning effort; start a new test conversation and verify the outgoing request/effective effort. Summary visibility is not a measurement of reasoning tokens. The meaning of the support flag can vary by client/model; do not claim that a configured xhigh reached the provider without evidence. If the error persists, report the unsupported field rather than dropping all reasoning or switching credentials.

A local transport-only probe of the inspected IDE backend (0.162.0-alpha.2, GPT-6.1 Sol) showed `reasoning.effort=xhigh` in the request with either `summary="none"` alone or both settings. Neither case sent a summary field. This confirms that client's request construction only, not provider inference quality or every version's behavior. See the [official configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

The controller should continue native orchestration autonomously when capability, scope and permissions are established. It should not ask for login merely because both login modes exist. Only request user action for an actual expired/revoked login, missing key, account/organization restriction or unresolved authority.

- **Transport/proxy failure:** compare the target environment, repair only authorized configuration, then make a bounded retry. Do not change auth or models to hide a connection failure.
- **Authentication failure:** stop that context's attempts, report login/key action needed, and preserve the other context.
- **Quota/rate limit:** respect that provider's response; do not switch to the other login automatically.
- **Explicit model/effort rejection:** refresh that same context and apply the existing bounded same-tier recovery policy. Pins remain authoritative.
- **Encrypted-context/region rejection:** a message such as “Encrypted content cannot be used in a different region” is a provider/session compatibility failure, not a bad password or missing model. Check that the native child used a compact packet with `fork_turns: "none"` where supported. If it already did, do not loop, copy authentication, strip encrypted reasoning, change endpoints or lower effort. Report the affected model/provider combination, keep completed work, and let the controller finish locally where appropriate. The provider/client must support compatible regional routing and encrypted-context replay before that native path can be declared working. Direct single-turn model success does not establish this capability.
- **No native subagent tools:** complete locally if appropriate, or explain the client limitation. More shell processes do not create supported native orchestration.

## Official references

- [Authentication](https://learn.chatgpt.com/docs/auth)
- [Workspace model availability](https://learn.chatgpt.com/docs/enterprise/workspace-model-availability)
- [CLI options and profiles](https://learn.chatgpt.com/docs/cli/reference)
- [Developer settings and IDE executable](https://learn.chatgpt.com/docs/developer-settings)

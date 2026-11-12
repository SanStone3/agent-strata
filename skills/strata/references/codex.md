# Codex integration

The primary model/effort belongs to the current CLI/App selection. Strata never installs primary keys or rejects a later user switch. Sol xhigh is a suggested personal starting point, not an invariant.

Check the active native tool's roles, override fields and fork restrictions. Codex custom agent model and effort settings take precedence over spawn values. Use an explicitly selected generic child if the named role pins different values and the tool supports overrides. The controller must preserve the role's task and permission boundaries. Reload named definitions through the client's supported session boundary and verify the effective binding for new children. Default routes and the resolver are in [model-routing.md](model-routing.md). [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

Templates live in `assets/templates/codex/`; rendered definitions need `name`, `description`, `model`, `model_reasoning_effort`, `sandbox_mode` and `developer_instructions`. Source templates omit concrete model IDs. Never install unresolved templates. Read-only sandbox declarations do not override the parent/host permissions; preserve read-only behavior in the packet too.

Use each client's actual CODEX_HOME for config, agents and bindings. Share skill files, not credentials or provider-bound manifests. Trusted-project settings load only under the client's trust policy; installation does not grant new trust.

Strata omits a numeric concurrency key. Use the native tool's actual slot count and [scaling.md](scaling.md). Preserve explicit user limits. Do not assume an old config key controls a newer host, and do not change feature flags to chase parallelism.

Follow the actual tool lifecycle: spawn may return before completion; a message may not wake an idle child; a follow-up may start another turn. Collect required results before delivery. No descendant delegation, cross-provider calls, independent commit/push/deploy or scope expansion.

Install and verify through [install.md](install.md) and [validation.md](validation.md). Sources: [subagents](https://developers.openai.com/codex/subagents), [config](https://developers.openai.com/codex/config-basic), [skills](https://developers.openai.com/codex/skills).

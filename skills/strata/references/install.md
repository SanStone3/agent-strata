# Install or update

Share skill source; keep each client's config, agents, login and context-bound manifests separate.

| Item | Codex personal | Project |
|---|---|---|
| Skill | `~/.agents/skills/strata` | `.agents/skills/strata` |
| Config / agents | actual `CODEX_HOME/config.toml`, `CODEX_HOME/agents` | `.codex/config.toml`, `.codex/agents` |
| Rules | actual `CODEX_HOME/AGENTS.md` | `AGENTS.md` |

Claude uses `~/.claude/skills`, `~/.claude/agents`, `~/.claude/settings.json`, `~/.claude/CLAUDE.md` or project equivalents. Keep Claude model/effort policy independent; see [claude.md](claude.md).

## Shared main checkout

For a maintained single source, clone the public repository's `main` branch, then link discovered skill locations to `<checkout>/skills/strata`. Inspect and back up existing directories before replacing them with links. Preserve local improvements by integrating them before replacement. Do not copy credentials or provider-specific bindings into the repository.

```bash
git clone --branch main https://github.com/SanStone3/agent-strata.git /path/to/agent-strata
# After checking and backing up any existing target:
ln -s /path/to/agent-strata/skills/strata /path/to/discovered-skills/strata
```

All linked projects then read the same source. **A symlink tracks the checkout, not remote pushes automatically.** On an authorized update inspect status/remotes, fetch main and fast-forward only; preserve a dirty/diverged checkout for inspection. Do not reset/stash/rewrite local work.

```bash
git -C /path/to/agent-strata fetch origin main
git -C /path/to/agent-strata merge --ff-only origin/main
```

No background updater is installed. Fetch/update at an authorized maintenance point, not on every model turn. Restart/reload only when the client requires it and no active task is disrupted. Model policy changes invalidate prior fingerprints; regenerate bindings per client before dispatching changed named roles.

A snapshot installation is also available:

```bash
npx -y skills@1.5.23 add SanStone3/agent-strata -g -a codex -s strata -y
```

That installer is [Vercel's CLI](https://github.com/vercel-labs/skills), not native Codex; a copied snapshot needs a later explicit update.

## Merge client configuration

1. Identify the actual executable/home/scope and read target files. Back up changed files outside the public repository; exclude secrets.
2. Native runtime model/effort overrides can route new children directly. For definition-only clients, resolve a fresh matching-client catalog and render into a new staging directory; see [model-routing.md](model-routing.md).
3. Merge only the generated agent table, definitions and one delimited rules section. Preserve user customizations, primary model/effort/context, provider, auth, permissions, MCP and hooks. Source templates are not resolved agents.
4. Keep concurrency unset in Strata templates. Remove a known old Strata three-agent pin during this requested upgrade; preserve explicit user/project limits and actual host capacity. Default to one writer.
5. Claude installation separately merges its templates and spawn depth policy; do not alter its model policy as part of a Codex refresh.
6. Parse and run [validation](validation.md). Verify skill discovery and effective role model/effort in the intended client; catalog/structural checks do not prove inference access. New definitions may need a new session; do not restart an active client automatically.

Primary `controller` resolution is advisory only. Rendering never writes primary settings; a user's subsequent CLI/App switch is expected, not configuration drift. Do not install an auto-updater that resets it.

Uninstall by removing only known links, merged Strata keys and managed rule sections from the change record, preserving later user edits. Keep pre-install backups until verification. A skill uninstall does not remove independently installed agent/config files.

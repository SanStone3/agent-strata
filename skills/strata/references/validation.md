# Validation and troubleshooting

## Source package

From the repository root:

```bash
python3 skills/strata/scripts/validate.py --repo .
python3 -m unittest discover -s tests -v
npx -y skills@1.5.23 add . --list
```

From an installed skill directory, validate the package alone:

```bash
python3 scripts/validate.py
```

If OpenAI's `skill-creator` is installed, also run its `quick_validate.py` against `skills/strata`.

## Explicit Codex home check

To inspect an active Codex setup, pass its home directory explicitly:

```bash
python3 skills/strata/scripts/validate.py --repo . --codex-home /path/to/codex-home
```

This is read-only and checks only `/path/to/codex-home/config.toml`, its five expected `agents/*.toml` files, and `/path/to/codex-home/AGENTS.md`. `--repo` validates the source package; `--codex-home` validates those active-client invariants without requiring whole-file equality. An installed home may pin a concurrency ceiling above the default budget when the user asked for it, so the installed check accepts a positive value while the template must stay at `3`. Without `--codex-home`, validation does not inspect a default home or claim to validate an active client.

## Explicit Claude home check

To inspect an active Claude Code setup:

```bash
python3 skills/strata/scripts/validate.py --repo . --claude-home /path/to/claude-home
```

This is read-only and checks `/path/to/claude-home/settings.json` (`model`, `effortLevel`, and `env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`) and its seven expected `agents/*.md` files against the tier invariants: model alias, effort, tool lists, `maxTurns`, and the no-descendant prohibition. It also checks that `/path/to/claude-home/CLAUDE.md` still states the core policies: default budget of three active subagents, one writer by default, the conditions for raising the budget, disjoint write domains, no descendants, and no cross-provider invocation. The patterns tolerate reworded personal variants, so a customized rules file passes as long as the policies survive.

## Installed configuration

Check, without exposing secrets:

1. Skill discovery reports `strata` for the intended client and scope.
2. TOML, JSON, YAML frontmatter, and `agents/openai.yaml` parse successfully.
3. Each native Agent definition has required frontmatter/keys and a unique name.
4. Scouts/reviewers have read-only tools or sandbox defaults.
5. Code Workers and consequential Reviewers explicitly request `xhigh`, and client status confirms the resolved model actually supports and uses it.
6. No Agent instruction invokes the other provider, commits, pushes, deploys, or spawns descendants. On Claude Code, `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` is `1` so this is also enforced mechanically.
7. The rules section states the default budget of three active subagents and one writer, that the budget caps concurrency rather than total work, the conditions for raising it, disjoint write domains with frozen shared contracts, no descendant or cross-provider invocation, and compact or limited forks for named custom roles.
8. The effective concurrency cap is known and recorded, not merely requested: for Codex, confirmed by observed parallelism; for Claude Code, the client default unless the user asked for another ceiling.
9. Existing unrelated settings remain present.

## Behavioral smoke test

Use a disposable or read-only task:

```text
Map the three most relevant code paths for this bug using a read-only scout.
Return only file/symbol evidence, uncertainty, and the recommended next step.
```

Then use a temporary small implementation and observe that the controller assigns only one writing worker and reviews its returned diff.

To test the budget itself, request a read-only wave of one more agent than the intended budget and observe the client's actual parallelism and its refusal behavior. Do not run that test with writers.

## Common failures

### Skill installed but not visible

- Confirm the reported path with `npx skills list -g --json` or project-level `npx skills list --json`.
- Restart the client if the top-level skill directory was created after session startup.
- Check YAML frontmatter and directory name.

### Custom agents not visible

- Verify the scope path and unique `name` values.
- Restart after first creating the agents directory.
- For Codex project agents, verify project trust without changing it implicitly.
- For Claude, use `/doctor` and inspect current scope precedence.

### Wrong effort or model

- Check runtime/session overrides, environment variables, managed settings, and custom Agent fields in precedence order.
- Do not claim the configured value is effective until the client status confirms it. Claude aliases that resolve to 4.6-class models can lower `xhigh` to `high`; pin an approved compatible full model ID or report the invariant as unmet.
- If an alias resolves differently on a third-party provider, pin an approved full model ID.

### A raised concurrency ceiling has no effect

- Confirm which configuration file and scope the client actually loads.
- Observe real parallelism instead of trusting the requested key. On Codex, a build whose multi-agent feature owns concurrency ignores the older key; confirm the honored key against that version's documentation before touching feature tables.
- On Claude Code, a spawn refusal reports `Concurrent subagent limit reached` and instructs no retry. Queue the packet rather than raising the ceiling, unless the user asked for a higher one.
- Remember that forks consume a slot and resumes bypass the limit check, so observed parallelism can exceed the configured ceiling without any error.

### Descendant agents appear

- On Claude Code, set `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` to `1` and start a new session.
- Confirm every Agent definition still carries the no-descendant prohibition; a replaced or user-edited definition is the usual cause.

### Fable fails

Return the exact availability, quota, billing, or version condition. Do not loop. Claude fallback is not triggered by authentication, billing, rate-limit, request-size, or transport errors.

### Too many write conflicts

Stop the wave, inspect the working tree, and reassign one writer at a time. Re-partition the write domains before the next parallel attempt, and pull every shared path into controller scope. Do not use destructive Git cleanup to erase user work.

# Validation and troubleshooting

## Source package

From the repository root:

```bash
python3 skills/layered-orchestration/scripts/validate.py --repo .
python3 -m unittest discover -s tests -v
npx -y skills@1.5.23 add . --list
```

If OpenAI's `skill-creator` is installed, also run its `quick_validate.py` against `skills/layered-orchestration`.

## Explicit Codex home check

To inspect an active Codex setup, pass its home directory explicitly:

```bash
python3 skills/layered-orchestration/scripts/validate.py --repo . --codex-home /path/to/codex-home
```

This is read-only and checks only `/path/to/codex-home/config.toml`, its five expected `agents/*.toml` files, and `/path/to/codex-home/AGENTS.md`. `--repo` validates the source package; `--codex-home` validates those active-client invariants without requiring whole-file equality. Without `--codex-home`, validation does not inspect a default home or claim to validate an active client.

## Installed configuration

Check, without exposing secrets:

1. Skill discovery reports `layered-orchestration` for the intended client and scope.
2. TOML, JSON, YAML frontmatter, and `agents/openai.yaml` parse successfully.
3. Each native Agent definition has required frontmatter/keys and a unique name.
4. Scouts/reviewers have read-only tools or sandbox defaults.
5. Code Workers and consequential Reviewers explicitly request `xhigh`, and client status confirms the resolved model actually supports and uses it.
6. No Agent instruction invokes the other provider, commits, pushes, deploys, or spawns descendants.
7. The rules section states max three active subagents, one writer by default, no descendant or cross-provider invocation, and compact or limited forks for named custom roles.
8. Existing unrelated settings remain present.

## Behavioral smoke test

Use a disposable or read-only task:

```text
Map the three most relevant code paths for this bug using a read-only scout.
Return only file/symbol evidence, uncertainty, and the recommended next step.
```

Then use a temporary small implementation and observe that the controller assigns only one writing worker and reviews its returned diff.

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

### Fable fails

Return the exact availability, quota, billing, or version condition. Do not loop. Claude fallback is not triggered by authentication, billing, rate-limit, request-size, or transport errors.

### Too many write conflicts

Stop parallel writers, inspect the working tree, and reassign one writer at a time. Do not use destructive Git cleanup to erase user work.

# Validation

```bash
python3 skills/strata/scripts/validate.py --repo .
python3 -m unittest discover -s tests -v
# Optional if the matching skill-creator is installed:
python3 /path/to/skill-creator/scripts/quick_validate.py skills/strata
```

Installed package alone: `python3 scripts/validate.py`. Active client checks are opt-in and read-only:

```bash
python3 skills/strata/scripts/validate.py --repo . --codex-home /path/to/home \
  --bindings /path/to/fresh/model-bindings.json
python3 skills/strata/scripts/validate.py --repo . --claude-home /path/to/claude-home
```

Codex checks five roles, models, selected efforts, boundaries and rules. Templates omit primary keys and numeric concurrency caps; installed configs may have explicit positive user caps or omit them. Current user primary selection is never compared with an old controller recommendation. Bindings are recomputed from their catalog/policy/context; no manifest means model availability/tier compatibility remains unverified.

Use each login's actual CODEX_HOME. Pass a fresh catalog from the matching client or a fresh `resolve_models.py --discover` result to `--runtime-context`. The validator checks the capture time, client context and normalized model catalog against the installed binding. A bare context has no timestamp or model evidence. `--codex-profile NAME` selects the profile, `--model-policy` selects an approved policy, and `--codex-rules` supports rules above `.codex`. Keep catalogs and account markers private and local to the client.

Claude validation retains its independent alias/effort/tool/spawn-depth contracts. It does not prove the provider's alias resolves to a compatible model.

Verification levels:

1. Structure: parse files, references and roles; no secrets/private paths.
2. Discovery: the intended client sees skill and role definitions/catalog entries.
3. Native execution: an authorized packet actually runs with the expected model/effort and permissions.
4. Acceptance: returned changes and meaningful task checks pass.

Do not present level 1 or 2 as level 3 or 4. Use authorized work for native verification; no paid benchmark solely for installation. If testing capacity is requested, use disposable read-only packets and respect host refusal without looping.

For failures inspect active client precedence and actual schema. Missing roles may require a session reload. Unsupported effort remains unresolved; authentication/quota/transport errors do not trigger model cycling. Encrypted-region/history errors: [auth-context.md](auth-context.md). Conflicting writers: stop affected work, inspect and serialize; do not erase user changes.

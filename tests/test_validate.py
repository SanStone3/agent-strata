from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from unittest import mock
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_SKILL = REPO_ROOT / "skills" / "strata"
VALIDATOR_PATH = SOURCE_SKILL / "scripts" / "validate.py"

SPEC = importlib.util.spec_from_file_location("agent_strata_validate", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATE)


class ValidatorMutationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="agent-strata-validator-")
        self.skill = Path(self.temporary.name) / "strata"
        shutil.copytree(SOURCE_SKILL, self.skill)
        self.codex_home = Path(self.temporary.name) / "codex-home"
        self.codex_home.mkdir()
        template = self.skill / "assets" / "templates" / "codex"
        policy = VALIDATE.ROUTING.read_json(self.skill / "assets/model-policy.json")
        catalog = {"models": [{"model": name, "efforts": ["medium", "xhigh"]}
                              for name in ("gpt-6-luna", "gpt-6.1-sol", "gpt-6-astra")]}
        self.binding = VALIDATE.ROUTING.resolve(catalog, policy)
        staging = Path(self.temporary.name) / "rendered"
        VALIDATE.ROUTING.render(self.binding, staging, self.skill)
        shutil.copy(staging / "config-snippet.toml", self.codex_home / "config.toml")
        shutil.copytree(staging / "agents", self.codex_home / "agents")
        shutil.copy(staging / "AGENTS-snippet.md", self.codex_home / "AGENTS.md")
        self.bindings_path = staging / "model-bindings.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def validate(
        self, codex_home: Path | None = None, claude_home: Path | None = None, bindings: Path | None = None
    ) -> tuple[int, str]:
        stderr = io.StringIO()
        stdout = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
            code = VALIDATE.Validator(None, self.skill, codex_home, claude_home, bindings).run()
        return code, stderr.getvalue() + stdout.getvalue()

    def replace(self, relative: str, before: str, after: str) -> None:
        path = self.skill / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(before, text)
        path.write_text(text.replace(before, after, 1), encoding="utf-8")

    def test_baseline_passes(self) -> None:
        code, output = self.validate()
        self.assertEqual(0, code, output)

    def test_hardcoded_codex_template_model_fails(self) -> None:
        self.replace("assets/templates/codex/agents/reviewer.toml", 'name = "reviewer"', 'name = "reviewer"\nmodel = "gpt-6-astra"')
        code, output = self.validate()
        self.assertEqual(1, code)
        self.assertIn("reviewer.toml template must not hard-code a model", output)

    def test_wrong_codex_agent_defaults_fail(self) -> None:
        self.replace("assets/templates/codex/config-snippet.toml", "enabled = true", "enabled = false")
        self.replace("assets/templates/codex/config-snippet.toml", "[agents]", '[agents]\ndefault_subagent_model = "gpt-6-luna"')
        code, output = self.validate()
        self.assertEqual(1, code)
        self.assertIn("Codex agents must be enabled", output)
        self.assertIn("resolve the default subagent model dynamically", output)

    def test_wrong_claude_model_fails(self) -> None:
        self.replace("assets/templates/claude/agents/opus-worker.md", "model: opus", "model: haiku")
        code, output = self.validate()
        self.assertEqual(1, code)
        self.assertIn("opus-worker.md model must be opus", output)

    def test_non_xhigh_worker_fails(self) -> None:
        self.replace("assets/templates/claude/agents/sonnet-worker.md", "effort: xhigh", "effort: high")
        code, output = self.validate()
        self.assertEqual(1, code)
        self.assertIn("sonnet-worker.md effort must be xhigh", output)

    def test_unterminated_frontmatter_fails(self) -> None:
        self.replace("assets/templates/claude/agents/haiku-scout.md", "\n---\n\nExplore only.", "\n\nExplore only.")
        code, output = self.validate()
        self.assertEqual(1, code)
        self.assertIn("unterminated YAML frontmatter", output)

    def test_secret_in_yaml_fails(self) -> None:
        secret = "github_" + "pat_" + "A" * 24
        path = self.skill / "leak.yml"
        path.write_text(f"token: {secret}\n", encoding="utf-8")
        code, output = self.validate()
        self.assertEqual(1, code)
        self.assertIn("secret or private absolute path", output)

    def test_private_home_path_in_python_fails(self) -> None:
        private_path = "/home/" + "sample-user/private-project"
        path = self.skill / "leak.py"
        path.write_text(f"PRIVATE_PATH = {private_path!r}\n", encoding="utf-8")
        code, output = self.validate()
        self.assertEqual(1, code)
        self.assertIn("secret or private absolute path", output)

    def test_missing_codex_core_policies_fail(self) -> None:
        self.replace(
            "assets/templates/codex/AGENTS-snippet.md", "at most three active subagents", "at most four active subagents"
        )
        self.replace("assets/templates/codex/AGENTS-snippet.md", "one writer by default", "multiple writers by default")
        self.replace("assets/templates/codex/AGENTS-snippet.md", "Subagents do not spawn descendants", "Subagents may spawn descendants")
        self.replace(
            "assets/templates/codex/AGENTS-snippet.md", "invoke another coding-agent provider", "invoke external agents"
        )
        code, output = self.validate()
        self.assertEqual(1, code)
        for policy in (
            "max three active subagents",
            "one writer by default",
            "no descendant agents",
            "no cross-provider invocation",
        ):
            self.assertIn(f"missing Codex AGENTS policy: {policy}", output)

    def test_missing_codex_compact_fork_rule_fails(self) -> None:
        self.replace(
            "assets/templates/codex/AGENTS-snippet.md",
            "Named custom roles use compact task packets or limited recent-turn forks",
            "Named custom roles may use full-history forks",
        )
        self.replace(
            "assets/templates/codex/AGENTS-snippet.md",
            "Never combine explicit custom type with full-history fork",
            "Full-history forks are allowed",
        )
        code, output = self.validate()
        self.assertEqual(1, code)
        self.assertIn("missing Codex AGENTS policy: compact or limited fork", output)
        self.assertIn("missing Codex AGENTS policy: no full-history custom fork", output)

    def test_explicit_codex_home_checks_active_configuration(self) -> None:
        (self.codex_home / "AGENTS.md").write_text(
            """- Keep at most three spawned workers open; allow only one code-writing worker by default.
- The budget limits concurrency, not total work; further packets run in later waves.
- The budget may be raised only when every writer owns disjoint write domains with frozen shared contracts.
- Never invoke Claude, `claude`, a Claude MCP server, or a cross-provider wrapper from Codex.
- Workers must not commit, push, deploy, or spawn more agents.
- When spawning a named custom role, pass a compact task packet or a limited recent-turn fork. Do not use a full-history fork with an explicit custom agent type.
""",
            encoding="utf-8",
        )
        code, output = self.validate(self.codex_home)
        self.assertEqual(0, code, output)
        config = self.codex_home / "config.toml"
        config.write_text(config.read_text().replace('model = "gpt-6-astra"', 'model = "user-selected-model"').replace('model_reasoning_effort = "xhigh"', 'model_reasoning_effort = "high"'), encoding="utf-8")
        code, output = self.validate(self.codex_home)
        self.assertEqual(0, code, output)
        config.write_text(config.read_text().replace("user-selected-model", "gpt-6-astra").replace('model_reasoning_effort = "high"', 'model_reasoning_effort = "xhigh"'))
        agent = self.codex_home / "agents/reviewer.toml"
        agent.write_text(agent.read_text().replace("gpt-6-astra", "gpt-6-luna"))
        code, output = self.validate(self.codex_home, bindings=self.bindings_path)
        self.assertEqual(1, code)
        self.assertIn("reviewer.toml model differs from the reviewer binding", output)

    def test_explicit_claude_home_checks_active_configuration(self) -> None:
        claude_home = Path(self.temporary.name) / "claude-home"
        claude_home.mkdir()
        template = self.skill / "assets" / "templates" / "claude"
        shutil.copy(template / "settings-snippet.json", claude_home / "settings.json")
        shutil.copytree(template / "agents", claude_home / "agents")
        shutil.copy(template / "CLAUDE-snippet.md", claude_home / "CLAUDE.md")
        code, output = self.validate(claude_home=claude_home)
        self.assertEqual(0, code, output)
        settings = claude_home / "settings.json"
        settings.write_text(
            '{"model": "claude-fable-5[1m]", "effortLevel": "xhigh",'
            ' "env": {"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1"}}',
            encoding="utf-8",
        )
        code, output = self.validate(claude_home=claude_home)
        self.assertEqual(0, code, output)
        settings.write_text(
            '{"model": "haiku", "effortLevel": "xhigh",'
            ' "env": {"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1"}}',
            encoding="utf-8",
        )
        code, output = self.validate(claude_home=claude_home)
        self.assertEqual(1, code)
        self.assertIn("Opus- or Fable-class", output)
        shutil.copy(template / "settings-snippet.json", settings)
        rules = claude_home / "CLAUDE.md"
        rules.write_text(
            rules.read_text(encoding="utf-8").replace("one writer by default", "many writers", 1),
            encoding="utf-8",
        )
        code, output = self.validate(claude_home=claude_home)
        self.assertEqual(1, code)
        self.assertIn("missing Claude rules policy: one writer by default", output)
        shutil.copy(template / "CLAUDE-snippet.md", rules)
        agent = claude_home / "agents" / "opus-reviewer.md"
        agent.write_text(
            agent.read_text(encoding="utf-8").replace("effort: xhigh", "effort: high", 1),
            encoding="utf-8",
        )
        code, output = self.validate(claude_home=claude_home)
        self.assertEqual(1, code)
        self.assertIn("opus-reviewer.md effort must be xhigh", output)

    def test_fallback_toml_ignores_unrelated_tables_and_values(self) -> None:
        (self.codex_home / "config.toml").write_text(
            """model = "gpt-5.6-sol"
model_context_window = 1000000
model_auto_compact_token_limit = 900000
model_reasoning_effort = "xhigh"
status_line = ["ignored"]

[agents]
max_concurrent_threads_per_session = 3
default_subagent_model = "gpt-5.6-terra"
default_subagent_reasoning_effort = "xhigh"
enabled = true

[projects."/example"]
trust_level = "trusted"

[tui]
status_line = ["model-name"]
""",
            encoding="utf-8",
        )
        with mock.patch.object(VALIDATE, "tomllib", None):
            code, output = self.validate(self.codex_home)
        self.assertEqual(0, code, output)


    def test_template_concurrency_budget_must_pin_three(self) -> None:
        self.replace(
            "assets/templates/codex/config-snippet.toml",
            "max_concurrent_threads_per_session = 3",
            "max_concurrent_threads_per_session = 6",
        )
        code, output = self.validate()
        self.assertEqual(1, code)
        self.assertIn("Codex template concurrency budget must pin 3 spawned threads", output)

    def test_installed_home_may_raise_the_concurrency_ceiling(self) -> None:
        config = self.codex_home / "config.toml"
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                "max_concurrent_threads_per_session = 3",
                "max_concurrent_threads_per_session = 6",
                1,
            ),
            encoding="utf-8",
        )
        code, output = self.validate(self.codex_home)
        self.assertEqual(0, code, output)
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                "max_concurrent_threads_per_session = 6",
                "max_concurrent_threads_per_session = 0",
                1,
            ),
            encoding="utf-8",
        )
        code, output = self.validate(self.codex_home)
        self.assertEqual(1, code)
        self.assertIn("max_concurrent_threads_per_session must be a positive integer", output)

    def test_installed_home_may_omit_the_long_session_baseline(self) -> None:
        config = self.codex_home / "config.toml"
        kept = [
            line
            for line in config.read_text(encoding="utf-8").splitlines()
            if not line.startswith(("model_context_window", "model_auto_compact_token_limit"))
        ]
        config.write_text("\n".join(kept) + "\n", encoding="utf-8")
        code, output = self.validate(self.codex_home)
        self.assertEqual(0, code, output)

    def test_installed_compact_limit_must_stay_below_the_window(self) -> None:
        config = self.codex_home / "config.toml"
        config.write_text('model_context_window = 1000000\nmodel_auto_compact_token_limit = 1000000\n' + config.read_text())
        code, output = self.validate(self.codex_home)
        self.assertEqual(1, code)
        self.assertIn("auto-compact limit must stay below the context window", output)

    def test_legacy_installed_roles_are_checked_against_bindings(self) -> None:
        for alias, role in VALIDATE.ROUTING.ALIASES.items():
            p = self.codex_home / "agents" / (role.replace("_", "-") + ".toml")
            text = p.read_text().replace('name = "' + role + '"', 'name = "' + alias + '"')
            p.unlink()
            (p.parent / (alias.replace("_", "-") + ".toml")).write_text(text)
        code, output = self.validate(self.codex_home, bindings=self.bindings_path)
        self.assertEqual(0, code, output)
        self.assertIn("Legacy role terra_worker maps to worker", output)

    def test_missing_binding_warns_without_claiming_access(self) -> None:
        code, output = self.validate(self.codex_home)
        self.assertEqual(0, code, output)
        self.assertIn("availability and tier compatibility are unverified", output)
        self.assertIn("inference access not tested", output)

    def test_binding_drift_is_rejected(self) -> None:
        self.binding["bindings"]["worker"]["model"] = "gpt-6-luna"
        self.bindings_path.write_text(json.dumps(self.binding))
        code, output = self.validate(self.codex_home, bindings=self.bindings_path)
        self.assertEqual(1, code)
        self.assertIn("Binding no longer matches", output)

    def test_controller_configuration_drift_is_rejected(self) -> None:
        config = self.codex_home / "config.toml"
        config.write_text(config.read_text().replace('model_reasoning_effort = "xhigh"', 'model_reasoning_effort = "high"'))
        code, output = self.validate(self.codex_home, bindings=self.bindings_path)
        self.assertEqual(1, code)
        self.assertIn("primary model/effort differs from the controller binding", output)

    def test_installed_models_cannot_be_omitted(self) -> None:
        p = self.codex_home / "agents/worker.toml"
        p.write_text('\n'.join(line for line in p.read_text().splitlines() if not line.startswith('model =')))
        code, output = self.validate(self.codex_home)
        self.assertEqual(1, code)
        self.assertIn("installed agent needs a resolved model", output)

    def test_default_model_drift_fails_with_binding(self) -> None:
        p = self.codex_home / "config.toml"
        p.write_text(p.read_text().replace("gpt-6.1-sol", "gpt-6-luna"))
        code, output = self.validate(self.codex_home, bindings=self.bindings_path)
        self.assertEqual(1, code)
        self.assertIn("default subagent model differs", output)

    def test_primary_model_must_not_be_in_template(self) -> None:
        p = self.skill / "assets/templates/codex/config-snippet.toml"
        p.write_text('model = "gpt-6-astra"\n' + p.read_text())
        code, output = self.validate()
        self.assertEqual(1, code)
        self.assertIn("preserve primary model", output)

    def test_readonly_reviewer_cannot_become_writer(self) -> None:
        self.replace("assets/templates/codex/agents/reviewer.toml", 'sandbox_mode = "read-only"', 'sandbox_mode = "workspace-write"')
        code, output = self.validate()
        self.assertEqual(1, code)
        self.assertIn("sandbox must be read-only", output)

    def test_project_rules_can_live_above_codex_home(self) -> None:
        rules = Path(self.temporary.name) / "AGENTS.md"
        shutil.move(self.codex_home / "AGENTS.md", rules)
        validator = VALIDATE.Validator(None, self.skill, self.codex_home, bindings=self.bindings_path, codex_rules=rules)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, validator.run(), validator.errors)

    def test_missing_scaling_reference_fails(self) -> None:
        (self.skill / "references" / "scaling.md").unlink()
        code, output = self.validate()
        self.assertEqual(1, code)
        self.assertIn("missing file: references/scaling.md", output)

    def test_missing_claude_scaling_policies_fail(self) -> None:
        self.replace(
            "assets/templates/claude/CLAUDE-snippet.md",
            "The budget caps concurrency, not total work",
            "Open as many agents as convenient",
        )
        self.replace("assets/templates/claude/CLAUDE-snippet.md", "Raise the budget only", "Feel free to raise it")
        self.replace("assets/templates/claude/CLAUDE-snippet.md", "disjoint write domains", "separate areas")
        code, output = self.validate()
        self.assertEqual(1, code)
        for policy in (
            "budget caps concurrency, not total work",
            "conditions for raising the budget",
            "disjoint write domains",
        ):
            self.assertIn(f"missing Claude rules policy: {policy}", output)

    def test_claude_spawn_depth_must_be_one(self) -> None:
        self.replace(
            "assets/templates/claude/settings-snippet.json",
            '"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1"',
            '"CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "2"',
        )
        code, output = self.validate()
        self.assertEqual(1, code)
        self.assertIn("CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH must be", output)


if __name__ == "__main__":
    unittest.main()

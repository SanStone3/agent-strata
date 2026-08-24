from __future__ import annotations

import contextlib
import importlib.util
import io
import shutil
import tempfile
import unittest
from unittest import mock
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_SKILL = REPO_ROOT / "skills" / "layered-orchestration"
VALIDATOR_PATH = SOURCE_SKILL / "scripts" / "validate.py"

SPEC = importlib.util.spec_from_file_location("agent_strata_validate", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATE)


class ValidatorMutationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="agent-strata-validator-")
        self.skill = Path(self.temporary.name) / "layered-orchestration"
        shutil.copytree(SOURCE_SKILL, self.skill)
        self.codex_home = Path(self.temporary.name) / "codex-home"
        self.codex_home.mkdir()
        template = self.skill / "assets" / "templates" / "codex"
        shutil.copy(template / "config-snippet.toml", self.codex_home / "config.toml")
        shutil.copytree(template / "agents", self.codex_home / "agents")
        shutil.copy(template / "AGENTS-snippet.md", self.codex_home / "AGENTS.md")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def validate(self, codex_home: Path | None = None) -> tuple[int, str]:
        stderr = io.StringIO()
        stdout = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
            code = VALIDATE.Validator(None, self.skill, codex_home).run()
        return code, stderr.getvalue() + stdout.getvalue()

    def replace(self, relative: str, before: str, after: str) -> None:
        path = self.skill / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(before, text)
        path.write_text(text.replace(before, after, 1), encoding="utf-8")

    def test_baseline_passes(self) -> None:
        code, output = self.validate()
        self.assertEqual(0, code, output)

    def test_wrong_codex_model_fails(self) -> None:
        self.replace("assets/templates/codex/agents/sol-reviewer.toml", 'model = "gpt-5.6-sol"', 'model = "gpt-5.6-luna"')
        code, output = self.validate()
        self.assertEqual(1, code)
        self.assertIn("sol-reviewer.toml model must be gpt-5.6-sol", output)

    def test_wrong_codex_agent_defaults_fail(self) -> None:
        self.replace("assets/templates/codex/config-snippet.toml", "enabled = true", "enabled = false")
        self.replace(
            "assets/templates/codex/config-snippet.toml",
            'default_subagent_model = "gpt-5.6-terra"',
            'default_subagent_model = "gpt-5.6-luna"',
        )
        code, output = self.validate()
        self.assertEqual(1, code)
        self.assertIn("Codex agents must be enabled", output)
        self.assertIn("Codex default subagent model must be gpt-5.6-terra", output)

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
- Never invoke Claude, `claude`, a Claude MCP server, or a cross-provider wrapper from Codex.
- Workers must not commit, push, deploy, or spawn more agents.
- When spawning a named custom role, pass a compact task packet or a limited recent-turn fork. Do not use a full-history fork with an explicit custom agent type.
""",
            encoding="utf-8",
        )
        code, output = self.validate(self.codex_home)
        self.assertEqual(0, code, output)
        config = self.codex_home / "config.toml"
        config.write_text(
            config.read_text(encoding="utf-8").replace('model = "gpt-5.6-sol"', 'model = "gpt-5.6-luna"', 1),
            encoding="utf-8",
        )
        code, output = self.validate(self.codex_home)
        self.assertEqual(1, code)
        self.assertIn("Codex primary model must be gpt-5.6-sol", output)

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


if __name__ == "__main__":
    unittest.main()

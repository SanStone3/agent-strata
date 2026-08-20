from __future__ import annotations

import contextlib
import importlib.util
import io
import shutil
import tempfile
import unittest
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

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def validate(self) -> tuple[int, str]:
        stderr = io.StringIO()
        stdout = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
            code = VALIDATE.Validator(None, self.skill).run()
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


if __name__ == "__main__":
    unittest.main()

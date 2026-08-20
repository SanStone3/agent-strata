#!/usr/bin/env python3
"""Read-only structural validation for the Agent Strata repository."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    tomllib = None  # type: ignore[assignment]

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - optional for installed-skill checks
    yaml = None  # type: ignore[assignment]


REQUIRED_ROOT_FILES = (
    "README.md",
    "LICENSE",
    "docs/installation.md",
    "docs/orchestration.md",
)

REQUIRED_SKILL_FILES = (
    "SKILL.md",
    "agents/openai.yaml",
    "references/install.md",
    "references/codex.md",
    "references/claude.md",
    "references/task-contract.md",
    "references/validation.md",
    "assets/templates/codex/config-snippet.toml",
    "assets/templates/codex/AGENTS-snippet.md",
    "assets/templates/claude/settings-snippet.json",
    "assets/templates/claude/CLAUDE-snippet.md",
)

CODEX_AGENTS = {
    "luna-scout.toml": ("luna_scout", "gpt-5.6-luna", "medium", "read-only"),
    "luna-executor.toml": ("luna_executor", "gpt-5.6-luna", "medium", "workspace-write"),
    "terra-worker.toml": ("terra_worker", "gpt-5.6-terra", "xhigh", "workspace-write"),
    "sol-worker.toml": ("sol_worker", "gpt-5.6-sol", "xhigh", "workspace-write"),
    "sol-reviewer.toml": ("sol_reviewer", "gpt-5.6-sol", "xhigh", "read-only"),
}

READ_ONLY_TOOLS = frozenset({"Read", "Grep", "Glob"})
WRITE_TOOLS = frozenset({"Read", "Grep", "Glob", "Edit", "Write", "Bash"})

CLAUDE_AGENTS = {
    "haiku-scout.md": ("haiku-scout", "haiku", None, READ_ONLY_TOOLS, 32),
    "sonnet-worker.md": ("sonnet-worker", "sonnet", "xhigh", WRITE_TOOLS, 64),
    "opus-worker.md": ("opus-worker", "opus", "xhigh", WRITE_TOOLS, 80),
    "opus-reviewer.md": ("opus-reviewer", "opus", "xhigh", READ_ONLY_TOOLS, 48),
    "fable-controller.md": ("fable-controller", "fable", "xhigh", None, None),
    "fable-worker.md": ("fable-worker", "fable", "xhigh", WRITE_TOOLS, 120),
    "fable-reviewer.md": ("fable-reviewer", "fable", "xhigh", READ_ONLY_TOOLS, 80),
}


class Validator:
    def __init__(self, repo: Path | None, skill: Path) -> None:
        self.repository_mode = repo is not None
        self.root = repo.resolve() if repo is not None else skill.resolve()
        self.skill = self.root / "skills" / "layered-orchestration" if repo is not None else self.root
        self.errors: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def require(self, path: Path) -> bool:
        if not path.is_file():
            self.error(f"missing file: {path.relative_to(self.root)}")
            return False
        return True

    def load_toml(self, path: Path) -> dict[str, Any]:
        if tomllib is not None:
            try:
                with path.open("rb") as handle:
                    return tomllib.load(handle)
            except (OSError, tomllib.TOMLDecodeError) as exc:
                self.error(f"invalid TOML {path.relative_to(self.root)}: {exc}")
                return {}

        # Python 3.10 has no tomllib. Parse the deliberately small template
        # subset without adding a package dependency: tables, strings, ints,
        # booleans, and triple-quoted multiline strings.
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            self.error(f"cannot read TOML {path.relative_to(self.root)}: {exc}")
            return {}

        result: dict[str, Any] = {}
        current = result
        multiline_key: str | None = None
        multiline_lines: list[str] = []
        for number, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            if multiline_key is not None:
                if stripped.endswith('"""'):
                    before = raw_line.rsplit('"""', 1)[0]
                    if before:
                        multiline_lines.append(before)
                    current[multiline_key] = "\n".join(multiline_lines)
                    multiline_key = None
                    multiline_lines = []
                else:
                    multiline_lines.append(raw_line)
                continue
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("[") and stripped.endswith("]"):
                section = stripped[1:-1].strip()
                if not section or "." in section:
                    self.error(f"unsupported TOML table at {path.relative_to(self.root)}:{number}")
                    return {}
                value = result.setdefault(section, {})
                if not isinstance(value, dict):
                    self.error(f"conflicting TOML table at {path.relative_to(self.root)}:{number}")
                    return {}
                current = value
                continue
            if "=" not in raw_line:
                self.error(f"invalid TOML line at {path.relative_to(self.root)}:{number}")
                return {}
            key, raw_value = (part.strip() for part in raw_line.split("=", 1))
            if raw_value == '"""':
                multiline_key = key
                multiline_lines = []
            elif raw_value.startswith('"') and raw_value.endswith('"'):
                try:
                    current[key] = json.loads(raw_value)
                except json.JSONDecodeError as exc:
                    self.error(f"invalid TOML string at {path.relative_to(self.root)}:{number}: {exc}")
                    return {}
            elif raw_value in ("true", "false"):
                current[key] = raw_value == "true"
            elif re.fullmatch(r"[+-]?\d+", raw_value):
                current[key] = int(raw_value)
            else:
                self.error(f"unsupported TOML value at {path.relative_to(self.root)}:{number}")
                return {}
        if multiline_key is not None:
            self.error(f"unterminated TOML multiline string in {path.relative_to(self.root)}")
            return {}
        return result

    @staticmethod
    def basic_yaml_scalar(raw_value: str) -> Any:
        value = raw_value.strip()
        if value.startswith('"') and value.endswith('"'):
            return json.loads(value)
        if value.startswith("'") and value.endswith("'"):
            return value[1:-1].replace("''", "'")
        if value.startswith(('"', "'")) or value.endswith(('"', "'")):
            raise ValueError("unbalanced quoted scalar")
        if value in ("true", "false"):
            return value == "true"
        if re.fullmatch(r"[+-]?\d+", value):
            return int(value)
        return value

    def basic_yaml_mapping(self, block: str, path: Path) -> dict[str, Any]:
        result: dict[str, Any] = {}
        stack: list[tuple[int, dict[str, Any]]] = [(-1, result)]
        for number, raw_line in enumerate(block.splitlines(), start=1):
            if not raw_line.strip() or raw_line.lstrip().startswith("#"):
                continue
            if "\t" in raw_line:
                self.error(f"tabs are not valid indentation in {path.relative_to(self.root)}:{number}")
                return {}
            indent = len(raw_line) - len(raw_line.lstrip(" "))
            match = re.match(r"^\s*([A-Za-z][A-Za-z0-9_-]*):(?:\s+(.*))?$", raw_line)
            if not match:
                self.error(f"unsupported YAML at {path.relative_to(self.root)}:{number}")
                return {}
            while stack and indent <= stack[-1][0]:
                stack.pop()
            if not stack:
                self.error(f"invalid YAML indentation at {path.relative_to(self.root)}:{number}")
                return {}
            parent = stack[-1][1]
            key, raw_value = match.group(1), match.group(2)
            if key in parent:
                self.error(f"duplicate YAML key {key} at {path.relative_to(self.root)}:{number}")
                return {}
            if raw_value is None or not raw_value.strip():
                child: dict[str, Any] = {}
                parent[key] = child
                stack.append((indent, child))
            else:
                try:
                    parent[key] = self.basic_yaml_scalar(raw_value)
                except (ValueError, json.JSONDecodeError) as exc:
                    self.error(f"invalid YAML scalar at {path.relative_to(self.root)}:{number}: {exc}")
                    return {}
        return result

    def load_yaml(self, path: Path, *, frontmatter: bool) -> dict[str, Any]:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.error(f"cannot read YAML {path.relative_to(self.root)}: {exc}")
            return {}

        block = text
        if frontmatter:
            lines = text.splitlines()
            if not lines or lines[0] != "---":
                self.error(f"missing YAML frontmatter: {path.relative_to(self.root)}")
                return {}
            try:
                closing = lines.index("---", 1)
            except ValueError:
                self.error(f"unterminated YAML frontmatter: {path.relative_to(self.root)}")
                return {}
            block = "\n".join(lines[1:closing])

        if yaml is None:
            return self.basic_yaml_mapping(block, path)
        try:
            values = yaml.safe_load(block)
        except yaml.YAMLError as exc:
            self.error(f"invalid YAML {path.relative_to(self.root)}: {exc}")
            return {}
        if not isinstance(values, dict):
            self.error(f"YAML root must be a mapping: {path.relative_to(self.root)}")
            return {}
        return values

    def validate_layout(self) -> None:
        if self.repository_mode:
            for relative in REQUIRED_ROOT_FILES:
                self.require(self.root / relative)
        for relative in REQUIRED_SKILL_FILES:
            self.require(self.skill / relative)

    def validate_skill(self) -> None:
        path = self.skill / "SKILL.md"
        if not self.require(path):
            return
        values = self.load_yaml(path, frontmatter=True)
        if values.get("name") != "layered-orchestration":
            self.error("SKILL.md name must be layered-orchestration")
        description = values.get("description", "")
        for phrase in ("Codex", "Claude Code", "xhigh", "do not use"):
            if phrase not in description:
                self.error(f"SKILL.md description must discriminate on: {phrase}")

        metadata_path = self.skill / "agents/openai.yaml"
        metadata = self.load_yaml(metadata_path, frontmatter=False)
        interface = metadata.get("interface", {})
        if not isinstance(interface, dict):
            self.error("agents/openai.yaml interface must be a mapping")
        else:
            for key in ("display_name", "short_description", "default_prompt"):
                if not interface.get(key):
                    self.error(f"agents/openai.yaml missing interface.{key}")

    def validate_codex(self) -> None:
        config_path = self.skill / "assets/templates/codex/config-snippet.toml"
        config = self.load_toml(config_path)
        if config.get("model") != "gpt-5.6-sol":
            self.error("Codex primary model must be gpt-5.6-sol")
        if config.get("model_reasoning_effort") != "xhigh":
            self.error("Codex primary effort must be xhigh")
        if config.get("model_context_window") != 1_000_000:
            self.error("Codex context window must be 1000000")
        if config.get("model_auto_compact_token_limit") != 900_000:
            self.error("Codex auto-compact limit must be 900000")
        agents_config = config.get("agents", {})
        if agents_config.get("max_concurrent_threads_per_session") != 3:
            self.error("Codex max concurrent subagents must be 3")
        if agents_config.get("default_subagent_reasoning_effort") != "xhigh":
            self.error("Codex default subagent effort must be xhigh")

        names: set[str] = set()
        directory = self.skill / "assets/templates/codex/agents"
        for filename, (expected_name, model, effort, sandbox) in CODEX_AGENTS.items():
            path = directory / filename
            if not self.require(path):
                continue
            values = self.load_toml(path)
            for key in ("name", "description", "developer_instructions"):
                if not values.get(key):
                    self.error(f"{filename} missing required key: {key}")
            if values.get("name") != expected_name:
                self.error(f"{filename} has wrong name")
            if expected_name in names:
                self.error(f"duplicate Codex agent name: {expected_name}")
            names.add(expected_name)
            if values.get("model") != model:
                self.error(f"{filename} model must be {model}")
            if values.get("model_reasoning_effort") != effort:
                self.error(f"{filename} effort must be {effort}")
            if values.get("sandbox_mode") != sandbox:
                self.error(f"{filename} sandbox must be {sandbox}")
            if "spawn subagents" not in values.get("developer_instructions", ""):
                self.error(f"{filename} must prohibit descendant agents")

    def validate_claude(self) -> None:
        settings_path = self.skill / "assets/templates/claude/settings-snippet.json"
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.error(f"invalid Claude settings JSON: {exc}")
            settings = {}
        if settings.get("model") != "opus[1m]":
            self.error("Claude default model must be opus[1m]")
        if settings.get("effortLevel") != "xhigh":
            self.error("Claude default effortLevel must be xhigh")

        names: set[str] = set()
        directory = self.skill / "assets/templates/claude/agents"
        for filename, (expected_name, model, effort, expected_tools, max_turns) in CLAUDE_AGENTS.items():
            path = directory / filename
            if not self.require(path):
                continue
            values = self.load_yaml(path, frontmatter=True)
            for key in ("name", "description", "model"):
                if not values.get(key):
                    self.error(f"{filename} missing required frontmatter: {key}")
            if values.get("name") != expected_name:
                self.error(f"{filename} has wrong name")
            if expected_name in names:
                self.error(f"duplicate Claude agent name: {expected_name}")
            names.add(expected_name)
            if values.get("model") != model:
                self.error(f"{filename} model must be {model}")
            if effort is not None and values.get("effort") != effort:
                self.error(f"{filename} effort must be {effort}")
            raw_tools = values.get("tools")
            if isinstance(raw_tools, str):
                tools = {item.strip() for item in raw_tools.split(",") if item.strip()}
            elif isinstance(raw_tools, list):
                tools = {str(item) for item in raw_tools}
            else:
                tools = set()
            if expected_tools is None:
                if raw_tools is not None:
                    self.error(f"{filename} should inherit main-session tools")
            elif tools != expected_tools:
                self.error(f"{filename} tools must be {', '.join(sorted(expected_tools))}")
            if values.get("maxTurns") != max_turns:
                if max_turns is None:
                    self.error(f"{filename} must not set maxTurns")
                else:
                    self.error(f"{filename} maxTurns must be {max_turns}")
            if expected_name.endswith(("worker", "reviewer")) and values.get("effort") != "xhigh":
                self.error(f"{filename} code/review effort must be xhigh")
            body = path.read_text(encoding="utf-8")
            if "spawn subagents" not in body and expected_name != "fable-controller":
                self.error(f"{filename} must prohibit descendant agents")

    def validate_content(self) -> None:
        markdown_files = list(self.root.rglob("*.md"))
        checked_suffixes = {".md", ".toml", ".json", ".yaml", ".yml", ".py", ".txt"}
        source_files = [
            path
            for path in self.root.rglob("*")
            if path.is_file() and path.suffix.lower() in checked_suffixes and ".git" not in path.parts
        ]
        placeholder = re.compile(
            "|".join(
                (
                    r"\bTO" + r"DO\b",
                    r"\bT" + r"BD\b",
                    r"\bFIX" + r"ME\b",
                    r"\[TO" + r"DO",
                )
            )
        )
        secret_or_private = re.compile(
            "|".join(
                (
                    r"gh" + r"[opsu]_[A-Za-z0-9]{20,}",
                    r"github_" + r"pat_[A-Za-z0-9_]{20,}",
                    r"sk" + r"-[A-Za-z0-9]{20,}",
                    r"sk" + r"-ant-[A-Za-z0-9_-]{20,}",
                    r"/home/[A-Za-z0-9._-]+/",
                    r"/Users/[A-Za-z0-9._-]+/",
                    r"[A-Za-z]:\\Users\\[A-Za-z0-9._ -]+\\",
                )
            )
        )
        cross_invocation = re.compile(r"\b(?:codex\s+(?:exec|--)|claude\s+(?:-p|--print))\b", re.IGNORECASE)

        for path in source_files:
            text = path.read_text(encoding="utf-8")
            relative = path.relative_to(self.root)
            if placeholder.search(text):
                self.error(f"unfinished placeholder in {relative}")
            if secret_or_private.search(text):
                self.error(f"secret or private absolute path in {relative}")
            if cross_invocation.search(text):
                self.error(f"cross-provider CLI invocation pattern in {relative}")

        link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        for path in markdown_files:
            text = path.read_text(encoding="utf-8")
            for target in link_pattern.findall(text):
                clean = target.split("#", 1)[0].strip()
                if not clean or clean.startswith(("http://", "https://", "mailto:", "/")):
                    continue
                candidate = (path.parent / clean).resolve()
                if not candidate.exists():
                    self.error(f"broken local link in {path.relative_to(self.root)}: {target}")

    def run(self) -> int:
        self.validate_layout()
        self.validate_skill()
        self.validate_codex()
        self.validate_claude()
        self.validate_content()
        if self.errors:
            print("Agent Strata validation failed:", file=sys.stderr)
            for error in self.errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        print("Agent Strata validation passed")
        print(f"Target: {self.root}")
        print(f"Mode: {'repository' if self.repository_mode else 'installed skill'}")
        print(f"Codex agents: {len(CODEX_AGENTS)}")
        print(f"Claude agents: {len(CLAUDE_AGENTS)}")
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, help="Agent Strata repository root; omit to validate this installed skill")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    installed_skill = Path(__file__).resolve().parents[1]
    raise SystemExit(Validator(arguments.repo, installed_skill).run())

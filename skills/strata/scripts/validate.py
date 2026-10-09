#!/usr/bin/env python3
"""Read-only structural validation for the Agent Strata repository."""

from __future__ import annotations

import argparse
import importlib.util
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


_ROUTING_SPEC = importlib.util.spec_from_file_location("strata_routing", Path(__file__).with_name("resolve_models.py"))
assert _ROUTING_SPEC is not None and _ROUTING_SPEC.loader is not None
ROUTING = importlib.util.module_from_spec(_ROUTING_SPEC)
_ROUTING_SPEC.loader.exec_module(ROUTING)


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
    "references/model-routing.md",
    "references/auth-context.md",
    "assets/model-policy.json",
    "scripts/resolve_models.py",
    "references/claude.md",
    "references/task-contract.md",
    "references/scaling.md",
    "references/validation.md",
    "assets/templates/codex/config-snippet.toml",
    "assets/templates/codex/AGENTS-snippet.md",
    "assets/templates/claude/settings-snippet.json",
    "assets/templates/claude/CLAUDE-snippet.md",
)

CODEX_AGENTS = {
    role.replace("_", "-") + ".toml": (role, effort, sandbox)
    for role, (_, effort, sandbox) in ROUTING.ROLES.items()
}
LEGACY_CODEX_AGENTS = {role: alias for alias, role in ROUTING.ALIASES.items()}

CODEX_CONFIG_ROOT_KEYS = frozenset(
    {"model", "model_context_window", "model_auto_compact_token_limit", "model_reasoning_effort", "model_provider"}
)
CODEX_CONFIG_TABLE_KEYS = {
    "agents": frozenset(
        {
            "enabled",
            "max_concurrent_threads_per_session",
            "default_subagent_model",
            "default_subagent_reasoning_effort",
        }
    )
}

SHARED_SCALING_POLICIES = {
    "budget caps concurrency, not total work": re.compile(
        r"(?:budget caps concurrency,? not total work|budget limits concurrency,? not total work|"
        r"caps concurrency rather than total work)",
        re.IGNORECASE,
    ),
    "conditions for raising the budget": re.compile(
        r"(?:raise the budget only|raise that budget only|budget may be raised only)",
        re.IGNORECASE,
    ),
    "disjoint write domains": re.compile(r"disjoint write domains?", re.IGNORECASE),
}

CODEX_AGENTS_POLICIES = {
    "max three active subagents": re.compile(
        r"\b(?:at most three active subagents|at most three spawned workers open)\b", re.IGNORECASE
    ),
    "one writer by default": re.compile(
        r"\b(?:one writer by default|only one code-writing worker by default)\b", re.IGNORECASE
    ),
    "no descendant agents": re.compile(
        r"\b(?:subagents do not spawn descendants|workers must not\b[^\n]*\bspawn more agents)\b", re.IGNORECASE
    ),
    "no cross-provider invocation": re.compile(
        r"\b(?:invoke another coding-agent provider|never invoke claude\b[^\n]*\bcross-provider wrapper)\b",
        re.IGNORECASE,
    ),
    "compact or limited fork": re.compile(
        r"\b(?:named custom roles use compact task packets or limited recent-turn forks|when spawning a named custom role, pass a compact task packet or a limited recent-turn fork)\b",
        re.IGNORECASE,
    ),
    "no full-history custom fork": re.compile(
        r"\b(?:never combine explicit custom type with full-history fork|do not use a full-history fork with an explicit custom agent type)\b",
        re.IGNORECASE,
    ),
}

CLAUDE_RULES_POLICIES = {
    "max three active subagents": re.compile(
        r"\b(?:at most three active subagents|at most three workers active)\b", re.IGNORECASE
    ),
    "one writer by default": re.compile(
        r"\b(?:one writer by default|only one code-writing worker by default)\b", re.IGNORECASE
    ),
    "no descendant agents": re.compile(
        r"\b(?:subagents do not spawn descendants|workers must not\b[^\n]*\bspawn more agents)\b", re.IGNORECASE
    ),
    "no cross-provider invocation": re.compile(
        r"\b(?:invoke another coding-agent provider|never invoke codex\b[^\n]*\bcross-provider wrapper)\b",
        re.IGNORECASE,
    ),
}

CODEX_AGENTS_POLICIES.update(SHARED_SCALING_POLICIES)
CLAUDE_RULES_POLICIES.update(SHARED_SCALING_POLICIES)

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
    def __init__(
        self,
        repo: Path | None,
        skill: Path,
        codex_home: Path | None = None,
        claude_home: Path | None = None,
        bindings: Path | None = None,
        model_policy: Path | None = None,
        codex_rules: Path | None = None,
        codex_profile: str | None = None,
        runtime_context: Path | None = None,
    ) -> None:
        self.repository_mode = repo is not None
        self.root = repo.resolve() if repo is not None else skill.resolve()
        self.skill = self.root / "skills" / "strata" if repo is not None else self.root
        self.codex_home = codex_home.resolve() if codex_home is not None else None
        self.claude_home = claude_home.resolve() if claude_home is not None else None
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.bindings_path = bindings
        self.model_policy = model_policy or self.skill / "assets/model-policy.json"
        self.codex_rules = codex_rules
        self.codex_profile = codex_profile
        self.runtime_context = runtime_context
        self.binding_context: dict[str, Any] | None = None
        self.effective_codex_provider: str | None = None
        self.bindings: dict[str, Any] | None = None

    def error(self, message: str) -> None:
        self.errors.append(message)

    def display_path(self, path: Path) -> str:
        for base in (self.root, self.codex_home, self.claude_home):
            if base is not None:
                try:
                    return str(path.relative_to(base))
                except ValueError:
                    pass
        return path.name

    def require(self, path: Path) -> bool:
        if not path.is_file():
            self.error(f"missing file: {self.display_path(path)}")
            return False
        return True

    def load_toml(
        self,
        path: Path,
        *,
        root_keys: frozenset[str] | None = None,
        table_keys: dict[str, frozenset[str]] | None = None,
    ) -> dict[str, Any] | None:
        if tomllib is not None:
            try:
                with path.open("rb") as handle:
                    return tomllib.load(handle)
            except (OSError, tomllib.TOMLDecodeError) as exc:
                self.error(f"invalid TOML {self.display_path(path)}: {exc}")
                return None

        # Python 3.10 has no tomllib. Parse the deliberately small relevant
        # subset without adding a dependency, skipping unrelated config tables.
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            self.error(f"cannot read TOML {self.display_path(path)}: {exc}")
            return None

        result: dict[str, Any] = {}
        current: dict[str, Any] | None = result
        allowed_keys = root_keys
        multiline_key: str | None = None
        multiline_lines: list[str] = []
        for number, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            if multiline_key is not None:
                if stripped.endswith('"""'):
                    before = raw_line.rsplit('"""', 1)[0]
                    if before:
                        multiline_lines.append(before)
                    if current is None:
                        self.error(f"invalid TOML multiline string in {self.display_path(path)}:{number}")
                        return None
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
                if table_keys is not None and section not in table_keys:
                    current = None
                    allowed_keys = None
                    continue
                if not section or "." in section:
                    self.error(f"unsupported TOML table at {self.display_path(path)}:{number}")
                    return None
                value = result.setdefault(section, {})
                if not isinstance(value, dict):
                    self.error(f"conflicting TOML table at {self.display_path(path)}:{number}")
                    return None
                current = value
                allowed_keys = table_keys[section] if table_keys is not None else None
                continue
            if current is None:
                continue
            if "=" not in raw_line:
                self.error(f"invalid TOML line at {self.display_path(path)}:{number}")
                return None
            key, raw_value = (part.strip() for part in raw_line.split("=", 1))
            if allowed_keys is not None and key not in allowed_keys:
                continue
            if raw_value == '"""':
                multiline_key = key
                multiline_lines = []
            elif raw_value.startswith('"') and raw_value.endswith('"'):
                try:
                    current[key] = json.loads(raw_value)
                except json.JSONDecodeError as exc:
                    self.error(f"invalid TOML string at {self.display_path(path)}:{number}: {exc}")
                    return None
            elif raw_value in ("true", "false"):
                current[key] = raw_value == "true"
            elif re.fullmatch(r"[+-]?\d+", raw_value):
                current[key] = int(raw_value)
            else:
                self.error(f"unsupported TOML value at {self.display_path(path)}:{number}")
                return None
        if multiline_key is not None:
            self.error(f"unterminated TOML multiline string in {self.display_path(path)}")
            return None
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
                self.error(f"tabs are not valid indentation in {self.display_path(path)}:{number}")
                return {}
            indent = len(raw_line) - len(raw_line.lstrip(" "))
            match = re.match(r"^\s*([A-Za-z][A-Za-z0-9_-]*):(?:\s+(.*))?$", raw_line)
            if not match:
                self.error(f"unsupported YAML at {self.display_path(path)}:{number}")
                return {}
            while stack and indent <= stack[-1][0]:
                stack.pop()
            if not stack:
                self.error(f"invalid YAML indentation at {self.display_path(path)}:{number}")
                return {}
            parent = stack[-1][1]
            key, raw_value = match.group(1), match.group(2)
            if key in parent:
                self.error(f"duplicate YAML key {key} at {self.display_path(path)}:{number}")
                return {}
            if raw_value is None or not raw_value.strip():
                child: dict[str, Any] = {}
                parent[key] = child
                stack.append((indent, child))
            else:
                try:
                    parent[key] = self.basic_yaml_scalar(raw_value)
                except (ValueError, json.JSONDecodeError) as exc:
                    self.error(f"invalid YAML scalar at {self.display_path(path)}:{number}: {exc}")
                    return {}
        return result

    def load_yaml(self, path: Path, *, frontmatter: bool) -> dict[str, Any]:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.error(f"cannot read YAML {self.display_path(path)}: {exc}")
            return {}

        block = text
        if frontmatter:
            lines = text.splitlines()
            if not lines or lines[0] != "---":
                self.error(f"missing YAML frontmatter: {self.display_path(path)}")
                return {}
            try:
                closing = lines.index("---", 1)
            except ValueError:
                self.error(f"unterminated YAML frontmatter: {self.display_path(path)}")
                return {}
            block = "\n".join(lines[1:closing])

        if yaml is None:
            return self.basic_yaml_mapping(block, path)
        try:
            values = yaml.safe_load(block)
        except yaml.YAMLError as exc:
            self.error(f"invalid YAML {self.display_path(path)}: {exc}")
            return {}
        if not isinstance(values, dict):
            self.error(f"YAML root must be a mapping: {self.display_path(path)}")
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
        if values.get("name") != "strata":
            self.error("SKILL.md name must be strata")
        description = values.get("description", "")
        for phrase in ("Codex", "Claude Code", "xhigh", "concurrency budget", "do not use"):
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

    def validate_codex_config(self, config_path: Path, *, template: bool) -> None:
        config = self.load_toml(
            config_path, root_keys=CODEX_CONFIG_ROOT_KEYS, table_keys=CODEX_CONFIG_TABLE_KEYS
        )
        if config is None:
            return
        if not template and self.codex_profile:
            if not re.fullmatch(r"[A-Za-z0-9_-]+", self.codex_profile):
                self.error("Codex profile must be a simple profile name")
                return
            profile_path = config_path.parent / (self.codex_profile + ".config.toml")
            if not self.require(profile_path):
                return
            overlay = self.load_toml(profile_path, root_keys=CODEX_CONFIG_ROOT_KEYS, table_keys=CODEX_CONFIG_TABLE_KEYS)
            if overlay is None:
                return
            config = dict(config)
            for key, value in overlay.items():
                if isinstance(value, dict) and isinstance(config.get(key), dict):
                    config[key] = {**config[key], **value}
                else:
                    config[key] = value
        if not template:
            self.effective_codex_provider = config.get("model_provider") or "openai"
            if not isinstance(self.effective_codex_provider, str):
                self.error("Codex model_provider must be a string")
            if self.binding_context:
                if self.binding_context.get("provider") != self.effective_codex_provider:
                    self.error("Model binding provider differs from the selected Codex configuration")
        model = config.get("model")
        if template:
            if any(key in config for key in CODEX_CONFIG_ROOT_KEYS):
                self.error("Codex template must preserve primary model, effort and context settings")
        elif model is not None and (not isinstance(model, str) or not model.strip()):
            self.error("Codex primary model must be a nonempty string when set")
        if not template and self.bindings and "controller" in self.bindings:
            controller = self.bindings["controller"]
            if model != controller["model"] or config.get("model_reasoning_effort") != controller["reasoning_effort"]:
                self.error("Codex primary model/effort differs from the controller binding")
        window = config.get("model_context_window")
        compact = config.get("model_auto_compact_token_limit")
        for key, value in (("model_context_window", window), ("model_auto_compact_token_limit", compact)):
            if value is not None and (type(value) is not int or value <= 0):
                self.error(f"Codex {key} must be a positive integer when set")
        if type(window) is int and type(compact) is int and compact >= window:
            self.error("Codex auto-compact limit must stay below the context window")
        agents_config = config.get("agents", {})
        if not isinstance(agents_config, dict):
            self.error("Codex agents config must be a table")
            return
        if agents_config.get("enabled") is not True:
            self.error("Codex agents must be enabled")
        cap = agents_config.get("max_concurrent_threads_per_session")
        if template:
            if cap != 3:
                self.error("Codex template concurrency budget must pin 3 spawned threads")
        elif type(cap) is not int or cap < 1:
            # A raised ceiling is allowed when the user asked for it; an absent
            # or non-positive value leaves the effective budget unknown.
            self.error(f"Codex max_concurrent_threads_per_session must be a positive integer, found: {cap!r}")
        default_model = agents_config.get("default_subagent_model")
        if template and default_model is not None:
            self.error("Codex template must resolve the default subagent model dynamically")
        elif default_model is not None:
            if not isinstance(default_model, str) or not default_model.strip():
                self.error("Codex default subagent model must be a nonempty string")
            elif self.bindings and default_model != self.bindings["worker"]["model"]:
                self.error("Codex default subagent model differs from the worker binding")
        if agents_config.get("default_subagent_reasoning_effort") != "xhigh":
            self.error("Codex default subagent effort must be xhigh")

    def validate_codex_agents(self, directory: Path, *, template: bool = True) -> None:
        names: set[str] = set()
        for filename, (role, effort, sandbox) in CODEX_AGENTS.items():
            expected_name = role
            path = directory / filename
            if not template and not path.exists():
                alias = LEGACY_CODEX_AGENTS[role]
                legacy = directory / (alias.replace("_", "-") + ".toml")
                if legacy.exists():
                    path, filename, expected_name = legacy, legacy.name, alias
                    self.warnings.append(f"Legacy role {alias} maps to {role}; migrate its definition and references together")
            if not self.require(path):
                continue
            values = self.load_toml(path)
            if values is None:
                continue
            for key in ("name", "description", "developer_instructions"):
                if not values.get(key):
                    self.error(f"{filename} missing required key: {key}")
            actual_name = values.get("name")
            if actual_name != expected_name:
                self.error(f"{filename} has wrong name")
            if isinstance(actual_name, str):
                if actual_name in names:
                    self.error(f"duplicate Codex agent name: {actual_name}")
                names.add(actual_name)
            model = values.get("model")
            if not template and values.get("model_provider") not in (None, self.effective_codex_provider):
                self.error(f"{filename} must inherit the selected provider, not override it")
            if template:
                if model is not None:
                    self.error(f"{filename} template must not hard-code a model")
            elif not isinstance(model, str) or not model.strip():
                self.error(f"{filename} installed agent needs a resolved model")
            elif self.bindings and model != self.bindings[role]["model"]:
                self.error(f"{filename} model differs from the {role} binding")
            if values.get("model_reasoning_effort") != effort:
                self.error(f"{filename} effort must be {effort}")
            if values.get("sandbox_mode") != sandbox:
                self.error(f"{filename} sandbox must be {sandbox}")
            instructions = values.get("developer_instructions", "")
            if not isinstance(instructions, str) or "spawn subagents" not in instructions:
                self.error(f"{filename} must prohibit descendant agents")
            if not isinstance(instructions, str) or "invoke Claude or another external coding agent" not in instructions:
                self.error(f"{filename} must prohibit cross-provider invocation")

    def validate_policies(self, path: Path, policies: dict[str, re.Pattern[str]], label: str) -> None:
        if not self.require(path):
            return
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            self.error(f"cannot read {label} policy {self.display_path(path)}: {exc}")
            return
        for description, pattern in policies.items():
            if not pattern.search(text):
                self.error(f"{self.display_path(path)} missing {label} policy: {description}")

    def validate_codex_policies(self, path: Path) -> None:
        self.validate_policies(path, CODEX_AGENTS_POLICIES, "Codex AGENTS")

    def validate_codex(self) -> None:
        if self.runtime_context and not self.bindings_path:
            self.error("--runtime-context requires --bindings")
        if self.codex_profile and not self.codex_home:
            self.error("--codex-profile requires --codex-home")
        try:
            policy = ROUTING.read_json(self.model_policy)
            ROUTING.validate_policy(policy)
            if self.bindings_path:
                expected_context = None
                if self.runtime_context:
                    expected_context = ROUTING.read_json(self.runtime_context)
                    if isinstance(expected_context, dict) and "context" in expected_context:
                        expected_context = expected_context["context"]
                    if not isinstance(expected_context, dict):
                        raise ROUTING.RoutingError("Runtime context must contain a context object")
                result = ROUTING.verify_binding(ROUTING.read_json(self.bindings_path), policy, expected_context=expected_context)
                self.binding_context = result.get("context")
                if self.binding_context and self.codex_home:
                    if Path(self.binding_context.get("codex_home", "")).resolve() != self.codex_home:
                        raise ROUTING.RoutingError("Model binding belongs to a different CODEX_HOME")
                    if self.binding_context.get("profile") != self.codex_profile:
                        raise ROUTING.RoutingError("Model binding profile differs; select the matching --codex-profile")
                    if not self.runtime_context:
                        self.warnings.append("Current auth/endpoint/executable identity is unverified; pass a fresh --runtime-context for full context comparison")
                elif self.codex_home:
                    self.warnings.append("Binding has no runtime context; host/auth/provider identity remains unverified")
                if result["unresolved"]:
                    raise ROUTING.RoutingError("Installed configuration requires the controller (unless preserved) and all five subagent bindings")
                self.bindings = result["bindings"]
        except (ROUTING.RoutingError, TypeError, KeyError) as exc:
            self.error(f"Model routing validation failed: {exc}")
        template = self.skill / "assets/templates/codex"
        self.validate_codex_config(template / "config-snippet.toml", template=True)
        self.validate_codex_agents(template / "agents")
        self.validate_codex_policies(template / "AGENTS-snippet.md")

        if self.codex_home is None:
            return
        if not self.codex_home.is_dir():
            self.error("Codex home must be a directory")
            return
        config_path = self.codex_home / "config.toml"
        if self.require(config_path):
            self.validate_codex_config(config_path, template=False)
        if not self.bindings_path:
            self.warnings.append("Codex model availability and tier compatibility are unverified; pass a fresh --bindings snapshot")
        self.validate_codex_agents(self.codex_home / "agents", template=False)
        self.validate_codex_policies(self.codex_rules or self.codex_home / "AGENTS.md")

    def validate_claude_settings(self, path: Path, *, template: bool) -> None:
        try:
            settings = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.error(f"invalid Claude settings JSON {self.display_path(path)}: {exc}")
            return
        model = settings.get("model")
        if template:
            if model != "opus[1m]":
                self.error("Claude default model must be opus[1m]")
        elif not isinstance(model, str) or not re.search(r"opus|fable", model):
            # An installed home may legitimately run above the opus[1m] baseline
            # (for example an explicit Fable primary); only a weaker tier fails.
            self.error(f"Claude primary model must be an Opus- or Fable-class model, found: {model!r}")
        if settings.get("effortLevel") != "xhigh":
            self.error("Claude default effortLevel must be xhigh")
        env = settings.get("env")
        if not isinstance(env, dict):
            self.error("Claude settings must define env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH")
        else:
            depth = env.get("CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH")
            if depth is None:
                self.error("Claude settings must set CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH")
            elif str(depth) != "1":
                self.error(
                    "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH must be \"1\" so descendant agents are client-enforced"
                )

    def validate_claude_agents(self, directory: Path) -> None:
        names: set[str] = set()
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

    def validate_claude(self) -> None:
        template = self.skill / "assets/templates/claude"
        self.validate_claude_settings(template / "settings-snippet.json", template=True)
        self.validate_claude_agents(template / "agents")
        self.validate_policies(template / "CLAUDE-snippet.md", CLAUDE_RULES_POLICIES, "Claude rules")

        if self.claude_home is None:
            return
        if not self.claude_home.is_dir():
            self.error("Claude home must be a directory")
            return
        settings_path = self.claude_home / "settings.json"
        if self.require(settings_path):
            self.validate_claude_settings(settings_path, template=False)
        self.validate_claude_agents(self.claude_home / "agents")
        self.validate_policies(self.claude_home / "CLAUDE.md", CLAUDE_RULES_POLICIES, "Claude rules")

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
                    self.error(f"broken local link in {self.display_path(path)}: {target}")

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
        for warning in self.warnings:
            print(f"Warning: {warning}")
        print("Agent Strata validation passed (structure; inference access not tested)")
        print(f"Target: {self.root}")
        mode = "repository" if self.repository_mode else "installed skill package"
        if self.codex_home is not None:
            mode += " + explicit Codex home"
        if self.claude_home is not None:
            mode += " + explicit Claude home"
        print(f"Mode: {mode}")
        print(f"Codex agents: {len(CODEX_AGENTS)}")
        print(f"Claude agents: {len(CLAUDE_AGENTS)}")
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", type=Path, help="Agent Strata repository root; omit to validate only this installed skill package"
    )
    parser.add_argument(
        "--codex-home", type=Path, help="explicit Codex home to check config.toml, agents, and AGENTS.md"
    )
    parser.add_argument(
        "--claude-home", type=Path, help="explicit Claude home to check settings.json and agents"
    )
    parser.add_argument("--bindings", type=Path, help="fresh model-bindings.json from resolve_models.py")
    parser.add_argument("--model-policy", type=Path, help="policy used to resolve the supplied binding")
    parser.add_argument("--codex-profile", help="named profile in the selected Codex home")
    parser.add_argument("--runtime-context", type=Path, help="fresh discovery catalog/context to compare with the binding")
    parser.add_argument("--codex-rules", type=Path, help="project-root AGENTS.md when Codex home is project/.codex")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    installed_skill = Path(__file__).resolve().parents[1]
    raise SystemExit(Validator(arguments.repo, installed_skill, arguments.codex_home, arguments.claude_home, arguments.bindings, arguments.model_policy, arguments.codex_rules, arguments.codex_profile, arguments.runtime_context).run())

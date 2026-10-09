#!/usr/bin/env python3
"""Resolve Codex role bindings without inference or changes to client configuration."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import queue
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
TIERS = {"efficient": 0, "balanced": 1, "deep": 2}
ROLES = {
    "scout": ("efficient", "medium", "read-only"),
    "executor": ("efficient", "medium", "workspace-write"),
    "worker": ("balanced", "xhigh", "workspace-write"),
    "deep_worker": ("deep", "xhigh", "workspace-write"),
    "reviewer": ("deep", "xhigh", "read-only"),
}
CONTROLLER = {"controller": ("deep", "xhigh", "inherited")}
ALL_ROLES = {**CONTROLLER, **ROLES}
ALIASES = {"luna_scout": "scout", "luna_executor": "executor",
           "terra_worker": "worker", "sol_worker": "deep_worker", "sol_reviewer": "reviewer"}


class RoutingError(ValueError):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def normalize_context(context):
    """Only retain the non-secret discovery identity, never raw RPC results."""
    if context is None:
        return None
    required = {"schema_version", "host", "executable", "client_version", "codex_home",
                "cwd", "profile", "provider", "auth_mode", "auth_source"}
    if (not isinstance(context, dict) or set(context) - required - {"endpoint_fingerprint"}
            or not required.issubset(context) or type(context["schema_version"]) is not int
            or context["schema_version"] != 1):
        raise RoutingError("Invalid discovery context schema")
    for key in required - {"schema_version", "profile"}:
        value = context[key]
        if not isinstance(value, str) or not value or len(value) > 4096 or any(ord(c) < 32 for c in value):
            raise RoutingError(f"Invalid discovery context field: {key}")
    profile = context["profile"]
    if profile is not None and (not isinstance(profile, str) or not profile or len(profile) > 256
                                or any(ord(c) < 32 for c in profile)):
        raise RoutingError("Invalid discovery context profile")
    for key in ("executable", "codex_home", "cwd"):
        if not Path(context[key]).is_absolute():
            raise RoutingError(f"Discovery context path must be absolute: {key}")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", context["provider"]):
        raise RoutingError("Invalid discovery context provider")
    if context["auth_mode"] not in ("chatgpt", "api-key", "unknown"):
        raise RoutingError("Invalid discovery context auth mode")
    if context["auth_source"] not in ("account/read", "login-status", "unknown"):
        raise RoutingError("Invalid discovery context auth source")
    fingerprint = context.get("endpoint_fingerprint")
    if "endpoint_fingerprint" in context and (not isinstance(fingerprint, str)
                                             or not re.fullmatch(r"[0-9a-f]{64}", fingerprint)):
        raise RoutingError("Invalid discovery endpoint fingerprint")
    return dict(context)


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RoutingError(f"Cannot read JSON: {Path(path).name}") from exc


def check_age(timestamp, max_age_hours=24):
    try:
        date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if date.tzinfo is None:
            raise ValueError("timezone required")
        age = (datetime.now(timezone.utc) - date).total_seconds()
    except (AttributeError, TypeError, ValueError) as exc:
        raise RoutingError("Catalog timestamp must be an ISO timestamp with timezone") from exc
    if age < -300 or age > max_age_hours * 3600:
        raise RoutingError("Catalog is stale or dated in the future; refresh it")


def normalize_catalog(payload):
    """Accept model/list, its JSON-RPC envelope, or a tool-derived models array."""
    if not isinstance(payload, dict):
        raise RoutingError("Catalog must be an object")
    if payload.get("error"):
        raise RoutingError("Catalog contains an RPC error")
    body = payload.get("result", payload)
    if not isinstance(body, dict):
        raise RoutingError("Catalog result must be an object")
    if body.get("nextCursor"):
        raise RoutingError("Incomplete catalog: collect every model/list page")
    rows = body.get("data", body.get("models"))
    if not isinstance(rows, list) or not rows:
        raise RoutingError("Catalog must contain a nonempty data or models array")
    models = {}
    for row in rows:
        if not isinstance(row, dict):
            raise RoutingError("Invalid model entry")
        name = row.get("model", row.get("slug", row.get("id")))
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", name):
            raise RoutingError("Invalid model identifier")
        raw = row.get("supportedReasoningEfforts", row.get("supported_reasoning_levels", row.get("efforts", [])))
        if not isinstance(raw, list):
            raise RoutingError(f"Invalid reasoning options for {name}")
        efforts = []
        for item in raw:
            effort = item.get("reasoningEffort", item.get("effort")) if isinstance(item, dict) else item
            if not isinstance(effort, str) or not effort:
                raise RoutingError(f"Invalid reasoning option for {name}")
            efforts.append(effort)
        hidden = row.get("hidden", False)
        default = row.get("isDefault", False)
        if not isinstance(hidden, bool) or not isinstance(default, bool):
            raise RoutingError(f"Invalid visibility/default flag for {name}")
        upgrade = row.get("upgrade")
        if upgrade is not None and not isinstance(upgrade, str):
            raise RoutingError(f"Invalid upgrade target for {name}")
        modalities = row.get("inputModalities", row.get("input_modalities"))
        if modalities is not None and (not isinstance(modalities, list) or not all(isinstance(x, str) for x in modalities)):
            raise RoutingError(f"Invalid modalities for {name}")
        model = {"model": name, "efforts": sorted(set(efforts)), "hidden": hidden,
                 "isDefault": default, "upgrade": upgrade, "inputModalities": modalities}
        if name in models and models[name] != model:
            raise RoutingError(f"Conflicting duplicate model: {name}")
        models[name] = model
    return models


def validate_policy(policy):
    if not isinstance(policy, dict) or policy.get("schema_version") != 1:
        raise RoutingError("Unsupported routing policy schema")
    if not isinstance(policy.get("roles"), dict) or set(policy["roles"]) != set(ROLES):
        raise RoutingError("Policy must define the five stable roles")
    for role, (tier, effort, sandbox) in ROLES.items():
        if policy["roles"][role] != {"tier": tier, "effort": effort, "sandbox": sandbox}:
            raise RoutingError(f"Policy changes the capability/effort/sandbox contract for {role}")
    if policy.get("controller") != {"tier": "deep", "effort": "xhigh", "sandbox": "inherited"}:
        raise RoutingError("Policy must recommend a deep-tier xhigh controller")
    families = policy.get("families")
    if not isinstance(families, list):
        raise RoutingError("Policy families must be an array")
    for rule in families:
        if not isinstance(rule, dict) or rule.get("tier") not in TIERS or type(rule.get("priority")) is not int:
            raise RoutingError("Invalid family classification")
        try:
            re.compile(rule["pattern"])
        except (KeyError, TypeError, re.error) as exc:
            raise RoutingError("Invalid family pattern") from exc
    for key in ("models", "pins", "role_preferences"):
        if not isinstance(policy.get(key, {}), dict):
            raise RoutingError(f"Policy {key} must be an object")
    for model, info in policy.get("models", {}).items():
        if not isinstance(info, dict) or info.get("tier") not in TIERS or not info.get("evidence") or type(info.get("priority")) is not int:
            raise RoutingError(f"Explicit model classification needs tier, priority and evidence: {model}")
    for role, model in policy.get("pins", {}).items():
        if role not in ALL_ROLES or not isinstance(model, str) or not model:
            raise RoutingError("Invalid role pin")
    for role, preferences in policy.get("role_preferences", {}).items():
        if (role not in ROLES or not isinstance(preferences, list) or not preferences
                or any(not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", name)
                       for name in preferences)
                or len(set(preferences)) != len(preferences)):
            raise RoutingError("Role preferences require a stable subagent role and nonempty unique model identifiers")


def classifications(models, policy):
    known = {}
    for name in models:
        info = policy.get("models", {}).get(name)
        matches = [r for r in policy["families"] if re.fullmatch(r["pattern"], name)]
        if info is None and matches:
            if len({r["tier"] for r in matches}) != 1:
                raise RoutingError(f"Conflicting classifications for {name}")
            info = max(matches, key=lambda r: r["priority"])
        if info:
            version = tuple(int(x) for x in re.findall(r"\d+", name))
            known[name] = {"tier": info["tier"], "rank": (info["priority"], version, 0), "evidence": "policy"}
    # Follow catalog-provided upgrades, never invent a model name or a major-version tier.
    # Reject cycles, including cycles entirely within otherwise unknown families.
    for start in models:
        seen = set()
        name = start
        while name in models:
            if name in seen:
                raise RoutingError("Cyclic model upgrade metadata")
            seen.add(name)
            name = models[name]["upgrade"]
    for _ in range(len(models)):
        changed = False
        for name, model in models.items():
            target = model["upgrade"]
            if name not in known or target not in models or target in known:
                continue
            # Multiple sources must agree before assigning an unknown successor.
            sources = [known[s] for s in models if models[s]["upgrade"] == target and s in known]
            if len({s["tier"] for s in sources}) != 1:
                raise RoutingError(f"Ambiguous upgrade tier for {target}")
            origin = max(sources, key=lambda s: s["rank"])
            priority, version, depth = origin["rank"]
            known[target] = {"tier": origin["tier"], "rank": (priority, version, depth + 1), "evidence": f"catalog upgrade from {name}"}
            changed = True
        if not changed:
            break
    # Check late-arriving sources too. Explicit policy classifications remain authoritative.
    for target, info in known.items():
        if info["evidence"] == "policy":
            continue
        if any(known[s]["tier"] != info["tier"] for s in known if models[s]["upgrade"] == target):
            raise RoutingError(f"Ambiguous upgrade tier for {target}")
    return known


def resolve(payload, policy, *, pins=None, excluded=(), allowed=None, modalities=(), preserve_primary=False):
    validate_policy(policy)
    if not isinstance(payload, dict):
        raise RoutingError("Catalog must be an object")
    if payload.get("captured_at"):
        check_age(payload["captured_at"])
    context = normalize_context(payload.get("context"))
    models = normalize_catalog(payload)
    known = classifications(models, policy)
    selected_pins = dict(policy.get("pins", {}))
    selected_pins.update(pins or {})
    if set(selected_pins) - set(ALL_ROLES):
        raise RoutingError("Unknown pinned role")
    if preserve_primary and "controller" in selected_pins:
        raise RoutingError("Cannot combine a controller pin with preserve-primary")
    bindings, unresolved = {}, {}
    excluded = set(excluded)
    allowed = set(allowed) if allowed is not None else None
    for role, (tier, effort, sandbox) in ALL_ROLES.items():
        if role == "controller" and preserve_primary:
            continue
        pin = selected_pins.get(role)
        candidates = []
        for name, model in models.items():
            if name not in known or name in excluded or (allowed is not None and name not in allowed):
                continue
            info = known[name]
            if effort not in model["efforts"] or (model["hidden"] and name != pin):
                continue
            if modalities and not set(modalities).issubset(model["inputModalities"] or []):
                continue
            if pin:
                if name != pin or (role != "controller" and TIERS[info["tier"]] < TIERS[tier]):
                    continue
            elif info["tier"] != tier:
                continue
            candidates.append(name)
        preferences = policy.get("role_preferences", {}).get(role, [])
        preference_rank = {name: len(preferences) - index for index, name in enumerate(preferences)}
        candidates.sort(key=lambda n: (preference_rank.get(n, 0), known[n]["rank"], models[n]["isDefault"], n), reverse=True)
        if not candidates:
            unresolved[role] = "Pinned model does not meet the catalog/policy constraints" if pin else f"No eligible {tier} model supporting {effort}"
            continue
        name = candidates[0]
        bindings[role] = {"model": name, "reasoning_effort": effort, "sandbox_mode": sandbox,
                          "tier": known[name]["tier"], "pinned": bool(pin), "evidence": known[name]["evidence"],
                          "alternatives": candidates[1:] if not pin else []}
    return {"schema_version": 1, "generated_at": utc_now(),
            "catalog_captured_at": payload.get("captured_at"),
            "catalog_source": payload.get("source", "supplied catalog"),
            "context": context, "context_sha256": digest(context),
            "catalog_sha256": digest(models), "policy_sha256": digest(policy),
            "catalog": list(models.values()), "bindings": bindings, "unresolved": unresolved,
            "constraints": {"pins": selected_pins, "excluded": sorted(excluded),
                            "allowed": sorted(allowed) if allowed is not None else None,
                            "modalities": sorted(modalities), "preserve_primary": preserve_primary},
            "unclassified": sorted(set(models) - set(known)),
            "access_verified": False,
            "warnings": ["Catalog membership is not an entitlement or successful-inference check.",
                         "Use only with the same host, account, provider and calling tool; refresh after any change."]}


def verify_binding(document, policy, expected_context=None):
    """Recompute a saved binding; do not trust edited role models or effort fields."""
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise RoutingError("Unsupported binding schema")
    check_age(document.get("generated_at"))
    constraints = document.get("constraints")
    if not isinstance(constraints, dict):
        raise RoutingError("Binding constraints are missing")
    payload = {"models": document.get("catalog"), "captured_at": document.get("catalog_captured_at"),
               "source": document.get("catalog_source", "supplied catalog"), "context": document.get("context")}
    result = resolve(payload, policy, **constraints)
    for key in ("catalog_sha256", "policy_sha256", "context_sha256", "bindings", "unresolved"):
        if result[key] != document.get(key):
            raise RoutingError(f"Binding no longer matches its catalog and policy: {key}")
    if expected_context is not None and result["context"] != normalize_context(expected_context):
        raise RoutingError("Binding discovery context differs from the expected runtime context")
    if document.get("access_verified") is not False:
        raise RoutingError("Model discovery cannot verify inference access")
    return result


def _stop_process(process, thread):
    if process.poll() is None:
        try:
            process.terminate()
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)
    thread.join(timeout=2)
    for stream in (process.stdin, process.stdout):
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass


def _capture_status(command, env, cwd, timeout):
    """Bound both output and time; status output may contain credentials."""
    if timeout <= 0:
        return None
    try:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, env=env, cwd=cwd)
    except OSError:
        return None
    output, finished, invalid = bytearray(), threading.Event(), threading.Event()

    def reader():
        try:
            while True:
                chunk = process.stdout.read(4096)
                if not chunk:
                    break
                if len(output) + len(chunk) > 16384:
                    invalid.set()
                    break
                output.extend(chunk)
        except OSError:
            invalid.set()
        finally:
            finished.set()

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    deadline = time.monotonic() + timeout
    try:
        if not finished.wait(timeout) or invalid.is_set():
            return None
        try:
            if process.wait(timeout=max(0, deadline - time.monotonic())) != 0:
                return None
        except subprocess.TimeoutExpired:
            return None
        return output.decode("utf-8", errors="replace")
    finally:
        _stop_process(process, thread)


def _provider_context(result):
    config = result.get("config") if isinstance(result, dict) else None
    if not isinstance(config, dict):
        return "unknown", None
    provider = config.get("model_provider", config.get("modelProvider"))
    if provider is None:
        provider = "openai"
    if not isinstance(provider, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", provider):
        return "unknown", None
    providers = config.get("model_providers", config.get("modelProviders", {}))
    selected = providers.get(provider) if isinstance(providers, dict) else None
    endpoint = selected.get("base_url", selected.get("baseUrl")) if isinstance(selected, dict) else None
    fingerprint = hashlib.sha256(endpoint.encode()).hexdigest() if isinstance(endpoint, str) and endpoint else None
    return provider, fingerprint


def _account_auth(result):
    account = result.get("account") if isinstance(result, dict) else None
    kind = account.get("type") if isinstance(account, dict) else None
    return {"chatgpt": "chatgpt", "apiKey": "api-key", "api-key": "api-key"}.get(kind, "unknown") if isinstance(kind, str) else "unknown"


def discover(codex="codex", timeout=20, codex_home=None, cwd=None, profile=None,
             expected_auth=None, expected_provider=None):
    """Read models and identity through the selected client without inference/login."""
    if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise RoutingError("Discovery timeout must be positive")
    if expected_auth not in (None, "chatgpt", "api-key"):
        raise RoutingError("Expected auth must be chatgpt or api-key")
    if expected_provider is not None and (not isinstance(expected_provider, str)
            or expected_provider == "unknown" or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", expected_provider)):
        raise RoutingError("Expected provider must be a known provider identifier")
    env = os.environ.copy()
    target_cwd = Path(cwd or Path.cwd()).expanduser().resolve()
    if not target_cwd.is_dir():
        raise RoutingError("Discovery working directory does not exist")
    home = Path(codex_home if codex_home is not None else env.get("CODEX_HOME") or Path.home() / ".codex").expanduser()
    home = (target_cwd / home).resolve()
    env["CODEX_HOME"] = str(home)
    # Resolve relative PATH entries against the requested working directory too.
    search_path = os.pathsep.join(str((target_cwd / entry).resolve())
                                 for entry in env.get("PATH", os.defpath).split(os.pathsep))
    command = os.path.expanduser(os.fspath(codex))
    if os.path.dirname(command):
        command = str(target_cwd / command)
    executable = shutil.which(command, path=search_path)
    if executable is None:
        raise RoutingError("Codex executable not found or not executable")
    executable = str(Path(executable).resolve())
    context = {"schema_version": 1, "host": socket.gethostname(), "executable": executable,
               "client_version": "unknown", "codex_home": str(home), "cwd": str(target_cwd),
               "profile": profile, "provider": "unknown", "auth_mode": "unknown", "auth_source": "unknown"}
    normalize_context(context)
    base_command = [executable] + (["--profile", profile] if profile is not None else [])
    deadline = time.monotonic() + timeout
    version_output = _capture_status(base_command + ["--version"], env, str(target_cwd), min(2, timeout / 4))
    if version_output is not None:
        match = re.search(r"(?m)^codex(?:-cli)? ([0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9._-]+)?)\s*$", version_output)
        if match:
            context["client_version"] = match[1]
    messages, stopped = queue.Queue(maxsize=64), threading.Event()
    process = subprocess.Popen(base_command + ["app-server", "--listen", "stdio://"],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                               env=env, cwd=str(target_cwd))

    def enqueue(value):
        while not stopped.is_set():
            try:
                messages.put(value, timeout=0.05)
                return
            except queue.Full:
                pass

    def reader():
        try:
            while not stopped.is_set():
                line = process.stdout.readline(1_048_577)
                if not line:
                    break
                if len(line) > 1_048_576:
                    enqueue(RoutingError("Oversized app-server response"))
                    return
                enqueue(line)
        except (OSError, UnicodeError):
            enqueue(RoutingError("Invalid app-server output"))
        finally:
            enqueue(None)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()

    def send(message):
        try:
            process.stdin.write(json.dumps(message) + "\n")
            process.stdin.flush()
        except OSError as exc:
            raise RoutingError("App-server input closed during discovery") from exc

    def request(number, method, params, request_timeout=None):
        request_deadline = deadline if request_timeout is None else min(deadline, time.monotonic() + request_timeout)
        send({"id": number, "method": method, "params": params})
        for _ in range(10000):
            remaining = request_deadline - time.monotonic()
            if remaining <= 0:
                raise RoutingError("Model discovery timed out")
            try:
                line = messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise RoutingError("Model discovery timed out") from exc
            if isinstance(line, Exception):
                raise line
            if line is None:
                raise RoutingError("App-server exited before model discovery completed")
            try:
                message = json.loads(line)
            except ValueError as exc:
                raise RoutingError("Invalid app-server JSON") from exc
            if not isinstance(message, dict):
                raise RoutingError("Invalid app-server message")
            if message.get("id") != number:
                continue
            if "error" in message:
                raise RoutingError(f"App-server rejected {method}")
            result = message.get("result")
            if not isinstance(result, dict):
                raise RoutingError(f"Invalid {method} result")
            return result
        raise RoutingError("Too many app-server notifications")

    def optional_request(number, method, params):
        try:
            return request(number, method, params, min(2, max(0, deadline - time.monotonic()) / 3))
        except RoutingError:
            return None

    try:
        request(1, "initialize", {"clientInfo": {"name": "agent_strata", "version": "2.0.0"}, "capabilities": {}})
        send({"method": "initialized", "params": {}})
        rows, cursor, seen = [], None, set()
        for page in range(100):
            params = {"limit": 100, "includeHidden": True}
            if cursor is not None:
                params["cursor"] = cursor
            result = request(page + 2, "model/list", params)
            if not isinstance(result.get("data"), list):
                raise RoutingError("Invalid model/list data")
            rows.extend(result["data"])
            cursor = result.get("nextCursor")
            if cursor is None:
                break
            if not isinstance(cursor, str) or not cursor or cursor in seen:
                raise RoutingError("Invalid or repeated model/list cursor")
            seen.add(cursor)
        else:
            raise RoutingError("Model catalog exceeded pagination limit")
        config = optional_request(102, "config/read", {"includeLayers": False})
        context["provider"], fingerprint = _provider_context(config)
        if fingerprint is not None:
            context["endpoint_fingerprint"] = fingerprint
        account = optional_request(103, "account/read", {"refreshToken": False})
        context["auth_mode"] = _account_auth(account)
        if context["auth_mode"] != "unknown":
            context["auth_source"] = "account/read"
    finally:
        stopped.set()
        _stop_process(process, thread)
    if context["auth_mode"] == "unknown":
        status = _capture_status(base_command + ["login", "status"], env, str(target_cwd),
                                 min(2, max(0, deadline - time.monotonic())))
        if status is not None:
            # Classify only known status lines; never store or print the output/key.
            modes = set()
            if re.search(r"(?mi)^Logged in using ChatGPT\s*$", status):
                modes.add("chatgpt")
            if re.search(r"(?mi)^Logged in using an API key(?:\s*[-:].*)?\s*$", status):
                modes.add("api-key")
            if len(modes) == 1:
                context["auth_mode"] = modes.pop()
                context["auth_source"] = "login-status"
    if expected_auth is not None and context["auth_mode"] != expected_auth:
        raise RoutingError("Discovery authentication does not match expected auth (or is unknown)")
    if expected_provider is not None and context["provider"] != expected_provider:
        raise RoutingError("Discovery provider does not match expected provider (or is unknown)")
    payload = {"data": rows, "source": "codex app-server model/list", "captured_at": utc_now(),
               "context": normalize_context(context), "access_verified": False}
    normalize_catalog(payload)
    return payload


def render(document, directory, skill=SKILL):
    """Generate a NEW staging directory. Installation remains a syntax-aware merge."""
    if document["unresolved"]:
        raise RoutingError("Cannot render an incomplete role binding")
    directory = Path(directory)
    if directory.exists():
        raise RoutingError("Output directory already exists; use a new staging directory")
    template = skill / "assets/templates/codex"
    directory.mkdir(parents=True)
    try:
        (directory / "agents").mkdir()
        for role in ROLES:
            binding = document["bindings"][role]
            filename = role.replace("_", "-") + ".toml"
            content = (template / "agents" / filename).read_text(encoding="utf-8")
            (directory / "agents" / filename).write_text(
                "model = " + json.dumps(binding["model"]) + "\n" + content, encoding="utf-8")
        content = (template / "config-snippet.toml").read_text(encoding="utf-8")
        controller = document["bindings"].get("controller")
        if controller:
            content = "model = " + json.dumps(controller["model"]) + "\nmodel_reasoning_effort = " + json.dumps(controller["reasoning_effort"]) + "\n\n" + content
        content = content.replace("[agents]\n", "[agents]\ndefault_subagent_model = " + json.dumps(document["bindings"]["worker"]["model"]) + "\n", 1)
        (directory / "config-snippet.toml").write_text(content, encoding="utf-8")
        shutil.copyfile(template / "AGENTS-snippet.md", directory / "AGENTS-snippet.md")
        (directory / "model-bindings.json").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    except BaseException:
        shutil.rmtree(directory)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--catalog", type=Path, help="complete model/list JSON or tool-derived catalog")
    source.add_argument("--discover", action="store_true", help="read model/list; never starts inference")
    parser.add_argument("--codex", default="codex", help="Codex executable for discovery")
    parser.add_argument("--codex-home", type=Path, help="Codex home for discovery; inherited environment is preserved")
    parser.add_argument("--cwd", type=Path, help="working directory for the selected Codex client")
    parser.add_argument("--profile", help="selected Codex configuration profile")
    parser.add_argument("--expected-auth", choices=("chatgpt", "api-key"), help="fail unless stored auth is identified as expected")
    parser.add_argument("--expected-provider", help="fail unless the effective provider matches")
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--policy", type=Path, default=SKILL / "assets/model-policy.json")
    parser.add_argument("--pin", action="append", default=[], metavar="ROLE=MODEL")
    parser.add_argument("--exclude", action="append", default=[], metavar="MODEL")
    parser.add_argument("--allowed-model", action="append", help="intersect with calling tool's model allowlist")
    parser.add_argument("--require-modality", action="append", default=[])
    parser.add_argument("--role", choices=list(ALL_ROLES) + list(ALIASES), help="require only this role to resolve")
    parser.add_argument("--preserve-primary", action="store_true", help="resolve only subagents; leave primary model and effort unchanged")
    parser.add_argument("--output-dir", type=Path, help="render all roles into a new staging directory")
    args = parser.parse_args(argv)
    try:
        pins = {}
        for item in args.pin:
            role, separator, model = item.partition("=")
            role = ALIASES.get(role, role)
            if not separator or role not in ALL_ROLES or not model or role in pins:
                raise RoutingError("Pins must be unique ROLE=MODEL pairs")
            pins[role] = model
        if not args.discover and any(value is not None for value in (
                args.codex_home, args.cwd, args.profile, args.expected_auth, args.expected_provider)):
            raise RoutingError("Discovery target and expected-auth/provider options require --discover")
        payload = discover(args.codex, args.timeout, codex_home=args.codex_home, cwd=args.cwd,
                           profile=args.profile, expected_auth=args.expected_auth,
                           expected_provider=args.expected_provider) if args.discover else read_json(args.catalog)
        result = resolve(payload, read_json(args.policy), pins=pins, excluded=args.exclude,
                         allowed=args.allowed_model, modalities=args.require_modality, preserve_primary=args.preserve_primary)
        if args.output_dir:
            render(result, args.output_dir)
        print(json.dumps(result, indent=2))
        role = ALIASES.get(args.role, args.role)
        return 2 if (role in result["unresolved"] if role else result["unresolved"]) else 0
    except (RoutingError, OSError, TypeError, KeyError) as exc:
        print(f"Model routing failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

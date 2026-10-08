#!/usr/bin/env python3
"""Resolve Codex role bindings without inference or changes to client configuration."""
from __future__ import annotations

import argparse
import hashlib
import json
import queue
import re
import shutil
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
ALIASES = {"luna_scout": "scout", "luna_executor": "executor",
           "terra_worker": "worker", "sol_worker": "deep_worker", "sol_reviewer": "reviewer"}


class RoutingError(ValueError):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


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
    for key in ("models", "pins"):
        if not isinstance(policy.get(key, {}), dict):
            raise RoutingError(f"Policy {key} must be an object")
    for model, info in policy.get("models", {}).items():
        if not isinstance(info, dict) or info.get("tier") not in TIERS or not info.get("evidence") or type(info.get("priority")) is not int:
            raise RoutingError(f"Explicit model classification needs tier, priority and evidence: {model}")
    for role, model in policy.get("pins", {}).items():
        if role not in ROLES or not isinstance(model, str) or not model:
            raise RoutingError("Invalid role pin")


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


def resolve(payload, policy, *, pins=None, excluded=(), allowed=None, modalities=()):
    validate_policy(policy)
    if not isinstance(payload, dict):
        raise RoutingError("Catalog must be an object")
    if payload.get("captured_at"):
        check_age(payload["captured_at"])
    models = normalize_catalog(payload)
    known = classifications(models, policy)
    selected_pins = dict(policy.get("pins", {}))
    selected_pins.update(pins or {})
    if set(selected_pins) - set(ROLES):
        raise RoutingError("Unknown pinned role")
    bindings, unresolved = {}, {}
    excluded = set(excluded)
    allowed = set(allowed) if allowed is not None else None
    for role, (tier, effort, sandbox) in ROLES.items():
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
                if name != pin or TIERS[info["tier"]] < TIERS[tier]:
                    continue
            elif info["tier"] != tier:
                continue
            candidates.append(name)
        candidates.sort(key=lambda n: (known[n]["rank"], models[n]["isDefault"], n), reverse=True)
        if not candidates:
            unresolved[role] = "Pinned model does not meet the catalog/policy constraints" if pin else f"No eligible {tier} model supporting {effort}"
            continue
        name = candidates[0]
        bindings[role] = {"model": name, "reasoning_effort": effort, "sandbox_mode": sandbox,
                          "tier": tier, "pinned": bool(pin), "evidence": known[name]["evidence"],
                          "alternatives": candidates[1:] if not pin else []}
    return {"schema_version": 1, "generated_at": utc_now(),
            "catalog_captured_at": payload.get("captured_at"),
            "catalog_source": payload.get("source", "supplied catalog"),
            "catalog_sha256": digest(models), "policy_sha256": digest(policy),
            "catalog": list(models.values()), "bindings": bindings, "unresolved": unresolved,
            "constraints": {"pins": selected_pins, "excluded": sorted(excluded),
                            "allowed": sorted(allowed) if allowed is not None else None,
                            "modalities": sorted(modalities)},
            "unclassified": sorted(set(models) - set(known)),
            "access_verified": False,
            "warnings": ["Catalog membership is not an entitlement or successful-inference check.",
                         "Use only with the same host, account, provider and calling tool; refresh after any change."]}


def verify_binding(document, policy):
    """Recompute a saved binding; do not trust edited role models or effort fields."""
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise RoutingError("Unsupported binding schema")
    check_age(document.get("generated_at"))
    constraints = document.get("constraints")
    if not isinstance(constraints, dict):
        raise RoutingError("Binding constraints are missing")
    payload = {"models": document.get("catalog"), "captured_at": document.get("catalog_captured_at")}
    result = resolve(payload, policy, **constraints)
    for key in ("catalog_sha256", "policy_sha256", "bindings", "unresolved"):
        if result[key] != document.get(key):
            raise RoutingError(f"Binding no longer matches its catalog and policy: {key}")
    return result


def discover(codex="codex", timeout=20):
    """Read all model/list pages through a short-lived, non-inference app-server."""
    if timeout <= 0:
        raise RoutingError("Discovery timeout must be positive")
    messages = queue.Queue()
    process = subprocess.Popen([codex, "app-server", "--listen", "stdio://"],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True, encoding="utf-8")

    def reader():
        try:
            while True:
                line = process.stdout.readline(1_048_577)
                if not line:
                    break
                if len(line) > 1_048_576:
                    messages.put(RoutingError("Oversized app-server response"))
                    return
                messages.put(line)
        finally:
            messages.put(None)

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    deadline = time.monotonic() + timeout

    def send(message):
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()

    def request(number, method, params):
        send({"id": number, "method": method, "params": params})
        for _ in range(10000):
            remaining = deadline - time.monotonic()
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
                payload = {"data": rows, "source": "codex app-server model/list", "captured_at": utc_now()}
                normalize_catalog(payload)
                return payload
            if not isinstance(cursor, str) or not cursor or cursor in seen:
                raise RoutingError("Invalid or repeated model/list cursor")
            seen.add(cursor)
        raise RoutingError("Model catalog exceeded pagination limit")
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
        thread.join(timeout=2)
        process.stdin.close()
        process.stdout.close()


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
        for role, binding in document["bindings"].items():
            filename = role.replace("_", "-") + ".toml"
            content = (template / "agents" / filename).read_text(encoding="utf-8")
            (directory / "agents" / filename).write_text(
                "model = " + json.dumps(binding["model"]) + "\n" + content, encoding="utf-8")
        content = (template / "config-snippet.toml").read_text(encoding="utf-8")
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
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--policy", type=Path, default=SKILL / "assets/model-policy.json")
    parser.add_argument("--pin", action="append", default=[], metavar="ROLE=MODEL")
    parser.add_argument("--exclude", action="append", default=[], metavar="MODEL")
    parser.add_argument("--allowed-model", action="append", help="intersect with calling tool's model allowlist")
    parser.add_argument("--require-modality", action="append", default=[])
    parser.add_argument("--role", choices=list(ROLES) + list(ALIASES), help="require only this role to resolve")
    parser.add_argument("--output-dir", type=Path, help="render all roles into a new staging directory")
    args = parser.parse_args(argv)
    try:
        pins = {}
        for item in args.pin:
            role, separator, model = item.partition("=")
            role = ALIASES.get(role, role)
            if not separator or role not in ROLES or not model or role in pins:
                raise RoutingError("Pins must be unique ROLE=MODEL pairs")
            pins[role] = model
        payload = discover(args.codex, args.timeout) if args.discover else read_json(args.catalog)
        result = resolve(payload, read_json(args.policy), pins=pins, excluded=args.exclude,
                         allowed=args.allowed_model, modalities=args.require_modality)
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

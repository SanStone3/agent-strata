from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/strata"
SPEC = importlib.util.spec_from_file_location("strata_resolve_test", SKILL / "scripts/resolve_models.py")
R = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R)


def model(name, **kw):
    return {"model": name, "supportedReasoningEfforts": [{"reasoningEffort": x} for x in ("medium", "xhigh")], **kw}


def catalog(*extra):
    return {"captured_at": R.utc_now(), "data": [model(n) for n in (
        "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol", "gpt-6-luna", "gpt-6-sol", "gpt-6.1-sol", "gpt-6-astra"
    )] + list(extra)}


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.policy = R.read_json(SKILL / "assets/model-policy.json")

    def resolve(self, payload=None, **kw):
        return R.resolve(payload or catalog(), self.policy, **kw)

    def test_current_roles_and_efforts(self):
        doc = self.resolve()
        self.assertEqual({}, doc["unresolved"])
        for role, name in {"scout": "gpt-6-luna", "executor": "gpt-6-luna", "worker": "gpt-6.1-sol",
                           "deep_worker": "gpt-6-astra", "reviewer": "gpt-6-astra"}.items():
            self.assertEqual(name, doc["bindings"][role]["model"])
        self.assertFalse(doc["access_verified"])
        self.assertEqual("gpt-6-astra", doc["bindings"]["controller"]["model"])
        self.assertEqual("xhigh", doc["bindings"]["controller"]["reasoning_effort"])
        self.assertEqual("inherited", doc["bindings"]["controller"]["sandbox_mode"])
        self.assertEqual("read-only", doc["bindings"]["reviewer"]["sandbox_mode"])

    def test_controller_tracks_newest_eligible_deep_model(self):
        doc = self.resolve(catalog(model("gpt-6.2-astra")))
        self.assertEqual("gpt-6.2-astra", doc["bindings"]["controller"]["model"])

    def test_explicit_controller_choice_is_respected(self):
        doc = self.resolve(pins={"controller": "gpt-6.1-sol"})
        self.assertEqual("gpt-6.1-sol", doc["bindings"]["controller"]["model"])
        self.assertTrue(doc["bindings"]["controller"]["pinned"])
        self.assertEqual("balanced", doc["bindings"]["controller"]["tier"])

    def test_missing_deep_tier_does_not_weaken_controller(self):
        doc = self.resolve({"models": [model("gpt-6.1-sol")]})
        self.assertIn("controller", doc["unresolved"])
        self.assertNotIn("controller", doc["bindings"])

    def test_controller_requires_xhigh_even_when_pinned(self):
        payload = {"models": [{"model": "gpt-6-astra", "efforts": ["high"]}]}
        self.assertIn("controller", self.resolve(payload, pins={"controller": "gpt-6-astra"})["unresolved"])

    def test_preserve_primary_roundtrip_and_render(self):
        doc = self.resolve(preserve_primary=True)
        self.assertNotIn("controller", doc["bindings"])
        self.assertEqual(doc["bindings"], R.verify_binding(doc, self.policy)["bindings"])
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "out"
            R.render(doc, directory)
            content = (directory / "config-snippet.toml").read_text()
            self.assertFalse(any(line.startswith(("model =", "model_reasoning_effort =")) for line in content.splitlines()))
        with self.assertRaisesRegex(R.RoutingError, "Cannot combine"):
            self.resolve(preserve_primary=True, pins={"controller": "gpt-6-astra"})

    def test_new_minor_version_is_numeric_not_lexical(self):
        doc = self.resolve(catalog(model("gpt-6.9-sol"), model("gpt-6.10-sol")))
        self.assertEqual("gpt-6.10-sol", doc["bindings"]["worker"]["model"])

    def test_new_major_unknown_does_not_steal_role(self):
        doc = self.resolve(catalog(model("gpt-99-sol"), model("unfamiliar-model")))
        self.assertEqual("gpt-6.1-sol", doc["bindings"]["worker"]["model"])
        self.assertIn("gpt-99-sol", doc["unclassified"])

    def test_explicit_upgrade_adopts_new_name(self):
        payload = catalog(model("next-worker", upgrade="later-worker"), model("later-worker"))
        payload["data"][5]["upgrade"] = "next-worker"
        doc = self.resolve(payload)
        self.assertEqual("later-worker", doc["bindings"]["worker"]["model"])

    def test_known_upgrade_target_keeps_own_classification(self):
        payload = catalog()
        payload["data"][2]["upgrade"] = "gpt-6-sol"
        doc = self.resolve(payload)
        self.assertNotIn("gpt-6-sol", doc["bindings"]["deep_worker"]["alternatives"])

    def test_upgrade_cycles_rejected(self):
        payload = catalog(model("a", upgrade="b"), model("b", upgrade="a"))
        with self.assertRaisesRegex(R.RoutingError, "Cyclic"):
            self.resolve(payload)

    def test_conflicting_upgrade_tiers_rejected(self):
        payload = catalog(model("future"))
        payload["data"][3]["upgrade"] = "future"
        payload["data"][5]["upgrade"] = "future"
        with self.assertRaisesRegex(R.RoutingError, "Ambiguous"):
            self.resolve(payload)

    def test_model_without_xhigh_cannot_be_worker(self):
        payload = {"models": [{"model": "gpt-6.1-sol", "efforts": ["high"]}]}
        doc = self.resolve(payload)
        self.assertIn("worker", doc["unresolved"])

    def test_missing_effort_metadata_is_not_support(self):
        self.assertIn("worker", self.resolve({"models": [{"id": "gpt-6.1-sol"}]})["unresolved"])

    def test_unsupported_new_version_uses_compatible_same_tier(self):
        payload = catalog()
        payload["data"][5]["supportedReasoningEfforts"] = ["medium"]
        self.assertEqual("gpt-6-sol", self.resolve(payload)["bindings"]["worker"]["model"])

    def test_user_pin_overrides_newer_model(self):
        doc = self.resolve(pins={"worker": "gpt-6-sol"})
        self.assertEqual("gpt-6-sol", doc["bindings"]["worker"]["model"])
        self.assertEqual([], doc["bindings"]["worker"]["alternatives"])

    def test_pin_never_silently_falls_back(self):
        doc = self.resolve(pins={"worker": "missing"})
        self.assertIn("worker", doc["unresolved"])
        doc = self.resolve(pins={"worker": "gpt-6-sol"}, excluded=["gpt-6-sol"])
        self.assertIn("worker", doc["unresolved"])

    def test_pin_cannot_lower_minimum_capability(self):
        self.assertIn("reviewer", self.resolve(pins={"reviewer": "gpt-6-luna"})["unresolved"])

    def test_explicit_stronger_pin_allowed(self):
        doc = self.resolve(pins={"worker": "gpt-6-astra"})
        self.assertEqual("gpt-6-astra", doc["bindings"]["worker"]["model"])

    def test_missing_tier_does_not_auto_escalate(self):
        self.assertIn("worker", self.resolve({"models": [model("gpt-6-astra")]})["unresolved"])

    def test_allowlist_and_exclusions_restrict_candidates(self):
        doc = self.resolve(allowed=["gpt-6-sol", "gpt-6-astra"], excluded=["gpt-6-sol"])
        self.assertIn("worker", doc["unresolved"])
        self.assertIn("scout", doc["unresolved"])
        self.assertIn("reviewer", doc["bindings"])
        self.assertEqual({}, self.resolve(allowed=[])["bindings"])

    def test_hidden_model_requires_pin(self):
        payload = catalog(model("gpt-6.2-sol", hidden=True))
        self.assertEqual("gpt-6.1-sol", self.resolve(payload)["bindings"]["worker"]["model"])
        self.assertEqual("gpt-6.2-sol", self.resolve(payload, pins={"worker": "gpt-6.2-sol"})["bindings"]["worker"]["model"])

    def test_explicit_classification_requires_evidence(self):
        self.policy["models"]["org-model"] = {"tier": "balanced", "priority": 30}
        with self.assertRaisesRegex(R.RoutingError, "evidence"):
            self.resolve(catalog(model("org-model")))
        self.policy["models"]["org-model"]["evidence"] = "Organization-approved evaluated worker"
        self.assertEqual("org-model", self.resolve(catalog(model("org-model")))["bindings"]["worker"]["model"])

    def test_modalities_must_be_confirmed(self):
        doc = self.resolve(modalities=["image"])
        self.assertEqual({}, doc["bindings"])
        payload = catalog()
        payload["data"][5]["inputModalities"] = ["text", "image"]
        self.assertIn("worker", self.resolve(payload, modalities=["image"])["bindings"])

    def test_catalog_formats(self):
        payload = catalog()
        rpc = {"id": 2, "result": {"data": payload["data"], "nextCursor": None}}
        self.assertEqual(R.normalize_catalog(payload), R.normalize_catalog(rpc))
        self.assertEqual(R.normalize_catalog(payload), R.normalize_catalog({"models": self.resolve(payload)["catalog"]}))

    def test_invalid_or_incomplete_catalog_rejected(self):
        bad = [{}, {"data": []}, {"error": {"code": -1}}, {"result": []},
               {"data": [model("gpt-6-sol")], "nextCursor": "more"},
               {"models": [model("gpt-6-sol", hidden="false")]},
               {"models": [model("gpt-6-sol"), model("gpt-6-sol", hidden=True)]},
               {"models": [{"model": "bad\nmodel"}]}]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(R.RoutingError):
                R.normalize_catalog(value)

    def test_stale_or_naive_catalog_rejected(self):
        for date in ("2001-01-01T00:00:00Z", "2100-01-01T00:00:00Z", "2026-10-08T12:00:00"):
            payload = catalog()
            payload["captured_at"] = date
            with self.subTest(date=date), self.assertRaises(R.RoutingError):
                self.resolve(payload)

    def test_policy_cannot_weaken_role_contract(self):
        self.policy["roles"]["worker"]["effort"] = "high"
        with self.assertRaisesRegex(R.RoutingError, "contract"):
            self.resolve()

    def test_binding_roundtrip_and_mutation_detection(self):
        doc = self.resolve()
        self.assertEqual(doc["bindings"], R.verify_binding(doc, self.policy)["bindings"])
        for key, value in (("model", "gpt-6-luna"), ("reasoning_effort", "high"), ("sandbox_mode", "read-only")):
            changed = copy.deepcopy(doc)
            changed["bindings"]["worker"][key] = value
            with self.subTest(key=key), self.assertRaises(R.RoutingError):
                R.verify_binding(changed, self.policy)
        self.policy["reviewed_on"] = "changed"
        with self.assertRaisesRegex(R.RoutingError, "policy_sha256"):
            R.verify_binding(doc, self.policy)

    def test_render_complete_new_directory_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "out"
            R.render(self.resolve(), directory)
            self.assertEqual(5, len(list((directory / "agents").glob("*.toml"))))
            self.assertIn('model = "gpt-6.1-sol"', (directory / "agents/worker.toml").read_text())
            text = (directory / "config-snippet.toml").read_text()
            self.assertIn('model = "gpt-6-astra"', text)
            self.assertIn('model_reasoning_effort = "xhigh"', text)
            self.assertNotIn('model_context_window =', text)
            with self.assertRaisesRegex(R.RoutingError, "already exists"):
                R.render(self.resolve(), directory)
            self.assertTrue((directory / "model-bindings.json").is_file())

    def test_render_missing_role_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "out"
            with self.assertRaisesRegex(R.RoutingError, "incomplete"):
                R.render(self.resolve(allowed=[]), directory)
            self.assertFalse(directory.exists())

    def test_render_failure_removes_only_its_new_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "out"
            sentinel = Path(tmp) / "keep"
            sentinel.write_text("user work")
            with self.assertRaises(OSError):
                R.render(self.resolve(), directory, Path(tmp) / "absent-skill")
            self.assertFalse(directory.exists())
            self.assertEqual("user work", sentinel.read_text())

    def test_cli_role_alias_pin_and_exit_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "models.json"
            path.write_text(json.dumps({"models": [model("gpt-6-sol")]}))
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(0, R.main(["--catalog", str(path), "--role", "terra_worker", "--pin", "terra_worker=gpt-6-sol"]))
            self.assertTrue(json.loads(stdout.getvalue())["bindings"]["worker"]["pinned"])
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(2, R.main(["--catalog", str(path)]))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(1, R.main(["--catalog", str(path), "--pin", "worker=no", "--pin", "worker=other"]))


FAKE_SERVER = '''import json,sys,time
mode=sys.argv[1]
page=0
for line in sys.stdin:
 msg=json.loads(line)
 method=msg['method']
 if method not in ('initialize','initialized','model/list'):
  raise RuntimeError('Unexpected inference or mutation')
 if method=='initialized': continue
 if mode=='timeout': time.sleep(10); continue
 if method=='initialize': result={}
 else:
  page+=1
  if mode=='rpc_error':
   print(json.dumps({'id':msg['id'],'error':{'code':-1}}),flush=True); continue
  if mode=='exit': sys.exit(0)
  if mode=='malformed': print('broken-json',flush=True); continue
  if mode=='repeat': result={'data':[],'nextCursor':'same'}
  elif page==1:
   assert 'cursor' not in msg['params']
   result={'data':[{'model':'gpt-6-luna','efforts':['medium']}],'nextCursor':'second'}
  else:
   assert msg['params']['cursor']=='second'
   result={'data':[{'model':'gpt-6.1-sol','efforts':['xhigh']},{'model':'gpt-6-astra','efforts':['xhigh']}],'nextCursor':None}
 print(json.dumps({'method':'notification','params':{}}),flush=True)
 print(json.dumps({'id':msg['id'],'result':result}),flush=True)
'''


class DiscoveryTests(unittest.TestCase):
    def discover(self, mode="ok", timeout=3):
        real_popen = subprocess.Popen
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "fake.py"
            script.write_text(FAKE_SERVER)
            processes = []

            def launch(command, **kwargs):
                self.assertEqual(["codex", "app-server", "--listen", "stdio://"], command)
                process = real_popen([sys.executable, str(script), mode], **kwargs)
                processes.append(process)
                return process

            with mock.patch.object(R.subprocess, "Popen", side_effect=launch):
                try:
                    return R.discover(timeout=timeout)
                finally:
                    for process in processes:
                        self.assertIsNotNone(process.poll(), "Discovery leaked its process")

    def test_protocol_and_all_pages(self):
        payload = self.discover()
        self.assertEqual(3, len(payload["data"]))
        self.assertIn("captured_at", payload)

    def test_protocol_failures_and_process_cleanup(self):
        for mode in ("rpc_error", "exit", "malformed", "repeat", "timeout"):
            with self.subTest(mode=mode), self.assertRaises(R.RoutingError):
                self.discover(mode, timeout=0.3 if mode == "timeout" else 3)


if __name__ == "__main__":
    unittest.main()

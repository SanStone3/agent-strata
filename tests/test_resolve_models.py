from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
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


def discovery_context(**updates):
    context = {"schema_version": 1, "host": "test-host", "executable": "/tmp/strata/codex",
               "client_version": "0.161.0", "codex_home": "/tmp/strata/home", "cwd": "/tmp/strata/work",
               "profile": None, "provider": "openai", "auth_mode": "chatgpt", "auth_source": "account/read"}
    context.update(updates)
    return context


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.policy = R.read_json(SKILL / "assets/model-policy.json")

    def resolve(self, payload=None, **kw):
        return R.resolve(payload or catalog(), self.policy, **kw)

    def test_current_roles_and_efforts(self):
        doc = self.resolve()
        self.assertEqual({}, doc["unresolved"])
        for role, name in {"scout": "gpt-5.6-luna", "executor": "gpt-5.6-luna", "worker": "gpt-6.1-sol",
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

    def test_role_preferences_prioritize_ordered_eligible_models(self):
        self.policy["role_preferences"] = {"scout": ["gpt-5.6-luna", "gpt-6-luna"],
                                           "executor": ["gpt-5.6-luna"]}
        doc = self.resolve()
        for role in ("scout", "executor"):
            self.assertEqual("gpt-5.6-luna", doc["bindings"][role]["model"])
            self.assertEqual("medium", doc["bindings"][role]["reasoning_effort"])
            self.assertFalse(doc["bindings"][role]["pinned"])
        self.assertEqual(["gpt-6-luna"], doc["bindings"]["scout"]["alternatives"])
        self.assertEqual("gpt-6-astra", doc["bindings"]["controller"]["model"])
        self.assertFalse(doc["access_verified"])
        self.assertEqual(doc["bindings"], R.verify_binding(doc, self.policy)["bindings"])
        self.policy["role_preferences"]["scout"].reverse()
        self.assertEqual("gpt-6-luna", self.resolve()["bindings"]["scout"]["model"])

    def test_preferences_missing_hidden_incompatible_or_wrong_tier_fall_back(self):
        self.policy["role_preferences"] = {"scout": ["gpt-5.6-luna"]}
        for condition in ("missing", "hidden", "effort", "tier", "unclassified"):
            payload = catalog()
            if condition == "missing":
                del payload["data"][0]
            elif condition == "hidden":
                payload["data"][0]["hidden"] = True
            elif condition == "effort":
                payload["data"][0]["supportedReasoningEfforts"] = ["high"]
            elif condition == "tier":
                self.policy["role_preferences"]["scout"] = ["gpt-5.6-sol"]
            else:
                self.policy["role_preferences"]["scout"] = ["unknown-model"]
                payload["data"].append(model("unknown-model"))
            with self.subTest(condition=condition):
                self.assertEqual("gpt-6-luna", self.resolve(payload)["bindings"]["scout"]["model"])
        self.policy["role_preferences"] = {"worker": ["gpt-5.6-terra"]}
        payload = catalog()
        payload["data"][1]["supportedReasoningEfforts"] = ["high"]
        self.assertEqual("gpt-6.1-sol", self.resolve(payload)["bindings"]["worker"]["model"])

    def test_preferences_obey_filters_and_pins(self):
        self.policy["role_preferences"] = {"scout": ["gpt-5.6-luna"]}
        for options in ({"allowed": ["gpt-6-luna"]}, {"excluded": ["gpt-5.6-luna"]},
                        {"pins": {"scout": "gpt-6-luna"}}):
            with self.subTest(options=options):
                self.assertEqual("gpt-6-luna", self.resolve(**options)["bindings"]["scout"]["model"])
        payload = catalog()
        payload["data"][3]["inputModalities"] = ["image"]
        self.assertEqual("gpt-6-luna", self.resolve(payload, modalities=["image"])["bindings"]["scout"]["model"])
        self.policy["pins"]["scout"] = "gpt-6-luna"
        self.assertEqual("gpt-6-luna", self.resolve()["bindings"]["scout"]["model"])

    def test_absent_preferences_preserve_family_ranking(self):
        self.policy.pop("role_preferences", None)
        for role in ("scout", "executor"):
            self.assertEqual("gpt-6-luna", self.resolve()["bindings"][role]["model"])

    def test_malformed_role_preferences_rejected(self):
        for preferences in (None, [], {"invalid": ["gpt-5.6-luna"]}, {"controller": ["gpt-5.6-sol"]},
                            {"scout": "gpt-5.6-luna"}, {"scout": []}, {"scout": [""]},
                            {"scout": [" "]}, {"scout": [42]}, {"scout": [{}]},
                            {"scout": ["gpt-5.6-luna", "gpt-5.6-luna"]}):
            self.policy["role_preferences"] = preferences
            with self.subTest(preferences=preferences), self.assertRaisesRegex(R.RoutingError, "[Pp]references"):
                self.resolve()

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

    def test_plain_catalog_has_no_invented_context(self):
        doc = self.resolve()
        self.assertIsNone(doc["context"])
        self.assertEqual(R.digest(None), doc["context_sha256"])
        self.assertIsNone(R.verify_binding(doc, self.policy)["context"])
        with self.assertRaisesRegex(R.RoutingError, "context"):
            R.verify_binding(doc, self.policy, expected_context=discovery_context())

    def test_context_roundtrip_and_drift_detection(self):
        payload = catalog()
        payload["context"] = discovery_context(endpoint_fingerprint="a" * 64)
        doc = self.resolve(payload)
        saved = json.loads(json.dumps(doc))
        self.assertEqual(payload["context"], R.verify_binding(saved, self.policy, payload["context"])["context"])
        payload["context"]["host"] = "caller-mutated"
        self.assertEqual("test-host", doc["context"]["host"])
        for key, value in (("host", "different-host"), ("codex_home", "/tmp/other-home"),
                           ("cwd", "/tmp/other-work"), ("profile", "api"), ("provider", "evolab"),
                           ("executable", "/tmp/other-codex"), ("client_version", "0.162.0-alpha.1"),
                           ("auth_mode", "api-key"), ("auth_source", "login-status"),
                           ("endpoint_fingerprint", "b" * 64)):
            changed = copy.deepcopy(doc)
            changed["context"][key] = value
            with self.subTest(key=key):
                with self.assertRaisesRegex(R.RoutingError, "context_sha256"):
                    R.verify_binding(changed, self.policy)
                changed["context_sha256"] = R.digest(changed["context"])
                with self.assertRaisesRegex(R.RoutingError, "expected runtime context"):
                    R.verify_binding(changed, self.policy, expected_context=doc["context"])

    def test_context_hash_and_access_claim_cannot_be_dropped_or_edited(self):
        doc = self.resolve({**catalog(), "context": discovery_context()})
        for key in ("context", "context_sha256"):
            changed = copy.deepcopy(doc)
            del changed[key]
            with self.subTest(key=key), self.assertRaisesRegex(R.RoutingError, "context_sha256"):
                R.verify_binding(changed, self.policy)
        changed = copy.deepcopy(doc)
        changed["access_verified"] = True
        with self.assertRaisesRegex(R.RoutingError, "cannot verify"):
            R.verify_binding(changed, self.policy)

    def test_context_rejects_raw_account_or_config_fields(self):
        for extra in ({"email": "private@example.invalid"}, {"headers": {"Authorization": "secret"}},
                      {"endpoint_fingerprint": "https://secret.invalid"}, {"auth_mode": "other"}):
            with self.subTest(extra=extra), self.assertRaises(R.RoutingError):
                self.resolve({**catalog(), "context": discovery_context(**extra)})

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

    def test_cli_passes_discovery_target_and_guards(self):
        with mock.patch.object(R, "discover", return_value=catalog()) as discover, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, R.main(["--discover", "--codex", "/tmp/test-codex", "--timeout", "4",
                                        "--codex-home", "/tmp/home", "--cwd", "/tmp/work", "--profile", "api",
                                        "--expected-auth", "api-key", "--expected-provider", "evolab"]))
        discover.assert_called_once_with("/tmp/test-codex", 4, codex_home=Path("/tmp/home"), cwd=Path("/tmp/work"),
                                         profile="api", expected_auth="api-key", expected_provider="evolab")
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            self.assertEqual(1, R.main(["--catalog", "unused.json", "--expected-auth", "chatgpt"]))
        self.assertIn("require --discover", stderr.getvalue())


FAKE_SERVER = '''import json,os,signal,sys,time
mode=os.environ['STRATA_TEST_MODE']
def log(item):
 with open(os.environ['STRATA_TEST_LOG'],'a') as stream:
  stream.write(json.dumps(item)+'\\n')
log({'argv':sys.argv[1:],'cwd':os.getcwd(),'home':os.environ.get('CODEX_HOME'),
     'proxy':os.environ.get('HTTPS_PROXY'),'sentinel':os.environ.get('STRATA_TEST_SENTINEL')})
if sys.argv[-1]=='--version':
 if mode=='version_timeout': time.sleep(10)
 if mode=='oversized_version': print('private-token'*2000,flush=True)
 else: print('codex-cli 0.162.0-alpha.1',flush=True)
 sys.exit(0)
if sys.argv[-2:]==['login','status']:
 if mode=='status_timeout': time.sleep(10)
 if mode=='fallback_api': print('Logged in using an API key - sk-secret-login-key',file=sys.stderr)
 elif mode=='unknown_auth':
  print('Not logged in; private-diagnostic',file=sys.stderr); sys.exit(1)
 else: print('Logged in using ChatGPT',file=sys.stderr)
 sys.exit(0)
assert sys.argv[-3:]==['app-server','--listen','stdio://']
if mode=='ignore_term': signal.signal(signal.SIGTERM,signal.SIG_IGN)
page=0
for line in sys.stdin:
 msg=json.loads(line)
 log({'rpc':msg})
 method=msg['method']
 if method not in ('initialize','initialized','model/list','config/read','account/read'):
  raise RuntimeError('Unexpected inference or mutation')
 if method=='initialized': continue
 if mode in ('timeout','ignore_term'): time.sleep(10); continue
 if method=='initialize': result={}
 elif method=='config/read':
  assert msg['params']=={'includeLayers':False}
  if mode=='optional_timeout': time.sleep(10); continue
  if mode=='config_error':
   print(json.dumps({'id':msg['id'],'error':{'message':'secret-config-error'}}),flush=True); continue
  if mode in ('api','fallback_api'):
   result={'config':{'model_provider':'evolab','model_providers':{'evolab':{
    'base_url':'https://secret-user:secret-password@example.invalid/v1?token=secret-endpoint',
    'http_headers':{'Authorization':'secret-header'},'experimental_bearer_token':'secret-bearer'}}}}
  else: result={'config':{}}
 elif method=='account/read':
  assert msg['params']=={'refreshToken':False}
  if mode in ('fallback_chatgpt','fallback_api','unknown_auth','status_timeout'):
   print(json.dumps({'id':msg['id'],'error':{'message':'secret-account-error'}}),flush=True); continue
  result={'account':{'type':'apiKey' if mode=='api' else 'chatgpt',
                     'email':'private-email@example.invalid','id':'private-account-id','apiKey':'secret-account-key'}}
 else:
  page+=1
  if mode=='rpc_error':
   print(json.dumps({'id':msg['id'],'error':{'code':-1}}),flush=True); continue
  if mode=='exit': sys.exit(0)
  if mode=='malformed': print('broken-json',flush=True); continue
  if mode=='oversized': print('x'*1048577,flush=True); continue
  if mode=='invalid_utf8': sys.stdout.buffer.write(b'\\xff\\n'); sys.stdout.buffer.flush(); continue
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
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.home, self.work, self.bin = (self.root / name for name in ("home", "work", "bin"))
        for directory in (self.home, self.work, self.bin):
            directory.mkdir()
        self.script = self.bin / "codex-real"
        self.script.write_text("#!" + sys.executable + "\n" + FAKE_SERVER)
        self.script.chmod(0o755)
        (self.bin / "codex").symlink_to(self.script)
        self.log = self.root / "calls.jsonl"

    def discover(self, mode="ok", timeout=10, **options):
        real_popen = subprocess.Popen
        processes = []

        def launch(command, **kwargs):
            self.assertEqual(str(self.script), command[0])
            self.assertNotIn("shell", kwargs)
            self.assertIsNot(kwargs["env"], os.environ)
            process = real_popen(command, **kwargs)
            processes.append(process)
            return process

        env = {"STRATA_TEST_MODE": mode, "STRATA_TEST_LOG": str(self.log), "PATH": str(self.bin),
               "CODEX_HOME": str(self.root / "inherited-home"), "HTTPS_PROXY": "http://test-proxy.invalid:9999",
               "STRATA_TEST_SENTINEL": "inherited"}
        target = {"codex_home": self.home, "cwd": self.work, **options}
        with mock.patch.dict(os.environ, env), mock.patch.object(R.subprocess, "Popen", side_effect=launch):
            before = dict(os.environ)
            try:
                return R.discover(timeout=timeout, **target)
            finally:
                self.assertEqual(before, dict(os.environ), "Discovery mutated global environment")
                for process in processes:
                    self.assertIsNotNone(process.poll(), "Discovery leaked its process")
                    self.assertTrue(process.stdout.closed)
                    if process.stdin is not None:
                        self.assertTrue(process.stdin.closed)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_protocol_and_all_pages(self):
        payload = self.discover()
        self.assertEqual(3, len(payload["data"]))
        self.assertIn("captured_at", payload)
        self.assertFalse(payload["access_verified"])
        self.assertEqual("chatgpt", payload["context"]["auth_mode"])
        self.assertEqual("account/read", payload["context"]["auth_source"])
        self.assertEqual("openai", payload["context"]["provider"])
        methods = [item["rpc"]["method"] for item in self.calls() if "rpc" in item]
        self.assertEqual(["initialize", "initialized", "model/list", "model/list", "config/read", "account/read"], methods)
        self.assertEqual(2, sum("argv" in item for item in self.calls()))

    def test_target_home_cwd_profile_executable_version_and_inherited_environment(self):
        payload = self.discover(profile="api", expected_auth="chatgpt", expected_provider="openai")
        context = payload["context"]
        self.assertEqual(str(self.script), context["executable"])
        self.assertEqual(str(self.home), context["codex_home"])
        self.assertEqual(str(self.work), context["cwd"])
        self.assertEqual("api", context["profile"])
        self.assertEqual("0.162.0-alpha.1", context["client_version"])
        commands = [item for item in self.calls() if "argv" in item]
        self.assertEqual([["--profile", "api", "--version"],
                          ["--profile", "api", "app-server", "--listen", "stdio://"]], [item["argv"] for item in commands])
        for command in commands:
            self.assertEqual(str(self.home), command["home"])
            self.assertEqual(str(self.work), command["cwd"])
            self.assertEqual("inherited", command["sentinel"])
            self.assertEqual("http://test-proxy.invalid:9999", command["proxy"])

    def test_inherited_and_relative_home_resolution(self):
        self.assertEqual(str(self.root / "inherited-home"), self.discover(codex_home=None)["context"]["codex_home"])
        self.assertEqual(str(self.home), self.discover(codex_home="../home", codex="../bin/codex")["context"]["codex_home"])

    def test_api_provider_fingerprint_contains_no_credentials(self):
        payload = self.discover("api", expected_auth="api-key", expected_provider="evolab")
        context = payload["context"]
        self.assertEqual("api-key", context["auth_mode"])
        endpoint = "https://secret-user:secret-password@example.invalid/v1?token=secret-endpoint"
        self.assertEqual(R.hashlib.sha256(endpoint.encode()).hexdigest(), context["endpoint_fingerprint"])
        policy = R.read_json(SKILL / "assets/model-policy.json")
        serialized = json.dumps(R.resolve(payload, policy))
        for secret in ("secret-", "private-", "example.invalid", "Authorization", "apiKey"):
            self.assertNotIn(secret, serialized)

    def test_login_status_fallback_uses_same_target_and_never_verifies_access(self):
        for mode, expected in (("fallback_chatgpt", "chatgpt"), ("fallback_api", "api-key")):
            with self.subTest(mode=mode):
                payload = self.discover(mode, profile="stored", expected_auth=expected)
                self.assertEqual(expected, payload["context"]["auth_mode"])
                self.assertEqual("login-status", payload["context"]["auth_source"])
                self.assertFalse(payload["access_verified"])
                self.assertNotIn("secret", json.dumps(payload))
                command = self.calls()[-1]
                self.assertEqual(["--profile", "stored", "login", "status"], command["argv"])
                self.assertEqual(str(self.home), command["home"])
                self.assertEqual(str(self.work), command["cwd"])

    def test_unknown_auth_and_provider_are_not_invented(self):
        payload = self.discover("unknown_auth")
        self.assertEqual("unknown", payload["context"]["auth_mode"])
        self.assertEqual("unknown", payload["context"]["auth_source"])
        payload = self.discover("config_error")
        self.assertEqual("unknown", payload["context"]["provider"])

    def test_expected_guards_fail_closed_and_hide_remote_errors(self):
        for mode, options in (("ok", {"expected_auth": "api-key"}), ("unknown_auth", {"expected_auth": "chatgpt"}),
                              ("api", {"expected_provider": "openai"}), ("config_error", {"expected_provider": "openai"})):
            with self.subTest(mode=mode), self.assertRaises(R.RoutingError) as caught:
                self.discover(mode, **options)
            self.assertNotIn("secret", str(caught.exception))

    def test_status_and_optional_reads_are_time_and_output_bounded(self):
        for mode in ("version_timeout", "status_timeout", "oversized_version", "optional_timeout"):
            start = time.monotonic()
            with self.subTest(mode=mode):
                payload = self.discover(mode, timeout=1)
                self.assertLess(time.monotonic() - start, 3)
                self.assertNotIn("private-", json.dumps(payload))
                if mode in ("version_timeout", "oversized_version"):
                    self.assertEqual("unknown", payload["context"]["client_version"])
                elif mode == "status_timeout":
                    self.assertEqual("unknown", payload["context"]["auth_mode"])
                else:
                    self.assertEqual("unknown", payload["context"]["provider"])

    def test_invalid_target_is_rejected_before_starting_process(self):
        for options in ({"timeout": 0}, {"timeout": float("nan")}, {"expected_auth": "other"},
                        {"expected_provider": "unknown"}, {"profile": ""}, {"cwd": self.root / "absent"}):
            with self.subTest(options=options), self.assertRaises(R.RoutingError):
                self.discover(**options)
        self.assertFalse(self.log.exists())
        with self.assertRaisesRegex(R.RoutingError, "not found"):
            R.discover(codex=str(self.root / "missing-codex"), cwd=self.work)

    def test_protocol_failures_and_process_cleanup(self):
        for mode in ("rpc_error", "exit", "malformed", "repeat", "timeout", "oversized", "invalid_utf8", "ignore_term"):
            with self.subTest(mode=mode), self.assertRaises(R.RoutingError):
                self.discover(mode, timeout=0.3 if mode in ("timeout", "ignore_term") else 3)


if __name__ == "__main__":
    unittest.main()

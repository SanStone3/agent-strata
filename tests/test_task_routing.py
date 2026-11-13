"""Task model/effort and primary-preservation regressions, without inference."""
import copy
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from test_resolve_models import R, SKILL
from test_validate import VALIDATE


class TaskRoutingTests(unittest.TestCase):
    def setUp(self):
        self.policy = R.read_json(SKILL / 'assets/model-policy.json')
        self.catalog = {'models': [
            {'model': name, 'efforts': ['low', 'medium', 'high', 'xhigh', 'max']}
            for name in ('gpt-6-luna', 'gpt-6.1-terra', 'gpt-6.1-sol', 'gpt-6-astra')]}

    def resolve(self, **kw):
        return R.resolve(self.catalog, self.policy, **kw)

    def test_coding_prefers_sol_and_scoped_prefers_terra_at_supported_efforts(self):
        for task_kind, expected in (('coding', 'gpt-6.1-sol'), ('scoped', 'gpt-6.1-terra')):
            for effort in ('low', 'medium', 'high', 'xhigh'):
                with self.subTest(task_kind=task_kind, effort=effort):
                    doc = self.resolve(task_kind=task_kind, efforts={'worker': effort})
                    model = expected if effort in ('medium', 'high') else 'gpt-6.1-sol'
                    self.assertEqual(model, doc['bindings']['worker']['model'])
                    self.assertEqual(effort, doc['bindings']['worker']['reasoning_effort'])
                    self.assertNotIn('controller', doc['bindings'])

    def test_complex_roles_cannot_be_downgraded_to_terra(self):
        for role in ('deep_worker', 'reviewer'):
            doc = self.resolve(pins={role: 'gpt-6.1-terra'})
            self.assertIn(role, doc['unresolved'])
        doc = self.resolve(excluded=['gpt-6.1-sol'])
        self.assertEqual({'worker', 'deep_worker', 'reviewer'}, doc['unresolved'].keys())
        scoped = self.resolve(task_kind='scoped', excluded=['gpt-6.1-sol'])
        self.assertEqual('gpt-6.1-terra', scoped['bindings']['worker']['model'])

    def test_deep_worker_xhigh_keeps_sol_and_workspace_boundary(self):
        doc = self.resolve(efforts={'deep_worker': 'xhigh'})
        worker = doc['bindings']['deep_worker']
        self.assertEqual(('gpt-6.1-sol', 'xhigh', 'workspace-write'),
                         (worker['model'], worker['reasoning_effort'], worker['sandbox_mode']))
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'rendered'
            R.render(doc, output)
            role = VALIDATE.Validator(None, SKILL).load_toml(output / 'agents/deep-worker.toml')
            self.assertEqual(worker['reasoning_effort'], role['model_reasoning_effort'])
            self.assertEqual(worker['model'], role['model'])

    def test_worker_fallback_filters_and_pin(self):
        for kw in ({'excluded': ['gpt-6.1-terra']}, {'allowed': ['gpt-6-luna', 'gpt-6.1-sol']}):
            doc = self.resolve(task_kind='scoped', **kw)
            self.assertEqual('gpt-6.1-sol', doc['bindings']['worker']['model'])
        doc = self.resolve(task_kind='scoped', pins={'worker': 'gpt-6.1-terra'}, excluded=['gpt-6.1-terra'])
        self.assertIn('worker', doc['unresolved'])
        self.catalog['models'][1]['hidden'] = True
        self.assertEqual('gpt-6.1-sol', self.resolve(task_kind='scoped')['bindings']['worker']['model'])
        self.assertEqual('gpt-6.1-terra', self.resolve(pins={'worker': 'gpt-6.1-terra'})['bindings']['worker']['model'])

    def test_xhigh_scoped_work_uses_sol_unless_terra_is_explicitly_pinned(self):
        doc = self.resolve(task_kind='scoped', efforts={'worker': 'xhigh'})
        self.assertEqual('gpt-6.1-sol', doc['bindings']['worker']['model'])
        doc = self.resolve(task_kind='scoped', efforts={'worker': 'xhigh'}, pins={'worker': 'gpt-6.1-terra'})
        self.assertEqual('gpt-6.1-terra', doc['bindings']['worker']['model'])

    def test_historical_policy_controller_pin_does_not_block_workers(self):
        self.policy['pins']['controller'] = 'gpt-6-astra'
        doc = self.resolve()
        self.assertNotIn('controller', doc['bindings'])
        self.assertTrue(any('Ignored policy controller pin' in x for x in doc['warnings']))
        self.assertEqual(doc['bindings'], R.verify_binding(doc, self.policy)['bindings'])
        with self.assertRaisesRegex(R.RoutingError, 'manual primary selection'):
            self.resolve(preserve_primary=False)

    def test_cli_requires_explicit_scoped_choice_without_sol(self):
        self.catalog['models'] = self.catalog['models'][:2]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'catalog.json'
            path.write_text(json.dumps(self.catalog))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(2, R.main(['--catalog', str(path), '--role', 'worker']))
                self.assertEqual(0, R.main(['--catalog', str(path), '--role', 'worker', '--task-kind', 'scoped']))
                self.assertEqual(2, R.main(['--catalog', str(path), '--role', 'deep_worker']))

    def test_modality_evidence_required(self):
        self.catalog['models'][1]['inputModalities'] = ['text']
        self.catalog['models'][2]['inputModalities'] = ['text', 'image']
        doc = self.resolve(task_kind='scoped', modalities=['image'])
        self.assertEqual('gpt-6.1-sol', doc['bindings']['worker']['model'])
        self.assertTrue({'scout', 'executor'} <= doc['unresolved'].keys())
        self.assertIn('worker', self.resolve(modalities=['image'], pins={'worker': 'gpt-6.1-terra'})['unresolved'])

    def test_task_effort_roundtrip_and_tamper_detection(self):
        for level in ('medium', 'high', 'xhigh'):
            doc = self.resolve(efforts={'worker': level})
            self.assertEqual(level, R.verify_binding(doc, self.policy)['bindings']['worker']['reasoning_effort'])
        changed = copy.deepcopy(doc)
        changed['bindings']['worker']['reasoning_effort'] = 'medium'
        with self.assertRaises(R.RoutingError):
            R.verify_binding(changed, self.policy)
        changed = copy.deepcopy(doc)
        changed['constraints']['efforts']['worker'] = 'medium'
        with self.assertRaises(R.RoutingError):
            R.verify_binding(changed, self.policy)

    def test_missing_support_fails_without_silent_effort_lowering(self):
        self.catalog['models'][1]['efforts'] = ['medium']
        self.catalog['models'][2]['efforts'] = ['medium']
        doc = self.resolve(efforts={'worker': 'high'})
        self.assertIn('worker', doc['unresolved'])
        for efforts in ({'worker': 'max'}, {'reviewer': 'medium'}, {'scout': 'xhigh'}, {'typo': 'medium'}):
            with self.subTest(efforts=efforts), self.assertRaises(R.RoutingError):
                self.resolve(efforts=efforts)

    def test_render_primary_free_even_for_advisory_controller(self):
        doc = self.resolve(preserve_primary=False, pins={'controller': 'gpt-6.1-sol'},
                           efforts={'controller': 'high', 'worker': 'high'})
        for _ in range(2):
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / 'staged'
                R.render(doc, out)
                validator = VALIDATE.Validator(None, SKILL)
                config = validator.load_toml(out / 'config-snippet.toml')
                self.assertFalse({'model', 'model_reasoning_effort', 'model_context_window'} & config.keys())
                self.assertNotIn('max_concurrent_threads_per_session', config['agents'])
                self.assertEqual('high', config['agents']['default_subagent_reasoning_effort'])
                worker = validator.load_toml(out / 'agents/worker.toml')
                self.assertEqual('high', worker['model_reasoning_effort'])
                self.assertEqual('gpt-6.1-sol', worker['model'])
                self.assertEqual(worker['model'], config['agents']['default_subagent_model'])


if __name__ == '__main__':
    unittest.main()

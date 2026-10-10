import ast
import hashlib
import json
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import jinja2
ROOT = Path(__file__).resolve().parents[1]


class DeployedTemplateTests(unittest.TestCase):
    def test_custom_templates_match_audited_hashes_and_json_has_no_proxy_credentials(self):
        manifest = json.loads((ROOT / 'docs/production-source-manifest-20261010.json').read_text())
        for item in manifest['mounted_templates']:
            data = (ROOT / 'deployment/templates' / item['path']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), item['sha256'])
        data = json.loads((ROOT / 'deployment/templates/v2ray/default.json').read_text())
        self.assertTrue(data['routing']['rules'])
        self.assertEqual({o['protocol'] for o in data['outbounds']}, {'freedom', 'blackhole'})

    def test_subscription_page_renders_with_dummy_user_and_actual_datetime_filter(self):
        scope = {'datetime': datetime}
        tree = ast.parse((ROOT / 'app/templates/filters.py').read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'datetimeformat')
        exec(compile(ast.Module(body=[fn], type_ignores=[]), '<filter>', 'exec'), scope)
        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        env.filters['datetime'] = scope['datetimeformat']
        page = (ROOT / 'deployment/templates/subscription/index.html').read_text()
        result = env.from_string(page).render(user=SimpleNamespace(username='fixture_user', status='active', expire=1900000000, used_traffic=0, data_limit=10737418240))
        self.assertIn('fixture_user', result)
        self.assertNotIn('{{ user.', result)


if __name__ == '__main__': unittest.main()

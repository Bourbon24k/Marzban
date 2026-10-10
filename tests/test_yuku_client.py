"""Execute route/renderer code in isolation from database and Xray services."""
import ast
import base64
import json
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
ROOT = Path(__file__).resolve().parents[1]


def load_function(path, name, scope, class_name=None):
    tree = ast.parse((ROOT / path).read_text())
    nodes = tree.body if class_name is None else next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name).body
    fn = next(n for n in nodes if isinstance(n, ast.FunctionDef) and n.name == name)
    fn.decorator_list = []; fn.returns = None
    for arg in fn.args.args + fn.args.kwonlyargs: arg.annotation = None
    fn.args.defaults = [ast.Constant(None) for _ in fn.args.defaults]
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), str(path), 'exec'), scope)
    return scope[name]


class YukuClientTests(unittest.TestCase):
    def test_yuku_route_keeps_hwid_limit_and_opts_in_only_yuku(self):
        scope = dict(re=re, base64=base64)
        for flag in ('USE_CUSTOM_JSON_DEFAULT', 'USE_CUSTOM_JSON_FOR_V2RAYN', 'USE_CUSTOM_JSON_FOR_V2RAYNG', 'USE_CUSTOM_JSON_FOR_STREISAND', 'USE_CUSTOM_JSON_FOR_HAPP'): scope[flag] = False
        resolve = load_function('app/routers/subscription.py', 'resolve_format', scope)
        enforce = Mock(return_value=True); generate = Mock(return_value='blocked-notice')
        scope.update(UserResponse=SimpleNamespace(model_validate=lambda u: u), crud=SimpleNamespace(update_user_sub=Mock()), enforce_device_limit=enforce, generate_subscription=generate, device_limit_notice_lines=lambda: ['Device limit'], SUB_SUPPORT_URL='', SUB_PROFILE_TITLE='', SUB_UPDATE_INTERVAL=12, encode_title=lambda x: x, get_subscription_user_info=lambda u: {}, get_announce_text=lambda u: '', Response=lambda **kw: kw)
        route = load_function('app/routers/subscription.py', 'user_subscription', scope)
        request = SimpleNamespace(headers={}, url='https://example.test/sub/token'); user = SimpleNamespace(username='fixture')
        for ua in ('Yuku/0.3.1', 'yUkU/0.3.1', 'INCY/1', 'Happ/2.0.0', 'Other/1'):
            with self.subTest(ua=ua):
                response = route(request, object(), user, ua)
                self.assertEqual(response['content'], 'blocked-notice')
                self.assertEqual(generate.call_args.kwargs['notice_lines'], ['Device limit'])
                self.assertEqual(generate.call_args.kwargs['include_yuku_metadata'], ua.lower().startswith('yuku/'))
                if ua.lower().startswith('yuku/'): self.assertEqual(generate.call_args.kwargs['config_format'], 'v2ray-json')
        self.assertEqual(enforce.call_count, 5)
        self.assertEqual(resolve('Happ/2.0.0')[0], 'v2ray')

    def test_renderer_preserves_profiles_and_marks_only_opted_in_automatic(self):
        scope = dict(json=json, UUIDEncoder=json.JSONEncoder)
        add = load_function('app/subscription/v2ray.py', 'add_config', scope, 'V2rayJsonConfig')
        render = load_function('app/subscription/v2ray.py', 'render', scope, 'V2rayJsonConfig')
        outbound = {'protocol': 'vless', 'settings': {'address': 'fixture.example'}}
        for opted_in in (False, True):
            obj = SimpleNamespace(base={'routing': {'rules': []}}, base_outbounds=[], profile_outbounds=[], config=[], auto_member_tags={2: [], 1: []}, routing_profile=False, yuku_metadata_enabled=opted_in, build_auto_config=lambda group: {'remarks': f'auto-{group}', 'outbounds': [], 'meta': {'serverDescription': 'balancer'}})
            metadata = {'schemaVersion': 1, 'kind': 'server', 'networkRole': 'normal', 'hostID': '41', 'autoSelectGroup': 1} if opted_in else None
            add(obj, 'host-a', [outbound], 'description', metadata); add(obj, 'host-b', [outbound])
            result = json.loads(render(obj, False))
            self.assertEqual([row['remarks'] for row in result], ['auto-1', 'auto-2', 'host-a', 'host-b'])
            self.assertEqual(result[2]['outbounds'], [outbound])
            self.assertEqual(result[2]['meta']['serverDescription'], 'description')
            self.assertEqual('yuku' in result[2]['meta'], opted_in)
            for automatic in result[:2]:
                self.assertEqual('yuku' in automatic['meta'], opted_in)
                if opted_in: self.assertEqual(automatic['meta']['yuku']['kind'], 'automatic')
            self.assertNotIn('meta', result[3])


if __name__ == '__main__': unittest.main()

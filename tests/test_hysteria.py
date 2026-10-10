import unittest
from urllib.parse import urlsplit, parse_qs, unquote
from pydantic import ValidationError
from app.models.proxy import HysteriaSettings, ProxyTypes
from app.models.user import UserCreate
from app.subscription.hysteria import share_link, xray_outbound, singbox_outbound, mihomo_node
from app.utils.audit import _jsonable
from app.xray.config import XRayConfig
from app.xray.node import ReSTXRayNode, RPyCXRayNode
from xray_api.types.account import HysteriaAccount

class HysteriaTests(unittest.TestCase):
    def setUp(self):
        self.inbound={'protocol':'hysteria','network':'hysteria','tls':'tls','port':443,
                      'sni':'example.com','ais':False,'obfs_password':'obfs token',
                      'finalmask':{'udp':[{'type':'salamander','settings':{'password':'obfs token'}}]}}
        self.settings={'auth':'a:@/?#% token'}
    def test_uri_credentials_ipv6_and_tls(self):
        u=urlsplit(share_link('H2 test','2001:db8::1',self.inbound,self.settings))
        self.assertEqual(unquote(u.username),self.settings['auth']);self.assertEqual(u.hostname,'2001:db8::1')
        q=parse_qs(u.query);self.assertNotIn('insecure',q);self.assertEqual(q['obfs-password'],['obfs token'])
    def test_formats_keep_auth_and_salamander(self):
        x=xray_outbound('example.com',self.inbound,self.settings)
        self.assertEqual(x['streamSettings']['hysteriaSettings']['auth'],self.settings['auth'])
        self.assertEqual(x['streamSettings']['finalmask'],self.inbound['finalmask'])
        s=singbox_outbound('H2','example.com',self.inbound,self.settings)
        self.assertEqual(s['type'],'hysteria2');self.assertEqual(s['password'],self.settings['auth']);self.assertFalse(s['tls']['insecure'])
        m=mihomo_node('H2','example.com',self.inbound,self.settings);self.assertEqual(m['obfs-password'],'obfs token')
    def test_random_auth_rotation_and_empty_rejected(self):
        a,b=HysteriaSettings(),HysteriaSettings();self.assertNotEqual(a.auth,b.auth)
        old=a.auth;a.revoke();self.assertNotEqual(old,a.auth)
        with self.assertRaises(ValidationError):HysteriaSettings(auth='')
    def test_protobuf_matches_native_core(self):
        m=HysteriaAccount(email='1.test',auth='test-token').message
        self.assertEqual(m.type,'xray.proxy.hysteria.account.Account');self.assertEqual(m.value,b'\x0a\x0atest-token')
        self.assertIs(ProxyTypes.Hysteria.account_model,HysteriaAccount)
    def test_auth_is_redacted(self):
        self.assertEqual(_jsonable({'hysteria':self.settings})['hysteria']['auth'],'***')
    def test_nodes_filter_master_only_without_mutating_input(self):
        cfg={'inbounds':[{'tag':'h2','yukuMasterOnly':True},{'tag':'vless'}]}
        # _prepare_config only requires mapping/copy, not an active remote node.
        from copy import deepcopy
        class Config(dict):
            def copy(self):return Config(deepcopy(dict(self)))
        for node in (ReSTXRayNode, RPyCXRayNode):
            c=Config(cfg);r=node._prepare_config(None,c)
            self.assertEqual([i['tag'] for i in r['inbounds']],['vless']);self.assertEqual(len(c['inbounds']),2)
    def test_wrong_version_transport_and_cross_protocol_rejected(self):
        from app import xray
        tag=next(iter(xray.config.inbounds_by_tag))
        with self.assertRaises(ValidationError):
            UserCreate(username='cross_test',proxies={'vless':{}},inbounds={'vless':[tag]})
        cfg={'inbounds':[{'tag':'wrong','protocol':'hysteria','port':443,'settings':{'version':1}}],
             'outbounds':[{'tag':'direct','protocol':'freedom'}]}
        with self.assertRaises(ValueError):XRayConfig(cfg)

if __name__=='__main__':unittest.main()

import base64
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

_ORIGINAL_X402_PAY_TO = os.environ.pop('X402_PAY_TO', None)
os.environ.setdefault('STRIPE_SECRET_KEY', 'sk_test_dummy')

_CWD = None
_TMP = None


def setUpModule():
    global app_saas, m2m, _CWD, _TMP
    if 'app_saas' not in sys.modules:
        _CWD = os.getcwd()
        _TMP = tempfile.mkdtemp(prefix='omnicirelpc-m2m-test-')
        os.chdir(_TMP)
    import app_saas
    import m2m


def tearDownModule():
    if _TMP:
        os.chdir(_CWD)
        shutil.rmtree(_TMP, ignore_errors=True)
    if _ORIGINAL_X402_PAY_TO is not None:
        os.environ['X402_PAY_TO'] = _ORIGINAL_X402_PAY_TO


class M2MTests(unittest.TestCase):
    def setUp(self):
        app_saas.app.config['TESTING'] = True
        self.client = app_saas.app.test_client()
        self.original_wsgi_app = app_saas.app.wsgi_app
        self.original_m2m_config = {
            name: getattr(m2m, name)
            for name in (
                'X402_PAY_TO',
                'X402_PRICE',
                'X402_NETWORK',
                'X402_FACILITATOR_URL',
                '_paywall_installed',
            )
        }
        self.server = None
        self.server_thread = None

    def tearDown(self):
        app_saas.app.wsgi_app = self.original_wsgi_app
        for name, value in self.original_m2m_config.items():
            setattr(m2m, name, value)
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server_thread.join(timeout=2)

    def test_disabled_endpoints_and_robots(self):
        status = self.client.get('/api/m2m/status')
        self.assertEqual(status.status_code, 200)
        self.assertFalse(status.get_json()['enabled'])

        for path in ('/api/m2m/recaps', '/api/m2m/recaps/2026-W44'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.get_json()['error'], 'm2m_not_configured')

        robots = self.client.get('/robots.txt')
        self.assertEqual(robots.status_code, 200)
        self.assertIn('Disallow: /api/m2m', robots.get_data(as_text=True))

    def test_paywall_gates_only_m2m_recap_routes(self):
        class FacilitatorHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != '/supported':
                    self.send_error(404)
                    return
                body = json.dumps({
                    'kinds': [{
                        'x402Version': 2,
                        'scheme': 'exact',
                        'network': 'eip155:84532',
                    }],
                    'extensions': [],
                    'signers': {},
                }).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                pass

        self.server = HTTPServer(('127.0.0.1', 0), FacilitatorHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

        pay_to = '0x' + '1' * 40
        network = 'eip155:84532'
        m2m.X402_PAY_TO = pay_to
        m2m.X402_NETWORK = network
        m2m.X402_FACILITATOR_URL = f'http://127.0.0.1:{self.server.server_port}'

        self.assertTrue(m2m.install_paywall(app_saas.app))

        response = self.client.get('/api/m2m/recaps')
        self.assertEqual(response.status_code, 402)
        payment_required = response.headers.get('PAYMENT-REQUIRED')
        self.assertTrue(payment_required or response.get_data())
        if payment_required:
            try:
                payment_required = base64.b64decode(payment_required, validate=True).decode()
            except (ValueError, UnicodeDecodeError):
                pass
        payment_details = payment_required or ''
        payment_details += response.get_data(as_text=True)
        self.assertIn(pay_to, payment_details)
        self.assertIn(network, payment_details)

        status = self.client.get('/api/m2m/status')
        self.assertEqual(status.status_code, 200)
        self.assertTrue(status.get_json()['enabled'])

        self.assertEqual(self.client.get('/recaps').status_code, 200)

    def test_facilitator_without_network_leaks_nothing(self):
        class FacilitatorHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = json.dumps({
                    'kinds': [{'scheme': 'exact', 'network': 'eip155:84532'}],
                    'extensions': [],
                    'signers': {},
                }).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                pass

        self.server = HTTPServer(('127.0.0.1', 0), FacilitatorHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

        m2m.X402_PAY_TO = '0x' + '1' * 40
        # Réseau non supporté par ce facilitator -> install_paywall recalé.
        # Avant le fix : m2m_state() restait enabled=True sans middleware,
        # les routes servaient le JSON gratuitement. Maintenant : 503.
        m2m.X402_NETWORK = 'eip155:8453'
        m2m.X402_FACILITATOR_URL = f'http://127.0.0.1:{self.server.server_port}'

        self.assertFalse(m2m.install_paywall(app_saas.app))

        for path in ('/api/m2m/recaps', '/api/m2m/recaps/2026-W44'):
            self.assertEqual(self.client.get(path).status_code, 503)
        self.assertFalse(
            self.client.get('/api/m2m/status').get_json()['enabled'])

    def test_missing_x402_package_keeps_paywall_uninstalled(self):
        pay_to = '0x' + '1' * 40
        original_wsgi_app = app_saas.app.wsgi_app
        with patch.dict(sys.modules, {'x402': None}):
            self.assertIsNone(m2m._load_x402())
            with patch.object(m2m, 'X402_PAY_TO', pay_to):
                self.assertFalse(m2m.install_paywall(app_saas.app))
        self.assertIs(app_saas.app.wsgi_app, original_wsgi_app)


if __name__ == '__main__':
    unittest.main()

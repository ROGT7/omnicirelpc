import json
import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

_TMP = tempfile.mkdtemp(prefix='omnicirelpc-test-')
_CWD = os.getcwd()
os.chdir(_TMP)
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('STRIPE_SECRET_KEY', 'sk_test_dummy')
os.environ.setdefault('STRIPE_PUBLISHABLE_KEY', 'pk_test_dummy')
import app_saas  # noqa: E402

ADSENSE = 'ca-pub-7810870385090344'
PRIVATE_EMAIL = 'private-user@example.com'


def tearDownModule():
    os.chdir(_CWD)
    shutil.rmtree(_TMP, ignore_errors=True)


class PublicPagesTests(unittest.TestCase):
    def setUp(self):
        app_saas.app.config['TESTING'] = True
        self.client = app_saas.app.test_client()
        self.recaps = app_saas.list_recaps()
        self.assertTrue(self.recaps)
        conn = sqlite3.connect('users.db')
        conn.execute('INSERT OR IGNORE INTO users (email, password, plan) VALUES (?, ?, ?)',
                     (PRIVATE_EMAIL, 'x', 'premium'))
        conn.commit()
        conn.close()

    def test_robots_txt(self):
        res = self.client.get('/robots.txt')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.mimetype.startswith('text/plain'))
        body = res.get_data(as_text=True)
        self.assertIn('Sitemap: https://omnicirelpc.onrender.com/sitemap.xml', body)
        for path in ('/dashboard', '/alerts', '/premium', '/export', '/delete-account'):
            self.assertIn(f'Disallow: {path}\n', body)

    def test_sitemap_lists_public_pages_only(self):
        res = self.client.get('/sitemap.xml')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'application/xml')
        body = res.get_data(as_text=True)
        self.assertIn('<loc>https://omnicirelpc.onrender.com/recaps</loc>', body)
        for recap in self.recaps:
            self.assertIn(f"<loc>https://omnicirelpc.onrender.com/recaps/{recap['slug']}</loc>", body)
            self.assertIn(f"<lastmod>{recap['published']}</lastmod>", body)
        for path in app_saas.PRIVATE_PATHS + ['/login', '/register']:
            self.assertNotIn(f'onrender.com{path}<', body)

    def test_recaps_index(self):
        res = self.client.get('/recaps')
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn(ADSENSE, body)
        self.assertIn('name="viewport"', body)
        for recap in self.recaps:
            self.assertIn(f"/recaps/{recap['slug']}", body)

    def test_homepage_links_recaps(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('href="/recaps"', res.get_data(as_text=True))

    def test_each_recap_page(self):
        titles, descriptions = set(), set()
        for recap in self.recaps:
            res = self.client.get(f"/recaps/{recap['slug']}")
            self.assertEqual(res.status_code, 200)
            body = res.get_data(as_text=True)
            self.assertIn(ADSENSE, body)
            self.assertIn('name="viewport"', body)
            self.assertIn('<meta name="description"', body)
            self.assertIn(f"https://omnicirelpc.onrender.com/recaps/{recap['slug']}", body)
            self.assertIn('href="/recaps"', body)
            self.assertIn('href="/register"', body)
            self.assertIn('9,99 €/mois', body)
            self.assertIn('UTC', body)
            self.assertTrue(recap['sources'])
            for source in recap['sources']:
                self.assertTrue(source['url'].startswith('https://'))
            self.assertNotIn(PRIVATE_EMAIL, body)
            titles.add(recap['title'])
            descriptions.add(recap['description'])
        self.assertEqual(len(titles), len(self.recaps))
        self.assertEqual(len(descriptions), len(self.recaps))

    def test_recap_page_hides_session_data(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['email'] = PRIVATE_EMAIL
            sess['plan'] = 'premium'
        res = self.client.get(f"/recaps/{self.recaps[0]['slug']}")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn(PRIVATE_EMAIL, res.get_data(as_text=True))

    def test_unknown_or_invalid_slug_returns_404(self):
        for slug in ('2099-W01', '..%2Fapp_saas', 'abc', '2026-W41.json'):
            self.assertEqual(self.client.get(f'/recaps/{slug}').status_code, 404)

    def test_private_routes_still_require_login(self):
        for path in ('/dashboard', '/alerts', '/premium', '/export'):
            res = self.client.get(path)
            self.assertEqual(res.status_code, 302)
            self.assertIn('/login', res.headers['Location'])

    def test_external_strings_are_escaped(self):
        tmp = tempfile.mkdtemp()
        recap = {
            'title': '<script>alert(1)</script>', 'description': '"><img src=x>',
            'published': '2026-01-01', 'period_label': 'p', 'observed_at': 'o',
            'intro': '<b>x</b>', 'sections': [{'heading': 'h', 'paragraphs': ['<i>y</i>']}],
            'sources': [{'label': '<u>s</u>', 'url': 'https://example.com/?a=1&b="2"'}],
            'method': 'm',
        }
        with open(os.path.join(tmp, '2026-W01.json'), 'w', encoding='utf-8') as f:
            json.dump(recap, f)
        try:
            with patch.object(app_saas, 'RECAPS_DIR', tmp):
                body = self.client.get('/recaps/2026-W01').get_data(as_text=True)
                sitemap = self.client.get('/sitemap.xml').get_data(as_text=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        for raw in ('<script>alert(1)</script>', '<img src=x>', '<b>x</b>', '<i>y</i>', '<u>s</u>', 'b="2"'):
            self.assertNotIn(raw, body)
        self.assertIn('&lt;script&gt;', body)
        self.assertIn('/recaps/2026-W01</loc>', sitemap)


if __name__ == '__main__':
    unittest.main()

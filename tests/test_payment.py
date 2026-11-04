import os
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import stripe

_STATE = {}


def setUpModule():
    global app_saas
    _STATE['cwd'] = os.getcwd()
    _STATE['tmp'] = tempfile.mkdtemp(prefix='omnicirelpc-pay-test-')
    os.chdir(_STATE['tmp'])
    os.environ.setdefault('SECRET_KEY', 'test-secret-key')
    os.environ.setdefault('STRIPE_SECRET_KEY', 'sk_test_dummy')
    import app_saas
    app_saas.init_users_db()


def tearDownModule():
    os.chdir(_STATE['cwd'])
    shutil.rmtree(_STATE['tmp'], ignore_errors=True)


def checkout(**fields):
    data = {'id': 'cs_test_1', 'client_reference_id': '1', 'status': 'complete',
            'payment_status': 'paid', 'customer': 'cus_test_1', 'subscription': 'sub_test_1',
            'customer_details': {'email': 'u@example.com'}}
    data.update(fields)
    return stripe.checkout.Session.construct_from(data, 'sk_test_dummy')


class PaymentSuccessTests(unittest.TestCase):
    def setUp(self):
        app_saas.app.config['TESTING'] = True
        conn = sqlite3.connect('users.db')
        conn.execute('DELETE FROM users')
        conn.execute("INSERT INTO users (id, email, password, plan) VALUES (1, 'u@example.com', 'x', 'free')")
        conn.commit()
        conn.close()
        self.client = app_saas.app.test_client()
        with self.client.session_transaction() as s:
            s['user_id'] = 1
            s['email'] = 'u@example.com'
            s['plan'] = 'free'

    def user(self):
        conn = sqlite3.connect('users.db')
        row = conn.execute('SELECT plan, stripe_customer_id, stripe_subscription_id FROM users WHERE id = 1').fetchone()
        conn.close()
        return row

    def test_checkout_requests_session_id_and_reference(self):
        with patch.object(stripe.checkout.Session, 'create',
                          return_value=checkout(url='https://checkout.stripe.com/x')) as create:
            res = self.client.post('/create-checkout-session')
        self.assertEqual(res.status_code, 303)
        kwargs = create.call_args.kwargs
        self.assertEqual(kwargs['line_items'], [{'price': app_saas.PRICE_ID, 'quantity': 1}])
        self.assertTrue(kwargs['success_url'].endswith('/payment-success?session_id={CHECKOUT_SESSION_ID}'))
        self.assertEqual(kwargs['client_reference_id'], '1')

    @patch.object(stripe.checkout.Session, 'retrieve')
    def test_missing_session_id_does_not_upgrade(self, retrieve):
        res = self.client.get('/payment-success')
        self.assertEqual(res.headers['Location'], '/premium')
        retrieve.assert_not_called()
        self.assertEqual(self.user()[0], 'free')

    @patch.object(stripe.checkout.Session, 'retrieve', side_effect=stripe.error.InvalidRequestError('nope', 'id'))
    def test_unknown_session_does_not_upgrade(self, retrieve):
        res = self.client.get('/payment-success?session_id=cs_fake')
        self.assertEqual(res.headers['Location'], '/premium')
        self.assertEqual(self.user()[0], 'free')

    def test_unpaid_or_foreign_session_does_not_upgrade(self):
        for fields in ({'payment_status': 'unpaid'}, {'payment_status': 'no_payment_required'}, {'status': 'open'},
                       {'client_reference_id': '2'}, {'customer_details': {'email': 'other@example.com'}}):
            with patch.object(stripe.checkout.Session, 'retrieve', return_value=checkout(**fields)):
                res = self.client.get('/payment-success?session_id=cs_test_1')
            self.assertEqual(res.headers['Location'], '/premium', fields)
            self.assertEqual(self.user()[0], 'free', fields)

    def test_paid_session_upgrades_and_stores_customer(self):
        with patch.object(stripe.checkout.Session, 'retrieve', return_value=checkout()) as retrieve:
            res = self.client.get('/payment-success?session_id=cs_test_1')
        retrieve.assert_called_once_with('cs_test_1')
        self.assertEqual(res.headers['Location'], '/dashboard')
        self.assertEqual(self.user(), ('premium', 'cus_test_1', 'sub_test_1'))
        with self.client.session_transaction() as s:
            self.assertEqual(s['plan'], 'premium')


if __name__ == '__main__':
    unittest.main()

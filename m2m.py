"""API payante machine-to-machine (M2M) via le protocole x402.

Vend les récaps hebdo en JSON à des agents : paiement en USDC sur Base,
vérifié et réglé par un facilitator x402. Le rail est activé en posant
X402_PAY_TO (adresse EVM de réception des paiements). Sans elle, les routes
payantes répondent 503 — aucune donnée ne part gratuitement.

Variables d'environnement :
  X402_PAY_TO          adresse EVM recevant les paiements (requis)
  X402_PRICE           prix par requête (défaut "$0.05")
  X402_NETWORK         réseau CAIP-2 (défaut "eip155:84532" = Base Sepolia,
                       seul réseau EVM du facilitator gratuit x402.org ;
                       "eip155:8453" = Base mainnet via un facilitator CDP)
  X402_FACILITATOR_URL URL du facilitator (défaut https://x402.org/facilitator)

Le package `x402[flask,evm]` n'est requis que lorsque X402_PAY_TO est posé ;
il est importé paresseusement pour que l'app tourne sans lui.
"""

import os

X402_PAY_TO = os.environ.get('X402_PAY_TO', '')
X402_PRICE = os.environ.get('X402_PRICE', '$0.05')
# Le facilitator gratuit x402.org ne règle que Base Sepolia (eip155:84532).
# Pour de l'USDC réel : X402_NETWORK=eip155:8453 + X402_FACILITATOR_URL vers
# un facilitator mainnet (ex. CDP, auth par API key).
X402_NETWORK = os.environ.get('X402_NETWORK', 'eip155:84532')
X402_FACILITATOR_URL = os.environ.get('X402_FACILITATOR_URL', 'https://x402.org/facilitator')

PAID_PATTERNS = ['GET /api/m2m/recaps', 'GET /api/m2m/recaps/*']

# True uniquement quand install_paywall a réellement posé le middleware :
# m2m_state()['enabled'] doit refléter ça, sinon les routes servent le JSON
# gratuitement (ex. X402_NETWORK=eip155:8453 avec le facilitator gratuit
# x402.org, qui ne supporte que Sepolia -> /supported recalé, pas de paywall).
_paywall_installed = False


def _load_x402():
    """Importe x402 paresseusement ; None si le package est absent."""
    try:
        from x402 import x402ResourceServerSync
        from x402.http import (
            FacilitatorConfig,
            HTTPFacilitatorClientSync,
            PaymentOption,
            RouteConfig,
        )
        from x402.http.middleware import FlaskPaymentMiddleware
        from x402.mechanisms.evm.exact import ExactEvmServerScheme
    except ImportError:
        return None
    return {
        'x402ResourceServerSync': x402ResourceServerSync,
        'FacilitatorConfig': FacilitatorConfig,
        'HTTPFacilitatorClientSync': HTTPFacilitatorClientSync,
        'PaymentOption': PaymentOption,
        'RouteConfig': RouteConfig,
        'FlaskPaymentMiddleware': FlaskPaymentMiddleware,
        'ExactEvmServerScheme': ExactEvmServerScheme,
    }


def m2m_state():
    """État courant du rail M2M, exposé publiquement sur /api/m2m/status."""
    if not X402_PAY_TO:
        return {'enabled': False, 'reason': 'X402_PAY_TO not set'}
    if _load_x402() is None:
        return {'enabled': False, 'reason': 'x402[flask,evm] package not installed'}
    if not _paywall_installed:
        return {'enabled': False,
                'reason': 'paywall not installed (facilitator/network check failed)'}
    return {
        'enabled': True,
        'pay_to': X402_PAY_TO,
        'price': X402_PRICE,
        'network': X402_NETWORK,
        'facilitator': X402_FACILITATOR_URL,
    }


def _facilitator_supports(facilitator_url, network, scheme='exact'):
    """Vérifie via /supported que le facilitator règle scheme+network."""
    try:
        import httpx
        data = httpx.get(f"{facilitator_url.rstrip('/')}/supported",
                         timeout=15).json()
        return any(k.get('scheme') == scheme and k.get('network') == network
                   for k in data.get('kinds', []))
    except Exception:
        # Facilitator injoignable ou format inattendu : on laisse le
        # middleware décider (il loggue ses propres erreurs de config).
        return True


def install_paywall(app):
    """Installe le middleware x402 sur l'app Flask. No-op si non configuré.

    Retourne True si le paywall est actif.
    """
    if not X402_PAY_TO:
        return False
    x402 = _load_x402()
    if x402 is None:
        app.logger.warning('x402 package missing: paid M2M routes stay disabled')
        return False

    facilitator = x402['HTTPFacilitatorClientSync'](
        x402['FacilitatorConfig'](url=X402_FACILITATOR_URL)
    )
    if not _facilitator_supports(X402_FACILITATOR_URL, X402_NETWORK):
        app.logger.error(
            'x402: facilitator %s ne supporte pas scheme=exact sur %s '
            '(le gratuit x402.org ne règle que eip155:84532) — paywall désactivé',
            X402_FACILITATOR_URL, X402_NETWORK)
        return False
    server = x402['x402ResourceServerSync'](facilitator)
    server.register(X402_NETWORK, x402['ExactEvmServerScheme']())

    routes = {
        pattern: x402['RouteConfig'](
            accepts=x402['PaymentOption'](
                scheme='exact',
                pay_to=X402_PAY_TO,
                price=X402_PRICE,
                network=X402_NETWORK,
            ),
            description='Weekly crypto market recap data as JSON',
            mime_type='application/json',
        )
        for pattern in PAID_PATTERNS
    }
    x402['FlaskPaymentMiddleware'](app, routes, server)
    global _paywall_installed
    _paywall_installed = True
    app.logger.info(
        'x402 paywall active: %s on %s -> %s', X402_PRICE, X402_NETWORK, X402_PAY_TO
    )
    return True

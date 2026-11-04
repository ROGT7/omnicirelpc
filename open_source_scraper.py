"""
SCRAPER OPEN SOURCE POUR OMNICIRELPC
Remplacement des APIs payantes par du scraping open source
"""

import requests
import feedparser
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
import re
import sqlite3
import os
from typing import List, Dict, Any, Optional, Tuple

class OpenSourceDataCollector:
    """Collecteur de données open source sans API token"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # Anti-spam simple pour CoinGecko (après un 429, on attend un peu avant de rappeler)
        self.coingecko_block_until = 0.0
        self.reddit_block_until = 0.0

        # Dictionnaire des descriptions des cryptomonnaies principales
        self.crypto_descriptions = {
            'BTC': 'Bitcoin - La première cryptomonnaie décentralisée, créée en 2009 par Satoshi Nakamoto. Considérée comme une réserve de valeur numérique et de l\'or digital.',
            'ETH': 'Ethereum - Plateforme de contrats intelligents qui permet la création d\'applications décentralisées (dApps) et de tokens NFT. Utilise le mécanisme de preuve de participation (Proof of Stake).',
            'SOL': 'Solana - Blockchain haute performance conçue pour les applications décentralisées et les crypto-monnaies. Connue pour sa rapidité et ses faibles coûts de transaction.',
            'XRP': 'XRP - Cryptomonnaie conçue pour les paiements transfrontaliers rapides et peu coûteux. Développée par Ripple Labs pour les institutions financières.',
            'BNB': 'Binance Coin - Token natif de l\'échange Binance, utilisé pour payer les frais de transaction et participer aux ventes de tokens sur la plateforme Binance.',
            'DOGE': 'Dogecoin - Cryptomonnaie créée comme une blague en 2013, devenue populaire grâce à son communauté et au soutien de célébrités comme Elon Musk.',
            'ADA': 'Cardano - Plateforme de contrats intelligents basée sur une approche scientifique et philosophique, développée par Charles Hoskinson (co-fondateur d\'Ethereum).',
            'AVAX': 'Avalanche - Plateforme de contrats intelligents qui se concentre sur la scalabilité, la sécurité et la décentralisation. Utilise un consensus Proof of Stake.',
            'DOT': 'Polkadot - Protocole qui permet le transfert de données et d\'actifs entre différentes blockchains. Créé par Gavin Wood (co-fondateur d\'Ethereum).',
            'MATIC': 'Polygon - Solution de scalabilité pour Ethereum qui permet des transactions plus rapides et moins chères tout en maintenant la sécurité d\'Ethereum.',
            'LINK': 'Chainlink - Réseau d\'oracles décentralisés qui connecte les contrats intelligents aux données du monde réel. Essentiel pour les DeFi.',
            'UNI': 'Uniswap - Protocole d\'échange décentralisé (DEX) construit sur Ethereum. Pionnier des automated market makers (AMM).',
            'LTC': 'Litecoin - Créée en 2011 par Charlie Lee, considérée comme l\'argent numérique par rapport à l\'or numérique (Bitcoin). Transactions plus rapides.',
            'ATOM': 'Cosmos - Écosystème de blockchains interconnectées qui permet la communication entre différentes chaînes. "Internet des blockchains".',
            'NEAR': 'NEAR Protocol - Plateforme de contrats intelligents axée sur la convivialité et la scalabilité. Utilise un mécanisme de sharding.',
            'ALGO': 'Algorand - Blockchain Proof of Stake qui se concentre sur la décentralisation, la sécurité et la scalabilité. Fondée par Silvio Micali.',
            'VET': 'VeChain - Plateforme blockchain spécialisée dans la gestion de la chaîne d\'approvisionnement et les solutions IoT.',
            'ICP': 'Internet Computer - Blockchain qui vise à étendre les fonctionnalités d\'Internet pour permettre des sites web et applications décentralisés.',
            'FIL': 'Filecoin - Réseau de stockage décentralisé qui permet aux utilisateurs de louer leur espace disque non utilisé. Complément d\'IPFS.',
            'TRX': 'TRON - Plateforme blockchain axée sur le divertissement et le partage de contenu. Fondée par Justin Sun.',
            'HT': 'Huobi Token - Token natif de l\'échange Huobi, utilisé pour réduire les frais de transaction et accéder à des services premium.',
            'MKR': 'MakerDAO - Protocole DeFi qui émet le stablecoin DAI. MKR est le token de gouvernance du système.',
            'COMP': 'Compound - Protocole DeFi de prêt et d\'emprunt décentralisé. COMP est le token de gouvernance.',
            'SUSHI': 'SushiSwap - Fork d\'Uniswap avec des fonctionnalités supplémentaires comme le staking et la gouvernance.',
            'YFI': 'Yearn Finance - Agrégateur de protocoles DeFi qui optimise les rendements pour les utilisateurs. Pionnier du "yield farming".',
            'AAVE': 'Aave - Protocole de prêt et d\'emprunt décentralisé. Innovateur des "flash loans".',
            'SNX': 'Synthetix - Plateforme qui permet la création d\'actifs synthétiques sur blockchain.',
            'CRV': 'Curve - Protocole DAX spécialisé dans l\'échange de stablecoins avec faible slippage.',
            'RUNE': 'THORChain - Protocole de liquidité inter-chaînes qui permet l\'échange direct entre différentes blockchains.',
            'KSM': 'Kusama - Réseau de test pour Polkadot, mais avec son propre écosystème. "Canary network" de Polkadot.',
            'EGLD': 'Elrond - Blockchain haute performance avec sharding stateful. Renommée en MultiversX.',
            'FTM': 'Fantom - Blockchain rapide et peu coûteuse pour les dApps. Utilise un consensus DAG.',
            'ONE': 'Harmony - Blockchain qui utilise le sharding pour atteindre une grande scalabilité.',
            'CELO': 'Celo - Plateforme blockchain mobile-first pour les paiements et les services financiers décentralisés.',
            'AR': 'Arweave - Réseau de stockage permanent et décentralisé. "Disque dur permanent".',
            'KAVA': 'Kava - Plateforme DeFi qui offre des prêts et des services financiers sur plusieurs blockchains.',
            'ZEC': 'Zcash - Cryptomonnaie axée sur la confidentialité avec des transactions anonymes optionnelles (zk-SNARKs).',
            'DASH': 'Dash - Cryptomonnaie axée sur la confidentialité avec des transactions instantanées (InstantSend).',
            'ENJ': 'Enjin Coin - Plateforme pour les actifs de jeu et les NFT dans l\'écosystème du gaming.',
            'MANA': 'Decentraland - Monde virtuel décentralisé où les utilisateurs peuvent acheter des terrains et créer des expériences.',
            'SAND': 'The Sandbox - Plateforme de gaming et de métaverse basée sur Ethereum où les utilisateurs peuvent créer et monétiser des expériences.',
            'CHZ': 'Chiliz - Plateforme de tokenisation sportive pour les clubs et les fans de sport.',
            'AXS': 'Axie Infinity - Jeu blockchain où les joueurs collectionnent et font combattre des créatures appelées Axies.',
            'GALA': 'Gala Games - Plateforme de gaming blockchain qui permet aux joueurs de posséder leurs actifs de jeu.',
            'LUNA': 'Terra Classic - Ancienne blockchain Terra qui a subi un effondrement en mai 2022. Maintenant une communauté décentralisée.',
            'USTC': 'TerraUSD Classic - Ancien stablecoin algorithmique de Terra, maintenant maintenu par la communauté.',
            'SHIB': 'Shiba Inu - Meme coin inspiré de Dogecoin avec son propre écosystème DeFi (ShibaSwap).',
            'FTT': 'FTX Token - Token natif de l\'échange FTX (maintenant en faillite). Historique important dans l\'écosystème crypto.',
            'GMT': 'StepN - Application "move-to-earn" où les utilisateurs gagnent des crypto-monnaies en marchant ou courant.',
            'APE': 'ApeCoin - Token de gouvernance pour l\'écosystème Bored Ape Yacht Club et les projets Yuga Labs.',
            'GRT': 'The Graph - Protocole d\'indexation décentralisé pour les données blockchain, comme Google pour les blockchains.',
            'HNT': 'Helium - Réseau décentralisé d\'IoT et de téléphonie utilisant la preuve de couverture.',
            'STX': 'Stacks - Smart contracts sur Bitcoin. Permet les dApps et les NFTs sécurisés par le réseau Bitcoin.',
            'MINA': 'Mina Protocol - Blockchain la plus légère au monde avec une taille constante de 22KB grâce aux zk-SNARKs.',
            'ROSE': 'Oasis Network - Blockchain axée sur la confidentialité et les applications décentralisées confidentielles.',
            'CELR': 'Celer Network - Plateforme de solutions de scalabilité inter-chaînes et de rollups optimistes.',
            'INJ': 'Injective Protocol - Plateforme d\'échange décentralisée avec des produits financiers dérivés.',
            'OCEAN': 'Ocean Protocol - Plateforme pour le partage et la monétisation de données décentralisées.',
            'RSR': 'Reserve - Protocole pour les systèmes de paiement stables et les tokenisation d\'actifs.',
            'BAL': 'Balancer - Protocole DAX avec des pools pondérés personnalisables et la gestion de portefeuille automatisée.',
            'LRC': 'Loopring - Solution de scalabilité pour les échanges décentralisés avec zkRollups.',
            'QTUM': 'Qtum - Plateforme hybride qui combine la technologie Bitcoin avec la flexibilité des contrats intelligents d\'Ethereum.',
            'KNC': 'Kyber Network - Protocole de liquidité décentralisé pour les échanges instantanés de tokens.',
            'ZRX': '0x - Protocole d\'échange décentralisé construit sur Ethereum avec des relais décentralisés.',
            'BAND': 'Band Protocol - Réseau d\'oracles décentralisés similaire à Chainlink, avec un focus sur l\'Asie.',
            'RVN': 'Ravencoin - Blockchain spécialisée dans le transfert d\'actifs et la création de tokens personnalisés.',
            'HOT': 'Holo - Plateforme de cloud computing décentralisé basée sur la technologie Holochain.',
            'LRC': 'Loopring - Solution de scalabilité Layer-2 pour les échanges décentralisés utilisant zkRollups.',
            'KMD': 'Komodo - Plateforme blockchain avec des fonctionnalités de confidentialité et d\'atomic swaps.',
            'REN': 'Ren - Protocole qui permet le transfert d\'actifs entre différentes blockchains.',
            'CRO': 'Cronos - Ecosystème Crypto.com avec sa blockchain et sa carte de paiement crypto.',
            'WAXP': 'WAX - Worldwide Asset eXchange - Spécialisé dans les NFTs et le gaming sur blockchain.',
            'BAT': 'Basic Attention Token - Token qui récompense les utilisateurs pour leur attention dans le navigateur Brave.',
            'DCR': 'Decred - Cryptomonnaie axée sur la gouvernance décentralisée et le financement par la communauté.',
            'WAVES': 'Waves - Plateforme blockchain pour les applications décentralisées et les tokens personnalisés.',
            'ZIL': 'Zilliqa - Blockchain haute performance utilisant le sharding pour la scalabilité.',
            'NEXO': 'Nexo - Plateforme de prêt crypto avec des cartes de paiement et des services financiers.',
            'BNT': 'Bancor - Protocole DAX pionnier avec le mécanisme de liquidité automatique.',
            'MLN': 'Melon Protocol - Plateforme de gestion de portefeuille décentralisée.',
            'CVC': 'Civic - Plateforme d\'identité numérique décentralisée et vérification d\'identité.',
            'GNO': 'Gnosis - Plateforme de prédiction décentralisée et infrastructure pour les marchés prédictifs.',
            'RLC': 'iExec - Plateforme de cloud computing décentralisé pour les applications d\'IA et les calculs intensifs.',
            'KDA': 'Kadena - Blockchain commerciale avec des transactions par chaîne et un langage de contrat intelligent.',
            'ARPA': 'ARPA - Réseau de calcul multipartite sécurisé et de génération de nombres aléatoires.',
            'STRAX': 'Stratis - Plateforme blockchain B2B avec des solutions pour les entreprises.',
            'LOOM': 'Loom Network - Plateforme de gaming et de réseaux sociaux sur blockchain.',
            'XEM': 'NEM - Blockchain avec des fonctionnalités uniques comme la preuve d\'importance et les mosaïques.',
            'HOT': 'Holo - Infrastructure de cloud computing décentralisé basée sur Holochain.',
            'FUN': 'FunFair - Plateforme de gaming et de casino décentralisé avec des transactions transparentes.',
            'MITH': 'Mithril - Réseau social décentralisé avec des récompenses en crypto-monnaie.',
            'QKC': 'QuarkChain - Blockchain haute performance avec un sharding à deux couches.',
            'SC': 'Siacoin - Réseau de stockage décentralisé similaire à Filecoin mais plus ancien.',
            'NPXS': 'Pundi X - Plateforme de paiement crypto avec des terminaux de paiement physiques.',
            'XVG': 'Verge - Cryptomonnaie axée sur la confidentialité avec plusieurs algorithmes de minage.',
            'DGB': 'Digibyte - Blockchain rapide et sécurisée avec plusieurs algorithmes et une adoption mondiale.',
            'SYS': 'Syscoin - Plateforme de commerce électronique décentralisé avec des fonctionnalités de marché.',
            'STORJ': 'Storj - Réseau de stockage décentralisé similaire à Sia mais avec une architecture différente.',
            'VTHO': 'VeChainThor - Token d\'énergie utilisé pour les transactions sur le réseau VeChain.',
            'ONG': 'Ontology Gas - Token utilisé pour les transactions sur la blockchain Ontology.',
            'DATA': 'Streamr - Plateforme de streaming de données en temps réel décentralisée.',
            'ETC': 'Ethereum Classic - Version originale d\'Ethereum après le hard fork de The DAO.',
            'ZRX': '0x - Protocole d\'échange décentralisé avec des relais et des tokens de gouvernance.',
            'ANT': 'Aragon - Plateforme pour la création et la gestion d\'organisations autonomes décentralisées (DAOs).',
            'REP': 'Augur - Plateforme de prédiction décentralisée sur les événements du monde réel.',
            'GNT': 'Golem - Réseau de calcul distribué pour le cloud computing décentralisé.',
            'BTS': 'BitShares - Plateforme d\'échange décentralisé et de monnaie numérique.',
            'KNC': 'Kyber Network - Protocole de liquidité décentralisé pour les échanges instantanés.',
            'PNK': 'Kleros - Protocole d\'arbitrage décentralisé pour les disputes en ligne.',
            'MLN': 'Melon - Plateforme de gestion de portefeuille décentralisée sur Ethereum.',
            'RCN': 'Ripio Credit Network - Protocole de prêt décentralisé basé sur le crédit.',
            'WTC': 'Waltonchain - Plateforme IoT avec intégration blockchain pour la chaîne d\'approvisionnement.',
            'POA': 'POA Network - Blockchain autorisée pour les applications d\'entreprise.',
            'QSP': 'Quantstamp - Protocole d\'audit de contrats intelligents décentralisé.',
            'LRC': 'Loopring - Protocole d\'échange décentralisé Layer-2 avec zkRollups.',
            'MCO': 'Monaco - Carte de paiement crypto avec des récompenses en tokens.',
            'ICN': 'Iconomi - Plateforme de gestion d\'actifs numériques et d\'indices crypto.',
            'WINGS': 'Wings - Plateforme de crowdfunding et de gestion de projets DAO.',
            'RLC': 'iExec - Plateforme de cloud computing décentralisé pour l\'IA et les calculs intensifs.',
            'HUM': 'Humaniq - Plateforme bancaire décentralisée pour les non-bancarisés.',
            'XMR': 'Monero - Cryptomonnaie axée sur la confidentialité absolue avec des transactions anonymes non traçables.',
            'USDT': 'Tether - Le plus grand stablecoin, indexé sur le dollar américain avec réserves de garantie.',
            'USDC': 'USD Coin - Stablecoin indexé sur le dollar américain, développé par Coinbase et Circle.',
            'BUSD': 'Binance USD - Stablecoin indexé sur le dollar américain, régulé et émis par Binance.',
            'DAI': 'Dai - Stablecoin algorithmique sur-collatéralisé maintenu par MakerDAO.',
            'USDP': 'Pax Dollar - Stablecoin indexé sur le dollar américain et régulé par Paxos.',
            'TUSD': 'TrueUSD - Stablecoin indexé sur le dollar américain avec audits réguliers des réserves.',
            'FDUSD': 'First Digital USD - Stablecoin indexé sur le dollar américain développé par First Digital.',
            'USDE': 'Ethena USDe - Stablecoin synthétique indexé sur le dollar américain avec rendement intégré.',
            'PYUSD': 'PayPal USD - Stablecoin indexé sur le dollar américain émis par PayPal.',
            'EUR': 'EUR Stablecoin - Stablecoin indexé sur l\'euro pour les transactions européennes.',
            'GBP': 'GBP Stablecoin - Stablecoin indexé sur la livre sterling britannique.',
            'JPY': 'JPY Stablecoin - Stablecoin indexé sur le yen japonais.',
            'CHF': 'CHF Stablecoin - Stablecoin indexé sur le franc suisse.',
            'AUD': 'AUD Stablecoin - Stablecoin indexé sur le dollar australien.',
            'CAD': 'CAD Stablecoin - Stablecoin indexé sur le dollar canadien.',
            'CNY': 'CNY Stablecoin - Stablecoin indexé sur le yuan chinois.',
            'INR': 'INR Stablecoin - Stablecoin indexé sur la roupie indienne.',
            'SGD': 'SGD Stablecoin - Stablecoin indexé sur le dollar singapourien.',
            'HKD': 'HKD Stablecoin - Stablecoin indexé sur le dollar de Hong Kong.',
            'NZD': 'NZD Stablecoin - Stablecoin indexé sur le dollar néo-zélandais.',
            'SEK': 'SEK Stablecoin - Stablecoin indexé sur la couronne suédoise.',
            'NOK': 'NOK Stablecoin - Stablecoin indexé sur la couronne norvégienne.',
            'DKK': 'DKK Stablecoin - Stablecoin indexé sur la couronne danoise.',
            'PLN': 'PLN Stablecoin - Stablecoin indexé sur le zloty polonais.',
            'CZK': 'CZK Stablecoin - Stablecoin indexé sur la couronne tchèque.',
            'HUF': 'HUF Stablecoin - Stablecoin indexé sur le forint hongrois.',
            'RON': 'RON Stablecoin - Stablecoin indexé sur le leu roumain.',
            'BGN': 'BGN Stablecoin - Stablecoin indexé sur le lev bulgare.',
            'HRK': 'HRK Stablecoin - Stablecoin indexé sur la kuna croate.',
            'RUB': 'RUB Stablecoin - Stablecoin indexé sur le rouble russe.',
            'TRY': 'TRY Stablecoin - Stablecoin indexé sur la livre turque.',
            'ZAR': 'ZAR Stablecoin - Stablecoin indexé sur le rand sud-africain.',
            'MXN': 'MXN Stablecoin - Stablecoin indexé sur le peso mexicain.',
            'BRL': 'BRL Stablecoin - Stablecoin indexé sur le real brésilien.',
            'CLP': 'CLP Stablecoin - Stablecoin indexé sur le peso chilien.',
            'PEN': 'PEN Stablecoin - Stablecoin indexé sur le sol péruvien.',
            'COP': 'COP Stablecoin - Stablecoin indexé sur le peso colombien.',
            'VES': 'VES Stablecoin - Stablecoin indexé sur le bolívar vénézuélien.',
            'ARS': 'ARS Stablecoin - Stablecoin indexé sur le peso argentin.',
            'UYU': 'UYU Stablecoin - Stablecoin indexé sur le peso uruguayen.',
            'PYG': 'PYG Stablecoin - Stablecoin indexé sur le guarani paraguayen.',
            'BOB': 'BOB Stablecoin - Stablecoin indexé sur le bolivien bolivien.',
            'SVC': 'SVC Stablecoin - Stablecoin indexé sur le colon salvadorien.',
            'GTQ': 'GTQ Stablecoin - Stablecoin indexé sur le quetzal guatémaltèque.',
            'HNL': 'HNL Stablecoin - Stablecoin indexé sur le lempira hondurien.',
            'NIO': 'NIO Stablecoin - Stablecoin indexé sur le córdoba nicaraguayen.',
            'CRC': 'CRC Stablecoin - Stablecoin indexé sur le colon costaricien.',
            'PAB': 'PAB Stablecoin - Stablecoin indexé sur le balboa panaméen.',
            'DOP': 'DOP Stablecoin - Stablecoin indexé sur le peso dominicain.',
            'JMD': 'JMD Stablecoin - Stablecoin indexé sur le dollar jamaïcain.',
            'TTD': 'TTD Stablecoin - Stablecoin indexé sur le dollar trinidadien.',
            'BSD': 'BSD Stablecoin - Stablecoin indexé sur le dollar bahaméen.',
            'BBD': 'BBD Stablecoin - Stablecoin indexé sur le dollar barbadien.',
            'XCD': 'XCD Stablecoin - Stablecoin indexé sur le dollar des Caraïbes orientales.',
            'TTD': 'TTD Stablecoin - Stablecoin indexé sur le dollar trinidadien.',
            'JMD': 'JMD Stablecoin - Stablecoin indexé sur le dollar jamaïcain.',
            'BZD': 'BZD Stablecoin - Stablecoin indexé sur le dollar bélizien.',
            'GYD': 'GYD Stablecoin - Stablecoin indexé sur le dollar guyanien.',
            'SRD': 'SRD Stablecoin - Stablecoin indexé sur le dollar surinamais.',
            'AWG': 'AWG Stablecoin - Stablecoin indexé sur le florin arubais.',
            'ANG': 'ANG Stablecoin - Stablecoin indexé sur le florin néerlandais.',
            'CUP': 'CUP Stablecoin - Stablecoin indexé sur le peso cubain.',
            'CUC': 'CUC Stablecoin - Stablecoin indexé sur le peso cubain convertible.',
            'HTG': 'HTG Stablecoin - Stablecoin indexé sur la gourde haïtienne.',
            'XOF': 'XOF Stablecoin - Stablecoin indexé sur le franc CFA BCEAO.',
            'XAF': 'XAF Stablecoin - Stablecoin indexé sur le franc CFA BEAC.',
            'XPF': 'XPF Stablecoin - Stablecoin indexé sur le franc pacifique.',
            'XAU': 'XAU Stablecoin - Stablecoin indexé sur l\'or.',
            'XAG': 'XAG Stablecoin - Stablecoin indexé sur l\'argent.',
            'XPT': 'XPT Stablecoin - Stablecoin indexé sur le platine.',
            'XPD': 'XPD Stablecoin - Stablecoin indexé sur le palladium.'
        }

    def _get_profile_db_conn(self):
        """Retourne une connexion SQLite pour stocker les profils de coins."""
        if not hasattr(self, '_profile_db_conn') or self._profile_db_conn is None:
            db_path = os.path.join(os.path.dirname(__file__), "omnicirelpc.db")
            try:
                conn = sqlite3.connect(db_path, check_same_thread=False)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS coin_profiles (
                        symbol TEXT PRIMARY KEY,
                        profile TEXT
                    )
                """)
                conn.commit()
                self._profile_db_conn = conn
            except Exception as e:
                print(f"[ERREUR] Impossible d'initialiser la base des profils de coins: {e}")
                self._profile_db_conn = None
        return self._profile_db_conn
    
    def generate_crypto_description(self, symbol: str, price: float, change_24h: float, volume: float) -> str:
        """Génère une description lisible pour n'importe quelle crypto.
        - Utilise d'abord une API open source (CoinGecko) pour récupérer une description
          fondamentale (à quoi sert la coin, sur quoi elle tourne, etc.).
        - Ajoute ensuite les infos dynamiques de prix / variation / volume.
        - Si l'API ne renvoie rien, génère une description 100% automatique basée sur les chiffres.
        """

        base_desc = self.fetch_coin_profile(symbol)

        # Direction de la tendance
        if change_24h > 15:
            trend = "en forte hausse"
        elif change_24h > 5:
            trend = "en hausse"
        elif change_24h > 1:
            trend = "en légère hausse"
        elif change_24h < -15:
            trend = "en forte baisse"
        elif change_24h < -5:
            trend = "en baisse"
        elif change_24h < -1:
            trend = "en légère baisse"
        else:
            trend = "relativement stable"

        # Niveau de volume
        if volume > 100_000_000:
            volume_str = "un volume de trading très élevé"
        elif volume > 10_000_000:
            volume_str = "un volume de trading élevé"
        elif volume > 1_000_000:
            volume_str = "un volume de trading modéré"
        else:
            volume_str = "un volume de trading plus limité"

        market_part = (
            f"Actuellement, {symbol} s'échange autour de ${price:,.2f} "
            f"avec une variation de {change_24h:+.2f}% sur 24h. "
            f"Le marché la considère {trend}, avec {volume_str} "
            f"(environ ${volume:,.0f} échangés sur 24h)."
        )

        if base_desc:
            # Description fondamentale issue de l'API + situation de marché
            return f"{base_desc} {market_part}"
        else:
            # Coin sans profil API: description purement automatique
            return (
                f"{symbol} est une cryptomonnaie {trend}, "
                f"actuellement échangée autour de ${price:,.2f} "
                f"avec {volume_str} (≈ ${volume:,.0f} sur 24h, "
                f"variation {change_24h:+.2f}% sur 24h)."
            )

    def fetch_coin_profile(self, symbol: str) -> Optional[str]:
        """Récupère une description fondamentale depuis une API open source (CoinGecko).
        Retourne une courte phrase expliquant à quoi sert la coin, si disponible.
        """
        try:
            # Limiteur de taux interne pour CoinGecko
            # Objectif: ~50 profils par fenêtre de 20s max
            if not hasattr(self, 'profile_rate'):
                self.profile_rate = {'count': 0, 'reset_time': time.time()}
            now = time.time()
            window = 20.0
            limit = 50

            elapsed = now - self.profile_rate['reset_time']
            if elapsed > window:
                # Nouvelle fenêtre
                self.profile_rate = {'count': 0, 'reset_time': now}
            elif self.profile_rate['count'] >= limit:
                # Trop d'appels dans la fenêtre: attendre la fin de la fenêtre
                sleep_time = window - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                self.profile_rate = {'count': 0, 'reset_time': time.time()}

            # Cache en mémoire pour éviter de rappeler l'API pour le même symbole
            if not hasattr(self, 'coin_profile_cache'):
                self.coin_profile_cache: Dict[str, str] = {}
            sym = symbol.lower()
            if sym in self.coin_profile_cache:
                return self.coin_profile_cache[sym]

            # Vérifier d'abord dans la base SQLite coin_profiles
            conn = self._get_profile_db_conn()
            if conn is not None:
                try:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT profile FROM coin_profiles WHERE symbol = ?",
                        (symbol.upper(),)
                    )
                    row = cur.fetchone()
                    if row and row[0]:
                        profile = row[0]
                        self.coin_profile_cache[sym] = profile
                        return profile
                except Exception as db_err:
                    print(f"[ERREUR] Erreur lecture coin_profiles pour {symbol}: {db_err}")

            self.profile_rate['count'] += 1

            # 1) Rechercher le coin par symbole / nom
            search_url = "https://api.coingecko.com/api/v3/search"
            resp = self.session.get(search_url, params={"query": symbol}, timeout=10)
            if resp.status_code != 200:
                return None

            data = resp.json()
            coins = data.get("coins", [])
            if not coins:
                return None

            best: Optional[Dict[str, Any]] = None
            for c in coins:
                if c.get("symbol", "").lower() == sym:
                    best = c
                    break
            if best is None:
                best = coins[0]

            coin_id = best.get("id")
            if not coin_id:
                return None

            # 2) Récupérer les détails du coin (sans market_data pour limiter la charge)
            info_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            params = {
                "localization": "false",
                "tickers": "false",
                "market_data": "false",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false",
            }
            resp2 = self.session.get(info_url, params=params, timeout=10)
            if resp2.status_code != 200:
                return None

            info = resp2.json()
            # Description en français si dispo, sinon anglais
            desc = info.get("description", {}).get("fr") or info.get("description", {}).get("en")
            desc_clean = ""
            if desc:
                desc_clean = re.sub(r'<[^>]+>', '', desc).strip()
                if len(desc_clean) > 400:
                    cut = desc_clean[:400]
                    if "." in cut:
                        cut = cut[:cut.rfind(".") + 1]
                    desc_clean = cut

            categories = info.get("categories") or []
            cat_part = ""
            if categories:
                cat_part = " Catégories principales : " + ", ".join(categories[:3]) + "."

            profile = (desc_clean + cat_part).strip()
            if not profile:
                return None

            # Sauvegarder le profil dans la base coin_profiles pour réutilisation future
            conn = self._get_profile_db_conn()
            if conn is not None:
                try:
                    conn.execute(
                        "INSERT OR REPLACE INTO coin_profiles (symbol, profile) VALUES (?, ?)",
                        (symbol.upper(), profile)
                    )
                    conn.commit()
                except Exception as db_err:
                    print(f"[ERREUR] Erreur écriture coin_profiles pour {symbol}: {db_err}")

            self.coin_profile_cache[sym] = profile
            return profile

        except Exception as e:
            print(f"[ERREUR] Erreur profil CoinGecko pour {symbol}: {e}")
            return None
    
    def get_crypto_data(self) -> List[Dict]:
        """Récupère les données crypto.

        1) Essaye d'abord l'API publique Binance.
        2) Si Binance est indisponible (par ex. 451 géo-bloqué), fallback sur CoinGecko
           avec un seul appel `coins/markets` pour éviter les timeouts.
        """

        def score_crypto(item: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
            """Calcule un score de pertinence et enrichit avec ratios."""
            price = item.get("price") or 0.0
            change = item.get("change_24h") or 0.0
            market_cap = item.get("market_cap") or 0.0
            volume = item.get("volume") or 0.0
            rank = item.get("rank") or 9999
            vol_mcap = (volume / market_cap) if market_cap else 0.0
            ath = item.get("ath") or 0.0
            atl = item.get("atl") or 0.0
            distance_ath = ((ath - price) / ath * 100) if ath else 0.0
            distance_atl = ((price - atl) / price * 100) if atl else 0.0

            change_score = min(abs(change) / 5.0, 4.0)   # max 4
            vol_score = min(vol_mcap * 2.0, 3.0)         # max 3
            rank_score = 2.5 if rank <= 50 else 1.2 if rank <= 200 else 0.6
            score = change_score * 0.5 + vol_score * 0.3 + rank_score * 0.2

            item["vol_mcap"] = vol_mcap
            item["distance_ath_pct"] = distance_ath
            item["distance_atl_pct"] = distance_atl
            item["score"] = round(score, 3)
            return score, item

        def fetch_cg_enrichment(symbol: str) -> Tuple[float, Optional[int], Optional[float], Optional[float]]:
            """Récupère market cap, rank, ATH, ATL via CoinGecko pour un symbole donné."""
            try:
                now = time.time()
                if now < getattr(self, "coingecko_block_until", 0.0):
                    # CoinGecko récemment bloqué, on saute pour éviter 429
                    return 0.0, None, None, None

                search_resp = self.session.get(
                    "https://api.coingecko.com/api/v3/search",
                    params={"query": symbol},
                    timeout=10,
                )
                if search_resp.status_code != 200:
                    if search_resp.status_code == 429:
                        self.coingecko_block_until = time.time() + 60.0
                    print(f"[DEBUG] CoinGecko search status {search_resp.status_code} pour {symbol}")
                    return 0.0, None, None, None
                search_data = search_resp.json()
                cg_id = None
                for coin in search_data.get("coins", []):
                    if (coin.get("symbol") or "").lower() == symbol.lower():
                        cg_id = coin.get("id")
                        break
                if not cg_id:
                    return 0.0, None, None, None

                markets_resp = self.session.get(
                    "https://api.coingecko.com/api/v3/coins/markets",
                    params={
                        "vs_currency": "usd",
                        "ids": cg_id,
                        "order": "market_cap_desc",
                        "sparkline": "false",
                        "per_page": 1,
                        "page": 1,
                    },
                    timeout=10,
                )
                if markets_resp.status_code != 200:
                    if markets_resp.status_code == 429:
                        self.coingecko_block_until = time.time() + 60.0
                    print(f"[DEBUG] CoinGecko markets status {markets_resp.status_code} pour {symbol}")
                    return 0.0, None, None, None
                mkts = markets_resp.json()
                if not isinstance(mkts, list) or not mkts:
                    return 0.0, None, None, None
                m = mkts[0]
                market_cap = float(m.get("market_cap") or 0)
                rank = m.get("market_cap_rank") or None
                ath = float(m.get("ath") or 0)
                atl = float(m.get("atl") or 0)
                return market_cap, rank, ath, atl
            except Exception as e:
                print(f"[DEBUG] CoinGecko enrichment error {symbol}: {e}")
                return 0.0, None, None, None

        # 1) Tentative Binance + enrichissement CoinGecko pour market cap/ATH/ATL manquants
        try:
            crypto_list: List[Dict] = []

            url = "https://api.binance.com/api/v3/ticker/24hr"
            response = self.session.get(url, timeout=10)

            print(f"[DEBUG] Appel API Binance: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                print(f"[DEBUG] Données reçues: {len(data)} cryptos")

                # Filtrer pour ne garder que les paires USDT et exclure les stablecoins
                usdt_pairs = [
                    ticker
                    for ticker in data
                    if ticker.get('symbol', '').endswith('USDT')
                    and not ticker.get('symbol', '').startswith('USDT')
                    and not ticker.get('symbol', '').startswith('BUSD')
                    and not ticker.get('symbol', '').startswith('TUSD')
                    and not ticker.get('symbol', '').startswith('DAI')
                    and not ticker.get('symbol', '').startswith('USDC')
                ]

                print(f"[DEBUG] Paires USDT filtrées: {len(usdt_pairs)}")

                # Prendre un nombre raisonnable de cryptos par volume pour éviter les traitements trop longs
                sorted_by_volume = sorted(
                    usdt_pairs,
                    key=lambda x: float(x.get('quoteVolume', 0) or 0),
                    reverse=True,
                )

                for i, ticker in enumerate(sorted_by_volume[:120]):
                    try:
                        symbol = ticker.get('symbol', '').replace('USDT', '')
                        price = float(ticker.get('lastPrice', 0) or 0)
                        change_24h = float(ticker.get('priceChangePercent', 0) or 0)
                        volume = float(ticker.get('quoteVolume', 0) or 0)  # Volume en USDT

                        # Filtrer les cryptos avec très faible volume
                        if volume > 10000:  # Volume > 10K USDT
                            market_cap, rank, ath, atl = fetch_cg_enrichment(symbol)

                            crypto_item = {
                                'symbol': symbol,
                                'price': price,
                                'change_24h': change_24h,
                                'volume': volume,
                                'market_cap': market_cap,
                                'timestamp': datetime.now().isoformat(),
                                'description': "",
                                'rank': rank,
                                'high_24h': None,
                                'low_24h': None,
                                'ath': ath,
                                'atl': atl,
                            }
                            _, enriched = score_crypto(crypto_item)
                            crypto_list.append(enriched)

                            if i < 10:  # Afficher les 10 premiers pour debug
                                print(
                                    f"[DEBUG] Crypto #{i+1}: {symbol} - ${price:,.2f} - {change_24h:.2f}%"
                                )
                    except (ValueError, TypeError, KeyError) as e:
                        print(f"[DEBUG] Erreur parsing crypto {ticker.get('symbol', 'Unknown')}: {e}")
                        continue

                print(f"[DEBUG] Total crypto valides (Binance+CG enrichi): {len(crypto_list)}")
                if crypto_list:
                    return crypto_list
            else:
                print(f"[DEBUG] Erreur API Binance: Status {response.status_code}")
                print(f"[DEBUG] Response: {response.text}")

        except Exception as e:
            print(f"[ERREUR] Erreur collecte crypto (Binance): {e}")

        # 2) Fallback complet CoinGecko si Binance ne répond pas ou est vide
        try:
            now = time.time()
            if now < getattr(self, "coingecko_block_until", 0.0):
                print("[DEBUG] CoinGecko en pause après un 429 précédent, aucun appel API.")
                return []

            print("[DEBUG] Fallback CoinGecko markets pour les données crypto")
            markets_url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 100,
                "page": 1,
                "price_change_percentage": "24h",
            }
            resp = self.session.get(markets_url, params=params, timeout=15)
            print(f"[DEBUG] Appel API CoinGecko markets: {resp.status_code}")

            # Gestion explicite du 429: mettre CoinGecko en pause temporaire
            if resp.status_code == 429:
                self.coingecko_block_until = time.time() + 60.0  # 1 minute de pause
                print("[DEBUG] CoinGecko a renvoyé 429, mise en pause des appels pendant 60s.")
                print(f"[DEBUG] Response: {resp.text}")
                return []

            if resp.status_code != 200:
                print(f"[DEBUG] Erreur API CoinGecko: Status {resp.status_code}")
                print(f"[DEBUG] Response: {resp.text}")
                return []

            data = resp.json()
            crypto_list = []
            for i, coin in enumerate(data):
                try:
                    symbol = (coin.get("symbol") or "").upper()
                    price = float(coin.get("current_price") or 0)
                    change_24h = float(coin.get("price_change_percentage_24h") or 0)
                    volume = float(coin.get("total_volume") or 0)
                    market_cap = float(coin.get("market_cap") or 0)
                    rank = coin.get("market_cap_rank") or None
                    ath = float(coin.get("ath") or 0)
                    atl = float(coin.get("atl") or 0)
                    high_24h = float(coin.get("high_24h") or 0)
                    low_24h = float(coin.get("low_24h") or 0)

                    crypto_item = {
                        'symbol': symbol,
                        'price': price,
                        'change_24h': change_24h,
                        'volume': volume,
                        'market_cap': market_cap,
                        'timestamp': datetime.now().isoformat(),
                        # Pas de description détaillée ici pour garder le scraper léger
                        'description': "",
                        'rank': rank,
                        'ath': ath,
                        'atl': atl,
                        'high_24h': high_24h,
                        'low_24h': low_24h,
                    }
                    _, enriched = score_crypto(crypto_item)
                    crypto_list.append(enriched)
                    if i < 10:
                        print(
                            f"[DEBUG] Crypto CG #{i+1}: {symbol} - ${price:,.2f} - {change_24h:.2f}%"
                        )
                except (ValueError, TypeError, KeyError) as e:
                    print(f"[DEBUG] Erreur parsing crypto CoinGecko {coin.get('symbol', 'Unknown')}: {e}")
                    continue

            print(f"[DEBUG] Total crypto valides (CoinGecko): {len(crypto_list)}")
            return crypto_list
        except Exception as e:
            print(f"[ERREUR] Erreur collecte crypto (CoinGecko): {e}")
            return []

    # -------- News helpers --------
    def _score_news_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Score simple: source + longueur + fraîcheur approximée."""
        title = item.get("title", "")
        source = (item.get("source") or "").lower()
        content = item.get("content") or ""
        source_score = 1.0
        if any(k in source for k in ["coindesk", "cointelegraph", "decrypt", "reuters", "bbc", "techcrunch", "wired"]):
            source_score = 1.6
        length_score = min(len(content) / 400.0, 1.5)
        freshness = 0.8  # flux RSS récent
        score = round(source_score + length_score + freshness, 3)
        item["score"] = score
        return item

    def _dedup_news(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        deduped = []
        for it in items:
            key = (it.get("title", "").strip().lower(), (it.get("source") or "").strip().lower())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(it)
        return deduped

    def _fetch_full_article_body(self, url: str, max_chars: int = 2000) -> Optional[str]:
        """Tente de récupérer le corps complet d'un article à partir de son URL.
        Utilise des heuristiques simples (balise <article> ou tous les <p>) et nettoie le HTML.
        """
        try:
            resp = self.session.get(url, timeout=8)
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, 'html.parser')

            # Essayer d'abord une balise <article>
            article = soup.find('article')
            texts = []
            if article:
                texts = list(article.stripped_strings)
            else:
                # Fallback: concaténer tous les paragraphes
                paragraphs = soup.find_all('p')
                if not paragraphs:
                    return None
                for p in paragraphs:
                    texts.extend(list(p.stripped_strings))

            if not texts:
                return None

            full_text = ' '.join(texts)
            full_text = re.sub(r'\s+', ' ', full_text).strip()
            if not full_text:
                return None

            # Supprimer les blocs "bruit" en fin d'article (sections pub / disclaimer)
            cut_markers = [
                "More For You",
                "More for you",
                "Disclosure & Policies",
                "Disclosure & Polices",
                "Disclosure & Policies :",
                "Disclosure & Polices :",
                "CoinDesk is an award-winning media outlet",
            ]
            for marker in cut_markers:
                idx = full_text.find(marker)
                if idx != -1:
                    full_text = full_text[:idx].strip()
                    break

            if not full_text:
                return None

            return full_text[:max_chars]
        except Exception as e:
            print(f"[ERREUR] Erreur récupération article complet {url}: {e}")
            return None
    
    def get_crypto_news(self) -> List[Dict]:
        """Récupère les news crypto depuis plusieurs sources RSS"""
        news_list = []
        
        # Sources RSS gratuites
        rss_sources = [
            "https://cointelegraph.com/rss",
            "https://decrypt.co/feed",
            "https://www.coindesk.com/arc/outboundfeeds/rss"
        ]
        
        for rss_url in rss_sources:
            try:
                feed = feedparser.parse(rss_url)
                
                for entry in feed.entries[:5]:  # Limiter à 5 articles par source
                    # Nettoyer le contenu
                    content = entry.summary if hasattr(entry, 'summary') else entry.description
                    content = re.sub(r'<[^>]+>', '', content)  # Supprimer les balises HTML
                    
                    # Si le contenu est vide après nettoyage, utiliser le titre
                    if not content or content.strip() == '':
                        content = entry.title

                    # Si le résumé est très court, tenter de récupérer le corps complet de l'article
                    if False and content and len(content) < 300 and hasattr(entry, 'link'):
                        full_body = self._fetch_full_article_body(entry.link, max_chars=2000)
                        if full_body:
                            content = full_body
                    
                    # Limiter la longueur finale
                    if content:
                        content = content[:2000]
                    else:
                        content = "No content available"
                    
                    news_list.append({
                        'title': entry.title,
                        'content': content,
                        'source': feed.feed.title if hasattr(feed.feed, 'title') else rss_url,
                        'url': entry.link,
                        'published': entry.published if hasattr(entry, 'published') else datetime.now().isoformat(),
                        'category': 'crypto',
                        'timestamp': datetime.now()
                    })
                
                time.sleep(1)  # Respecter les limites de taux
                
            except Exception as e:
                print(f"[ERREUR] Erreur RSS {rss_url}: {e}")
        
        # Scoring + dédup + tri
        scored = [self._score_news_item(n) for n in news_list]
        scored = self._dedup_news(scored)
        scored = sorted(scored, key=lambda x: x.get("score", 0), reverse=True)[:30]
        return scored
    
    def get_world_news(self) -> List[Dict]:
        """Récupère les news mondiales depuis des sources open source"""
        news_list = []
        
        # Sources d'actualités gratuites
        sources = [
            {
                'name': 'BBC News',
                'rss': 'http://feeds.bbci.co.uk/news/rss.xml'
            },
            {
                'name': 'Reuters via Google News',
                'rss': 'https://news.google.com/rss/search?q=site%3Areuters.com+world&hl=en-US&gl=US&ceid=US%3Aen'
            },
            {
                'name': 'Google News',
                'rss': 'https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB'
            }
        ]
        
        for source in sources:
            try:
                feed = feedparser.parse(source['rss'])
                
                for entry in feed.entries[:3]:  # Limiter à 3 articles
                    # Nettoyer le contenu
                    content = entry.summary if hasattr(entry, 'summary') else entry.description
                    content = re.sub(r'<[^>]+>', '', content)  # Supprimer les balises HTML
                    
                    # Si le contenu est vide après nettoyage, utiliser le titre
                    if not content or content.strip() == '':
                        content = entry.title

                    # Si le résumé est très court, tenter de récupérer le corps complet
                    if content and len(content) < 300 and hasattr(entry, 'link'):
                        full_body = self._fetch_full_article_body(entry.link, max_chars=2000)
                        if full_body:
                            content = full_body
                    
                    # Limiter la longueur finale
                    if content:
                        content = content[:2000]
                    else:
                        content = "No content available"
                    
                    news_list.append({
                        'title': entry.title,
                        'content': content,
                        'source': source['name'],
                        'url': entry.link,
                        'published': entry.published if hasattr(entry, 'published') else datetime.now().isoformat(),
                        'category': 'world',
                        'timestamp': datetime.now()
                    })
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"[ERREUR] Erreur {source['name']}: {e}")
        
        scored = [self._score_news_item(n) for n in news_list]
        scored = self._dedup_news(scored)
        scored = sorted(scored, key=lambda x: x.get("score", 0), reverse=True)[:15]
        return scored
    
    def get_tech_news(self) -> List[Dict]:
        """Récupère les news tech depuis des sources spécialisées"""
        news_list = []
        
        tech_sources = [
            "https://techcrunch.com/feed/",
            "https://www.wired.com/feed/rss",
            "https://feeds.macrumors.com/"
        ]
        
        for rss_url in tech_sources:
            try:
                feed = feedparser.parse(rss_url)
                
                for entry in feed.entries[:3]:
                    content = entry.summary if hasattr(entry, 'summary') else entry.description
                    content = re.sub(r'<[^>]+>', '', content)
                    
                    # Si le contenu est vide après nettoyage, utiliser le titre
                    if not content or content.strip() == '':
                        content = entry.title

                    # Si le résumé est très court, tenter de récupérer le corps complet
                    if content and len(content) < 300 and hasattr(entry, 'link'):
                        full_body = self._fetch_full_article_body(entry.link, max_chars=2000)
                        if full_body:
                            content = full_body
                    
                    # Limiter la longueur finale
                    if content:
                        content = content[:2000]
                    else:
                        content = "No content available"
                    
                    news_list.append({
                        'title': entry.title,
                        'content': content,
                        'source': feed.feed.title if hasattr(feed.feed, 'title') else rss_url,
                        'url': entry.link,
                        'published': entry.published if hasattr(entry, 'published') else datetime.now().isoformat(),
                        'category': 'tech',
                        'timestamp': datetime.now()
                    })
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"[ERREUR] Erreur tech RSS {rss_url}: {e}")
        
        scored = [self._score_news_item(n) for n in news_list]
        scored = self._dedup_news(scored)
        scored = sorted(scored, key=lambda x: x.get("score", 0), reverse=True)[:15]
        return scored
    
    def scrape_reddit_trends(self) -> List[Dict]:
        """Scrape les tendances Reddit (sans API)"""
        trends = []
        
        try:
            # Subreddits à surveiller
            subreddits = ['worldnews', 'technology', 'CryptoCurrency', 'geopolitics']
            use_rss = False
            
            for subreddit in subreddits:
                if time.time() < self.reddit_block_until:
                    print("[DEBUG] Quota Reddit atteint, collecte suspendue")
                    break

                if use_rss:
                    trends.extend(self._scrape_reddit_rss(subreddit))
                    time.sleep(3)  # Rate limiting plus strict pour le flux RSS
                    continue

                url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=10"
                
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    self._respect_reddit_quota(response)
                    data = response.json()
                    
                    for post in data['data']['children'][:5]:
                        post_data = post['data']
                        
                        trends.append({
                            'title': post_data['title'],
                            'content': post_data.get('selftext', '')[:800],
                            'source': f"Reddit r/{subreddit}",
                            'url': f"https://reddit.com{post_data['permalink']}",
                            'score': post_data.get('score', 0),
                            'comments': post_data.get('num_comments', 0),
                            'category': subreddit,
                            'timestamp': datetime.fromtimestamp(post_data['created_utc'])
                        })
                elif response.status_code == 429:
                    self._block_reddit(response)
                    continue
                else:
                    print(f"[DEBUG] Reddit JSON r/{subreddit}: {response.status_code}, repli sur le flux RSS public")
                    use_rss = True
                    time.sleep(3)
                    trends.extend(self._scrape_reddit_rss(subreddit))
                    time.sleep(3)
                    continue
                
                time.sleep(1)  # Rate limiting
                
        except Exception as e:
            print(f"[ERREUR] Erreur Reddit: {e}")
        
        return trends

    def _block_reddit(self, response) -> None:
        try:
            delay = float(response.headers.get('Retry-After', 60))
        except (TypeError, ValueError):
            delay = 60.0
        self.reddit_block_until = time.time() + max(delay, 60.0)
        print("[DEBUG] Reddit 429, pause avant le prochain appel")

    def _respect_reddit_quota(self, response) -> None:
        """Suspend les appels quand Reddit annonce un quota épuisé (x-ratelimit-*)."""
        try:
            remaining = float(response.headers.get('x-ratelimit-remaining', 1))
            reset = float(response.headers.get('x-ratelimit-reset', 60))
        except (TypeError, ValueError):
            return
        if remaining < 1:
            self.reddit_block_until = time.time() + reset
    
    def _scrape_reddit_rss(self, subreddit: str) -> List[Dict]:
        """Repli sur le flux Atom public quand l'endpoint JSON est refusé (403)."""
        url = f"https://www.reddit.com/r/{subreddit}/hot.rss?limit=10"
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 429:
                self._block_reddit(response)
                return []
            if response.status_code != 200:
                print(f"[DEBUG] Reddit RSS r/{subreddit}: {response.status_code}")
                return []
            self._respect_reddit_quota(response)
            feed = feedparser.parse(response.content)
        except Exception as e:
            print(f"[ERREUR] Erreur Reddit RSS r/{subreddit}: {e}")
            return []

        trends = []
        for entry in feed.entries[:5]:
            published = entry.get('published_parsed') or entry.get('updated_parsed')
            html = entry.get('summary', '')
            trends.append({
                'title': entry.get('title', ''),
                'content': BeautifulSoup(html, 'html.parser').get_text(' ', strip=True)[:800],
                'source': f"Reddit r/{subreddit}",
                'url': entry.get('link', ''),
                'score': 0,
                'comments': 0,
                'category': subreddit,
                'timestamp': datetime(*published[:6]) if published else datetime.now(),
            })
        return trends

    def get_market_sentiment(self) -> Dict[str, Any]:
        """Analyse le sentiment du marché depuis plusieurs sources"""
        sentiment_data = {
            'overall_sentiment': 'neutral',
            'fear_greed_index': 50,  # Valeur simulée
            'trending_topics': [],
            'market_movers': []
        }
        
        try:
            # Simuler Fear & Greed Index (alternative)
            crypto_data = self.get_crypto_data()
            if crypto_data:
                positive_changes = sum(1 for crypto in crypto_data if crypto['change_24h'] > 0)
                total_changes = len(crypto_data)
                
                if total_changes > 0:
                    ratio = positive_changes / total_changes
                    if ratio > 0.7:
                        sentiment_data['overall_sentiment'] = 'bullish'
                        sentiment_data['fear_greed_index'] = 75
                    elif ratio < 0.3:
                        sentiment_data['overall_sentiment'] = 'bearish'
                        sentiment_data['fear_greed_index'] = 25
                    else:
                        sentiment_data['overall_sentiment'] = 'neutral'
                        sentiment_data['fear_greed_index'] = 50
            
            # Sujets tendances
            all_news = (self.get_crypto_news() + 
                       self.get_world_news() + 
                       self.get_tech_news())
            
            # Extraire les mots-clés les plus fréquents
            word_freq = {}
            for news in all_news[:20]:
                words = re.findall(r'\b\w+\b', news['title'].lower())
                for word in words:
                    if len(word) > 3 and word not in ['that', 'this', 'with', 'from', 'they', 'been', 'have']:
                        word_freq[word] = word_freq.get(word, 0) + 1
            
            # Top 10 mots-clés
            sentiment_data['trending_topics'] = sorted(word_freq.items(), 
                                                     key=lambda x: x[1], 
                                                     reverse=True)[:10]
            
        except Exception as e:
            print(f"[ERREUR] Erreur analyse sentiment: {e}")
        
        return sentiment_data
    
    def collect_all_data(self) -> Dict[str, Any]:
        """Collecte les données principales (mode léger pour le SaaS/Render).

        Pour éviter que le worker Gunicorn soit tué sur Render (timeout ou mémoire),
        on se limite ici aux cryptos et aux news crypto. Les autres sources (news
        monde/tech, Reddit, sentiment détaillé) restent disponibles pour un usage
        local mais ne sont pas appelées dans ce mode.
        """

        print("[COLLECTE] Début de la collecte des données open source (mode léger)...")

        crypto_data = self.get_crypto_data()
        crypto_news = self.get_crypto_news()

        all_data = {
            'crypto_data': crypto_data,
            'crypto_news': crypto_news,
            'world_news': [],
            'tech_news': [],
            'reddit_trends': [],
            'market_sentiment': {},
            'timestamp': datetime.now().isoformat(),
        }

        print(
            f"[COLLECTE] Terminé (léger) - {len(crypto_news)} news crypto, "
            f"{len(crypto_data)} cryptos"
        )

        return all_data

    def run_autonomous(self, interval_seconds: int = 600):
        print(f"[AUTONOME] Démarrage du collecteur open source (intervalle: {interval_seconds}s)")
        try:
            cycle = 0
            while True:
                cycle += 1
                print(f"\n[AUTONOME] Cycle #{cycle}")
                data = self.collect_all_data()
                print(f"[AUTONOME] Résumé: {len(data['crypto_data'])} cryptos, "
                      f"{len(data['crypto_news'])} news crypto, "
                      f"{len(data['world_news'])} news monde, "
                      f"{len(data['tech_news'])} news tech, "
                      f"{len(data['reddit_trends'])} posts Reddit")
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n[AUTONOME] Arrêt demandé par l'utilisateur. Fin de la collecte.")

# Test du collecteur
if __name__ == "__main__":
    collector = OpenSourceDataCollector()
    print("[AUTONOME] Mode autonome - collecte toutes les 10 minutes. Ctrl+C pour arrêter.")
    collector.run_autonomous(interval_seconds=600)

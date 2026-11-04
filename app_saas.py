from flask import Flask, render_template, request, session, redirect, url_for, flash, Response, send_from_directory, jsonify
import stripe
import sqlite3
import hashlib
from datetime import datetime, timedelta
import os
import csv
import io
import json
import random
import re
import secrets
import smtplib
from email.mime.text import MIMEText
from xml.sax.saxutils import escape as xml_escape

from open_source_scraper import OpenSourceDataCollector
import m2m

app = Flask(__name__)
# SECRET_KEY env requis en prod ; fallback ephemere pour ne pas crasher le boot.
# Sans env, les sessions sont invalidees a chaque redemarrage (inforgeable).
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

# Configuration Stripe
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
stripe.api_key = STRIPE_SECRET_KEY

# Configuration produit
PRICE_ID = os.getenv('STRIPE_PRICE_ID')  # ID du prix Stripe
PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

if STRIPE_SECRET_KEY and PUBLISHABLE_KEY:
    if STRIPE_SECRET_KEY.startswith('sk_live_') != PUBLISHABLE_KEY.startswith('pk_live_'):
        print("[SaaS] ERREUR: STRIPE_SECRET_KEY et STRIPE_PUBLISHABLE_KEY ne sont pas du même mode (live/test)")

# Configuration SMTP pour les alertes email (Gmail de l'application)
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
ALERT_FROM_EMAIL = os.getenv('ALERT_FROM_EMAIL', SMTP_USER)

# Initialiser la base de données utilisateurs
def init_users_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE,
            password TEXT,
            plan TEXT DEFAULT 'free',
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in cursor.fetchall()]
    if 'stripe_subscription_id' not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN stripe_subscription_id TEXT")
    conn.commit()
    conn.close()


def get_user_plan(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT plan FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return (row[0] if row and row[0] else 'free')


def is_premium_user():
    return 'user_id' in session and get_user_plan(session['user_id']) == 'premium'


def set_plan_by_customer(customer_id, plan):
    if not customer_id:
        return
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET plan = ? WHERE stripe_customer_id = ?', (plan, customer_id))
    conn.commit()
    conn.close()

# Initialiser la base de données principale
def init_main_db():
    conn = sqlite3.connect('omnicirelpc.db')
    cursor = conn.cursor()
    
    # Créer la table events si elle n'existe pas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY,
            title TEXT,
            content TEXT,
            category TEXT,
            priority TEXT,
            timestamp TEXT,
            impact REAL,
            price REAL,
            market_cap REAL,
            volume REAL,
            vol_mcap REAL,
            distance_ath REAL,
            distance_atl REAL,
            score REAL,
            change_pct REAL
        )
    ''')

    # Créer les autres tables utilisées par la GUI si elles n'existent pas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            analysis TEXT,
            timestamp TEXT,
            sentiment REAL,
            confidence REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            status TEXT,
            created_at TEXT,
            completed_at TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_crypto_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            symbol TEXT,
            direction TEXT,
            threshold_percent REAL,
            active INTEGER DEFAULT 1,
            last_triggered_at TEXT
        )
    ''')

    # Migration douce: ajouter les colonnes manquantes si base plus ancienne
    try:
        cursor.execute("PRAGMA table_info(events)")
        cols = [row[1] for row in cursor.fetchall()]
        if 'priority' not in cols:
            cursor.execute("ALTER TABLE events ADD COLUMN priority TEXT")
        if 'impact' not in cols:
            cursor.execute("ALTER TABLE events ADD COLUMN impact REAL")
        if 'price' not in cols:
            cursor.execute("ALTER TABLE events ADD COLUMN price REAL")
        if 'market_cap' not in cols:
            cursor.execute("ALTER TABLE events ADD COLUMN market_cap REAL")
        if 'volume' not in cols:
            cursor.execute("ALTER TABLE events ADD COLUMN volume REAL")
        if 'vol_mcap' not in cols:
            cursor.execute("ALTER TABLE events ADD COLUMN vol_mcap REAL")
        if 'distance_ath' not in cols:
            cursor.execute("ALTER TABLE events ADD COLUMN distance_ath REAL")
        if 'distance_atl' not in cols:
            cursor.execute("ALTER TABLE events ADD COLUMN distance_atl REAL")
        if 'score' not in cols:
            cursor.execute("ALTER TABLE events ADD COLUMN score REAL")
        if 'change_pct' not in cols:
            cursor.execute("ALTER TABLE events ADD COLUMN change_pct REAL")
    except Exception as e:
        print(f"[SaaS] Erreur migration schema events: {e}")

    conn.commit()
    conn.close()


def save_scraped_data_to_db(data):
    try:
        conn = sqlite3.connect('omnicirelpc.db')
        cursor = conn.cursor()

        cursor.execute("DELETE FROM events WHERE category='crypto';")

        for item in data:
            price = item.get('price')
            market_cap = item.get('market_cap')
            volume = item.get('volume')
            vol_mcap = item.get('vol_mcap')
            distance_ath = item.get('distance_ath_pct')
            distance_atl = item.get('distance_atl_pct')
            score = item.get('score')
            change_pct = item.get('change_24h')

            cursor.execute(
                """
                    INSERT INTO events (title, content, category, priority, timestamp, impact, price, market_cap, volume, vol_mcap, distance_ath, distance_atl, score, change_pct)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item['title'],
                    item['content'],
                    item['category'],
                    item['priority'],
                    item['timestamp'],
                    float(item['impact']),
                    price if price is not None else None,
                    market_cap if market_cap is not None else None,
                    volume if volume is not None else None,
                    vol_mcap if vol_mcap is not None else None,
                    distance_ath if distance_ath is not None else None,
                    distance_atl if distance_atl is not None else None,
                    score if score is not None else None,
                    change_pct if change_pct is not None else None,
                ),
            )

        conn.commit()
        conn.close()
        return len(data)
    except Exception as e:
        print(f"[SaaS] Erreur sauvegarde BDD: {e}")
        return 0


def cleanup_database_db(max_events: int = 500, max_analyses: int = 200, max_tasks: int = 200):
    try:
        conn = sqlite3.connect('omnicirelpc.db')
        cursor = conn.cursor()

        cursor.execute(
            """
                DELETE FROM events
                WHERE id NOT IN (
                    SELECT id FROM events
                    ORDER BY id DESC
                    LIMIT ?
                )
            """,
            (max_events,),
        )

        cursor.execute(
            """
                DELETE FROM analyses
                WHERE id NOT IN (
                    SELECT id FROM analyses
                    ORDER BY id DESC
                    LIMIT ?
                )
            """,
            (max_analyses,),
        )

        cursor.execute(
            """
                DELETE FROM tasks
                WHERE id NOT IN (
                    SELECT id FROM tasks
                    ORDER BY id DESC
                    LIMIT ?
                )
            """,
            (max_tasks,),
        )

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[SaaS] Erreur nettoyage BDD: {e}")


def send_email_alert(recipient_email, subject, body):
    smtp_host = SMTP_HOST
    smtp_port = SMTP_PORT
    smtp_user = SMTP_USER
    smtp_pass = SMTP_PASSWORD
    from_email = ALERT_FROM_EMAIL

    if not (smtp_host and smtp_user and smtp_pass and from_email):
        print("[SaaS] SMTP non configuré, alertes email ignorées")
        return False

    try:
        msg = MIMEText(body, _charset='utf-8')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = recipient_email

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[SaaS] Erreur envoi alerte email: {e}")
        return False


def run_scraper_once(recipient_email=None, user_id=None):
    collector = OpenSourceDataCollector()
    all_collected_data = collector.collect_all_data()

    news_data = (
        all_collected_data.get('crypto_news', [])
        + all_collected_data.get('world_news', [])
        + all_collected_data.get('tech_news', [])
    )
    crypto_data = all_collected_data.get('crypto_data', [])
    reddit_data = all_collected_data.get('reddit_trends', [])

    combined = []
    alert_items = []

    # Charger les préférences d'alertes de l'utilisateur
    user_alerts = []
    if user_id is not None:
        try:
            conn = sqlite3.connect('omnicirelpc.db')
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT symbol, direction, threshold_percent, active
                FROM user_crypto_alerts
                WHERE user_id = ? AND active = 1
                ''',
                (user_id,),
            )
            rows = cursor.fetchall()
            conn.close()
            for symbol, direction, threshold_percent, active in rows:
                user_alerts.append(
                    {
                        'symbol': (symbol or '').upper(),
                        'direction': direction or 'both',
                        'threshold': float(threshold_percent or 0),
                    }
                )
        except Exception as e:
            print(f"[SaaS] Erreur chargement alertes utilisateur: {e}")

    for item in news_data:
        impact = float(item.get("score", 0.6))
        combined.append(
            {
                'title': item.get('title', 'No title'),
                'priority': 'HIGH'
                if ('breaking' in item.get('title', '').lower() or impact >= 2.5)
                else 'MEDIUM',
                'category': 'news',
                'timestamp': item.get('timestamp', datetime.now().isoformat()),
                'impact': str(impact),
                'content': item.get('content', item.get('title', 'No content')),
            }
        )

    # Trier les cryptos par score, puis variation
    crypto_sorted = sorted(
        crypto_data,
        key=lambda x: (x.get('score', 0), abs(x.get('change_24h', 0) or 0)),
        reverse=True,
    )

    for item in crypto_sorted:
        change_value = item.get('change_24h', 0)
        if isinstance(change_value, (int, float)):
            change_str = f"{change_value:.2f}%"
            impact = item.get('score', abs(change_value) / 100.0)
        else:
            change_str = "0%"
            impact = item.get('score', 0.0)

        description = item.get('description', '')
        if description:
            content = (
                f"{item.get('symbol', 'Unknown')} - Price: ${item.get('price', 0):,.2f} - Change: {change_str}\n\n"
                f"📊 Description: {description}"
            )
        else:
            content_parts = [
                f"Prix: ${item.get('price', 0):,.2f}",
                f"Variation 24h: {change_str}",
            ]
            if item.get("market_cap"):
                content_parts.append(f"Market cap: ${item.get('market_cap', 0):,.0f}")
            if item.get("volume"):
                content_parts.append(f"Volume 24h: ${item.get('volume', 0):,.0f}")
            if item.get("vol_mcap") is not None:
                content_parts.append(f"Vol/MCap: {item.get('vol_mcap')*100:.2f}%")
            if item.get("distance_ath_pct") is not None:
                content_parts.append(f"Distance ATH: {item.get('distance_ath_pct'):.1f}%")
            if item.get("distance_atl_pct") is not None:
                content_parts.append(f"Distance ATL: {item.get('distance_atl_pct'):.1f}%")
            content = " | ".join(content_parts)

        combined.append(
            {
                'title': f"Crypto: {item.get('symbol', 'Unknown')} {change_str}",
                'priority': 'HIGH' if (abs(change_value) > 5 or impact >= 2.5) else 'MEDIUM',
                'category': 'crypto',
                'timestamp': item.get('timestamp', datetime.now().isoformat()),
                'impact': str(impact),
                'content': content,
            }
        )

        # Vérifier les alertes personnalisées
        symbol = (item.get('symbol', 'Unknown') or '').upper()
        for alert in user_alerts:
            if alert['symbol'] != symbol:
                continue
            threshold = alert['threshold']
            direction = alert['direction']
            if not isinstance(change_value, (int, float)):
                continue
            score_sig = item.get('score', 0.0)
            vol_mcap = item.get('vol_mcap') or 0.0
            strong_signal = score_sig >= 2.5 or vol_mcap >= 0.15
            if direction == 'up' and (change_value >= threshold or strong_signal):
                alert_items.append(
                    f"{symbol}: {change_str} (prix: ${item.get('price', 0):,.4f}, score {score_sig:.2f})"
                )
            elif direction == 'down' and (change_value <= -threshold or strong_signal):
                alert_items.append(
                    f"{symbol}: {change_str} (prix: ${item.get('price', 0):,.4f}, score {score_sig:.2f})"
                )
            elif direction == 'both' and (abs(change_value) >= threshold or strong_signal):
                alert_items.append(
                    f"{symbol}: {change_str} (prix: ${item.get('price', 0):,.4f}, score {score_sig:.2f})"
                )

    for item in reddit_data:
        combined.append(
            {
                'title': f"Reddit: {item.get('title', 'No title')[:50]}...",
                'priority': 'MEDIUM',
                'category': 'social',
                'timestamp': item.get('timestamp', datetime.now().strftime('%H:%M')),
                'impact': str(random.uniform(0.3, 0.8)),
                'content': f"Subreddit: {item.get('subreddit', 'unknown')} - {item.get('title', 'No title')}",
            }
        )

    count = save_scraped_data_to_db(combined)
    cleanup_database_db()

    alerts_to_send = []
    if recipient_email and alert_items:
        subject = "OmniCirelPC - Alertes Crypto"
        body = "Gros mouvements détectés sur les cryptos suivantes:\n\n" + "\n".join(alert_items)
        if send_email_alert(recipient_email, subject, body):
            alerts_to_send = alert_items

    return count, alerts_to_send


@app.route('/run-scraper')
def run_scraper_route():
    if 'user_id' not in session:
        return redirect('/login')
    
    is_premium = is_premium_user()
    recipient_email = session.get('email') if is_premium else None
    user_id = session.get('user_id') if is_premium else None

    scraped, alerts = run_scraper_once(recipient_email, user_id=user_id)
    flash(f"Scraping terminé : {scraped} éléments enregistrés.")
    if alerts:
        flash(f"Alertes envoyées : {', '.join(alerts)}")
    return redirect('/dashboard')

@app.route('/alerts', methods=['GET', 'POST'])
def alerts():
    if 'user_id' not in session:
        return redirect('/login')

    if not is_premium_user():
        flash('Les alertes personnalisées sont réservées aux membres Premium.')
        return redirect('/premium')

    user_id = session['user_id']

    if request.method == 'POST':
        symbol_manual = request.form.get('symbol', '').upper().strip()
        symbol_select = request.form.get('symbol_select', '').upper().strip()
        symbol = symbol_manual or symbol_select
        direction = request.form.get('direction', 'both')
        try:
            threshold = float(request.form.get('threshold', '10'))
        except ValueError:
            threshold = 10.0
        active = 1 if request.form.get('active') == 'on' else 0

        if symbol:
            try:
                conn = sqlite3.connect('omnicirelpc.db')
                cursor = conn.cursor()

                cursor.execute(
                    '''
                    SELECT id FROM user_crypto_alerts
                    WHERE user_id = ? AND symbol = ?
                    ''',
                    (user_id, symbol),
                )
                row = cursor.fetchone()

                if row:
                    cursor.execute(
                        '''
                        UPDATE user_crypto_alerts
                        SET direction = ?, threshold_percent = ?, active = ?
                        WHERE id = ?
                        ''',
                        (direction, threshold, active, row[0]),
                    )
                else:
                    cursor.execute(
                        '''
                        INSERT INTO user_crypto_alerts (user_id, symbol, direction, threshold_percent, active)
                        VALUES (?, ?, ?, ?, ?)
                        ''',
                        (user_id, symbol, direction, threshold, active),
                    )

                conn.commit()
                conn.close()
                flash("Alerte enregistrée.")
            except Exception as e:
                print(f"[SaaS] Erreur enregistrement alerte: {e}")
                flash("Erreur lors de l'enregistrement de l'alerte.")

    conn = sqlite3.connect('omnicirelpc.db')
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT * FROM user_crypto_alerts
        WHERE user_id = ?
        ORDER BY symbol
        ''',
        (user_id,),
    )
    alerts = cursor.fetchall()

    # Charger la liste des symboles crypto disponibles depuis la table events
    symbols = []
    try:
        cursor.execute(
            "SELECT DISTINCT title FROM events WHERE category = 'crypto'"
        )
        rows = cursor.fetchall()
        found = set()
        for (title,) in rows:
            if not title:
                continue
            m = re.search(r"Crypto:\s*([A-Za-z0-9]+)", title)
            if m:
                found.add(m.group(1).upper())
        symbols = sorted(found)
    except Exception as e:
        print(f"[SaaS] Erreur chargement symboles pour alertes: {e}")

    conn.close()

    return render_template('alerts.html', alerts=alerts, symbols=symbols)


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template('index.html', stripe_key=PUBLISHABLE_KEY)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, password))
            conn.commit()
            flash('Compte créé avec succès ! Connectez-vous.')
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash('Cet email est déjà utilisé.')
            return redirect('/register')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['email'] = user[1]
            session['plan'] = user[3] or 'free'
            return redirect('/dashboard')
        else:
            flash('Identifiants incorrects.')
            return redirect('/login')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/delete-account', methods=['GET', 'POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    if request.method == 'POST':
        password = request.form.get('password', '')
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()

        if not row or row[0] != password_hash:
            conn.close()
            flash("Mot de passe incorrect.")
            return redirect('/delete-account')

        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()

        try:
            conn_main = sqlite3.connect('omnicirelpc.db')
            cursor_main = conn_main.cursor()
            cursor_main.execute('DELETE FROM user_crypto_alerts WHERE user_id = ?', (user_id,))
            conn_main.commit()
            conn_main.close()
        except Exception as e:
            print(f"[SaaS] Erreur suppression données utilisateur: {e}")

        session.clear()
        flash('Votre compte a été supprimé avec succès.')
        return redirect('/')

    return render_template('delete_account.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    
    is_premium = is_premium_user()
    view_all_crypto = request.args.get('view_all_crypto') == '1'

    # Limites différentes pour gratuit vs premium (triés par score puis variation)
    if is_premium:
        news_limit = 80
        crypto_limit = 140 if not view_all_crypto else 400
    else:
        news_limit = 20
        crypto_limit = 20
    
    conn = sqlite3.connect('omnicirelpc.db')
    cursor = conn.cursor()

    # Crypto séparées
    cursor.execute(
        """
        SELECT id, title, content, category, priority, timestamp, impact,
               price, market_cap, volume, vol_mcap, distance_ath, distance_atl, score, change_pct
        FROM events
        WHERE category = 'crypto'
        ORDER BY COALESCE(score,0) DESC, ABS(COALESCE(change_pct,0)) DESC, timestamp DESC
        LIMIT ?
        """,
        (crypto_limit,),
    )
    crypto_rows = cursor.fetchall()

    # News / autres catégories séparées
    cursor.execute(
        """
        SELECT id, title, content, category, priority, timestamp, impact,
               price, market_cap, volume, vol_mcap, distance_ath, distance_atl, score, change_pct
        FROM events
        WHERE category != 'crypto'
        ORDER BY COALESCE(score,0) DESC, timestamp DESC
        LIMIT ?
        """,
        (news_limit,),
    )
    news_data = cursor.fetchall()
    
    # Dernière mise à jour (tous events confondus)
    cursor.execute("SELECT MAX(timestamp) FROM events")
    row = cursor.fetchone()
    last_update = row[0] if row and row[0] else None

    conn.close()

    # Construire une vue crypto enrichie avec le % de variation
    crypto_data = []
    for row in crypto_rows:
        (cid, title, content, category, priority, ts, impact,
         price, market_cap, volume, vol_mcap, distance_ath, distance_atl, score, change_pct) = row

        change_val = change_pct if change_pct is not None else None
        change_str = f"{change_val:+.2f}%" if isinstance(change_val, (int, float)) else None

        crypto_data.append(
            {
                'id': cid,
                'title': title,
                'content': content,
                'category': category,
                'priority': priority,
                'timestamp': ts,
                'impact': impact,
                'change_val': change_val,
                'change_str': change_str,
                'price': price,
                'market_cap': market_cap,
                'volume': volume,
                'vol_mcap': vol_mcap,
                'distance_ath': distance_ath,
                'distance_atl': distance_atl,
                'score': score,
            }
        )

    # Calculer l'impact moyen sur tous les éléments affichés
    all_impacts = []
    for row in news_data:
        if row[6] is not None:
            try:
                all_impacts.append(abs(float(row[6])))
            except (TypeError, ValueError):
                pass
    for item in crypto_data:
        if item['impact'] is not None:
            try:
                all_impacts.append(abs(float(item['impact'])))
            except (TypeError, ValueError):
                pass
    avg_impact = (sum(all_impacts) / len(all_impacts) * 100) if all_impacts else None

    # Nombre de cryptos suivies (symboles distincts)
    crypto_symbols = set()
    for item in crypto_data:
        m = re.search(r"Crypto:\s*([A-Za-z0-9]+)", item['title'])
        if m:
            crypto_symbols.add(m.group(1))
    crypto_count = len(crypto_symbols)

    return render_template(
        'dashboard.html',
        news_data=news_data,
        crypto_data=crypto_data,
        is_premium=is_premium,
        email=session['email'],
        avg_impact=avg_impact,
        crypto_count=crypto_count,
        last_update=last_update,
    )

@app.route('/premium')
def premium():
    if 'user_id' not in session:
        return redirect('/login')
    
    return render_template('premium.html', stripe_key=PUBLISHABLE_KEY)

@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    if 'user_id' not in session:
        return redirect('/login')
    
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': PRICE_ID,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('payment_cancel', _external=True),
            customer_email=session['email'],
            client_reference_id=str(session['user_id']),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        return f"Erreur: {str(e)}"

@app.route('/payment-success')
def payment_success():
    if 'user_id' not in session:
        return redirect('/login')

    checkout_id = request.args.get('session_id', '')
    try:
        if not checkout_id.startswith('cs_'):
            raise ValueError('session_id manquant')
        checkout_session = stripe.checkout.Session.retrieve(checkout_id)
    except Exception as e:
        print(f"[SaaS] Vérification paiement impossible: {e}")
        flash("Paiement non vérifié. Si vous avez été débité, contactez le support.")
        return redirect('/premium')

    session_email = (checkout_session.get('customer_details') or {}).get('email') or checkout_session.get('customer_email')
    if (
        checkout_session.get('client_reference_id') != str(session['user_id'])
        or checkout_session.get('status') != 'complete'
        or checkout_session.get('payment_status') != 'paid'
        or (session_email or '').lower() != (session.get('email') or '').lower()
    ):
        flash("Paiement non vérifié. Si vous avez été débité, contactez le support.")
        return redirect('/premium')

    # Mettre à jour le plan de l'utilisateur
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE users SET plan = ?, stripe_customer_id = ?, stripe_subscription_id = ? WHERE id = ?',
        ('premium', checkout_session.get('customer'), checkout_session.get('subscription'), session['user_id']),
    )
    conn.commit()
    conn.close()
    
    session['plan'] = 'premium'
    flash('🎉 Bienvenue dans OmniCirelPC Premium !')
    return redirect('/dashboard')

@app.route('/payment-cancel')
def payment_cancel():
    flash('Paiement annulé. Vous pouvez réessayer plus tard.')
    return redirect('/premium')

@app.route('/export')
def export():
    if 'user_id' not in session:
        return redirect('/login')
    
    if not is_premium_user():
        flash("L'export CSV est réservé aux membres Premium.")
        return redirect('/premium')

    limit = 100
    
    conn = sqlite3.connect('omnicirelpc.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, content, category, timestamp FROM events ORDER BY timestamp DESC LIMIT ?", (limit,))
    data = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Titre', 'Contenu', 'Catégorie', 'Date'])
    
    for row in data:
        writer.writerow([row[0], row[1], row[2], row[3]])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=omnicirelpc_export.csv'}
    )

@app.route('/ads.txt')
def ads_txt():
    content = "google.com, pub-7810870385090344, DIRECT, f08c47fec0942fa0\n"
    return Response(content, mimetype='text/plain')


@app.route('/privacy')
def privacy():
    return send_from_directory('.', 'privacy.html')


SITE_URL = os.getenv('SITE_URL', 'https://omnicirelpc.onrender.com').rstrip('/')
RECAPS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recaps')
RECAP_SLUG_RE = re.compile(r'^\d{4}-W\d{2}$')
PREMIUM_PRICE_LABEL = '9,99 €/mois'
PUBLIC_PATHS = ['/', '/recaps', '/privacy']
PRIVATE_PATHS = [
    '/dashboard', '/alerts', '/premium', '/export', '/delete-account',
    '/run-scraper', '/create-checkout-session', '/payment-success',
    '/payment-cancel', '/webhook', '/logout', '/api/m2m',
]


def load_recap(slug):
    if not RECAP_SLUG_RE.match(slug or ''):
        return None
    path = os.path.join(RECAPS_DIR, slug + '.json')
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8') as f:
        recap = json.load(f)
    recap['slug'] = slug
    return recap


def list_recaps():
    if not os.path.isdir(RECAPS_DIR):
        return []
    slugs = [n[:-5] for n in os.listdir(RECAPS_DIR) if n.endswith('.json')]
    recaps = [load_recap(s) for s in sorted(slugs, reverse=True)]
    return [r for r in recaps if r]


@app.route('/recaps')
def recaps_index():
    return render_template('recaps_index.html', recaps=list_recaps(), site_url=SITE_URL)


@app.route('/recaps/<slug>')
def recap_page(slug):
    recap = load_recap(slug)
    if recap is None:
        return 'Récap introuvable', 404
    return render_template(
        'recap.html',
        recap=recap,
        site_url=SITE_URL,
        premium_price=PREMIUM_PRICE_LABEL,
    )


def _m2m_paid_unavailable():
    return jsonify({'error': 'm2m_not_configured', 'state': m2m.m2m_state()}), 503


@app.route('/api/m2m/status')
def m2m_status():
    state = m2m.m2m_state()
    state['docs'] = 'Paid endpoints are gated by the x402 protocol (HTTP 402).'
    return jsonify(state)


@app.route('/api/m2m/recaps')
def m2m_recaps():
    if not m2m.m2m_state()['enabled']:
        return _m2m_paid_unavailable()
    items = [
        {
            'slug': r['slug'],
            'title': r.get('title'),
            'published': r.get('published'),
            'period_label': r.get('period_label'),
            'description': r.get('description'),
        }
        for r in list_recaps()
    ]
    # Contrat M2M {data, meta} — les pages /recaps publiques sont du HTML
    # humain ; ici on vend le JSON structuré + provenance aux agents.
    return jsonify({
        'data': items,
        'meta': {
            'kind': 'recaps_index',
            'count': len(items),
            'generated_at': datetime.now().isoformat(),
            'source': 'omnicirelpc',
        }})


@app.route('/api/m2m/recaps/<slug>')
def m2m_recap(slug):
    if not m2m.m2m_state()['enabled']:
        return _m2m_paid_unavailable()
    recap = load_recap(slug)
    if recap is None:
        return jsonify({'error': 'not_found'}), 404
    return jsonify({
        'data': recap,
        'meta': {
            'kind': 'recap',
            'slug': slug,
            'generated_at': datetime.now().isoformat(),
            'source': 'omnicirelpc',
        }})


m2m.install_paywall(app)


@app.route('/robots.txt')
def robots_txt():
    lines = ['User-agent: *', 'Allow: /']
    lines += [f'Disallow: {p}' for p in PRIVATE_PATHS]
    lines += ['', f'Sitemap: {SITE_URL}/sitemap.xml', '']
    return Response('\n'.join(lines), mimetype='text/plain')


@app.route('/sitemap.xml')
def sitemap_xml():
    entries = [(SITE_URL + p, None) for p in PUBLIC_PATHS]
    entries += [(f"{SITE_URL}/recaps/{r['slug']}", r.get('published')) for r in list_recaps()]
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in entries:
        parts.append('  <url>')
        parts.append(f'    <loc>{xml_escape(loc)}</loc>')
        if lastmod:
            parts.append(f'    <lastmod>{xml_escape(lastmod)}</lastmod>')
        parts.append('  </url>')
    parts.append('</urlset>')
    return Response('\n'.join(parts) + '\n', mimetype='application/xml')


@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('stripe-signature')

    if not STRIPE_WEBHOOK_SECRET or not sig_header:
        return 'Invalid signature', 400

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        return 'Invalid signature', 400
    
    obj = event['data']['object']

    # Gérer les événements webhook ici
    if event['type'] == 'checkout.session.completed':
        # Abonnement souscrit - passage en premium
        if obj.get('payment_status') == 'paid' and obj.get('client_reference_id'):
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET plan = ?, stripe_customer_id = ?, stripe_subscription_id = ? WHERE id = ?',
                ('premium', obj.get('customer'), obj.get('subscription'), obj.get('client_reference_id')),
            )
            conn.commit()
            conn.close()
    elif event['type'] == 'invoice.payment_succeeded':
        # Paiement réussi - renouvellement d'abonnement
        set_plan_by_customer(obj.get('customer'), 'premium')
    elif event['type'] in ('customer.subscription.deleted', 'invoice.payment_failed'):
        # Abonnement annulé ou paiement échoué - retour au plan gratuit
        set_plan_by_customer(obj.get('customer'), 'free')
    
    return '', 200

init_users_db()
init_main_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# OmniCirelPC SaaS - Guide de Déploiement

## 📋 Prérequis

- Compte GitHub
- Compte Render.com
- Compte Stripe configuré avec produit créé

## 🚀 Déploiement sur Render.com

### 1. Préparation du dépôt Git

```bash
git init
git add .
git commit -m "Initial commit - OmniCirelPC SaaS"
git branch -M main
git remote add origin https://github.com/votre-username/omnicirelpc-saas.git
git push -u origin main
```

### 2. Configuration sur Render.com

1. Connectez-vous à [Render.com](https://render.com)
2. Cliquez sur "New +" → "Web Service"
3. Connectez votre dépôt GitHub
4. Configurez le service:
   - **Name**: omnicirelpc-saas
   - **Branch**: main
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: Free (pour commencer)

### 3. Variables d'environnement

Ajoutez ces variables dans Render.com (aucune valeur par défaut dans le code):
- `FLASK_ENV`: production
- `SECRET_KEY`: clé aléatoire longue pour signer les sessions Flask (obligatoire, l'app ne démarre pas sans), ex. `python -c "import secrets; print(secrets.token_hex(32))"`
- `STRIPE_SECRET_KEY`: votre clé secrète Stripe (`sk_live_...` en production)
- `STRIPE_PUBLISHABLE_KEY`: votre clé publiable Stripe (`pk_live_...`, même mode que la clé secrète)
- `STRIPE_PRICE_ID`: votre ID de prix Stripe (créé dans le même mode live/test que les clés)
- `STRIPE_WEBHOOK_SECRET`: secret de signature du webhook (`whsec_...`)
- `SMTP_USER`: adresse Gmail d'envoi des alertes
- `SMTP_PASSWORD`: mot de passe d'application Gmail
- `SMTP_HOST` (optionnel, défaut `smtp.gmail.com`), `SMTP_PORT` (optionnel, défaut `587`), `ALERT_FROM_EMAIL` (optionnel, défaut `SMTP_USER`)

### 4. Configuration Webhooks Stripe

Pour activer/désactiver Premium automatiquement:
1. Allez dans votre dashboard Stripe
2. Developers → Webhooks
3. Ajoutez l'URL: `https://votre-app.onrender.com/webhook`
4. Sélectionnez les événements:
   - `checkout.session.completed`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. Copiez le "Signing secret" dans `STRIPE_WEBHOOK_SECRET`

## 🧪 Tests locaux

### Installation
```bash
pip install -r requirements.txt
```

### Lancement
```bash
python app_saas.py
```

### Test avec carte Stripe (mode test)
- Numéro: 4242 4242 4242 4242
- Date: n'importe quelle date future
- CVV: 3 chiffres
- Code postal: 5 chiffres

## 📊 Fonctionnalités

### Utilisateurs Gratuits
- 5 articles par jour maximum
- Publicités affichées
- Analyses basiques
- Support communautaire

### Utilisateurs Premium (9,99€/mois)
- Articles illimités
- Aucune publicité
- Export CSV
- Alertes personnalisées
- Support prioritaire
- Analyses avancées

## 🔧 Maintenance

### Sauvegardes automatiques
Les bases de données SQLite sont sauvegardées dans le dépôt Git. Pour une production:
- Migrez vers PostgreSQL sur Render.com
- Configurez les sauvegardes automatiques

### Monitoring
- Utilisez les logs de Render.com
- Surveillez les métriques Stripe
- Configurez des alertes pour les échecs de paiement

## 🆘 Support

Pour toute question technique:
- Vérifiez les logs sur Render.com
- Consultez la documentation Stripe
- Contactez le support via email

## 📈 Monétisation

### Revenus attendus
- 100 utilisateurs @ 9,99€/mois = 999€/mois
- 500 utilisateurs @ 9,99€/mois = 4,995€/mois
- 1000 utilisateurs @ 9,99€/mois = 9,990€/mois

### Coûts Render.com
- Instance Free: 0€
- Instance Standard: ~7€/mois
- Instance Pro: ~25€/mois

## 🎯 Prochaines étapes

1. Déployer l'application
2. Tester les paiements Stripe
3. Configurer Google AdSense
4. Ajouter plus de fonctionnalités premium
5. Marketing et acquisition d'utilisateurs

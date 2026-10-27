# Configuration des transferts Flutterwave

Les clés Flutterwave restent exclusivement côté serveur. Ne les ajoutez jamais au
HTML, au JavaScript, au dépôt Git ou à une conversation.

## Configuration locale

Installez les dépendances et appliquez la migration :

```sh
pip install -r requirements.txt
python manage.py migrate
```

Créez une clé de chiffrement Fernet indépendante de la clé Django :

```sh
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Définissez les variables d’environnement dans l’environnement du processus
Django, en commençant par des clés Flutterwave de test :

```text
DJANGO_SECRET_KEY=<clé Django privée>
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
FLW_SECRET_KEY=<clé secrète Flutterwave de test>
FLW_WEBHOOK_SECRET_HASH=<secret hash configuré dans le tableau de bord Flutterwave>
FLW_DATA_ENCRYPTION_KEY=<clé Fernet générée pour ce déploiement>
FLW_TRANSFERS_ENABLED=false
```

La clé Fernet est nécessaire pour lire les coordonnées chiffrées déjà stockées.
Sauvegardez-la de façon privée et durable ; la perdre rend ces coordonnées
irrécupérables. En production, désactivez le mode debug, utilisez HTTPS et
définissez des hôtes autorisés explicites.

## Réglages Flutterwave

1. Terminez la vérification KYC et activez les transferts via API.
2. Vérifiez que le compte marchand a les soldes requis dans la devise débitée
   et, selon le corridor, dans la devise utilisée pour les frais de versement.
3. Configurez l’URL webhook `https://<votre-domaine>/api/flutterwave/webhook/`
   et le même secret hash que `FLW_WEBHOOK_SECRET_HASH`. Activez les événements
   `charge.completed` et `transfer.completed`, ainsi que les nouvelles tentatives.
4. Testez le paiement, la vérification du paiement et le versement avec les clés
   de test avant d’utiliser des clés de production.
5. Après validation du paiement, des webhooks et des versements, définissez
   `FLW_TRANSFERS_ENABLED=true` pour activer le formulaire.

Le parcours vérifie les paiements auprès de Flutterwave avant de demander le
versement. Les destinations et réseaux affichés comme indisponibles sont bloqués
avant le paiement. La disponibilité réelle dépend aussi du KYC, des devises,
des autorisations et des soldes de votre compte Flutterwave.

Un échec de versement après encaissement est signalé comme « Versement à
vérifier » dans l’administration. Ce prototype ne déclenche pas automatiquement
de remboursement ; vérifiez et rapprochez ces transactions avant toute mise en
production. La documentation Flutterwave précise que ses taux de transfert
sont actualisés plusieurs fois par jour ; les conversions sont indicatives et
hors frais.

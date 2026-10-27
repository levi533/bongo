# Déployer BONGO sur Vercel

Vercel détecte l’application Django à partir de `manage.py` et de
`WSGI_APPLICATION`. Les fichiers statiques de `static/` sont collectés depuis
`STATICFILES_DIRS` dans `STATIC_ROOT` pendant le build, puis servis par le CDN
Vercel. Aucun serveur `runserver`, fichier `vercel.json` ou commande de build
personnalisée n’est nécessaire.

## Préparer le projet

1. Importez le dépôt GitHub `levi533/bongo` dans Vercel. Laissez le répertoire
   racine du projet à la racine du dépôt.
2. Créez une base de données PostgreSQL persistante, par exemple via une
   intégration Neon, puis ajoutez sa chaîne de connexion TLS comme variable
   `DATABASE_URL` dans les environnements Vercel **Production** et **Preview**.
   Une base SQLite n’est pas persistante sur Vercel.
3. Ajoutez les variables de déploiement suivantes dans Vercel :

   - `DJANGO_SECRET_KEY` : une clé Django secrète et aléatoire.
   - `DJANGO_DEBUG` : `false`.
   - `DJANGO_ALLOWED_HOSTS` : les hôtes autorisés, séparés par des virgules
     (par exemple `bongo.example.com,www.bongo.example.com`). Les domaines
     `*.vercel.app` et l’URL de déploiement Vercel sont déjà ajoutés.
   - `DJANGO_CSRF_TRUSTED_ORIGINS` : les origines HTTPS personnalisées séparées
     par des virgules, si vous avez un domaine propre.
   - `FLW_SECRET_KEY`, `FLW_WEBHOOK_SECRET_HASH` et `FLW_DATA_ENCRYPTION_KEY`
     uniquement si vous configurez Flutterwave. Générez la clé de chiffrement
     avec `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
     et conservez-la durablement : sa perte rendrait les coordonnées chiffrées
     irrécupérables.
   - `FLW_TRANSFERS_ENABLED=false` jusqu’à validation complète des paiements,
     webhooks et versements Flutterwave.

4. Laissez Vercel détecter automatiquement le framework et la commande de build.
   Le déploiement installe les dépendances de `requirements.txt` ; le runtime
   Python de Vercel découvre `bongo_site.wsgi.application`.
5. Après avoir renseigné `DATABASE_URL`, appliquez les migrations à la base de
   production une seule fois depuis un terminal de confiance :

   ```sh
   vercel env pull .env.vercel
   set -a
   . ./.env.vercel
   set +a
   python manage.py migrate
   ```

   Le fichier `.env.vercel` est ignoré par Git. Ne le partagez pas et ne le
   commitez pas.
6. Déployez depuis Vercel ou avec `vercel --prod`. Vérifiez ensuite la page,
   les fichiers `/static/` et les avis avec l’URL fournie.

Les transferts restent bloqués par défaut. Ne définissez
`FLW_TRANSFERS_ENABLED=true` qu’après validation des variables Flutterwave,
du webhook public HTTPS, des migrations et d’un essai réel ou de test complet.

Références : [documentation Django de Vercel](https://vercel.com/docs/frameworks/full-stack/django),
[runtime Python de Vercel](https://vercel.com/docs/functions/runtimes/python),
[configuration Django/Neon](https://neon.com/docs/guides/django).

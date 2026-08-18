# Déployer ApplyMatch AI

Architecture recommandée : PostgreSQL sur Neon, API FastAPI sur Render et frontend Next.js sur Vercel.

## 1. PostgreSQL (Neon)

1. Créer un projet Neon.
2. Copier la chaîne de connexion PostgreSQL.
3. Sur Render, créer la variable `DATABASE_URL` avec cette chaîne. Si elle commence par `postgresql://`, la remplacer par `postgresql+psycopg://`.

## 2. API (Render)

1. Connecter le dépôt GitHub et créer un Blueprint avec `render.yaml`.
2. Renseigner les variables marquées comme secrètes :
   - `DATABASE_URL`
   - `ADMIN_EMAIL`
   - `ADMIN_PASSWORD` (au moins 12 caractères)
   - `CORS_ORIGINS` (URL Vercel, sans slash final)
3. Déployer. Le démarrage applique les migrations et crée l’administrateur seulement s’il n’existe pas.
4. Vérifier `https://VOTRE-API.onrender.com/health`.

Ne jamais mettre `.env`, un mot de passe ou une clé API dans GitHub.

## 3. Frontend (Vercel)

1. Importer le même dépôt GitHub.
2. Choisir `frontend` comme **Root Directory**.
3. Ajouter `NEXT_PUBLIC_API_URL=https://VOTRE-API.onrender.com`.
4. Déployer.
5. Reporter l’URL Vercel dans `CORS_ORIGINS` sur Render puis redéployer l’API.

## 4. Vérification finale

Tester : connexion → import d’une offre → calcul du score → recommandation → ajout à la validation manuelle.

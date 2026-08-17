# Passage d'ApplyMatch AI à PostgreSQL

## 1. Installer les fichiers

Décompressez l'archive dans le projet avec les commandes fournies dans la conversation.

## 2. Installer Docker Desktop

Docker Desktop doit être installé et démarré sous Windows.

## 3. Configurer `.env`

Ajoutez ces lignes au fichier `.env` existant à la racine du projet :

```env
POSTGRES_DB=applymatch
POSTGRES_USER=applymatch
POSTGRES_PASSWORD=applymatch_local_password
DATABASE_URL=postgresql+psycopg://applymatch:applymatch_local_password@127.0.0.1:5432/applymatch
```

Conservez toutes les clés API et la clé JWT déjà présentes dans `.env`.

## 4. Démarrer PostgreSQL

```powershell
docker compose up -d postgres
docker compose ps
```

## 5. Installer le pilote et créer les tables

```powershell
pip install -r requirements.txt
python scripts\check_database.py
alembic upgrade head
alembic current
```

## 6. Vérifier ApplyMatch

```powershell
python -m pytest tests -q
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --env-file .env
```

L'ancien fichier `applymatch.db` n'est pas supprimé. Il reste disponible comme sauvegarde locale, mais l'application utilise PostgreSQL dès que `DATABASE_URL` est défini dans `.env`.


# ApplyMatch AI

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Render](https://img.shields.io/badge/Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)

Assistant qui collecte des offres d'alternance en cybersécurité, cloud,
réseaux, SOC et DevSecOps, les note par rapport à un profil, et prépare les
candidatures — sans jamais en envoyer une sans validation humaine.

## Le principe

```
Collecte automatique  →  Score explicable  →  File de validation  →  Documents générés  →  Brouillon Gmail
   (8 sources)             (règles /100)        (l'utilisateur          (CV adapté +          (prêt à relire et
                                                   décide)                 lettre en PDF)         envoyer soi-même)
```

Aucune étape ne saute la validation humaine : le score sert à trier et
prioriser, jamais à décider seul, et même la dernière étape s'arrête à un
**brouillon** Gmail — l'envoi reste un clic humain, jamais automatique.

## Fonctionnalités

- **Collecte multi-sources** : France Travail, La Bonne Alternance, Choisir
  le service public, Emploi Territorial, et les pages carrières Greenhouse,
  Lever, SmartRecruiters et Jooble — uniquement des API publiques, aucun
  scraping non autorisé.
- **Score de compatibilité explicable**, fondé sur des règles vérifiables
  plutôt qu'une boîte noire (détail ci-dessous).
- **File de validation manuelle** pour les offres ambiguës ou au score
  intermédiaire.
- **Génération de brouillons de candidature** (lettre de motivation en PDF/
  DOCX) à partir du profil et de l'offre.
- **Brouillon Gmail prêt à envoyer** (CV adapté + lettre de motivation en
  pièces jointes) une fois la candidature validée — jamais d'envoi
  automatique, l'utilisateur reste celui qui clique sur "Envoyer".
- **Notifications** sur les offres à fort score.
- **Historique des candidatures** et suivi du statut de chaque offre.
- **Tâches de fond** (Celery + Redis) pour la collecte périodique et les
  traitements longs, sans bloquer l'API.

## Algorithme de matching

Une offre n'est admissible que si elle respecte **tous** ces filtres :
alternance/apprentissage/stage, Île-de-France ou télétravail complet,
expérience demandée entre 0 et 2 ans (ou débutant accepté), correspondance
avec un domaine ciblé ou une technologie prouvée, offre ni archivée ni déjà
postulée.

Les offres admissibles reçoivent un score sur 100 :

| Critère | Points |
|---|---:|
| Technologies prouvées | 30 |
| Domaine / métier ciblé | 25 |
| Alternance ou stage | 15 |
| Expérience 0–2 ans | 10 |
| Île-de-France / télétravail compatible | 10 |
| Profil, études et missions | 5 |
| Fraîcheur de l'offre | 5 |

- Filtre obligatoire échoué → `rejected`
- Score < 70 → `manual_review` (file de validation)
- Score ≥ 70 → `automatic_ready` (documents préparables automatiquement,
  envoi toujours soumis à confirmation)

Détail complet dans [`docs/MATCHING-V2.md`](docs/MATCHING-V2.md).

## Architecture

| | |
|---|---|
| **Backend** | Python, FastAPI, SQLAlchemy 2, Alembic, Celery + Redis (tâches de fond), Playwright (assistance navigateur) |
| **Frontend** | Next.js, React, TypeScript, TanStack Query, Tailwind CSS |
| **Base de données** | PostgreSQL |
| **Authentification** | JWT, mots de passe hashés en Argon2 |
| **Observabilité** | Sentry |
| **Tests** | Pytest (backend), Vitest + Testing Library (frontend) |
| **Déploiement** | API sur Render, base de données sur Neon, frontend sur Vercel |

```
applymatch-ai/
├── app/
│   ├── api/routes/       # endpoints (offres, matching, validation, candidatures, gmail...)
│   ├── services/         # collecteurs, moteur de score, génération de documents, envoi Gmail
│   ├── background/       # tâches Celery
│   └── models/           # SQLAlchemy
├── frontend/              # tableau de bord Next.js
├── migrations/            # Alembic
├── docs/                  # cahier des charges, backlog, algorithme de matching
└── tests/
```

## Principes

- Aucune expérience ni compétence inventée dans les documents générés.
- Aucun scraping non autorisé — uniquement des API publiques.
- Aucune candidature envoyée sans validation humaine.
- Score explicable, fondé d'abord sur des règles vérifiables plutôt que sur
  une IA opaque (la génération de texte par IA est une option désactivable,
  pas le cœur du scoring).
- Secrets et données personnelles exclus du dépôt.

## Lancer le projet en local

**Base de données et Redis :**

```bash
docker compose -f compose.yaml up -d
```

**Backend :**

```bash
pip install -r requirements.txt
cp .env.example .env   # puis renseigner les variables nécessaires
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend :**

```bash
cd frontend
npm install
npm run dev
```

## Lancer les tests

```bash
# Backend
pytest

# Frontend
cd frontend && npm test
```

## Déploiement

API sur Render (voir `render.yaml`), base de données PostgreSQL sur Neon,
frontend sur Vercel. Étapes détaillées dans
[`DEPLOYMENT.md`](DEPLOYMENT.md).

## Documentation

- [Cahier des charges](docs/CAHIER-DES-CHARGES.md)
- [Backlog V1](docs/BACKLOG-V1.md)
- [Algorithme de matching](docs/MATCHING-V2.md)

## Auteur

Olivier Polynice — Portfolio

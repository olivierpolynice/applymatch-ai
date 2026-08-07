ApplyMatch AI

Assistant intelligent d'analyse, de classement et de préparation des candidatures.

Objectif

ApplyMatch AI aide à évaluer des offres d'alternance en cybersécurité, cloud, réseaux, SOC et DevSecOps. L'application centralisera un profil et des offres, expliquera leur compatibilité et préparera des candidatures honnêtes. Toute candidature restera soumise à une validation humaine.

Statut

Le projet est en phase P0 — cadrage et initialisation. Aucune fonctionnalité d'analyse par IA n'est encore annoncée comme disponible.

La première version fonctionnelle sera locale et mono-utilisateur. Elle permettra d'enregistrer un profil et d'ajouter, consulter, modifier, filtrer et supprimer des offres saisies manuellement.

Périmètre V1

profil professionnel et critères de recherche ;

compétences et métiers ciblés ;

ajout manuel d'une offre ;

validation et nettoyage des entrées ;

liste, filtres et détail des offres ;

modification, suppression et changement de statut ;

détection des doublons évidents ;

tests essentiels.

Le score de compatibilité, l'import du CV, la génération de candidatures, la collecte automatique et les alertes arriveront dans des versions ultérieures.

Architecture prévue

Backend : Python, FastAPI, Pydantic, SQLAlchemy 2 et Alembic

Frontend : React, TypeScript et Vite

Base de données : PostgreSQL avec Docker

Tests : Pytest, Vitest et Testing Library

Architecture : monolithe modulaire avec API HTTP JSON

applymatch-ai/
├── backend/                # API FastAPI (créée en V1)
├── frontend/               # application React (créée en V1)
├── docs/
│   ├── CAHIER-DES-CHARGES.md
│   └── BACKLOG-V1.md
├── .gitignore
└── README.md

Principes

fonctionnement réel avant le design final ;

score futur explicable, fondé d'abord sur des règles vérifiables ;

aucune expérience ni compétence inventée ;

aucun scraping non autorisé ;

aucune candidature envoyée sans validation humaine ;

secrets et données personnelles exclus du dépôt.

Documentation

Cahier des charges P0

Backlog de la V1

Auteur

Olivier Polynice — Portfolio · LinkedIn
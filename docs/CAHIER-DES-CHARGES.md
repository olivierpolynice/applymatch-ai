ApplyMatch AI — Cahier des charges P0

Version : 1.2Date : 7 août 2026Porteur du projet : Olivier PolyniceStatut : P0-B en cours

Vision

ApplyMatch AI est un assistant personnel de recherche d'alternance. Il centralise un profil et des offres, mesure leur compatibilité de manière explicable, classe les opportunités et prépare des candidatures honnêtes. Olivier conserve toujours la décision finale.

Coller une offre et savoir rapidement si elle correspond réellement à mon profil, pourquoi, et quelle action entreprendre.

La première version est locale, mono-utilisateur et centrée sur les alternances en cybersécurité, systèmes et réseaux, cloud, DevSecOps, SOC et sécurité réseau en Île-de-France.

Périmètre V1

La V1 permet de gérer le profil, les compétences, les métiers ciblés et des offres ajoutées manuellement. Les offres peuvent être validées, nettoyées, conservées, recherchées, filtrées, modifiées, supprimées et classées par statut. Les doublons évidents sont signalés et les parcours essentiels sont testés.

Sont exclus de la V1 : import PDF, score de compatibilité, analyse sémantique, génération de messages, collecte automatique, scraping, notifications, envoi de candidature, authentification multi-utilisateur, statistiques avancées et design final.

Parcours V1

Olivier ouvre l'application locale.

Il consulte ou complète son profil.

Il saisit les informations d'une offre et colle sa description.

Le backend valide, normalise et nettoie les données.

Le système recherche un doublon évident.

L'offre est enregistrée avec le statut nouvelle.

Olivier la consulte, la filtre, la modifie, change son statut ou la supprime.

Architecture retenue

Élément

Choix

Backend

Python, FastAPI et Pydantic

Frontend

React, TypeScript et Vite

Base de données

PostgreSQL dans Docker

ORM et migrations

SQLAlchemy 2 et Alembic

Tests

Pytest, Vitest et Testing Library

Communication

API HTTP JSON avec fetch

Architecture

Monolithe modulaire

Authentification V1

Aucune, usage local mono-utilisateur

IA V2

Règles explicables puis analyse sémantique remplaçable

Les microservices, le RBAC, Prometheus et Grafana ne sont pas retenus en V1.

Modèle de données initial

Profile : identité professionnelle, formation, contrat, date de début, rythme, localisation et liens.

Skill : nom, nom normalisé et catégorie.

ProfileSkill : relation, niveau et preuve issue d'un projet, d'une formation ou d'une expérience.

TargetRole : métier ciblé associé au profil.

JobOffer : titre, entreprise, localisation, contrat, niveau, rythme, source, URL, description nettoyée, date, statut, empreinte et dates techniques.

Les analyses et sous-scores seront stockés séparément en V2.

Pages V1

Tableau de bord minimal

Mon profil

Ajouter une offre

Mes offres

Détail d'une offre

Sécurité et fiabilité

Toute description d'offre est une donnée externe non fiable.

Les entrées sont validées côté backend et leur taille est limitée.

Aucun HTML actif externe n'est rendu directement.

Les secrets restent dans des variables d'environnement.

Les erreurs n'exposent pas de données personnelles.

Aucun CV réel ni jeu de données personnel n'est publié.

Aucune candidature n'est envoyée automatiquement.

Aucune plateforme n'est collectée sans autorisation vérifiée.

Risques principaux

Risque

Réponse

Périmètre trop grand

Bloquer la V2 jusqu'à la validation complète de la V1

Faux score par mots-clés

Règles explicables et tests sur de vraies offres en V2

Hallucination

Génération limitée aux preuves enregistrées

Prompt injection

Isoler l'offre comme donnée externe non fiable

Blocage des plateformes

Aucun scraping non autorisé

Données personnelles exposées

Exécution locale et démonstration séparée

Répétition des anciens projets

Pas de RBAC ni d'observabilité avancée en V1

Définition de terminé — V1

La V1 est terminée lorsque le profil et les critères persistent, qu'une offre valide peut être ajoutée et gérée entièrement, que les doublons évidents sont signalés, que les erreurs sont sûres et compréhensibles, que les tests critiques réussissent et que le lancement sous Windows est documenté. Aucun secret, CV réel ou fonctionnalité fictive ne doit être présent dans le dépôt.

Validation du P0

Cahier des charges validé

Périmètre V1 figé

Architecture et modèle de données validés

Pages, parcours et risques validés

Dépôt GitHub public créé

README initial préparé

.gitignore préparé

Arborescence initiale définie

Backlog V1 préparé

Premier commit poussé

Une fois le premier commit vérifié sur main, le P0 sera officiellement terminé.
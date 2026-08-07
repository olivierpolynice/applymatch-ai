ApplyMatch AI — Backlog V1

Objectif V1 : enregistrer un profil et gérer manuellement de vraies offres dans une application locale fiable.

Ordre de réalisation

V1.1 — Socle backend

Initialiser Python et FastAPI.

Ajouter la configuration par variables d'environnement.

Créer GET /api/v1/health.

Ajouter un premier test Pytest.

Documenter le lancement sous Windows et Visual Studio Code.

V1.2 — Persistance

Configurer PostgreSQL avec Docker Compose.

Configurer SQLAlchemy 2.

Configurer Alembic.

Créer et vérifier la migration initiale.

V1.3 — Profil

Créer les modèles Profile, Skill, ProfileSkill et TargetRole.

Afficher le profil unique.

Modifier le profil et ses critères.

Gérer les compétences et leurs preuves.

Tester les validations et la persistance.

V1.4 — Offres

Créer le modèle JobOffer et ses statuts.

Ajouter une offre manuellement.

Valider et nettoyer les champs.

Détecter les doublons évidents par URL et empreinte normalisée.

Lister, rechercher, filtrer et trier les offres.

Consulter, modifier et supprimer une offre.

Tester les cas valides, invalides et les doublons.

V1.5 — Interface

Initialiser React, TypeScript et Vite.

Créer la navigation et le tableau de bord minimal.

Créer la page Mon profil.

Créer le formulaire Ajouter une offre.

Créer la liste et les filtres.

Créer la page de détail et les actions.

Afficher proprement les erreurs et états de chargement.

V1.6 — Validation finale

Ajouter les tests frontend essentiels.

Vérifier le parcours complet sur Windows.

Vérifier qu'aucun secret, CV ou donnée personnelle sensible n'est commité.

Mettre à jour le README avec les fonctions réellement disponibles.

Valider tous les critères de fin de V1 du cahier des charges.

Règle de périmètre

Le score de compatibilité, l'import PDF, la génération de candidature, la collecte automatique, les notifications et les statistiques ne font pas partie de la V1. Une nouvelle fonctionnalité ne peut entrer en V1 que si une fonctionnalité de poids comparable en sort.
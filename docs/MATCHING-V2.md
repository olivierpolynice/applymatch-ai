# ApplyMatch AI — Algorithme de matching V2

## Filtres obligatoires

Une offre est admissible uniquement si elle respecte toutes ces règles :

- alternance, apprentissage, professionnalisation ou stage ;
- Île-de-France ou télétravail complet depuis la France ;
- expérience demandée comprise entre 0 et 2 ans, ou débutant accepté ;
- correspondance avec un domaine ciblé ou une technologie prouvée ;
- offre non archivée et non déjà postulée.

Une alternance publiée techniquement comme `CDD 12 mois` reste admissible si
le titre ou la description indique clairement `alternance`, `apprentissage`
ou `professionnalisation`.

## Score sur 100

| Critère | Points |
|---|---:|
| Technologies prouvées | 30 |
| Domaine/métier ciblé | 25 |
| Alternance ou stage | 15 |
| Expérience 0–2 ans | 10 |
| Île-de-France/télétravail compatible | 10 |
| Profil, études et missions | 5 |
| Fraîcheur de l’offre | 5 |

## Décisions

- filtre obligatoire échoué : `rejected` ;
- offre admissible avec score inférieur à 70 : `manual_review` ;
- offre admissible avec score supérieur ou égal à 70 : `automatic_ready`.

`automatic_ready` signifie que les documents peuvent être préparés
automatiquement. L’envoi réel reste conditionné à un canal officiellement
compatible, à l’absence de question inconnue et à une confirmation externe.

## Sections de l’interface

- Nouvelles ;
- À examiner (`score < 70`) ;
- Prioritaires (`score >= 70`) ;
- Rejetées ;
- Déjà postulé (historique et documents archivés).

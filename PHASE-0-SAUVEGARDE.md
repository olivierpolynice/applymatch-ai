# Phase 0 — Sauvegarder ApplyMatch AI

Cette phase ne modifie ni l'algorithme ni les donnees. Elle cree une sauvegarde
hors du dossier du projet.

## 1. Creer un point de retour Git

Dans PowerShell :

```powershell
cd C:\DevOps\applymatch-ai
git status
git add .
git commit -m "checkpoint avant ApplyMatch V3"
git push origin HEAD
```

Ne lance pas `git add .` si `git status` affiche un fichier `.env`, un mot de
passe ou une cle API. Le fichier `.env` doit rester ignore par Git.

## 2. Executer la sauvegarde complete

```powershell
cd C:\DevOps\applymatch-ai
powershell -ExecutionPolicy Bypass -File .\scripts\backup_phase0.ps1
```

Le script cree par defaut :

```text
C:\DevOps\applymatch-ai-backups\applymatch-ai-AAAAMMJJ-HHMMSS\
```

Il enregistre :

- `repository.bundle` : historique Git complet ;
- `source-code.zip` : code actuel sans `.env`, environnements et dependances ;
- `working-tree.patch` : modifications non commitees ;
- `applymatch.db` ou `applymatch.dump` : sauvegarde de la base ;
- `.env.example` et `env-keys-only.txt` : structure de configuration sans secrets ;
- `MANIFEST.txt` : controle de la sauvegarde.

## 3. Verifier le resultat

```powershell
Get-ChildItem C:\DevOps\applymatch-ai-backups |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
```

Ouvre le dernier dossier puis verifie que `MANIFEST.txt` contient :

```text
Base sauvegardee : True
Secrets .env inclus : False
```

La phase 1 ne commence que lorsque ces deux lignes sont correctes et que le
`git push` a reussi.

## Restauration d'urgence

Pour reconstruire le depot Git dans un nouveau dossier :

```powershell
git clone "C:\DevOps\applymatch-ai-backups\DOSSIER\repository.bundle" `
    "C:\DevOps\applymatch-ai-restored"
```

La restauration de la base depend de son type. Ne remplace jamais la base
actuelle avant d'en faire une seconde copie.

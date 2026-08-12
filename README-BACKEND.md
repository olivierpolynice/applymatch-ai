# Backend ApplyMatch AI

Le backend FastAPI charge automatiquement le profil unique situé dans
`candidate_profile/candidate_profile.yaml`. Au démarrage, il synchronise ce
profil en base et désactive les anciens profils.

## Installation (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Lancement

```powershell
uvicorn app.main:app --reload
```

API : `http://127.0.0.1:8000`

Documentation : `http://127.0.0.1:8000/docs`

## Test de synchronisation

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/candidate-profiles/sync
Invoke-RestMethod http://127.0.0.1:8000/candidate-profiles
```

## Tests

```powershell
pytest -q
```

La route historique `POST /candidate-profiles` reste présente pour la
compatibilité des tests. Le profil utilisé normalement par l'application est
celui du fichier YAML.

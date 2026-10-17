# SmartMed — Backend & IA

API REST (FastAPI + PostgreSQL) et modules d'intelligence artificielle
de l'application SmartMed.

## Prérequis

- Python (version à préciser)
- PostgreSQL installé et démarré

## Installation

```bash
git clone <URL-DU-DEPOT>
cd <NOM-DU-DOSSIER>
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Copiez `.env.example` en `.env`, puis remplissez les valeurs
(base de données, clé secrète JWT). **Ne commitez jamais `.env`.**

## Lancer l'API

```bash
uvicorn app.main:app --reload
```

- Swagger : http://localhost:8000/docs
- Pour tester depuis un téléphone : ajouter `--host 0.0.0.0`

## Structure

| Dossier | Rôle |
|---|---|
| `app/api/routes/` | endpoints (auth, users...) |
| `app/schemas/` | formats d'entrée et de sortie (Pydantic) |
| `app/models/` | tables SQLAlchemy |
| `app/services/` | logique métier |
| `app/core/` | configuration, sécurité (JWT) |
| `AI/` | modules IA (recommandation, avis, temps d'attente) |

## Contrat API

Tout changement d'endpoint ou de champ est annoncé au Frontend
**avant** le merge. Swagger doit rester à jour.

## Tests

```bash
pytest
```

## Règles Git

- Ne jamais développer sur `main`.
- Une branche par fonctionnalité : `feature/backend-...`
- Une Pull Request par fonctionnalité, avec tests.
- Aucun secret dans Git.
# SmartMed — Backend

API REST de SmartMed construite avec **FastAPI**, **SQLAlchemy** et **PostgreSQL**.
Sprint 1 : authentification et gestion du profil utilisateur.

## Stack

- Python 3.10+
- FastAPI + Uvicorn
- PostgreSQL + SQLAlchemy
- JWT (PyJWT) + bcrypt
- Pytest

## Structure

```
backend/
├── app/
│   ├── main.py          # point d'entrée
│   ├── core/            # config, sécurité (hash, JWT)
│   ├── db/              # engine, session, Base
│   ├── models/          # tables SQLAlchemy
│   ├── schemas/         # validation Pydantic (entrée/sortie)
│   ├── services/        # logique métier
│   └── api/
│       ├── deps.py      # dépendances (get_current_user)
│       └── routes/      # endpoints
├── tests/
├── requirements.txt
└── .env.example
```

## Installation

### 1. Prérequis

- Python 3.10+
- PostgreSQL installé et démarré

### 2. Environnement virtuel

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1      # Linux/Mac : source venv/bin/activate
pip install -r requirements.txt
```

### 3. Base de données

Dans `psql -U postgres` :

```sql
CREATE USER smartmed_user WITH PASSWORD 'votre_mot_de_passe';
CREATE DATABASE smartmed OWNER smartmed_user;
```

### 4. Configuration

```powershell
copy .env.example .env
```

Puis remplir `.env` avec vos propres valeurs. Générer une clé secrète :

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

| Variable | Description |
|---|---|
| `DATABASE_URL` | URL PostgreSQL de connexion |
| `SECRET_KEY` | Clé de signature des JWT (ne jamais la commiter) |
| `ALGORITHM` | Algorithme JWT (`HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée de vie du token |

### 5. Créer les tables

```powershell
python -c "import app.models; from app.db.base import Base; from app.db.session import engine; Base.metadata.create_all(bind=engine)"
```

## Lancer le serveur

```powershell
uvicorn app.main:app --reload
```

- API : http://127.0.0.1:8000
- Swagger : http://127.0.0.1:8000/docs

## Tests

```powershell
python -m pytest -v
```

Les tests utilisent une base SQLite en mémoire : la base PostgreSQL n'est pas touchée.

## Contrat API (Sprint 1)

| ID | Méthode | Endpoint | But | Auth | Succès | Erreurs |
|---|---|---|---|---|---|---|
| A01 | POST | `/auth/register` | Créer un compte | Non | 201 | 409, 422 |
| A02 | POST | `/auth/login` | Connexion + JWT | Non | 200 | 401 |
| A03 | POST | `/auth/logout` | Déconnexion | Oui | 200 | 401 |
| A04 | GET | `/users/me` | Voir le profil | Oui | 200 | 401 |
| A05 | PUT | `/users/me` | Modifier le profil | Oui | 200 | 401, 422 |

### Exemples

**Register** — `POST /auth/register`

```json
{ "name": "Sarra", "email": "sarra@mail.com", "password": "123456" }
```

Réponse `201` :

```json
{
  "id": 1,
  "name": "Sarra",
  "email": "sarra@mail.com",
  "role": "Patient",
  "created_at": "2026-10-11T10:00:00Z"
}
```

**Login** — `POST /auth/login`

```json
{ "email": "sarra@mail.com", "password": "123456" }
```

Réponse `200` :

```json
{ "access_token": "JWT...", "token_type": "bearer" }
```

Erreur `401` : `{ "detail": "Invalid credentials" }`

**Routes protégées** : envoyer l'en-tête

```
Authorization: Bearer <access_token>
```

### Règles de validation

- `name` : 2 à 100 caractères
- `email` : format email valide, unique (insensible à la casse)
- `password` : 6 à 72 caractères
- Le `role` ne peut pas être choisi par l'utilisateur (toujours `Patient`)

## Sécurité

- Mots de passe hashés avec bcrypt, jamais stockés en clair
- JWT signé avec `SECRET_KEY`, avec expiration
- Aucun secret dans Git : `.env` est ignoré, `.env.example` sert de modèle

## Workflow Git

- Ne jamais coder sur `main`
- Une branche par fonctionnalité, une Pull Request par fonctionnalité
- Prévenir le Frontend avant de modifier un endpoint ou un champ JSON
- Lancer `python -m pytest -v` avant chaque merge
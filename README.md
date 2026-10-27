# CoachUp — Back-end

API de CoachUp en **FastAPI** (Python 3.12) avec **PostgreSQL**.

## Stack

| Rôle | Outil |
|---|---|
| Framework | FastAPI |
| ORM | SQLAlchemy 2 (async) + asyncpg |
| Migrations | Alembic |
| Config | pydantic-settings (`.env`) |
| Dépendances | [uv](https://docs.astral.sh/uv/) |
| Lint / format | Ruff |
| Tests | pytest + httpx |
| Métriques | Prometheus (`/metrics`) |
| Emails en local | Mailpit |

## Démarrage rapide

Prérequis : [uv](https://docs.astral.sh/uv/getting-started/installation/) et Docker.

```bash
cp .env.example .env              # puis adapter si besoin
docker compose up -d db mailpit   # Postgres + Mailpit
uv sync                           # installe Python 3.12 + dépendances
uv run alembic upgrade head       # applique les migrations
uv run fastapi dev app/main.py    # API sur http://localhost:8000
```

- Documentation Swagger : http://localhost:8000/docs
- Healthcheck : http://localhost:8000/api/v1/health (et `/health/db`)
- Métriques : http://localhost:8000/metrics
- Boîte mail de dev (Mailpit) : http://localhost:8025

> Un Postgres tourne déjà sur ta machine (port 5432) ? Mets `POSTGRES_PORT=5433` dans `.env`.

Tout lancer dans Docker (API comprise, avec rechargement auto) :

```bash
docker compose --profile full up --build --watch
```

## Commandes utiles

```bash
uv run pytest                                      # tests (nécessite la BDD)
uv run ruff check --fix . && uv run ruff format .  # lint + format
uv add <paquet>                                    # ajouter une dépendance
uv run alembic revision --autogenerate -m "msg"    # nouvelle migration
uv run alembic upgrade head                        # appliquer les migrations
uv run alembic downgrade -1                        # annuler la dernière
```

## Architecture

```
app/
├── main.py              # création de l'app FastAPI, CORS, métriques
├── core/config.py       # settings lus depuis .env
├── db/
│   ├── base.py          # Base SQLAlchemy + TimestampMixin
│   └── session.py       # engine + session async
├── models/              # modèles SQLAlchemy (tables)
├── schemas/             # schémas Pydantic (entrées/sorties API)
└── api/
    ├── deps.py          # dépendances partagées (SessionDep…)
    └── v1/
        ├── router.py    # agrège les routes v1
        └── routes/      # un fichier par domaine (auth, users…)
alembic/                 # migrations de la BDD
tests/
```

### Ajouter une fonctionnalité

1. Modèle dans `app/models/<domaine>.py`, puis l'importer dans `app/models/__init__.py`.
2. Générer la migration : `uv run alembic revision --autogenerate -m "..."` et **relire** le fichier généré.
3. Schémas Pydantic dans `app/schemas/<domaine>.py`.
4. Routes dans `app/api/v1/routes/<domaine>.py`, puis les brancher dans `app/api/v1/router.py`.
5. Tests dans `tests/`.

Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour le workflow Git.

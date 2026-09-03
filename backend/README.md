# Backend

FastAPI app under `app/`. Entry point: `app/main.py`.

## Module layout

```
app/
├── api/main.py       # mounts system + base + apps routers
├── core/             # config, db, security, arq
├── worker/           # ARQ WorkerSettings + tasks
└── modules/
    ├── system/       # health-check, private dev routes
    ├── base/         # platform (auth, users, …)
    └── apps/         # product-specific APIs (+ sample/)
```

## Canonical example

Inspect `app/modules/apps/sample/` before building new features — notes CRUD with router, service, repository, models, schemas, and migration.

## Local run (without Docker)

From repo root after `fast-svelte-ctrl setup-local`:

```bat
.venv\Scripts\activate
cd backend
set PYTHONPATH=%CD%
uvicorn app.main:app --reload --port 8000
```

Migrations:

```bat
cd backend
set PYTHONPATH=%CD%
alembic -c alembic.ini upgrade head
```

Worker (full runtime):

```bat
cd backend
..\.venv\Scripts\python.exe -m arq app.worker.worker.WorkerSettings
```

## API docs

| URL | UI |
|-----|-----|
| `/docs` | Swagger UI |
| `/sdoc` | Scalar |

OpenAPI schema: `/api/v1/openapi.json`

## Docker

Built from root `requirements.txt`. Prestart runs migrations + seeds `FIRST_SUPERUSER`.

Full docs: [docs/architecture.md](../docs/architecture.md) · [docs/modules.md](../docs/modules.md)

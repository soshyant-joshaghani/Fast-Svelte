# Architecture

Fast-Svelte is a modular full-stack foundation. This document describes how the pieces fit together.

## Three layers

```text
Fast-Svelte
│
├── Application Layer
│   ├── Frontend (SvelteKit)    frontend/src/
│   └── Backend (FastAPI)       backend/app/modules/
│
├── Infrastructure Layer
│   ├── PostgreSQL + Alembic
│   ├── Redis + ARQ workers
│   ├── Traefik (routing / TLS)
│   └── Docker Compose
│
└── Control Layer
    └── __ctrl__/               dev · test · deploy · scaffold
```

## Stack

| Layer | Technology | Role |
|-------|------------|------|
| Frontend | Svelte 5 + SvelteKit + TypeScript + Tailwind | UI components, routes, API clients |
| Backend | FastAPI + SQLModel | REST API and business logic |
| Database | PostgreSQL 18 | Persistent storage |
| Migrations | Alembic | Schema versioning |
| Jobs | ARQ + Redis 8 | Background processing |
| Proxy | Traefik 3.6 | Dev/prod routing and TLS |
| Control | `__ctrl__/` CLI | Dev, test, and deploy operations |

## Runtime profiles

Fast-Svelte supports two official dev/runtime modes:

| Profile | Command | Infrastructure | Apps |
|---------|---------|----------------|------|
| **Full** | `dev run all` | DB + Redis + Traefik + Adminer | uvicorn + ARQ worker + Vite |
| **Slim** | `dev run all --slim` | DB + Traefik + Adminer | uvicorn + Vite |

Slim is an official supported mode — not a fallback. Use it when the app does not need background jobs.

Production (`compose.yml`) always includes Redis + worker service.

## Request flow (backend)

```
HTTP Request
    ↓
FastAPI app (backend/app/main.py)
    ↓
API router (backend/app/api/main.py)
    ↓
Module router (backend/app/modules/.../router.py)
    ↓
Service (business logic)
    ↓
Repository (database access)
    ↓
PostgreSQL
```

### Layer responsibilities

**Router** — HTTP concerns only: path/method, dependency injection (`SessionDep`, `CurrentUser`), calling service functions, returning response models.

**Service** — Application logic: validation, authorization checks, coordinating repositories, raising `HTTPException` for business errors.

**Repository** — Persistence: queries, inserts, updates, deletes. No business rules.

**Models** — SQLModel table classes (`table=True`).

**Schemas** — Pydantic/SQLModel classes for API contracts (`NoteCreate`, `NotePublic`, etc.).

## Project layout

```
fast-svelte/
├── AGENTS.md                 # AI development contract
├── ROADMAP.md                # Long-term vision and goals
├── Readme.md                 # Quick start
├── package.json              # npm workspace root
├── __ctrl__/                 # CLI (dev run, test, deploy)
├── compose.dev.yml           # Dev infrastructure (db, redis, Traefik, adminer)
├── compose.yml               # Production stack
├── backend/app/
│   ├── main.py               # FastAPI entry
│   ├── api/                  # Router aggregation, shared deps
│   ├── core/                 # Config, db, security, arq
│   ├── alembics/core/        # Database migrations
│   └── modules/
│       ├── system/           # Health checks, private dev routes
│       ├── base/             # Auth, users (platform)
│       └── apps/             # Product features
├── frontend/src/
│   ├── lib/config/           # API URL helpers (backend.ts, api-url.ts)
│   ├── lib/modules/
│   │   ├── global/           # Auth, shared shell components
│   │   └── apps/             # Feature API clients + UI helpers
│   └── routes/               # SvelteKit pages (+page.svelte, +layout.svelte)
└── tests/
    ├── backend/              # pytest (mirrors backend modules)
    └── frontend/             # Vitest (config helpers, pure TS)
```

## Module types

### Platform modules (`modules/base/`)

Shared infrastructure used by every application: authentication, users. These ship with Fast-Svelte and are not product-specific.

Uses `crud.py` in the users submodule (predates the app-module convention).

### App modules (`modules/apps/<name>/`)

Product features you build on top of Fast-Svelte. Each module owns its backend and frontend code.

Standard app module structure (use only what you need):

```
backend/app/modules/apps/<name>/
├── models.py       # SQLModel tables
├── schemas.py      # API contracts
├── repository.py   # Database access
├── service.py      # Business logic
└── router.py       # HTTP endpoints
```

Register the router in `backend/app/modules/apps/router.py`.

Frontend counterpart:

```
frontend/src/lib/modules/apps/<name>/
└── api.ts          # TypeScript HTTP client

frontend/src/routes/<path>/+page.svelte   # SvelteKit route
```

## Canonical example: sample notes

The `sample` module is the reference implementation. It demonstrates a complete feature lifecycle:

| Step | File |
|------|------|
| Model | `backend/app/modules/apps/sample/models.py` |
| Migration | `backend/app/alembics/core/versions/002_sample_notes.py` |
| Repository | `backend/app/modules/apps/sample/repository.py` |
| Service | `backend/app/modules/apps/sample/service.py` |
| Router | `backend/app/modules/apps/sample/router.py` |
| SvelteKit UI | `frontend/src/routes/sample/notes/+page.svelte` |
| API client | `frontend/src/lib/modules/apps/sample/api.ts` |
| Tests | `tests/backend/apps/sample/test_notes.py` |

Open `http://dashboard.localhost/sample/notes` after starting dev to see the UI.

## Frontend architecture

SvelteKit routes live under `frontend/src/routes/`. The global shell provides:

- `+layout.svelte` — root layout and navigation
- `lib/modules/base/Authentication.svelte` — login UI
- `lib/modules/base/stores/auth.ts` — session persistence

Feature pages call the FastAPI backend via `fetch` using `API_BASE_URL` from `frontend/src/lib/config/backend.ts`.

SvelteKit gives access to the full JS/TS ecosystem — install npm packages (Three.js, Babylon.js, charts, etc.) in the `frontend` workspace.

## Database and migrations

- Connection settings: `backend/app/core/config.py` → `CORE_SQLALCHEMY_DATABASE_URI`
- Migrations run via `backend/scripts/prestart.sh` (Alembic upgrade head)
- Alembic env whitelists tables in `included_tables` — add new tables there
- Dev DB port: `localhost:5432` (published from Docker)

## Authentication

- OAuth2 password flow: `POST /api/v1/base/login/access-token`
- Current user: `GET /api/v1/base/login/me`
- Backend deps: `CurrentUser`, `SuperAdminUser` in `backend/app/api/deps.py`
- Frontend stores token via `authStore` in `lib/modules/base/stores/auth.ts`

App modules should use `CurrentUser` when endpoints require authentication.

## Configuration

| What | Where |
|------|-------|
| Secrets, DB credentials | `.env` (from `.env.example`) |
| App settings | `backend/app/core/config.py` |
| CORS, hosts | `compose.dev.yml` / `compose.yml` |
| Frontend API URL | `PUBLIC_API_BASE_URL` env var |

## Testing

Backend tests use FastAPI `TestClient` with a real dev database:

```bat
__ctrl__\fast-svelte-ctrl.bat test backend
```

Frontend tests use Vitest:

```bat
__ctrl__\fast-svelte-ctrl.bat test frontend
```

Test paths mirror module paths: `tests/backend/apps/sample/` tests `backend/app/modules/apps/sample/`.

## Background jobs (ARQ)

```
Enqueue (FastAPI)          Worker (ARQ)
      ↓                         ↓
create_arq_pool()         WorkerSettings
      ↓                         ↓
Redis ←────────────────── tasks.py
```

| File | Role |
|------|------|
| `backend/app/core/arq.py` | Redis connection + pool |
| `backend/app/worker/worker.py` | WorkerSettings (register functions) |
| `backend/app/worker/tasks.py` | Generic + app-specific tasks |

Dev: worker runs on host via `arq app.worker.worker.WorkerSettings` (full runtime only).
Prod: `worker` service in `compose.yml`.

Test enqueue (local only): `POST /api/v1/private/jobs/ping/`

## Module scaffolding

```bat
__ctrl__\fast-svelte-ctrl.bat app create myfeature
```

Creates backend router, frontend `api.ts` stub, SvelteKit route stub, and test — then extend using the sample module as reference.

## What belongs in core vs apps

**Core** (Fast-Svelte foundation): auth, database, migrations, CLI, deployment, testing infrastructure, modular conventions.

**Apps** (your product): any feature specific to what you are building — notes, orders, dashboards, AI workflows, 3D viewers, etc.

Before adding something to core, ask: *Could this be useful for fundamentally different applications?* If not, it belongs in `modules/apps/`.

## Logging and error handling

Fast-Svelte intentionally uses the **simple approach**: services raise `HTTPException` for business errors. No separate application-exception hierarchy.

| Context | Approach |
|---------|----------|
| Application code | `logging.getLogger(__name__)` |
| Business errors (not found, forbidden, validation) | `HTTPException` in **service** layer |
| Auth failures | `HTTPException` in deps/routers |
| Worker tasks | Log + ARQ retry via `max_tries` |
| Startup / prestart | `logging` in `backend_pre_start.py`, `initial_data.py` |
| Unexpected exceptions | FastAPI default 500 handling |

Do not add a separate error-handling framework or custom JSON error envelopes. See [conventions.md](conventions.md).

## File storage (extension point)

Fast-Svelte does **not** ship a storage abstraction yet. When applications need uploads or generated files:

- Implement storage access in the **feature module's service layer**
- Prefer an interface that could later swap local disk vs S3-compatible backends
- Do not hard-code AWS/Azure/GCP into core without a generality review

A future `backend/app/core/storage/` module may formalize this. Until then, keep module-local and documented.

## Documentation index

| Doc | Topic |
|-----|-------|
| [modules.md](modules.md) | Building features |
| [cli.md](cli.md) | `__ctrl__` commands |
| [runtime-profiles.md](runtime-profiles.md) | Full vs Slim |
| [background-jobs.md](background-jobs.md) | ARQ tasks |
| [development.md](development.md) | Local workflow |
| [testing.md](testing.md) | pytest, Vitest |
| [database.md](database.md) | Migrations, volumes |
| [deployment.md](deployment.md) | Production |
| [conventions.md](conventions.md) | Naming, responses, cross-module rules |

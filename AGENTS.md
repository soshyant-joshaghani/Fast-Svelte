# AGENTS.md — AI Development Contract

Read this file **first** before making architectural changes in Fast-Svelte.

Fast-Svelte is a **product-agnostic full-stack foundation** (SvelteKit + FastAPI + PostgreSQL + Redis/ARQ). Your job is to implement features **inside** the existing architecture — not redesign it.

## Start here

When asked to build a feature, answer these before writing code:

| Question | Answer |
|----------|--------|
| What to read first? | This file → [docs/architecture.md](docs/architecture.md) → [docs/conventions.md](docs/conventions.md) |
| What architecture to follow? | Router → Service → Repository → Database (see below) |
| Where does the feature belong? | `backend/app/modules/apps/<name>/` + `frontend/src/lib/modules/apps/<name>/` + `frontend/src/routes/(dashboard)/` |
| Is there a similar feature? | Inspect `modules/apps/` — reuse patterns |
| Should I scaffold? | Yes for new app modules: `__ctrl__\fast-svelte-ctrl.bat app create <name>` |
| Where does business logic go? | `service.py` |
| Where does database logic go? | `repository.py` |
| How are API schemas handled? | `schemas.py` — separate from `models.py` |
| How is the SvelteKit frontend structured? | `frontend/src/lib/modules/apps/<name>/api.ts` + `frontend/src/routes/(dashboard)/<path>/+page.svelte` |
| How are API clients written? | TypeScript in `api.ts` using `$lib/config/backend` (`API_BASE_URL`) |
| How are DB changes migrated? | Alembic in `backend/app/alembics/core/versions/` + `env.py` whitelist |
| Where do tests go? | `tests/backend/` mirroring module paths; `tests/frontend/` for Vitest |
| How are background jobs added? | `backend/app/worker/tasks.py` + register in `worker.py` — see [background-jobs.md](docs/background-jobs.md) |
| How to run the project? | `__ctrl__\fast-svelte-ctrl.bat dev run all` — see [cli.md](docs/cli.md) |
| Full or Slim runtime? | Full if feature needs background jobs; Slim otherwise — see [runtime-profiles.md](docs/runtime-profiles.md) |

## Before you write code

1. Read [ROADMAP.md](ROADMAP.md) for project philosophy.
2. Read [docs/architecture.md](docs/architecture.md) for structure and layer responsibilities.
3. Read [docs/conventions.md](docs/conventions.md) for naming, responses, and cross-module rules.
4. Read relevant docs: [modules.md](docs/modules.md), [background-jobs.md](docs/background-jobs.md), [runtime-profiles.md](docs/runtime-profiles.md).
5. Inspect the **canonical example** at `backend/app/modules/apps/sample/` and `frontend/src/lib/modules/apps/sample/`.
6. Inspect any existing module that solves a similar problem — reuse its patterns.

Do **not** invent a new architecture per feature. Do **not** explain to the developer where files go — put them in the right place.

Sibling kits (Fast-Next, Fast-Svelte, Fast-Nuxt, Fast-Rio) stay in sync on shared layers. Backend / `__ctrl__` / infra / UX-contract changes transfer to all four. Frontend UI stays in this kit. Policy: [../README.md](../README.md).

## Where things go

| Kind | Location |
|------|----------|
| App feature (backend) | `backend/app/modules/apps/<name>/` |
| App feature (frontend client) | `frontend/src/lib/modules/apps/<name>/` |
| SvelteKit routes | `frontend/src/routes/` (`login/`, `(dashboard)/`) |
| Shared dashboard shell | `frontend/src/lib/components/layout/` |
| UI primitives (shadcn-svelte) | `frontend/src/lib/components/ui/` |
| Platform auth/users | `backend/app/modules/base/` |
| System/health | `backend/app/modules/system/` |
| Shared frontend shell | `frontend/src/lib/modules/global/` |
| Shared config | `backend/app/core/config.py`, `.env` |
| Migrations | `backend/app/alembics/core/versions/` |
| Backend tests | `tests/backend/` (mirror module paths) |
| Frontend tests | `tests/frontend/` (Vitest) |
| Background tasks | `backend/app/worker/tasks.py` + register in `worker.py` |
| `__ctrl__` CLI | [`docs/cli.md`](docs/cli.md) — do not invent ad-hoc docker scripts |

## Scaffolding

Prefer the official generator for new app modules:

```bat
__ctrl__\fast-svelte-ctrl.bat app create myfeature
```

Then extend with layers as needed (see sample module).

## Backend layers

Use this flow for app modules:

    Router → Service → Repository → Database

| Layer | Responsibility |
|-------|----------------|
| **Router** | HTTP, auth deps, request/response, call service |
| **Service** | Business rules, validation, orchestration |
| **Repository** | Queries and persistence only |
| **Models** | SQLModel table definitions |
| **Schemas** | API input/output contracts |

Rules:

- Do **not** put business logic in routers or repositories.
- Keep API schemas separate from database models unless there is a clear reason to merge them.
- Register new routers in `backend/app/modules/apps/router.py`.

## Error boundary (intentional decision)

Fast-Svelte uses the **simple approach**: services raise `HTTPException` for business/API errors.

| Context | Approach |
|---------|----------|
| Business errors (not found, forbidden, validation) | `HTTPException` in **service** layer |
| Auth failures | `HTTPException` in deps/routers |
| Worker task failures | Log + ARQ `max_tries` retry |
| Unexpected exceptions | FastAPI default 500 handling |

Do **not** introduce a separate application-exception hierarchy or custom error envelope per module. Use `logging.getLogger(__name__)` for non-trivial operations.

## Frontend

- SvelteKit is first-class — implement UI in the feature module and route files, not scattered globals.
- Use `frontend/src/lib/modules/apps/<name>/api.ts` for HTTP clients.
- Use `frontend/src/routes/(dashboard)/` for authenticated pages; `login/` for auth.
- Reuse shell from `frontend/src/lib/components/layout/`.
- **Styling:** Tailwind + shadcn-svelte only. No `<style>` blocks or per-component CSS — utility classes and `$lib/components/ui/` primitives. Theme tokens live only in `frontend/src/app.css`.
- Use shadcn-svelte primitives from `$lib/components/ui/` — do not invent parallel button/card/table styles.
- Import API base URL from `$lib/config/backend` — do not hard-code URLs.
- SvelteKit gives access to the full JS/TS ecosystem (Three.js, Babylon.js, npm packages) — use npm for frontend dependencies.

## Database changes

When you add or change a table:

1. Add/update the SQLModel in the feature's `models.py`.
2. Create an Alembic migration in `backend/app/alembics/core/versions/`.
3. Add the table name to `included_tables` in `backend/app/alembics/core/env.py`.
4. Import the model in `env.py` so metadata is available.

## Tests

- Add backend tests under `tests/backend/` mirroring the module path.
- Add frontend tests under `tests/frontend/` (Vitest) for pure TS helpers and config.
- Test meaningful business logic and API behavior — not trivial getters.
- Run: `__ctrl__\fast-svelte-ctrl.bat test all`

## Configuration

- Secrets and credentials: `.env` (never commit secrets).
- Application settings: `backend/app/core/config.py`.
- Frontend API URL: `PUBLIC_API_BASE_URL` (see `frontend/src/lib/config/backend.ts`).
- Do not scatter `os.environ` reads across the codebase.

## Background jobs

- ARQ + Redis is the **only** background job mechanism — do not add Celery, RQ, or parallel queue systems.
- Register tasks in `backend/app/worker/tasks.py` and `backend/app/worker/worker.py`.
- Enqueue from **services** via `app.core.arq.create_arq_pool()` — not from routers.
- **Full runtime** starts Redis + ARQ worker; **Slim** skips both (official lightweight mode).
- Job enqueue endpoints return `503` when Redis is unavailable (expected in Slim).

See [docs/background-jobs.md](docs/background-jobs.md).

## CLI

Development is operated through `__ctrl__/` — the project control layer:

```bat
__ctrl__\fast-svelte-ctrl.bat dev run all          # full runtime (Redis + ARQ worker)
__ctrl__\fast-svelte-ctrl.bat dev run all --slim   # slim runtime (no Redis/worker)
__ctrl__\fast-svelte-ctrl.bat app create myfeature  # scaffold new module
__ctrl__\fast-svelte-ctrl.bat test all
```

See [Readme.md](Readme.md) and [docs/cli.md](docs/cli.md) for full CLI usage.

## What you must NOT do

- Do **not** turn Fast-Svelte into a product-specific template (AI app, CMS, SaaS, e-commerce, etc.).
- Do **not** invent a second pattern when one already exists.
- Do **not** modify core infrastructure (`__ctrl__/`, compose files, Traefik) for a feature-specific need unless explicitly asked.
- Do **not** add dependencies without a clear reason.
- Do **not** over-engineer — use the smallest correct change.
- Do **not** introduce FoxG-style `{ "code", "data", "meta" }` response envelopes — use FastAPI `response_model` and `HTTPException`.
- Do **not** add Admin/`User*` module naming or full RBAC unless the product explicitly requires it in an app module.

## FoxG `.rules/` (parent monorepo)

FoxG has separate architecture rules (admin CRUD, RBAC, custom responses). **Do not copy those into Fast-Svelte core.** Use [docs/conventions.md](docs/conventions.md) for Fast-Svelte-specific naming and boundaries.

## Canonical reference

The **sample notes module** is the reference implementation. Inspect before implementing a new feature:

```
backend/app/modules/apps/sample/
├── models.py        → Note table
├── schemas.py       → NoteCreate, NoteUpdate, NotePublic
├── repository.py    → DB access
├── service.py       → Business rules (+ HTTPException)
└── router.py        → HTTP endpoints

frontend/src/lib/modules/apps/sample/
└── api.ts           → TypeScript HTTP client

frontend/src/routes/(dashboard)/sample/notes/+page.svelte  → SvelteKit UI

tests/backend/apps/sample/test_notes.py  → API tests
```

Not every feature needs every layer. Match the sample module's depth when building similar CRUD features.

## Definition of done

A feature is complete when it has the appropriate layers for its complexity:

- [ ] Correct module location
- [ ] Router / service / repository as needed
- [ ] Migration (if database changes)
- [ ] API schemas
- [ ] Auth where required
- [ ] SvelteKit UI (if user-facing)
- [ ] Tests for meaningful behavior
- [ ] Background job (if async work required)
- [ ] Logging for non-trivial operations
- [ ] Documentation updated if workflow or behavior changed

## When in doubt

> Reuse existing conventions. Prefer the smallest change that correctly implements the request.

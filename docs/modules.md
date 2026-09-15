# Modules

Product features live in **app modules** — one ownership boundary per feature.

Before creating a new pattern, inspect the **canonical `sample` module** (notes CRUD). It is the reference implementation for how features are structured in Fast-Svelte.

## Locations

| Layer | Path |
|-------|------|
| Backend | `backend/app/modules/apps/<name>/` |
| Frontend client | `frontend/src/lib/modules/apps/<name>/api.ts` |
| SvelteKit route | `frontend/src/routes/<path>/+page.svelte` |
| Backend tests | `tests/backend/apps/<name>/` |
| Frontend tests | `tests/frontend/` (as needed) |

Platform code (not your product): `modules/base/` (auth), `modules/system/` (health).

Shared frontend shell: `frontend/src/lib/modules/base/` (design primitives at `base/ui/`). There is no project `components/` folder — modules are the component home.

## Backend layers

Use only what the feature needs:

```
Router → Service → Repository → Database
```

| File | When |
|------|------|
| `router.py` | Always — HTTP endpoints |
| `service.py` | Business rules, validation, orchestration |
| `repository.py` | Database queries |
| `models.py` | SQLModel tables |
| `schemas.py` | API input/output |

Register the router in `backend/app/modules/apps/router.py`.

Naming and cross-module rules: [conventions.md](conventions.md).

## Scaffold

```bat
__ctrl__\fast-svelte-ctrl.bat app create myfeature
```

Creates backend router, frontend `api.ts` stub, SvelteKit route stub, and backend test. Extend using the sample module as reference.

## Canonical example: `sample`

The **notes** module is the reference implementation. Inspect before building anything new:

| Step | Location |
|------|----------|
| Model | `backend/app/modules/apps/sample/models.py` |
| Migration | `backend/app/alembics/core/versions/002_sample_notes.py` |
| Repository | `backend/app/modules/apps/sample/repository.py` |
| Service | `backend/app/modules/apps/sample/service.py` |
| Router | `backend/app/modules/apps/sample/router.py` |
| API client | `frontend/src/lib/modules/apps/sample/api.ts` |
| SvelteKit UI | `frontend/src/routes/sample/notes/+page.svelte` |
| Tests | `tests/backend/apps/sample/test_notes.py` |

UI: http://dashboard.localhost/sample/notes

## Frontend API clients

TypeScript clients live in `frontend/src/lib/modules/apps/<name>/api.ts`:

- Import `API_BASE_URL` from `$lib/config/backend`
- Use `fetch` with auth headers from `$lib/modules/base/stores/auth`
- Export typed functions (`listNotes`, `createNote`, etc.) — see sample module

Keep routes thin: `+page.svelte` imports from the module's `api.ts` and handles UI state.

## Rules

- Keep feature code in the feature module — avoid scattering helpers globally.
- Simple features stay simple — do not add empty layers for ceremony.
- Add a migration when the schema changes (see [database.md](database.md)).
- Add tests for meaningful behavior (see [testing.md](testing.md)).
- Use npm for frontend-only dependencies (3D libraries, charts, etc.) in the `frontend` workspace.

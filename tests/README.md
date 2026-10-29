# Tests

- `backend/` — pytest against FastAPI (`tests/backend/` paths match `backend/app/modules/`)
- `frontend/` — Vitest for pure TS helpers and config

## Canonical examples

- Backend: `tests/backend/apps/sample/test_notes.py`
- Frontend: `tests/frontend/config/api-base-url.test.ts`

Inspect the sample module tests before writing new ones.

## Run

```bat
__ctrl__\fast-svelte-ctrl.bat test all
```

Or manually:

```bat
npm test
.venv\Scripts\activate
cd backend
set PYTHONPATH=.;..\tests\backend
pytest ..\tests\backend\ -v
```

Backend tests need the dev stack running (`dev run infra` → `localhost:5432`).

Full docs: [docs/testing.md](../docs/testing.md)

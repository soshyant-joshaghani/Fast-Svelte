# Development

## Launchpad workflow

Fast-Svelte is designed so you focus on product requirements, not repeated architecture decisions:

```text
Clone → setup-local → dev run all
    → give AI your feature requirements
    → AI reads AGENTS.md + inspects sample module
    → AI extends modules inside existing architecture
    → test all → deploy
```

You provide: product rules, features, UI requirements, integrations.
Fast-Svelte provides: structure, conventions, control CLI, testing, deployment path.
AI helps implement the product inside the guardrails. See [AGENTS.md](../AGENTS.md).

## First run

```bat
copy .env.example .env
__ctrl__\fast-svelte-ctrl.bat setup-local
__ctrl__\fast-svelte-ctrl.bat dev run all
```

`setup-local` creates `.venv`, installs Python deps from `requirements.txt`, and runs `npm install` for the workspace.

Choose Full or Slim: [runtime-profiles.md](runtime-profiles.md)

## Hot reload

- **API:** uvicorn `--reload` on port 8000 (host)
- **UI:** Vite HMR via `npm run dev` on port 5000 (host)
- **Infra:** Docker Compose (`compose.dev.yml`)

Edit Python and TypeScript files; services restart automatically.

## Manual run (without `__ctrl__`)

Prefer `__ctrl__` for normal development. Use manual commands only when debugging individual services.

Infra only (full — includes Redis):

```bat
docker compose -f compose.dev.yml up -d db redis proxy adminer
```

Infra only (slim — no Redis):

```bat
docker compose -f compose.dev.yml up -d db proxy adminer
```

API only:

```bat
cd backend
set PYTHONPATH=.
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Frontend only:

```bat
npm run dev
```

Worker (full stack):

```bat
cd backend
..\.venv\Scripts\python.exe -m arq app.worker.worker.WorkerSettings
```

## npm workspace

Root `package.json` defines an npm workspace with the `frontend` package:

```bat
npm run dev       # Vite dev server
npm run build     # production build
npm run test      # Vitest (tests/frontend/)
```

Install dependencies after clone: `__ctrl__\fast-svelte-ctrl.bat setup-local` or `npm install` from repo root.

## Configuration

| What | Where |
|------|-------|
| Secrets, DB/Redis credentials | `.env` |
| App settings | `backend/app/core/config.py` |
| CORS, hosts, domain | `compose.dev.yml` / `compose.yml` |
| Frontend → API URL | `PUBLIC_API_BASE_URL` env var |
| Vite API proxy | `API_PROXY_TARGET` (default `http://localhost:8000`) |

Do not read `os.environ` scattered across app code — use `settings` from `core/config.py`.

## Private dev routes

When `ENVIRONMENT=local`, FastAPI exposes `/api/v1/private/*` (signup without auth, job ping test). Not available in production.

## SvelteKit ecosystem

The frontend is a standard SvelteKit + TypeScript project. Install npm packages in the `frontend` workspace for:

- 3D/WebGL: Three.js, Babylon.js, Threlte
- Charts: Chart.js, D3
- UI: any Svelte-compatible component library

Keep backend logic in Python; use TypeScript for UI and client-side code.

# fast-svelte `__ctrl__`

The **control layer** for Fast-Svelte — one predictable CLI for the project lifecycle.

`__ctrl__` is not a loose collection of scripts. It is the official interface for:

- Starting and stopping dev infrastructure and apps
- Selecting runtime profiles (Full / Slim)
- Scaffolding app modules
- Running tests
- Deploying to production via SSH

```text
Fast-Svelte
│
├── Application Layer     (backend + frontend)
├── Infrastructure Layer  (db, redis, workers, proxy)
└── Control Layer         __ctrl__/  ← you are here
```

Prefer `__ctrl__` commands over ad-hoc `docker compose` or manual process management unless you have a specific reason.

This is **not** foxg-ctrl. FoxG platform VMs stay under `foxg-ctrl`; Fast-Svelte kit ops live here.

## Quick start (Windows)

From `fast-svelte/__ctrl__/`:

```bat
fast-svelte-ctrl.bat
```

Interactive prompt, or one-shot:

```bat
fast-svelte-ctrl.bat setup-local
fast-svelte-ctrl.bat dev run all
fast-svelte-ctrl.bat test all
fast-svelte-ctrl.bat list
fast-svelte-ctrl.bat connect
```

Linux/mac:

```bash
chmod +x fast-svelte-ctrl.sh
./fast-svelte-ctrl.sh status
```

## Command map

| Area | Commands |
|------|----------|
| Local tooling | `setup-local [--force]` |
| Dev stack | `dev run\|stop\|down\|purge\|reset {infra,apps,all}` · `--slim` for lightweight runtime |
| App scaffold | `app create <name>` |
| Tests | `test {all,backend,frontend}` |
| Local prod smoke | `prod start\|stop\|reset\|backup-acme\|…` |
| SSH / VM | `setup`, `pubkey`, `clone`, `env`, `start`, `stop`, `update`, `reset`, `backup-acme`, `connect`, … |

On-VM bash/bat scripts (what SSH `start`/`stop` invoke) live in [`remote/`](remote/README.md).

## Layout

| Path | Role |
|------|------|
| `servers.json` | Single VM entry (`fast-svelte`) |
| `safe/` | PEM, address, prod `.env` |
| `static/gpg` | Docker Ubuntu GPG (Iran bootstrap) |
| `remote/` | On-VM / local-prod compose scripts |
| `fast-svelte-ctrl.bat` / `.sh` | CLI entry |

## Typical first deploy (SSH)

```bat
fast-svelte-ctrl.bat setup
fast-svelte-ctrl.bat pubkey
REM add VM pubkey to GitHub
fast-svelte-ctrl.bat clone
fast-svelte-ctrl.bat env
fast-svelte-ctrl.bat start
```

Day-2:

```bat
fast-svelte-ctrl.bat update
fast-svelte-ctrl.bat status
fast-svelte-ctrl.bat backup-acme
```

## Local dev (Docker Desktop / host apps)

```bat
fast-svelte-ctrl.bat setup-local
fast-svelte-ctrl.bat dev run all
fast-svelte-ctrl.bat dev stop all
fast-svelte-ctrl.bat dev down all
fast-svelte-ctrl.bat dev purge infra
fast-svelte-ctrl.bat dev reset all
```

| Action | Infra (compose.dev.yml) | Apps (host) |
|--------|-------------------------|-------------|
| `run` / `start` | `up -d` db, redis (full), proxy, adminer + migrate | uvicorn :8000, arq worker (full), Vite :5000 |
| `stop` | `compose stop` — containers kept | kill host processes |
| `down` | `compose down` — volumes kept | kill host processes |
| `purge` | `compose down -v` — wipe data, stay down | kill host processes |
| `reset` | wipe then `run` | stop then run |

| Target | Notes |
|--------|-------|
| `infra` | Docker only + Alembic / initial_data |
| `apps` | host processes (needs infra already up) |
| `all` | run: infra→apps · stop/down/purge/reset: apps→infra |

Opens browser tabs for Adminer / Traefik / dashboard / API docs after a successful run.

**Runtime profiles:** `dev run all` (full — includes Redis + worker) · `dev run all --slim` (no Redis/worker). See [docs/runtime-profiles.md](../docs/runtime-profiles.md).

## Tests

```bat
fast-svelte-ctrl.bat test all
fast-svelte-ctrl.bat test backend
fast-svelte-ctrl.bat test frontend
```

Backend needs the dev DB (`dev run infra` → `localhost:15432`).

## Local production smoke

```bat
fast-svelte-ctrl.bat prod start
fast-svelte-ctrl.bat prod stop
fast-svelte-ctrl.bat prod reset
fast-svelte-ctrl.bat prod backup-acme
```

Same scripts SSH uses under `remote/`. Prefer SSH `start`/`stop` when operating the real VM from your laptop.

## Setup (ctrl tool itself)

```bat
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

`setup-local` also runs `npm install` for the frontend workspace.

Iran VMs (`iran_setup: true`) keep provider DNS, rewrite apt to Arvan `apt_mirror`, and use Arvan Docker `registry_mirror`. `clone` routes GitHub SSH via `ssh.github.com:443`.

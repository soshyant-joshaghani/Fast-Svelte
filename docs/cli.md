# CLI (`__ctrl__`)

`__ctrl__/` is the **control layer** for Fast-Svelte — the official interface for dev, test, deploy, and SSH ops. Prefer these commands over ad-hoc `docker compose` or manual process management.

Entry points:

```bat
__ctrl__\fast-svelte-ctrl.bat <command>
```

```bash
__ctrl__/fast-svelte-ctrl.sh <command>
```

Full reference: [`__ctrl__/README.md`](../__ctrl__/README.md)

## Local setup

```bat
fast-svelte-ctrl.bat setup-local
fast-svelte-ctrl.bat setup-local --force   # recreate .venv
```

Creates project `.venv`, installs `requirements.txt`, and runs `npm install` for the workspace.

## Development

```bat
fast-svelte-ctrl.bat dev run all
fast-svelte-ctrl.bat dev run all --slim
fast-svelte-ctrl.bat dev stop all
fast-svelte-ctrl.bat dev down all
fast-svelte-ctrl.bat dev purge infra
fast-svelte-ctrl.bat dev reset all
```

| Target | Meaning |
|--------|---------|
| `infra` | Docker: db, redis (full), proxy, adminer + migrations |
| `apps` | Host: uvicorn :8000, ARQ worker (full), Vite :3000 |
| `all` | Both (run order: infra → apps; stop: apps → infra) |

See [runtime-profiles.md](runtime-profiles.md) for `--slim`.

## Module scaffold

```bat
fast-svelte-ctrl.bat app create myfeature
```

## Tests

```bat
fast-svelte-ctrl.bat test all
fast-svelte-ctrl.bat test backend
fast-svelte-ctrl.bat test frontend
```

## Production (SSH from laptop)

```bat
fast-svelte-ctrl.bat setup
fast-svelte-ctrl.bat pubkey
fast-svelte-ctrl.bat clone
fast-svelte-ctrl.bat env
fast-svelte-ctrl.bat start
fast-svelte-ctrl.bat stop
fast-svelte-ctrl.bat update
fast-svelte-ctrl.bat status
fast-svelte-ctrl.bat connect
```

## Local prod smoke (Docker Desktop)

```bat
fast-svelte-ctrl.bat prod start
fast-svelte-ctrl.bat prod stop
fast-svelte-ctrl.bat prod reset
```

On-VM scripts: `__ctrl__/remote/` (invoked by SSH commands above).

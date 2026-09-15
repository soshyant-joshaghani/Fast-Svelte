# safe/ — keys, addresses, prod env (local only)

| Pattern | Purpose |
|---------|---------|
| `*-privatekey.pem` | SSH private key |
| `*-address.txt` | VM IP / hostname (first line) |
| `*-env.env` | Production secrets → uploaded as `~/projects/fast-svelte/.env` |

| Files | Server id |
|-------|-----------|
| `ar-fast-svelte-bamdad-*` | `fast-svelte` |

Copy the `*.example` stubs, drop the `.example` suffix, and fill real values.

`*.pem`, `*.env`, `*-address.txt` are gitignored.

Upload env to VM:

```bat
fast-svelte-ctrl.bat env
```

That copies `safe/ar-fast-svelte-bamdad-env.env` → `~/projects/fast-svelte/.env`.

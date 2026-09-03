#!/usr/bin/env bash
# Main CLI entry (pair with fast-svelte-ctrl.bat).
set -euo pipefail
cd "$(cd "$(dirname "$0")" && pwd)"

if [[ ! -x .venv/bin/python ]]; then
  echo "[fast-svelte-ctrl] Creating .venv and installing requirements..."
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

PY=(.venv/bin/python)

if [[ $# -eq 0 ]]; then
  exec "${PY[@]}" main.py
fi
exec "${PY[@]}" main.py "$@"

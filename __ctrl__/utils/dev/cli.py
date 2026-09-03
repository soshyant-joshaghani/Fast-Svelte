"""fast-svelte-ctrl dev — run/stop local Docker Desktop / host app stacks."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

from lib.config import ROOT

# __ctrl__ lives under fast-svelte/; the compose + apps root is the parent.
PROJECT = ROOT.parent

RUN_ORDER = ("infra", "apps")
STOP_ORDER = ("apps", "infra")
TARGETS = ("infra", "apps", "all")

COMPOSE_PROJECT_NAME = "fast-svelte-dev"
COMPOSE_FILE = "compose.dev.yml"
APP_STARTUP_TIMEOUT_S = 180.0
FULL_INFRA_SERVICES = ("db", "redis", "proxy", "adminer")
SLIM_INFRA_SERVICES = ("db", "proxy", "adminer")

FRONTEND_DEV_PORT = 3100

# (window_title, port) — host processes; port None = no listener (e.g. ARQ worker)
APP_PORTS = (
    ("fast-svelte-backend", 8000),
    ("fast-svelte-worker", None),
    ("fast-svelte-frontend", FRONTEND_DEV_PORT),
)

STACK_OPEN_URLS: dict[str, tuple[str, ...]] = {
    "infra": (
        "http://adminer.localhost/",
        "http://localhost:8090/",
    ),
    "apps": (
        "http://dashboard.localhost/",
        "http://api.localhost/docs",
        "http://api.localhost/sdoc",
    ),
}


def _require_cmd(name: str) -> str | None:
    path = shutil.which(name)
    if not path:
        print(f"error: '{name}' not found on PATH", file=sys.stderr)
        return None
    return path


def _npm_argv(*args: str) -> list[str] | None:
    """Build argv that can launch npm.cmd on Windows (CreateProcess can't)."""
    npm = _require_cmd("npm")
    if not npm:
        return None
    if sys.platform == "win32":
        return ["cmd", "/c", npm, *args]
    return [npm, *args]


def _run_npm(*args: str, **kwargs) -> subprocess.CompletedProcess | None:
    argv = _npm_argv(*args)
    if not argv:
        return None
    return subprocess.run(argv, **kwargs)


def _resolve_targets(target: str, *, order: tuple[str, ...]) -> tuple[str, ...]:
    if target == "all":
        return order
    return (target,)


def _ensure_env() -> None:
    env = PROJECT / ".env"
    example = PROJECT / ".env.example"
    if env.is_file():
        return
    if example.is_file():
        shutil.copy(example, env)
        print(f"created {env} from .env.example")
    else:
        print(f"warn: no .env or .env.example in {PROJECT}", file=sys.stderr)


def _open_stack_urls(targets: tuple[str, ...]) -> None:
    urls: list[str] = []
    for t in targets:
        for url in STACK_OPEN_URLS.get(t, ()):
            if url not in urls:
                urls.append(url)
    for url in urls:
        print(f"opening {url}")
        try:
            webbrowser.open(url)
        except Exception as exc:
            print(f"warn: could not open {url}: {exc}", file=sys.stderr)


def _compose(*args: str, check: bool = True) -> int:
    if not _require_cmd("docker"):
        return 1
    cmd = ["docker", "compose", "-f", COMPOSE_FILE, *args]
    print(f"[fast-svelte] {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=PROJECT)
    if check and proc.returncode != 0:
        return proc.returncode
    return proc.returncode


def _wait_postgres(service: str, *, timeout_s: float = 120.0) -> int:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        proc = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                COMPOSE_FILE,
                "exec",
                "-T",
                service,
                "pg_isready",
                "-U",
                "postgres",
            ],
            cwd=PROJECT,
            capture_output=True,
            check=False,
        )
        if proc.returncode == 0:
            return 0
        time.sleep(2)
    print(f"error: {service} not ready within {timeout_s:.0f}s", file=sys.stderr)
    return 1


def _wait_redis(*, timeout_s: float = 60.0) -> int:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        proc = subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                COMPOSE_FILE,
                "exec",
                "-T",
                "redis",
                "redis-cli",
                "ping",
            ],
            cwd=PROJECT,
            capture_output=True,
            check=False,
        )
        if proc.returncode == 0 and b"PONG" in (proc.stdout or b""):
            return 0
        time.sleep(2)
    print(f"error: redis not ready within {timeout_s:.0f}s", file=sys.stderr)
    return 1


def _venv_python() -> Path | None:
    if sys.platform == "win32":
        py = PROJECT / ".venv" / "Scripts" / "python.exe"
    else:
        py = PROJECT / ".venv" / "bin" / "python"
    return py if py.is_file() else None


def _setup_local(*, force_install: bool = False) -> int:
    """Ensure project .venv + npm (pip refresh when forced / new venv)."""
    _ensure_env()

    venv = PROJECT / ".venv"
    created = False
    if not venv.is_dir():
        if not _require_cmd("python"):
            return 1
        print("[fast-svelte] Creating Python venv at .venv ...")
        proc = subprocess.run(["python", "-m", "venv", str(venv)], cwd=PROJECT)
        if proc.returncode != 0:
            return proc.returncode
        created = True

    py = _venv_python()
    if not py:
        print("error: .venv python not found after create", file=sys.stderr)
        return 1

    if created or force_install:
        print("[fast-svelte] Installing Python requirements...")
        proc = subprocess.run(
            [str(py), "-m", "pip", "install", "-U", "pip"],
            cwd=PROJECT,
        )
        if proc.returncode != 0:
            return proc.returncode
        proc = subprocess.run(
            [str(py), "-m", "pip", "install", "-r", "requirements.txt"],
            cwd=PROJECT,
        )
        if proc.returncode != 0:
            return proc.returncode

    if not (PROJECT / "node_modules").is_dir() or force_install:
        print("[fast-svelte] Installing npm dependencies at root ...")
        proc = _run_npm("install", cwd=PROJECT)
        if proc is None:
            return 1
        if proc.returncode != 0:
            return proc.returncode

    # Optional (svelte-kit sync etc.); ignore failure if workspace script missing.
    _run_npm(
        "run",
        "prepare",
        "-w",
        "frontend",
        cwd=PROJECT,
        capture_output=True,
        check=False,
    )

    print("Local environment ready.")
    return 0


def _run_migrations() -> int:
    py = _venv_python()
    if not py:
        print("error: missing project .venv — run setup first", file=sys.stderr)
        return 1
    backend = PROJECT / "backend"
    env = {**os.environ, "PYTHONPATH": str(backend)}

    steps: list[list[str]] = [
        [str(py), "app/backend_pre_start.py"],
        # python -m: Windows venv *.exe launchers embed the python path from
        # create time and break if the project (or .venv) was moved.
        [str(py), "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        [str(py), "app/initial_data.py"],
    ]

    print("[fast-svelte] Running migrations + seed (local prestart)...")
    for cmd in steps:
        print(f"  {' '.join(cmd)}")
        proc = subprocess.run(cmd, cwd=backend, env=env)
        if proc.returncode != 0:
            return proc.returncode
        print(f"  ok ({cmd[-1] if cmd else 'step'})")
    print("[fast-svelte] Migrations + seed complete.")
    return 0


def _port_listening(port: int) -> bool:
    if sys.platform == "win32":
        return bool(_pids_on_port_windows(port))
    return bool(_pids_on_port_unix(port))


def _wait_ports(ports: tuple[int, ...], *, timeout_s: float = APP_STARTUP_TIMEOUT_S) -> list[int]:
    deadline = time.time() + timeout_s
    pending = set(ports)
    last_log = time.time()
    while pending and time.time() < deadline:
        ready = {p for p in pending if _port_listening(p)}
        pending -= ready
        if pending:
            now = time.time()
            if now - last_log >= 15.0:
                print(f"  still waiting for port(s) {sorted(pending)}...")
                last_log = now
            time.sleep(0.5)
    return sorted(pending)


def _pids_on_port_windows(port: int) -> set[int]:
    proc = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        capture_output=True,
        text=True,
        check=False,
    )
    pids: set[int] = set()
    for line in (proc.stdout or "").splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        if parts[3].upper() != "LISTENING":
            continue
        local = parts[1]
        if not (local.endswith(f":{port}") or local.endswith(f"]:{port}")):
            continue
        try:
            pid = int(parts[4])
        except ValueError:
            continue
        if pid > 0:
            pids.add(pid)
    return pids


def _pids_on_port_unix(port: int) -> set[int]:
    pids: set[int] = set()
    if shutil.which("lsof"):
        proc = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
            check=False,
        )
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if line.isdigit():
                pids.add(int(line))
        return pids
    if shutil.which("fuser"):
        proc = subprocess.run(
            ["fuser", f"{port}/tcp"],
            capture_output=True,
            text=True,
            check=False,
        )
        for token in (proc.stdout or "").replace("\n", " ").split():
            digits = "".join(c for c in token if c.isdigit())
            if digits:
                pids.add(int(digits))
    return pids


def _kill_pid(pid: int) -> None:
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            check=False,
        )
    else:
        try:
            os.kill(pid, 15)
        except ProcessLookupError:
            return
        except PermissionError:
            subprocess.run(["kill", "-9", str(pid)], check=False)


def _start_infra(*, slim: bool = False) -> int:
    services = SLIM_INFRA_SERVICES if slim else FULL_INFRA_SERVICES

    code = _setup_local()
    if code != 0:
        return code

    code = _compose("up", "-d", *services)
    if code != 0:
        return code
    code = _compose("up", "-d", "--force-recreate", "--no-deps", "proxy")
    if code != 0:
        return code

    print("[fast-svelte] Waiting for Postgres...")
    if _wait_postgres("db") != 0:
        return 1

    if not slim:
        print("[fast-svelte] Waiting for Redis...")
        if _wait_redis() != 0:
            return 1

    code = _run_migrations()
    if code != 0:
        return code

    if slim:
        print("Infra ready (slim): DB + Adminer + Traefik — no Redis.")
    else:
        print("Infra ready (full): DB + Redis + Adminer + Traefik.")
    return 0


def _backend_env() -> dict[str, str]:
    return {
        **os.environ,
        "PYTHONPATH": str(PROJECT / "backend"),
    }


def _quote_cmd_arg(arg: str) -> str:
    """Quote a token for cmd.exe if it contains whitespace/special chars."""
    if not arg or any(c in arg for c in ' \t"&|<>()^%'):
        return '"' + arg.replace('"', '""') + '"'
    return arg


def _start_named_console(
    title: str,
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> None:
    """Open a titled console like start-fast-svelte-dev.bat (`start "title" cmd /k …`).

    Uses shell=True so cmd.exe parses the line; argv is joined with cmd-safe quoting
    (avoids Python list2cmdline turning quotes into \\\").
    """
    inner = " ".join(_quote_cmd_arg(a) for a in args)
    cmdline = f'start "{title}" /D {_quote_cmd_arg(str(cwd))} cmd /k {inner}'
    subprocess.Popen(cmdline, shell=True, env=env)


def _app_specs(*, slim: bool) -> list[tuple[str, list[str], Path, dict[str, str], int | None]]:
    py = _venv_python()
    if not py:
        return []
    backend = PROJECT / "backend"
    env_be = _backend_env()
    env_fe = {
        **os.environ,
        "API_PROXY_TARGET": "http://localhost:8000",
        "PUBLIC_API_BASE_URL": "/api/v1",
    }
    py_s = str(py)

    specs: list[tuple[str, list[str], Path, dict[str, str], int | None]] = [
        (
            "fast-svelte-backend",
            [
                py_s,
                "-m",
                "uvicorn",
                "app.main:app",
                "--reload",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
            ],
            backend,
            env_be,
            8000,
        ),
    ]
    if not slim:
        specs.append(
            (
                "fast-svelte-worker",
                [py_s, "-m", "arq", "app.worker.worker.WorkerSettings"],
                backend,
                env_be,
                None,
            )
        )
    frontend_cmd = ["npm", "run", "dev", "-w", "frontend"]
    specs.append(
        (
            "fast-svelte-frontend",
            frontend_cmd,
            PROJECT,
            env_fe,
            FRONTEND_DEV_PORT,
        )
    )
    return specs


def _spawn_apps_windows(*, slim: bool = False) -> int:
    py = _venv_python()
    if not py:
        print("error: missing project .venv", file=sys.stderr)
        return 1
    if not _require_cmd("npm"):
        return 1

    specs = _app_specs(slim=slim)
    if not specs:
        print("error: missing project .venv", file=sys.stderr)
        return 1

    wait_ports: list[int] = []
    for title, args, cwd, env, port in specs:
        if port is not None and _port_listening(port):
            print(f"  {title}: already listening on :{port}")
            continue
        print(f"  {title}: starting (new console)...")
        _start_named_console(title, args, cwd=cwd, env=env)
        if port is not None:
            wait_ports.append(port)

    if wait_ports:
        print(f"  waiting for app ports :8000, :{FRONTEND_DEV_PORT}...")
        missing = _wait_ports(tuple(wait_ports))
        if missing:
            print(
                f"error: apps did not listen on port(s) {missing} within {int(APP_STARTUP_TIMEOUT_S)}s. "
                "Check the new console windows for errors.",
                file=sys.stderr,
            )
            return 1
    return 0


def _spawn_apps_unix(*, slim: bool = False) -> int:
    py = _venv_python()
    if not py:
        print("error: missing project .venv", file=sys.stderr)
        return 1

    specs = _app_specs(slim=slim)
    if not specs:
        print("error: missing project .venv", file=sys.stderr)
        return 1

    wait_ports: list[int] = []
    for title, cmd, cwd, env, port in specs:
        if title == "fast-svelte-frontend":
            npm_cmd = _npm_argv("run", "dev", "-w", "frontend")
            if not npm_cmd:
                return 1
            cmd = npm_cmd
        if port is not None and _port_listening(port):
            print(f"  {title}: already listening on :{port}")
            continue
        print(f"  {title}: starting...")
        subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        if port is not None:
            wait_ports.append(port)

    if wait_ports:
        print(f"  waiting for app ports :8000, :{FRONTEND_DEV_PORT}...")
        missing = _wait_ports(tuple(wait_ports))
        if missing:
            print(
                f"error: apps did not listen on port(s) {missing} within {int(APP_STARTUP_TIMEOUT_S)}s.",
                file=sys.stderr,
            )
            return 1
    return 0


def _start_apps(*, slim: bool = False) -> int:
    code = _setup_local()
    if code != 0:
        return code

    _stop_apps()

    profile = "slim" if slim else "full"
    print(f"[fast-svelte] Starting apps ({profile}): backend + frontend" + ("" if slim else " + worker"))
    if sys.platform == "win32":
        code = _spawn_apps_windows(slim=slim)
    else:
        code = _spawn_apps_unix(slim=slim)
    if code != 0:
        return code

    print()
    print("Dev stack ready (hot reload on save):")
    print("  Dashboard:   http://dashboard.localhost")
    print("  Sample Notes http://dashboard.localhost/sample/notes")
    print("  API docs:    http://api.localhost/docs")
    print("  Scalar:      http://api.localhost/sdoc")
    print("  Adminer:     http://adminer.localhost")
    print("  Traefik:     http://localhost:8090")
    print()
    print(f"Direct: http://localhost:{FRONTEND_DEV_PORT}  http://localhost:8000/docs  http://localhost:8000/sdoc")
    if not slim:
        print("Worker: fast-svelte-worker (ARQ)")
    print("Stop with: fast-svelte-ctrl.bat dev stop all")
    return 0


def _stop_apps() -> int:
    print("[fast-svelte] Stopping host apps (backend / frontend)...")
    killed: set[int] = set()
    for _title, port in APP_PORTS:
        if port is None:
            continue
        if sys.platform == "win32":
            pids = _pids_on_port_windows(port)
        else:
            pids = _pids_on_port_unix(port)
        for pid in pids:
            if pid in killed:
                continue
            print(f"  kill pid {pid} (port {port})")
            _kill_pid(pid)
            killed.add(pid)

    if sys.platform == "win32":
        for title, _port in APP_PORTS:
            subprocess.run(
                ["taskkill", "/F", "/FI", f"WINDOWTITLE eq {title}*"],
                capture_output=True,
                check=False,
            )

    if not killed:
        print("  (no listeners found on app ports; closed matching consoles if any)")
    else:
        print("Host apps stopped.")
    return 0


def _compose_stop() -> int:
    code = _compose("stop")
    if code != 0:
        return code
    print("Infra stopped (containers kept).")
    return 0


def _compose_down(*, volumes: bool = False) -> int:
    cmd = ["down", "--remove-orphans"]
    if volumes:
        cmd.append("-v")
        print("[fast-svelte] compose down -v  (WIPES VOLUMES)")
    code = _compose(*cmd)
    if code != 0:
        return code
    if volumes:
        _cleanup_leftover_volumes()
        print("Infra removed; named volumes wiped.")
    else:
        print("Infra removed (volumes kept).")
    return 0


def _list_volume_names() -> list[str]:
    proc = subprocess.run(
        ["docker", "volume", "ls", "-q"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]


def _cleanup_leftover_volumes() -> None:
    prefix_us = f"{COMPOSE_PROJECT_NAME}_"
    for name in _list_volume_names():
        if name.startswith(prefix_us):
            print(f"  removing leftover volume {name}")
            subprocess.run(
                ["docker", "volume", "rm", "-f", name],
                capture_output=True,
                check=False,
            )
    print("  pruning dangling anonymous volumes...")
    proc = subprocess.run(
        ["docker", "volume", "prune", "-f"],
        capture_output=True,
        text=True,
        check=False,
    )
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if out:
        for line in out.splitlines():
            print(f"  {line}")


def _run_one(target: str, *, slim: bool = False) -> int:
    if target == "infra":
        return _start_infra(slim=slim)
    if target == "apps":
        return _start_apps(slim=slim)
    print(f"error: unknown target {target!r}", file=sys.stderr)
    return 1


def _stop_one(target: str) -> int:
    if target == "infra":
        return _compose_stop()
    if target == "apps":
        return _stop_apps()
    print(f"error: unknown target {target!r}", file=sys.stderr)
    return 1


def _down_one(target: str) -> int:
    if target == "infra":
        return _compose_down(volumes=False)
    if target == "apps":
        return _stop_apps()
    print(f"error: unknown target {target!r}", file=sys.stderr)
    return 1


def _wipe_one(target: str) -> int:
    if target == "infra":
        return _compose_down(volumes=True)
    if target == "apps":
        return _stop_apps()
    print(f"error: unknown target {target!r}", file=sys.stderr)
    return 1


def cmd_dev_run(args: argparse.Namespace) -> int:
    slim = bool(getattr(args, "slim", False))
    targets = _resolve_targets(args.target, order=RUN_ORDER)
    for t in targets:
        code = _run_one(t, slim=slim)
        if code != 0:
            return code
    _open_stack_urls(targets)
    return 0


def cmd_dev_stop(args: argparse.Namespace) -> int:
    for t in _resolve_targets(args.target, order=STOP_ORDER):
        code = _stop_one(t)
        if code != 0:
            return code
    return 0


def cmd_dev_down(args: argparse.Namespace) -> int:
    for t in _resolve_targets(args.target, order=STOP_ORDER):
        code = _down_one(t)
        if code != 0:
            return code
    return 0


def cmd_dev_reset(args: argparse.Namespace) -> int:
    slim = bool(getattr(args, "slim", False))
    target = args.target
    print(
        f"WARNING: dev reset {target} removes compose named volumes "
        "(Postgres data for infra)."
    )
    for t in _resolve_targets(target, order=STOP_ORDER):
        code = _wipe_one(t)
        if code != 0:
            return code
    run_targets = _resolve_targets(target, order=RUN_ORDER)
    for t in run_targets:
        code = _run_one(t, slim=slim)
        if code != 0:
            return code
    _open_stack_urls(run_targets)
    return 0


def cmd_dev_purge(args: argparse.Namespace) -> int:
    target = args.target
    print(
        f"WARNING: dev purge {target} removes compose named volumes "
        "(Postgres data for infra). Stack will stay down."
    )
    for t in _resolve_targets(target, order=STOP_ORDER):
        code = _wipe_one(t)
        if code != 0:
            return code
    return 0


def _dev_help(args: argparse.Namespace) -> int:
    _ = args
    print(
        "usage: fast-svelte-ctrl.bat dev {run|start,stop,down,purge,reset} {infra,apps,all}\n"
        "\n"
        "examples:\n"
        "  fast-svelte-ctrl.bat dev run all\n"
        "  fast-svelte-ctrl.bat dev run all --slim\n"
        "  fast-svelte-ctrl.bat dev start all\n"
        "  fast-svelte-ctrl.bat dev stop apps\n"
        "  fast-svelte-ctrl.bat dev down all\n"
        "  fast-svelte-ctrl.bat dev purge infra\n"
        "  fast-svelte-ctrl.bat dev reset all\n"
        "\n"
        "run/start: compose up + host uvicorn/vite/worker (full)\n"
        "  --slim:         DB + apps only (no Redis / no worker)\n"
        "stop:   compose stop / kill host apps (containers kept)\n"
        "down:   compose down / kill host apps (volumes kept)\n"
        "purge:  compose down -v (wipe volumes, do not start)\n"
        "reset:  compose down -v then run (wipe volumes)\n"
        "order:  run infra->apps; stop/down/purge/reset: apps->infra\n"
        "Local only - not SSH / production VMs."
    )
    return 0


def build_dev_subparser(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser(
        "dev",
        help="Run/stop/down/purge/reset local Docker Desktop / host app stacks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  fast-svelte-ctrl.bat dev run all\n"
            "  fast-svelte-ctrl.bat dev run all --slim\n"
            "  fast-svelte-ctrl.bat dev start all\n"
            "  fast-svelte-ctrl.bat dev stop apps\n"
            "  fast-svelte-ctrl.bat dev down all\n"
            "  fast-svelte-ctrl.bat dev purge infra\n"
            "  fast-svelte-ctrl.bat dev reset all\n"
            "\n"
            "run/start: compose up + host uvicorn/vite/worker (full)\n"
            "  --slim:         DB + apps only (no Redis / no worker)\n"
            "stop:   compose stop / kill host apps (containers kept)\n"
            "down:   compose down / kill host apps (volumes kept)\n"
            "purge:  compose down -v (wipe volumes, do not start)\n"
            "reset:  compose down -v then run (wipe volumes)\n"
            "order:  run infra->apps; stop/down/purge/reset: apps->infra\n"
            "Local only - not SSH / production VMs."
        ),
    )
    sp.set_defaults(func=_dev_help)

    actions = sp.add_subparsers(dest="dev_action", required=False)

    for name, help_, fn in [
        ("run", "Start local stack(s)", cmd_dev_run),
        ("start", "Alias for run", cmd_dev_run),
        ("stop", "Stop services (compose stop — keep containers)", cmd_dev_stop),
        ("down", "Remove containers/networks (compose down — keep volumes)", cmd_dev_down),
        ("purge", "Wipe Docker volumes and leave stack down", cmd_dev_purge),
        ("reset", "Wipe Docker volumes then start again", cmd_dev_reset),
    ]:
        action_sp = actions.add_parser(name, help=help_)
        action_sp.add_argument(
            "target",
            choices=list(TARGETS),
            help="which local stack to act on",
        )
        if name in ("run", "start", "reset"):
            action_sp.add_argument(
                "--slim",
                action="store_true",
                help="slim runtime: skip Redis and ARQ worker (official lightweight mode)",
            )
        action_sp.set_defaults(func=fn)


def cmd_setup_local(args: argparse.Namespace) -> int:
    """Top-level: create/refresh project .venv + npm deps."""
    if getattr(args, "force", False):
        venv = PROJECT / ".venv"
        if venv.is_dir():
            print("[fast-svelte] Removing existing .venv (--force)...")
            shutil.rmtree(venv)
        nm = PROJECT / "node_modules"
        if nm.is_dir():
            print("[fast-svelte] Removing node_modules (--force)...")
            shutil.rmtree(nm)
    return _setup_local(force_install=True)

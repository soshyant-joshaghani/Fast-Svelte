"""fast-svelte-ctrl test — backend (pytest) + frontend (vitest)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from lib.config import ROOT
from utils.dev.cli import _setup_local, _venv_python

PROJECT = ROOT.parent
CTRL = "fast-svelte-ctrl"


def _coverage_exe(py: Path) -> list[str]:
    return [str(py), "-m", "coverage"]


def _run_backend() -> int:
    py = _venv_python()
    if not py:
        print(f"error: missing project .venv — run: {CTRL} setup-local", file=sys.stderr)
        return 1

    backend = PROJECT / "backend"
    tests_backend = PROJECT / "tests" / "backend"
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(backend), str(tests_backend)]),
    }
    cov = _coverage_exe(py)

    print("[fast-svelte] Backend tests (pytest + coverage)")
    print(f"  Requires dev DB: {CTRL}.bat dev run infra")
    steps: list[list[str]] = [
        [str(py), "app/tests_pre_start.py"],
        [*cov, "run", "-m", "pytest", str(tests_backend)],
        [*cov, "report"],
    ]
    for cmd in steps:
        print(f"  {' '.join(cmd)}")
        proc = subprocess.run(cmd, cwd=backend, env=env)
        if proc.returncode != 0:
            print("Backend tests failed.", file=sys.stderr)
            return proc.returncode
    print("Backend tests passed.")
    return 0


def _run_frontend() -> int:
    print("[fast-svelte] Frontend tests (vitest / npm test)")
    proc = subprocess.run(["npm", "test"], cwd=PROJECT, shell=(sys.platform == "win32"))
    if proc.returncode != 0:
        print("Frontend tests failed.", file=sys.stderr)
        return proc.returncode
    print("Frontend tests passed.")
    return 0


def _run_contract(base: str) -> int:
    script = PROJECT / "tests" / "contract" / "contract_test.py"
    if not script.is_file():
        print(f"error: missing {script}", file=sys.stderr)
        return 1
    print(f"[{CTRL.removesuffix('-ctrl')}] Wire contract test against {base}")
    print("  Needs a running API (spec: ../../../CONTRACT.md); the tier is STARTER.")
    cmd = [sys.executable, str(script.relative_to(PROJECT)), "--base", base, "--local", "--jobs"]
    print(f"  {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=PROJECT)
    if proc.returncode != 0:
        print("Contract test failed.", file=sys.stderr)
    return proc.returncode


def cmd_test(args: argparse.Namespace) -> int:
    if args.target == "contract":
        return _run_contract(args.base)

    code = _setup_local(force_install=False)
    if code != 0:
        return code

    target = args.target
    if target in ("backend", "all"):
        code = _run_backend()
        if code != 0:
            return code
    if target in ("frontend", "all"):
        code = _run_frontend()
        if code != 0:
            return code
    if target == "all":
        print("\nAll tests passed.")
    return 0


def _test_help(_: argparse.Namespace) -> int:
    print(
        f"usage: {CTRL}.bat test {{all,backend,frontend,contract}}\n"
        "\n"
        f"examples:\n"
        f"  {CTRL}.bat test all\n"
        f"  {CTRL}.bat test backend\n"
        f"  {CTRL}.bat test frontend\n"
        f"  {CTRL}.bat test contract [--base http://localhost:8000]\n"
    )
    return 0


def build_test_subparser(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser(
        "test",
        help="Run backend / frontend test suites",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            f"examples:\n"
            f"  {CTRL}.bat test all\n"
            f"  {CTRL}.bat test backend\n"
            f"  {CTRL}.bat test frontend\n"
            f"  {CTRL}.bat test contract --base http://localhost:8000"
        ),
    )
    sp.set_defaults(func=_test_help)
    actions = sp.add_subparsers(dest="test_target", required=False)

    for name, help_ in [
        ("all", "Backend then frontend"),
        ("backend", "pytest + coverage under tests/backend"),
        ("frontend", "npm test (vitest)"),
        ("contract", "Wire contract test (../../../CONTRACT.md) against a running API; not part of all"),
    ]:
        action_sp = actions.add_parser(name, help=help_)
        action_sp.set_defaults(func=cmd_test, target=name)
        if name == "contract":
            action_sp.add_argument(
                "--base", default="http://localhost:8000", help="API origin (default http://localhost:8000)"
            )

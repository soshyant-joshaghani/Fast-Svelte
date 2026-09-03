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


def cmd_test(args: argparse.Namespace) -> int:
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
        f"usage: {CTRL}.bat test {{all,backend,frontend}}\n"
        "\n"
        f"examples:\n"
        f"  {CTRL}.bat test all\n"
        f"  {CTRL}.bat test backend\n"
        f"  {CTRL}.bat test frontend\n"
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
            f"  {CTRL}.bat test frontend"
        ),
    )
    sp.set_defaults(func=_test_help)
    actions = sp.add_subparsers(dest="test_target", required=False)

    for name, help_ in [
        ("all", "Backend then frontend"),
        ("backend", "pytest + coverage under tests/backend"),
        ("frontend", "npm test (vitest)"),
    ]:
        action_sp = actions.add_parser(name, help=help_)
        action_sp.set_defaults(func=cmd_test, target=name)

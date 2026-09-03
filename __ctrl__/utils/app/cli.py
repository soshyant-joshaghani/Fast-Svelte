"""Scaffold new app modules."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from lib.config import ROOT

PROJECT = ROOT.parent

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _validate_name(name: str) -> str:
    name = name.strip().lower().replace("-", "_")
    if not _NAME_RE.match(name):
        raise SystemExit(
            "Module name must start with a letter and contain only lowercase "
            "letters, digits, and underscores."
        )
    if name in {"sample", "base", "system", "global"}:
        raise SystemExit(f"Reserved module name: {name}")
    return name


def _router_var(name: str) -> str:
    return f"{name}_router"


def _write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        print(f"  skip (exists): {path.relative_to(PROJECT)}")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  created: {path.relative_to(PROJECT)}")
    return True


def _register_router(name: str) -> None:
    router_file = PROJECT / "backend/app/modules/apps/router.py"
    text = router_file.read_text(encoding="utf-8")
    import_line = f"from app.modules.apps.{name}.router import {_router_var(name)}"
    include_line = f"apps_router.include_router({_router_var(name)})"

    if import_line in text and include_line in text:
        print(f"  skip (registered): {router_file.relative_to(PROJECT)}")
        return

    lines = text.splitlines()
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("from app.modules.apps."):
            insert_at = i + 1
    if import_line not in text:
        lines.insert(insert_at, import_line)

    if include_line not in text:
        for i, line in enumerate(lines):
            if line.strip().startswith("apps_router.include_router("):
                lines.insert(i + 1, include_line)
                break

    router_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  updated: {router_file.relative_to(PROJECT)}")


def _backend_router(name: str) -> str:
    var = _router_var(name)
    title = name.replace("_", " ").title()
    return f'''from fastapi import APIRouter

from app.modules.base.schemas import Message

{var} = APIRouter(prefix="/{name}", tags=["[APPS] {title}"])


@{var}.get("/", response_model=Message)
def {name}_root() -> Message:
    return Message(message="{title} module")
'''


def _backend_files(name: str) -> None:
    base = PROJECT / "backend/app/modules/apps" / name
    _write_if_missing(base / "router.py", _backend_router(name))
    _register_router(name)


def _frontend_api(name: str) -> str:
    return f'''import {{ API_BASE_URL }} from '$lib/config/backend';

export function moduleUrl(): string {{
\treturn `${{API_BASE_URL}}/{name}/`;
}}
'''


def _frontend_route(name: str) -> str:
    title = name.replace("_", " ").title()
    return f'''<script lang="ts">
\timport {{ moduleUrl }} from '$lib/modules/apps/{name}/api';
</script>

<section class="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
\t<p class="text-xs font-semibold tracking-[0.2em] text-slate-500 uppercase">{title}</p>
\t<h2 class="mt-2 text-2xl font-bold text-slate-100">{title}</h2>
\t<p class="mt-4 text-slate-400">
\t\tImplement UI in <code class="text-slate-300">src/lib/modules/apps/{name}/</code>.
\t\tAPI base: <code class="text-slate-300">{{moduleUrl()}}</code>
\t</p>
</section>
'''


def _test_file(name: str) -> str:
    return f'''def test_{name}_root(client):
    response = client.get("/api/v1/{name}/")
    assert response.status_code == 200
    assert "message" in response.json()
'''


def _frontend_files(name: str) -> None:
    api_dir = PROJECT / "frontend/src/lib/modules/apps" / name
    _write_if_missing(api_dir / "api.ts", _frontend_api(name))
    _write_if_missing(
        PROJECT / "frontend/src/routes/(dashboard)" / name / "+page.svelte",
        _frontend_route(name),
    )


def _test_files(name: str) -> None:
    test_dir = PROJECT / "tests/backend/apps" / name
    _write_if_missing(test_dir / f"test_{name}.py", _test_file(name))


def cmd_app_create(args: argparse.Namespace) -> int:
    name = _validate_name(args.name)
    mod_dir = PROJECT / "backend/app/modules/apps" / name
    if mod_dir.exists() and not args.force:
        print(
            f"error: module {name!r} already exists (use --force to scaffold missing files)",
            file=sys.stderr,
        )
        return 1

    print(f"[fast-svelte] Scaffolding app module: {name}")
    _backend_files(name)
    _frontend_files(name)
    _test_files(name)

    print()
    print("Next steps:")
    print("  1. Inspect backend/app/modules/apps/sample/ as the canonical example")
    print(f"  2. Add models/service/repository to backend/app/modules/apps/{name}/")
    print(f"  3. Implement UI in frontend/src/routes/(dashboard)/{name}/")
    print(f"  4. Run: __ctrl__\\fast-svelte-ctrl.bat test backend")
    return 0


def build_app_subparser(sub: argparse._SubParsersAction) -> None:
    sp = sub.add_parser("app", help="Scaffold application modules")
    actions = sp.add_subparsers(dest="app_action", required=True)

    create_sp = actions.add_parser("create", help="Create a new app module skeleton")
    create_sp.add_argument("name", help="module name (e.g. bookmarks, orders)")
    create_sp.add_argument(
        "--force",
        action="store_true",
        help="create missing files even if the module directory exists",
    )
    create_sp.set_defaults(func=cmd_app_create)

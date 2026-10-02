# Execution plan — Fast-Svelte

**Live status:** **[PROGRESS.md](./PROGRESS.md)**.

This kit is a **product-agnostic foundation**. When you clone it into a product (Fast-Site, Fast-Shop, …), replace this file with the product’s critical path, decisions, and stage acceptance checks. Keep the same two-file contract:

| File | Role |
|------|------|
| **EXECUTION.md** | Decisions, critical path, stage details + acceptance |
| **PROGRESS.md** | Live status board agents update every stage |

## Decisions

| Area | Decision |
|------|----------|
| Product | _(fill when forking)_ |
| Architecture | Keep Fast-Svelte’s Router → Service → Repository → PostgreSQL flow, auth, Alembic whitelist, cache helpers, `__ctrl__`, and full/slim profiles. |
| Styling | Tailwind + local shadcn-svelte primitives only. No component-local CSS. |
| Exclusions | _(fill when forking)_ |

## Critical path

```text
F0 freeze product scope + first stages
→ (add product stages)
```

## Stage details

### F0 — Freeze product scope

- Brand the fork and control commands for the product.
- Record scope, boundaries, cache policy, and explicit exclusions.
- Mirror stages into [PROGRESS.md](./PROGRESS.md).

Acceptance:

- Repository identifies as the product, not Fast-Svelte.
- PROGRESS.md lists the first real stages with statuses.
- Agents can pick the next `pending` stage without guessing.

## Workflow (mandatory for agents)

1. One stage at a time from PROGRESS.md.
2. Mark `in_progress` → implement → run tests → mark `done` only on green.
3. Never skip the test gate between stages.

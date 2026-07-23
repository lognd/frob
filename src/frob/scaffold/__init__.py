"""frob.scaffold -- `frob scaffold` project-template rendering
(docs/commands/scaffold.md). Re-exports `frob.scaffold.project`'s
`ScaffoldError` (the failure type callers catch), `list_project_types`,
`render_project`, and `install_worktree_lease_hook` (T-0431) -- all
consumed by `frob.app.scaffold_runner` (T-0362). Also re-exports
`frob.scaffold._managed`'s managed-boilerplate-block API (T-0736):
`apply_managed_blocks` and `scaffold_conformance_status`, consumed by
`frob scaffold apply` and `frob doctor` respectively. Also re-exports
`frob.scaffold._pool`'s worktree warm-pool API (T-0738,
docs/guides/worktree-pool.md): `warm_pool`, `lease_worktree`,
`pool_status`, `PoolEntry`, `PoolError` -- consumed today via the
Makefile's `pool-warm`/`pool-lease`/`pool-status` targets; a `frob
scaffold pool` CLI subcommand wiring these through `frob.app.
scaffold_runner` is a separately-filed, out-of-scope follow-up (see this
module's own Done report).
"""

from __future__ import annotations

from frob.scaffold._managed import (
    ManagedBlockStatus,
    apply_managed_blocks,
    scaffold_conformance_status,
)
from frob.scaffold._pool import (
    PoolEntry,
    PoolError,
    default_pool_dir,
    lease_worktree,
    pool_status,
    read_manifest,
    refill_pool_async,
    warm_pool,
    warm_worktree,
)
from frob.scaffold.project import (
    ScaffoldError,
    install_worktree_lease_hook,
    list_project_types,
    render_project,
)

__all__ = [
    "ManagedBlockStatus",
    "PoolEntry",
    "PoolError",
    "ScaffoldError",
    "apply_managed_blocks",
    "default_pool_dir",
    "install_worktree_lease_hook",
    "lease_worktree",
    "list_project_types",
    "pool_status",
    "read_manifest",
    "refill_pool_async",
    "render_project",
    "scaffold_conformance_status",
    "warm_pool",
    "warm_worktree",
]

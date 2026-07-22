"""frob.scaffold -- `frob scaffold` project-template rendering
(docs/commands/scaffold.md). Re-exports `frob.scaffold.project`'s
`ScaffoldError` (the failure type callers catch), `list_project_types`,
`render_project`, and `install_worktree_lease_hook` (T-0431) -- all
consumed by `frob.app.scaffold_runner` (T-0362). Also re-exports
`frob.scaffold._managed`'s managed-boilerplate-block API (T-0736):
`apply_managed_blocks` and `scaffold_conformance_status`, consumed by
`frob scaffold apply` and `frob doctor` respectively.
"""

from __future__ import annotations

from frob.scaffold._managed import (
    ManagedBlockStatus,
    apply_managed_blocks,
    scaffold_conformance_status,
)
from frob.scaffold.project import (
    ScaffoldError,
    install_worktree_lease_hook,
    list_project_types,
    render_project,
)

__all__ = [
    "ManagedBlockStatus",
    "ScaffoldError",
    "apply_managed_blocks",
    "install_worktree_lease_hook",
    "list_project_types",
    "render_project",
    "scaffold_conformance_status",
]

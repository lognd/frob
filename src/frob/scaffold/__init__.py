"""frob.scaffold -- `frob scaffold` project-template rendering
(docs/commands/scaffold.md). Re-exports `frob.scaffold.project`'s
`ScaffoldError` (the failure type callers catch), `list_project_types`,
`render_project`, and `install_worktree_lease_hook` (T-0431) -- all
consumed by `frob.app.scaffold_runner` (T-0362).
"""

from __future__ import annotations

from frob.scaffold.project import (
    ScaffoldError,
    install_worktree_lease_hook,
    list_project_types,
    render_project,
)

__all__ = [
    "ScaffoldError",
    "install_worktree_lease_hook",
    "list_project_types",
    "render_project",
]

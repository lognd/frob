"""frob.scaffold -- `frob scaffold` project-template rendering
(docs/commands/scaffold.md). Re-exports `frob.scaffold.project`'s
`ScaffoldError` (the failure type callers catch), `list_project_types`,
and `render_project` -- all consumed by `frob.app.scaffold_runner` (T-0362).
"""

from __future__ import annotations

from frob.scaffold.project import ScaffoldError, list_project_types, render_project

__all__ = ["ScaffoldError", "list_project_types", "render_project"]

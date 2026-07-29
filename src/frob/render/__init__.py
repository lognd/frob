"""The unified CLI output layer -- the ONLY place `frob` writes user-facing
stdout (T-0448 EPIC foundation).

Every command runner should build one `Renderer` (via `Renderer.for_stream`,
which resolves color exactly once against `sys.stdout`, CLI flags, and
environment) and write through it, instead of calling `print`,
`click.echo`, or a module logger for human-facing text. `--json`/machine
output stays a separate channel this layer does not touch -- callers gate
on `cfg.*_json` before ever constructing a `Renderer`.

See `frob.render._color` for the TTY/color precedence, `frob.render.
_palette` for the five-name semantic palette, and `frob.render._elements`
for the standardized vocabulary (heading, subhead, kv row, status pill,
count summary, path, ticket-id, table, tree, count deltas) each element
renders through. `frob.render._renderer.Progress` (T-0460) is the one
TTY-only, cursor-controlling exception to "every element is total plain
text" -- it never reaches a non-TTY stream at all, per the T-0419 contract.

A follow-up ticket (named, not yet filed, in T-0448's Done report) adds the
enforcement gate that fails `frob check` on a bare print/echo outside this
package, mirroring the module-logger discipline `frob.logging` already
enforces.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from frob.render._color import ColorFlag, resolve_color
from frob.render._elements import (
    Status,
    count_deltas,
    count_summary,
    heading,
    kv_row,
    path_label,
    status_pill,
    subhead,
    table,
    ticket_id_label,
    tree,
)
from frob.render._errors import RenderError
from frob.render._palette import accent, critical, good, muted, warn
from frob.render._renderer import Progress, Renderer, RenderWriter

__all__ = [
    "ColorFlag",
    "Progress",
    "RenderError",
    "RenderWriter",
    "Renderer",
    "Status",
    "accent",
    "count_deltas",
    "count_summary",
    "critical",
    "good",
    "heading",
    "kv_row",
    "muted",
    "path_label",
    "resolve_color",
    "status_pill",
    "subhead",
    "table",
    "ticket_id_label",
    "tree",
    "warn",
]

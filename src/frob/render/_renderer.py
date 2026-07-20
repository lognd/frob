"""The `Renderer` facade -- the only object a command runner should print
through (T-0448).

Bundles a resolved color decision with a target stream so runners never
call `should_color`/`resolve_color` themselves and never call `print`
directly for user-facing text; that concentration is what "no bare print
outside frob.render" (the follow-up enforcement gate, named in T-0448's
Done report) will check for.

`Renderer` itself only owns stream/color plumbing and the two
structure-only primitives (`blank`, `line`); every element-specific write
lives on the `Renderer.write` sub-namespace (`RenderWriter`) instead of as
a flat `write_*` method directly on `Renderer` -- ARCH001 flagged the flat
form as a god-class in the making once a dozen more commands start calling
through it, so the vocabulary gets its own home now, before that happens.
Each `RenderWriter` method emits exactly one line via the matching
`frob.render._elements` constructor. Fallible elements (`status`,
`ticket_id`) surface the `Result` to the caller instead of silently
swallowing a malformed value -- a runner decides whether that is a crash-
worthy bug or a "fall back to plain text" situation.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import IO

from typani.result import Err, Ok, Result

from frob.render._color import ColorFlag, resolve_color
from frob.render._elements import (
    count_summary,
    heading,
    kv_row,
    path_label,
    status_pill,
    subhead,
    ticket_id_label,
)
from frob.render._errors import RenderError
from frob.render._palette import critical, good, muted, warn


# frob:ticket T-0448
# frob:doc docs/modules/render.md#renderer
class RenderWriter:
    """The standardized element vocabulary, namespaced off `Renderer.write`
    so the vocabulary can grow (table, tree, progress -- named follow-ups
    in T-0448's Done report) without `Renderer` itself accreting methods."""

    def __init__(self, emit, *, color: bool) -> None:
        """Bind this writer to `emit` (a single-line sink) and a resolved
        color decision; constructed only by `Renderer`, never directly."""
        self._emit = emit
        self.color = color

    # frob:doc docs/modules/render.md#renderer
    def heading(self, text: str) -> None:
        """Emit a top-level section heading."""
        self._emit(heading(text, color=self.color))

    # frob:doc docs/modules/render.md#renderer
    def subhead(self, text: str) -> None:
        """Emit a secondary section heading."""
        self._emit(subhead(text, color=self.color))

    # frob:doc docs/modules/render.md#renderer
    def kv(self, key: str, value: str) -> None:
        """Emit a `key: value` row."""
        self._emit(kv_row(key, value, color=self.color))

    # frob:doc docs/modules/render.md#renderer
    def status(self, status: str, text: str) -> Result[None, RenderError]:
        """Emit `[STATUS] text`; propagates `Err(InvalidStatus)` rather
        than guessing at an unknown status value."""
        pill = status_pill(status, color=self.color)
        if pill.is_err:
            return Err(pill.danger_err)
        self._emit(f"{pill.danger_ok} {text}")
        return Ok(None)

    # frob:doc docs/modules/render.md#renderer
    def count_summary(self, counts: Mapping[str, int]) -> None:
        """Emit a `key=n, key=n` rollup line."""
        self._emit(count_summary(counts, color=self.color))

    # frob:doc docs/modules/render.md#renderer
    def path(self, p: str | Path) -> None:
        """Emit a `muted`-painted filesystem path."""
        self._emit(path_label(p, color=self.color))

    # frob:doc docs/modules/render.md#renderer
    def ticket_id(self, ticket_id: str) -> Result[None, RenderError]:
        """Emit an accent-painted `T-####` id; propagates
        `Err(InvalidTicketId)` for a malformed id."""
        label = ticket_id_label(ticket_id, color=self.color)
        if label.is_err:
            return Err(label.danger_err)
        self._emit(label.danger_ok)
        return Ok(None)

    # frob:doc docs/modules/render.md#renderer
    def good(self, text: str) -> None:
        """Emit `text` painted `good` -- a passed check or healthy state."""
        self._emit(good(text, self.color))

    # frob:doc docs/modules/render.md#renderer
    def warn(self, text: str) -> None:
        """Emit `text` painted `warn` -- a degraded-but-not-broken state."""
        self._emit(warn(text, self.color))

    # frob:doc docs/modules/render.md#renderer
    def critical(self, text: str) -> None:
        """Emit `text` painted `critical` -- a failed check or error."""
        self._emit(critical(text, self.color))

    # frob:doc docs/modules/render.md#renderer
    def muted(self, text: str) -> None:
        """Emit `text` painted `muted` -- secondary/low-priority context."""
        self._emit(muted(text, self.color))


# frob:ticket T-0448
# frob:doc docs/modules/render.md#renderer
class Renderer:
    """A stream bound to one resolved color decision. Structure-only
    primitives (`blank`, `line`) live here; the standardized element
    vocabulary lives on `.write` (a `RenderWriter`)."""

    def __init__(self, stream: IO[str] | None = None, *, color: bool) -> None:
        """Bind this renderer to `stream` (default stdout) with a color
        decision already resolved by the caller (see `Renderer.for_stream`)."""
        self.stream: IO[str] = stream if stream is not None else sys.stdout
        self.color = color
        self.write = RenderWriter(self._emit, color=color)

    # frob:doc docs/modules/render.md#renderer
    @classmethod
    def for_stream(
        cls,
        stream: IO[str] | None = None,
        *,
        color_flag: ColorFlag | None = None,
        no_color_flag: bool = False,
    ) -> "Renderer":
        """Build a `Renderer` for `stream` (default stdout), resolving
        color exactly once via `frob.render.resolve_color`."""
        target = stream if stream is not None else sys.stdout
        return cls(
            target,
            color=resolve_color(
                target, color_flag=color_flag, no_color_flag=no_color_flag
            ),
        )

    def _emit(self, line: str) -> None:
        """Write one line to the bound stream."""
        print(line, file=self.stream)

    # frob:doc docs/modules/render.md#renderer
    def blank(self) -> None:
        """Emit a blank line -- the only whitespace element, kept explicit
        so vertical spacing is never a stray `print()` outside this class."""
        self._emit("")

    # frob:doc docs/modules/render.md#renderer
    def line(self, text: str) -> None:
        """Emit `text` verbatim -- the escape hatch for body prose that has
        no dedicated element (e.g. an already-formatted tree dump)."""
        self._emit(text)


__all__ = ["RenderWriter", "Renderer"]

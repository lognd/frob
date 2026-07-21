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
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import TracebackType
from typing import IO

from typani.result import Err, Ok, Result

from frob.render._color import ColorFlag, resolve_color
from frob.render._elements import (
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
from frob.render._palette import critical, good, muted, warn


# frob:ticket T-0460
# frob:doc docs/modules/render.md#progress-t-0419-contract-tty-only
class Progress:
    """An ephemeral, TTY-only progress indicator (the T-0419 contract):
    `update` redraws one in-place line via a carriage return, and `clear`
    (also called automatically on context-manager exit) erases that line
    entirely so nothing is left behind once the tracked work completes. On
    a non-TTY stream every method is a no-op -- no cursor control, no bar,
    ever reaches a pipe or log capture."""

    def __init__(self, stream: IO[str], *, tty: bool) -> None:
        """Bind this indicator to `stream`; `tty` is decided once by the
        `Renderer` that constructs it, never re-checked per update."""
        self._stream = stream
        self._tty = tty
        self._last_len = 0

    # frob:doc docs/modules/render.md#progress-t-0419-contract-tty-only
    def update(self, label: str, current: int, total: int) -> None:
        """Redraw the progress line in place: `label [#####-----] NN%`.
        No-op when the bound stream is not a TTY."""
        if not self._tty:
            return
        pct = int(100 * current / total) if total else 0
        pct = max(0, min(100, pct))
        bar_width = 20
        filled = int(bar_width * current / total) if total else 0
        filled = max(0, min(bar_width, filled))
        bar = "#" * filled + "-" * (bar_width - filled)
        line = f"{label} [{bar}] {pct}%"
        pad = " " * max(0, self._last_len - len(line))
        self._stream.write(f"\r{line}{pad}")
        self._stream.flush()
        self._last_len = len(line)

    # frob:doc docs/modules/render.md#progress-t-0419-contract-tty-only
    def clear(self) -> None:
        """Erase the current progress line, leaving the cursor at column
        zero and no residue. No-op when the bound stream is not a TTY."""
        if not self._tty:
            return
        self._stream.write("\r" + " " * self._last_len + "\r")
        self._stream.flush()
        self._last_len = 0

    def __enter__(self) -> "Progress":
        """Enter the `with r.write.progress(...) as p:` block unchanged."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Always clear the progress line on block exit, success or not,
        so a raised exception never leaves a stale bar on screen."""
        self.clear()


# frob:ticket T-0448
# frob:ticket T-0460
# frob:doc docs/modules/render.md#renderer
class RenderWriter:
    """The standardized element vocabulary, namespaced off `Renderer.write`
    so the vocabulary can grow without `Renderer` itself accreting methods."""

    def __init__(
        self, emit, *, color: bool, stream: IO[str] | None = None, tty: bool = False
    ) -> None:
        """Bind this writer to `emit` (a single-line sink), a resolved
        color decision, and (for `progress`) the raw `stream`/`tty` state;
        constructed only by `Renderer`, never directly."""
        self._emit = emit
        self.color = color
        self._stream = stream
        self._tty = tty

    # frob:doc docs/modules/render.md#renderer
    def heading(self, text: str) -> None:
        """Emit a top-level section heading."""
        # frob:invariant terminates reason="not actual recursion: this call resolves to the module-level frob.render._elements.heading imported above, a distinct function with the same name, never RenderWriter.heading itself" measure="not recursive; call depth is fixed at 1"  # noqa: E501
        self._emit(heading(text, color=self.color))

    # frob:doc docs/modules/render.md#renderer
    def subhead(self, text: str) -> None:
        """Emit a secondary section heading."""
        # frob:invariant terminates reason="not actual recursion: this call resolves to the module-level frob.render._elements.subhead imported above, a distinct function with the same name, never RenderWriter.subhead itself" measure="not recursive; call depth is fixed at 1"  # noqa: E501
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
        # frob:invariant terminates reason="not actual recursion: this call resolves to the module-level frob.render._elements.count_summary imported above, a distinct function with the same name, never RenderWriter.count_summary itself" measure="not recursive; call depth is fixed at 1"  # noqa: E501
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
        # frob:invariant terminates reason="not actual recursion: this call resolves to the module-level frob.render._palette.good imported above, a distinct function with the same name, never RenderWriter.good itself" measure="not recursive; call depth is fixed at 1"  # noqa: E501
        self._emit(good(text, self.color))

    # frob:doc docs/modules/render.md#renderer
    def warn(self, text: str) -> None:
        """Emit `text` painted `warn` -- a degraded-but-not-broken state."""
        # frob:invariant terminates reason="not actual recursion: this call resolves to the module-level frob.render._palette.warn imported above, a distinct function with the same name, never RenderWriter.warn itself" measure="not recursive; call depth is fixed at 1"  # noqa: E501
        self._emit(warn(text, self.color))

    # frob:doc docs/modules/render.md#renderer
    def critical(self, text: str) -> None:
        """Emit `text` painted `critical` -- a failed check or error."""
        # frob:invariant terminates reason="not actual recursion: this call resolves to the module-level frob.render._palette.critical imported above, a distinct function with the same name, never RenderWriter.critical itself" measure="not recursive; call depth is fixed at 1"  # noqa: E501
        self._emit(critical(text, self.color))

    # frob:doc docs/modules/render.md#renderer
    def muted(self, text: str) -> None:
        """Emit `text` painted `muted` -- secondary/low-priority context."""
        # frob:invariant terminates reason="not actual recursion: this call resolves to the module-level frob.render._palette.muted imported above, a distinct function with the same name, never RenderWriter.muted itself" measure="not recursive; call depth is fixed at 1"  # noqa: E501
        self._emit(muted(text, self.color))

    # frob:ticket T-0460
    # frob:doc docs/modules/render.md#element-vocabulary
    def table(self, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
        """Emit a fixed-column table: header row, `-`-rule, then data rows,
        one `_emit` call per line."""
        # frob:invariant terminates reason="not actual recursion: this call resolves to the module-level frob.render._elements.table imported above, a distinct function with the same name, never RenderWriter.table itself" measure="not recursive; call depth is fixed at 1"  # noqa: E501
        for line in table(headers, rows, color=self.color):
            self._emit(line)

    # frob:ticket T-0460
    # frob:doc docs/modules/render.md#element-vocabulary
    def tree(self, entries: Sequence[tuple[int, str]]) -> None:
        """Emit a hierarchical `(depth, label)` listing, one `_emit` call
        per line."""
        # frob:invariant terminates reason="not actual recursion: this call resolves to the module-level frob.render._elements.tree imported above, a distinct function with the same name, never RenderWriter.tree itself" measure="not recursive; call depth is fixed at 1"  # noqa: E501
        for line in tree(entries, color=self.color):
            self._emit(line)

    # frob:ticket T-0460
    # frob:doc docs/modules/render.md#element-vocabulary
    def count_deltas(self, deltas: Mapping[str, tuple[int, int]]) -> None:
        """Emit a `key: old -> new (+/-n)` before/after rollup line."""
        # frob:invariant terminates reason="not actual recursion: this call resolves to the module-level frob.render._elements.count_deltas imported above, a distinct function with the same name, never RenderWriter.count_deltas itself" measure="not recursive; call depth is fixed at 1"  # noqa: E501
        self._emit(count_deltas(deltas, color=self.color))

    # frob:ticket T-0460
    # frob:doc docs/modules/render.md#progress-t-0419-contract-tty-only
    def progress(self, label: str) -> Progress:
        """Build a `Progress` bound to this writer's stream/TTY state (the
        T-0419 contract): ephemeral in-place updates on a human TTY, a
        silent no-op everywhere else. Use as a context manager so the line
        is always cleared on exit: `with r.write.progress("stage") as p:`."""
        stream = self._stream if self._stream is not None else sys.stdout
        return Progress(stream, tty=self._tty)


# frob:ticket T-0448
# frob:doc docs/modules/render.md#renderer
class Renderer:
    """A stream bound to one resolved color decision. Structure-only
    primitives (`blank`, `line`) live here; the standardized element
    vocabulary lives on `.write` (a `RenderWriter`)."""

    def __init__(self, stream: IO[str] | None = None, *, color: bool) -> None:
        """Bind this renderer to `stream` (default stdout) with a color
        decision already resolved by the caller (see `Renderer.for_stream`).
        TTY-ness is checked once here too (independent of the color
        decision, since `--no-color` on a real TTY must still gate
        `progress` off) and threaded into `RenderWriter`."""
        self.stream: IO[str] = stream if stream is not None else sys.stdout
        self.color = color
        self.is_tty = bool(getattr(self.stream, "isatty", lambda: False)())
        self.write = RenderWriter(
            self._emit, color=color, stream=self.stream, tty=self.is_tty
        )

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


__all__ = ["Progress", "RenderWriter", "Renderer"]

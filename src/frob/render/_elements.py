"""Standardized element vocabulary for the render layer (T-0448).

Every element has exactly one plain-text SHAPE (the sequence of characters
a plain-mode caller and a color-mode caller both produce, modulo ANSI
bytes) -- color only paints substrings of that same shape, it never adds or
removes structure. That is what makes plain mode "canonical machine-stable"
per the epic's design: `frob ... | tee` and an agent capturing stdout see
the identical columns a human sees, just without escape codes.

Elements that validate untrusted/derived input (`status_pill`,
`ticket_id_label`) return `typani.Result[str, RenderError]` per repo
convention; the rest are total functions over `str`/`Mapping` and cannot
fail.
"""
# frob:waive ARCH102 reason="this module IS a deliberate flat vocabulary of \
# independent leaf rendering primitives (T-0448's docstring above); cohesion here is \
# by ROLE -- every element shares the same plain/color-shape contract this docstring \
# names -- not by naming prefix or call graph, so 9 clusters over 10 exports is the \
# expected shape of a primitives catalog, not fragmentation. Splitting \
# heading/subhead/kv_row/status_pill/ path_label/ticket_id_label/table/tree into 8-9 \
# one-function files would scatter a single well-known `frob.render._elements` import \
# surface with no independent concern gained"

# frob:invariant INV-040
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal

from typani.result import Err, Ok, Result

from frob.render._errors import RenderError
from frob.render._palette import accent, critical, good, muted, warn

# frob:doc docs/modules/render.md#element-vocabulary
Status = Literal["ok", "warn", "error", "skip"]

_STATUS_PAINTERS = {
    "ok": good,
    "warn": warn,
    "error": critical,
    "skip": muted,
}
_STATUS_LABELS = {
    "ok": "OK",
    "warn": "WARN",
    "error": "ERROR",
    "skip": "SKIP",
}
_TICKET_ID_RE = re.compile(r"^T-\d{4}$")


# frob:ticket T-0448
# frob:doc docs/modules/render.md#element-vocabulary
def heading(text: str, *, color: bool) -> str:
    """A top-level section title -- bold in color mode, bare text in plain
    mode (position/blank-line spacing carries the hierarchy, not markup)."""
    return accent(text, color) if color else text


# frob:ticket T-0448
# frob:doc docs/modules/render.md#element-vocabulary
def subhead(text: str, *, color: bool) -> str:
    """A secondary section title, marked with a `--` prefix in BOTH modes
    so the shape is identical and only the paint differs."""
    shape = f"-- {text}"
    return accent(shape, color) if color else shape


# frob:ticket T-0448
# frob:doc docs/modules/render.md#element-vocabulary
def kv_row(key: str, value: str, *, color: bool) -> str:
    """A `key: value` line -- the key painted `muted` so the eye lands on
    the value, which is never colored (it is caller-supplied data, not a
    severity)."""
    key_text = muted(f"{key}:", color) if color else f"{key}:"
    return f"{key_text} {value}"


# frob:ticket T-0448
# frob:doc docs/modules/render.md#element-vocabulary
def status_pill(status: str, *, color: bool) -> Result[str, RenderError]:
    """A `[OK]`/`[WARN]`/`[ERROR]`/`[SKIP]` pill; `Err(InvalidStatus)` for
    any other value so a typo in caller code fails loudly rather than
    printing a silently-uncolored pill."""
    painter = _STATUS_PAINTERS.get(status)
    if painter is None:
        return Err(RenderError.InvalidStatus)
    label = _STATUS_LABELS[status]
    body = painter(label, color) if color else label
    return Ok(f"[{body}]")


# frob:ticket T-0448
# frob:doc docs/modules/render.md#element-vocabulary
def count_summary(counts: Mapping[str, int], *, color: bool) -> str:
    """A `key=n, key=n` summary line in insertion order -- the canonical
    shape for "N ok, M warned, K failed" style rollups."""
    parts = [f"{k}={v}" for k, v in counts.items()]
    shape = ", ".join(parts)
    return muted(shape, color) if color else shape


# frob:ticket T-0448
# frob:doc docs/modules/render.md#element-vocabulary
def path_label(p: str | Path, *, color: bool) -> str:
    """A filesystem path, painted `muted` -- secondary context next to a
    primary message, never the focal point of a line."""
    shape = str(p)
    return muted(shape, color) if color else shape


# frob:ticket T-0448
# frob:doc docs/modules/render.md#element-vocabulary
def ticket_id_label(ticket_id: str, *, color: bool) -> Result[str, RenderError]:
    """A `T-####` id, bold-accented; `Err(InvalidTicketId)` when the shape
    does not match, so a malformed id is caught at render time rather than
    silently printed as if it were valid."""
    if not _TICKET_ID_RE.match(ticket_id):
        return Err(RenderError.InvalidTicketId)
    return Ok(accent(ticket_id, color) if color else ticket_id)


# frob:ticket T-0460
# frob:doc docs/modules/render.md#element-vocabulary
def table(
    headers: Sequence[str], rows: Sequence[Sequence[str]], *, color: bool
) -> list[str]:
    """A fixed-column table -- header row (painted `accent`), a `-`-rule
    separator (painted `muted`), then data rows, one line per list entry so
    a caller emits each line verbatim. Column widths are the max of the
    header and every row's cell in that column, so the plain shape (widths,
    two-space gutters) is identical in color and plain mode -- color only
    paints the header/rule, it never re-flows a column."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    rule = "  ".join("-" * widths[i] for i in range(len(headers)))
    lines = [
        accent(header_line, color) if color else header_line,
        muted(rule, color) if color else rule,
    ]
    for row in rows:
        line = "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))
        lines.append(line)
    return lines


# frob:ticket T-0460
# frob:doc docs/modules/render.md#element-vocabulary
def tree(entries: Sequence[tuple[int, str]], *, color: bool) -> list[str]:
    """A hierarchical listing from `(depth, label)` pairs -- each line is
    two spaces of indent per depth level plus a `- ` marker, so the plain
    shape is deterministic and greppable (no box-drawing connectors that
    depend on sibling lookahead). `depth` 0 labels are painted `accent`
    (section roots); deeper labels are left uncolored body text."""
    lines = []
    for depth, label in entries:
        indent = "  " * depth
        shape = f"{indent}- {label}"
        if color and depth == 0:
            lines.append(f"{indent}- {accent(label, color)}")
        else:
            lines.append(shape)
    return lines


# frob:ticket T-0460
# frob:doc docs/modules/render.md#element-vocabulary
def count_deltas(deltas: Mapping[str, tuple[int, int]], *, color: bool) -> str:
    """A `key: old -> new (+n/-n)` rollup line for before/after counts (the
    `frob check --delta` use case). Fewer is assumed the improving
    direction (a violation-count convention, not a general one): a
    non-positive delta paints `good`, a positive delta paints `critical`,
    and an unchanged count paints `muted`."""
    parts = []
    for key, (before, after) in deltas.items():
        delta = after - before
        sign = f"+{delta}" if delta > 0 else str(delta)
        segment = f"{key}: {before} -> {after} ({sign})"
        if color:
            if delta > 0:
                segment = critical(segment, color)
            elif delta < 0:
                segment = good(segment, color)
            else:
                segment = muted(segment, color)
        parts.append(segment)
    return ", ".join(parts)


__all__ = [
    "Status",
    "count_deltas",
    "count_summary",
    "heading",
    "kv_row",
    "path_label",
    "status_pill",
    "subhead",
    "table",
    "ticket_id_label",
    "tree",
]
# invariant spec: [INV-040](invariants/INV-040.md)

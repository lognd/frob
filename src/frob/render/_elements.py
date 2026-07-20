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

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from typani.result import Err, Ok, Result

from frob.render._errors import RenderError
from frob.render._palette import accent, critical, good, muted, warn

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


__all__ = [
    "Status",
    "count_summary",
    "heading",
    "kv_row",
    "path_label",
    "status_pill",
    "subhead",
    "ticket_id_label",
]

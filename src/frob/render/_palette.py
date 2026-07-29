"""Semantic color palette for the render layer (T-0448).

Five named intents only -- `good`, `warn`, `critical`, `muted`, `accent` --
never a raw SGR code at a call site; a decorative color choice ("let's make
paths blue") is exactly the drift this module exists to prevent. Reuses the
SGR codes `frob.logging.color` already defines rather than inventing a
second palette (NO DUPLICATION) -- this module only adds the semantic
naming layer and the colorblind-safety composition on top.

Colorblind-safe: red/green confusion (deuteranopia/protanopia, the common
forms) is the risk to design around. `good` (green) and `critical` (red)
are the pair most likely to collide for those users, so `critical` also
carries `BOLD` -- weight, not just hue, distinguishes it even when red and
green read as the same color. `warn` (yellow) sits outside the red/green
confusion axis entirely. `accent` uses cyan, also outside that axis, so it
is never mistaken for a severity color. `muted` carries no hue at all
(`DIM`), so it never competes with the severity palette.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from frob.logging.color import BOLD, CYAN, DIM, GREEN, RED, YELLOW, paint

# frob:doc docs/modules/render.md#semantic-palette
GOOD = GREEN
# frob:doc docs/modules/render.md#semantic-palette
WARN = YELLOW
# frob:doc docs/modules/render.md#semantic-palette
CRITICAL = f"{BOLD};{RED}"
# frob:doc docs/modules/render.md#semantic-palette
MUTED = DIM
# frob:doc docs/modules/render.md#semantic-palette
ACCENT = CYAN


# frob:ticket T-0448
# frob:doc docs/modules/render.md#semantic-palette
def good(text: str, color: bool) -> str:
    """A passed check, healthy state, or clean result."""
    return paint(text, GOOD, color)


# frob:ticket T-0448
# frob:doc docs/modules/render.md#semantic-palette
def warn(text: str, color: bool) -> str:
    """A degraded-but-not-broken state, or a waived/skipped item."""
    return paint(text, WARN, color)


# frob:ticket T-0448
# frob:doc docs/modules/render.md#semantic-palette
def critical(text: str, color: bool) -> str:
    """A failed check or error condition -- bold red, kept distinguishable
    from `good` under red/green colorblindness by weight, not just hue."""
    return paint(text, CRITICAL, color)


# frob:ticket T-0448
# frob:doc docs/modules/render.md#semantic-palette
def muted(text: str, color: bool) -> str:
    """Secondary/low-priority information (paths, timestamps, ids)."""
    return paint(text, MUTED, color)


# frob:ticket T-0448
# frob:doc docs/modules/render.md#semantic-palette
def accent(text: str, color: bool) -> str:
    """A structural highlight (headings, subheadings) -- never a severity."""
    return paint(text, ACCENT, color)


__all__ = [
    "ACCENT",
    "CRITICAL",
    "GOOD",
    "MUTED",
    "WARN",
    "accent",
    "critical",
    "good",
    "muted",
    "warn",
]

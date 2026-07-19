"""Shared human-output styling helpers for CLI runners (T-0179).

Centralizes how ticket ids, states, and pass/fail/severity words get
painted so every `frob` subcommand's human-facing text draws from ONE
palette instead of ad hoc ANSI calls scattered per runner (the same
"one decision function" discipline `frob.logging.color.should_color`
already established for the color-or-not decision itself).

Every helper here is a pure text -> text transform: callers decide
`color` (normally `should_color(stream)`, evaluated against the SPECIFIC
stream a line will land on -- stdout for INFO/DEBUG, stderr for
WARNING+, per `frob.logging.config.toml`'s handler split) and these
functions never touch a stream themselves. `--json`/machine paths must
never call any of these -- they gate on `color` being statically False
long before reaching here, so a piped/non-TTY run stays byte-identical
to plain text (paint() is a no-op when `color` is False).
"""

from __future__ import annotations

from frob.logging.color import BOLD, CYAN, DIM, GREEN, RED, YELLOW, paint

# frob:ticket T-0179
# frob:doc docs/modules/app.md#shared-styling-helper-t-0179
# Ticket-state -> SGR code. States absent here (any future/unknown value)
# fall back to no color in `style_state` rather than guessing a mapping.
STATE_STYLE = {
    "done": GREEN,
    "in_progress": CYAN,
    "planned": YELLOW,
    "queued": DIM,
    "blocked": RED,
    "dropped": DIM,
    "failed": RED,
}


# frob:ticket T-0179
# frob:doc docs/modules/app.md#shared-styling-helper-t-0179
def style_ticket_id(ticket_id: str, color: bool) -> str:
    """A ticket id (`T-0042`) bolded -- a stable anchor across every listing."""
    return paint(ticket_id, BOLD, color)


# frob:ticket T-0179
# frob:doc docs/modules/app.md#shared-styling-helper-t-0179
def style_state(state: str, color: bool) -> str:
    """A ticket state word colored per `STATE_STYLE`; unrecognized states
    pass through unchanged rather than guessing a color."""
    code = STATE_STYLE.get(state)
    if code is None:
        return state
    return paint(state, code, color)


# frob:ticket T-0179
# frob:doc docs/modules/app.md#shared-styling-helper-t-0179
def style_ok(text: str, color: bool) -> str:
    """Green -- a passed check, PROVED verdict, or clean result."""
    return paint(text, GREEN, color)


# frob:ticket T-0179
# frob:doc docs/modules/app.md#shared-styling-helper-t-0179
def style_fail(text: str, color: bool) -> str:
    """Red -- a failed check, GAP, or error condition."""
    return paint(text, RED, color)


# frob:ticket T-0179
# frob:doc docs/modules/app.md#shared-styling-helper-t-0179
def style_warn(text: str, color: bool) -> str:
    """Yellow -- a WARNED/waived item."""
    return paint(text, YELLOW, color)


# frob:ticket T-0179
# frob:doc docs/modules/app.md#shared-styling-helper-t-0179
def style_header(text: str, color: bool) -> str:
    """Bold -- a section header."""
    return paint(text, BOLD, color)


# frob:ticket T-0179
# frob:doc docs/modules/app.md#shared-styling-helper-t-0179
def style_rule(rule_id: str, color: bool) -> str:
    """A rule/gate id (e.g. `THREAT002`) subtly highlighted in cyan."""
    return paint(rule_id, CYAN, color)


__all__ = [
    "STATE_STYLE",
    "style_fail",
    "style_header",
    "style_ok",
    "style_rule",
    "style_state",
    "style_ticket_id",
    "style_warn",
]

"""Single TTY/color decision for the whole render layer (T-0448).

`frob.logging.color.should_color` already owns the decision of whether a
LOG line gets ANSI (T-0023) -- it correctly knows nothing about CLI flags,
because a log formatter never sees `argparse.Namespace`. The render layer's
question is a strict superset: it also has to honor `--no-color`,
`--color=auto|always|never`, and `CLICOLOR_FORCE`, on top of every env var
`should_color` already understands. `resolve_color` is that superset
decision, computed exactly ONCE per CLI invocation (by
`frob.app.App`/callers building a `Renderer`) and threaded down rather than
re-derived per call site -- a second ad hoc `isatty()` check anywhere else
in the codebase is how NO_COLOR handling desyncs across commands.

Precedence (first match wins):
1. `--no-color` -- never color, full stop.
2. `--color=never` -- never.
3. `--color=always` -- always, even when piped (explicit override).
4. `NO_COLOR` set (any value, per no-color.org) -- never.
5. `FROB_NO_COLOR` set (any value) -- never; a frob-specific escape hatch
   for environments that can't set the generic `NO_COLOR` var.
6. `CLICOLOR_FORCE` set to a non-empty, non-"0" value -- always, even when
   piped (the de facto convention several CLI ecosystems share).
7. `TERM=dumb` -- never.
8. Otherwise: color iff the target stream is a TTY.
"""

from __future__ import annotations

import os
import sys
from typing import IO, Literal

ColorFlag = Literal["auto", "always", "never"]


# frob:ticket T-0448
# frob:doc docs/modules/render.md#color-resolution
def resolve_color(
    stream: IO[str] | None = None,
    *,
    color_flag: ColorFlag | None = None,
    no_color_flag: bool = False,
) -> bool:
    """Whether ANSI belongs on `stream` (default stdout) given CLI flags and
    environment, per the precedence documented on this module."""
    if no_color_flag:
        return False
    if color_flag == "never":
        return False
    if color_flag == "always":
        return True
    if "NO_COLOR" in os.environ:
        return False
    if "FROB_NO_COLOR" in os.environ:
        return False
    force = os.environ.get("CLICOLOR_FORCE")  # frob:waive SEC110 reason="terminal color-capability flag, not a secret"
    if force is not None and force not in ("", "0"):
        return True
    if os.environ.get("TERM") == "dumb":
        return False
    target = stream if stream is not None else sys.stdout
    return bool(getattr(target, "isatty", lambda: False)())


__all__ = ["ColorFlag", "resolve_color"]

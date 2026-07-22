"""Terminal color for frob's human-facing output (T-0023).

One decision function and one paint function -- every CLI surface that
wants color imports THESE two; a second should_color implementation is
how NO_COLOR handling desyncs across commands.

Precedence: NO_COLOR set (any value, per no-color.org) -> never;
FORCE_COLOR set -> always; else color only when the stream is a TTY and
TERM is not "dumb". JSON output paths must never call paint at all --
machine output stays byte-stable regardless of environment.
"""

# frob:invariant INV-037
from __future__ import annotations

import os
import sys
from typing import IO

# frob:doc docs/modules/logging.md#public-api
RED = "31"
# frob:doc docs/modules/logging.md#public-api
GREEN = "32"
# frob:doc docs/modules/logging.md#public-api
YELLOW = "33"
# frob:doc docs/modules/logging.md#public-api
CYAN = "36"
# frob:doc docs/modules/logging.md#public-api
BOLD = "1"
# frob:doc docs/modules/logging.md#public-api
DIM = "2"


# frob:doc docs/modules/logging.md#public-api
# frob:waive TEST005 reason="should_color 71.4% branch cover, debt T-0160"
def should_color(stream: IO[str] | None = None) -> bool:
    """Whether ANSI color belongs on `stream` (default stdout) right now."""
    if "NO_COLOR" in os.environ:
        return False
    if "FORCE_COLOR" in os.environ:
        return True
    target = stream if stream is not None else sys.stdout
    return bool(getattr(target, "isatty", lambda: False)()) and (
        os.environ.get("TERM") != "dumb"
    )


# frob:doc docs/modules/logging.md#public-api
def paint(text: str, code: str, enabled: bool = True) -> str:
    """`text` wrapped in the SGR `code` when `enabled`, verbatim otherwise."""
    if not enabled:
        return text
    return f"\x1b[{code}m{text}\x1b[0m"


__all__ = ["BOLD", "CYAN", "DIM", "GREEN", "RED", "YELLOW", "paint", "should_color"]

"""frob._cli_parsers._shims -- the ONE deprecation-shim mechanism for every
CLI verb/alias T-4690 deletes (T-4687 CLI surface reduction). Built on top
of the existing `frob:deprecated` directive convention (see
`frob.gates._debt_deprecated`, `frob.gates._deprecated_baseline`,
`frob.app.deprecated_runner`) and the working precedent in
`frob.app.fmt_runner` (T-3906): a removed spelling keeps working, with a
stderr notice, for one minor version, then starts failing loudly instead of
either vanishing silently or lingering forever.

Every runner for a deleted/renamed top-level verb calls `announce_shim`
once at the top of its `run()`. This is deliberately the ONLY place that
computes past-sunset behavior at CLI-invocation time -- a second
implementation of the same date check is exactly the duplication this
story exists to delete.
"""

from __future__ import annotations

import datetime as _dt
import sys

from frob.logging import get_logger
from frob.render import ColorFlag, Renderer

_log = get_logger(__name__)


def _parse_sunset(sunset: str) -> _dt.date:
    """Parse a `frob:deprecated`-style `sunset="YYYY-MM-DD"` value into a
    `date`; raises `ValueError` on malformed input rather than guessing,
    since a silently-mis-parsed sunset would defeat the whole mechanism."""
    return _dt.date.fromisoformat(sunset)


# frob:doc docs/modules/app.md#runners
def is_past_sunset(sunset: str, *, today: _dt.date | None = None) -> bool:
    """`True` once `today` (default: the real current date) is strictly
    after `sunset` -- the single source of truth every shim runner and
    `tests/unit/test_cli_shims.py` both call, so the boundary date itself
    is never duplicated as a literal comparison elsewhere."""
    return (today or _dt.date.today()) > _parse_sunset(sunset)


# frob:doc docs/modules/app.md#runners
# frob:ticket T-5285
def announce_shim(
    *,
    old_name: str,
    new_name: str,
    sunset: str,
    ticket: str,
    color: ColorFlag | None = None,
    no_color: bool = False,
    today: _dt.date | None = None,
) -> None:
    """Print the `old_name` -> `new_name` deprecation notice to stderr and,
    once `sunset` (`YYYY-MM-DD`) has passed, raise `SystemExit(1)` instead
    of letting the deleted spelling keep working forever -- the runtime
    half of the `frob:deprecated` contract whose static half is enforced by
    `frob.gates._debt_deprecated`'s DEPR00x family. Every deleted top-level
    verb in T-4690 (`explore`, `quality`, `design`, `ops`, `fmt`, `docs`,
    `whereis`, `verify status`, `fleet status`) calls this exactly once."""
    past_sunset = is_past_sunset(sunset, today=today)
    # T-5285: INFO-level logs route to STDOUT by default (frob.logging.
    # config.toml's `[handlers.stdout] level = "INFO"`, T-2979) -- an
    # _log.info here unconditionally prepended this notice onto every
    # shimmed command's stdout, including every `--json` invocation of a
    # shimmed command, breaking json.loads() on otherwise-valid output
    # (measured directly: tests/system/test_cli_arch.py::test_json_is_valid
    # and ~150 sibling --json tests across the shimmed aliases). The
    # human-readable notice is already correctly delivered via the
    # `renderer` (stderr) call right below; DEBUG keeps this diagnostic
    # line available via FROB_LOG_LEVEL without ever reaching stdout by
    # default.
    _log.debug(
        "cli shim: %s -> %s (ticket=%s sunset=%s past_sunset=%s)",
        old_name,
        new_name,
        ticket,
        sunset,
        past_sunset,
    )
    renderer = Renderer.for_stream(sys.stderr, color_flag=color, no_color_flag=no_color)
    if past_sunset:
        renderer.write.critical(
            f"frob {old_name} was removed (ticket={ticket}, sunset={sunset} has "
            f"passed) -- use `frob {new_name}` instead"
        )
        raise SystemExit(1)
    renderer.write.warn(
        f"frob {old_name} is DEPRECATED (ticket={ticket}, sunset={sunset}) -- use "
        f"`frob {new_name}` instead"
    )

"""Real, checked-in kill-switch/feature-flag mechanism for the risky (exec)
capability `frob.check`'s tool runners hold (T-0200, design/frob.strata's
`checker` node LINT004 finding).

`design/frob.strata`'s `std.lint` LINT004 rule (`src/frob/strata/_lint.py`)
fires on any node holding a risky (`exec`/`net`) `may` capability with no
declared `attr flag=<id>;` naming a REAL kill-switch identifier an operator
can flip live to disable it (T-0155). T-0150/T-0151 established this
repo's discipline of declaring only real, measured facts in `design/
frob.strata` -- never a `flag=<id>` naming a mechanism that does not exist
(the exact gap T-0155 refused to paper over, waiving LINT004 with a
pointer to this ticket instead). This module is that mechanism, for real:
an env-var-gated guard around `subprocess.run` that `frob.check`'s tool
runners (`_python.py`/`_native.py`/`_ts.py`) call through instead of
`subprocess.run` directly, so `FROB_DISABLE_EXEC=1` genuinely stops every
process this component spawns, without a redeploy or a code change.
"""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING

from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

_log = get_logger(__name__)

#: The operator-facing kill-switch identifier for `checker`'s `may "exec"`
#: capability (`design/frob.strata`'s `node checker { ... attr
#: flag="FROB_DISABLE_EXEC"; }`, T-0200). Any of `"1"`/`"true"`/`"yes"`/
#: `"on"` (case-insensitive) disables exec; unset or any other value
#: leaves it enabled -- the same permissive-unless-set posture every other
#: opt-in env var in this repo uses (fail toward the existing default
#: behavior, not toward a surprise outage).
# frob:doc docs/modules/process.md#public-api
EXEC_KILL_SWITCH_ENV = "FROB_DISABLE_EXEC"

#: The operator-facing kill-switch identifier for the `net` capability kind
#: (T-0200 built the mechanism; wiring a real outbound-network call site
#: through it is out of this ticket's scope -- `src/frob/vet/**` is not in
#: T-0200's `scope`, see the Done report for the filed follow-on ticket).
# frob:doc docs/modules/process.md#public-api
NET_KILL_SWITCH_ENV = "FROB_DISABLE_NET"

_TRUTHY = frozenset({"1", "true", "yes", "on"})


# frob:doc docs/modules/process.md#public-api
class ProcessGuardError(ErrorSet):
    """Kill-switch-triggered refusals `guarded_subprocess_run` returns
    instead of ever spawning a process while the switch is flipped."""

    ExecDisabled = "exec capability disabled via kill switch"


def _env_flag_set(name: str) -> bool:
    """True when env var `name` holds one of `_TRUTHY`'s values
    (case-insensitive) -- the shared truthiness rule both kill switches use."""
    return (
        os.environ.get(name, "").strip().lower() in _TRUTHY
    )  # frob:waive SEC110 reason="kill-switch flags (e.g. \
    # FROB_DISABLE_EXEC), not secrets"


# frob:doc docs/modules/process.md#public-api
def exec_enabled() -> bool:
    """Whether the `exec` capability is currently live: `False` exactly
    when `FROB_DISABLE_EXEC` (`EXEC_KILL_SWITCH_ENV`) is set to a truthy
    value in the current process environment, checked fresh on every call
    so an operator's live flip (no redeploy) takes effect immediately."""
    return not _env_flag_set(EXEC_KILL_SWITCH_ENV)


# frob:doc docs/modules/process.md#public-api
def net_enabled() -> bool:
    """Whether the `net` capability is currently live: `False` exactly
    when `FROB_DISABLE_NET` (`NET_KILL_SWITCH_ENV`) is set to a truthy
    value. No caller in this repo's `T-0200` scope exercises this yet
    (see module docstring) -- it exists so a future net call site has a
    real, checked-in switch to wire into on day one instead of inventing
    one under deadline."""
    return not _env_flag_set(NET_KILL_SWITCH_ENV)


# frob:doc docs/modules/process.md#public-api
# frob:invariant INV-019
def guarded_subprocess_run(
    args: Sequence[str], **kwargs: object
) -> Result[subprocess.CompletedProcess[str], ProcessGuardError]:
    """`subprocess.run(args, **kwargs)`, gated by `exec_enabled()`.

    Returns `Err(ProcessGuardError.ExecDisabled)` without ever spawning a
    process when the kill switch is flipped; otherwise `Ok(subprocess.run(
    ...))`. Every `frob.check` tool runner (`_python.py`/`_native.py`/
    `_ts.py`) calls this instead of `subprocess.run` directly so
    `FROB_DISABLE_EXEC=1` is a real, live, no-redeploy kill switch for the
    `checker` component's `may "exec"` capability (T-0200), not an
    aspirational `design/frob.strata` claim."""
    if not exec_enabled():
        _log.warning(
            "process: exec disabled via %s, refusing to spawn %r",
            EXEC_KILL_SWITCH_ENV,
            list(args),
        )
        return Err(ProcessGuardError.ExecDisabled)
    _log.debug("process: spawning %r", list(args))
    proc = subprocess.run(args, **kwargs)  # type: ignore[call-overload]  # ty: ignore[no-matching-overload]
    return Ok(proc)


__all__ = [
    "EXEC_KILL_SWITCH_ENV",
    "NET_KILL_SWITCH_ENV",
    "ProcessGuardError",
    "exec_enabled",
    "net_enabled",
    "guarded_subprocess_run",
]

"""T-2310: the `rapid` profile's automatic verification-debt drain.

COORDINATOR DECISION (recorded here verbatim, not optional -- T-2310's own
ticket body carries the full context): a drain IS required (T-2290 proved
deferral had become PERMANENT under `rapid` -- a watermark 6 days / 530
real commits stale, growing every land, with nothing that ever forced it
to advance), but it must never become a command nobody runs (the standing
"automatic over commands" directive). Five ordered constraints govern this
module:

 1. RAPID'S NEVER-BLOCK CONTRACT IS INVIOLABLE. The drain never blocks,
    slows, or gates a land. `spawn_deferred_drain` fires a DETACHED child
    and returns immediately, exactly like T-1684's sibling post-land
    sweep spawn (`frob.app.ticket_runner._rapid_sweep.
    spawn_deferred_post_land_sweep`) -- the land that triggers it is not
    waiting on anything this module does.
 2. AUTOMATIC, NOT INVOKED. Modeled directly on that same deferred sweep:
    the SAME detached-child machinery (`_detached_sweep_env`, the same
    `subprocess.Popen(..., start_new_session=True)` shape), a second
    independent spawn from the same land call site -- not a second,
    separately-invented mechanism, and not a command an operator has to
    remember exists.
 3. RUNS ONLY WHEN THE FLEET IS IDLE. `run_drain_async` -- the detached
    child's own entrypoint -- declines immediately (one non-blocking
    probe, `frob.tickets._leases._probe_land_once`, the SAME check
    `refuse_if_land_in_progress` uses) if any `frob ticket land` is
    currently in progress anywhere against this checkout. It SKIPS, never
    queues, never retry-loops -- the coordinator's exact wording. The
    check deliberately lives in the CHILD, not in `spawn_deferred_drain`
    itself: the spawning process IS a `frob ticket land` still holding
    `land.lock` at its own call site, so a check performed there would
    always see itself and never spawn anything. By the time the detached
    child's own Python interpreter starts (measurably slower than the
    spawning land's own remaining cleanup), that land's lock has very
    likely already released -- and if it has not, the child correctly
    treats that as a live land and declines, which is exactly the
    conservative behavior wanted.
 4. INCREMENTAL AND RESUMABLE. `run_drain_async` calls `frob.verify.
    _worker.run_coalesced_verification` exactly ONCE per invocation --
    never a loop over the whole backlog. That function's own existing
    contract already IS the bounded-batch primitive this constraint
    needs: one call verifies once at the queue's tip and, only on a
    genuinely green result, durably advances the watermark past every
    queued entry it covers; a red, unmeasurable, or interrupted (killed
    mid-`verify_fn`) call leaves the watermark exactly where it already
    was -- never corrupt, never rolled back, and MADE FURTHER progress if
    the round completed. Repeated per-land spawns (every real rapid land
    fires one) are what accumulate visible progress across a large
    backlog over time, the same way T-1684's sweep already amortizes a
    large, resumable check across many small triggers instead of one
    monolithic one.
 5. THE SOFT WARNING (T-2290's `rapid_soft_warning`) STAYS UNCHANGED. It
    is the backstop for when the drain cannot keep pace with new commits
    -- unaffected by this module.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger

_log = get_logger(__name__)

#: `.frob/verify-drain/<ticket>-<epoch>.log` -- one log file per detached
#: drain attempt, mirroring `frob.app.ticket_runner._rapid_sweep`'s own
#: `_LOG_DIR_REL` precedent for the sibling post-land sweep.
_LOG_DIR_REL = Path(".frob") / "verify-drain"


# frob:doc docs/modules/tickets-verify-sweep.md#automatic-watermark-drain-t-2310
# frob:tests tests/unit/verify/test_drain.py::TestRunDrainAsync.test_declines_while_a_land_is_in_progress  # noqa: E501
# frob:tests tests/unit/verify/test_drain.py::TestSpawnDeferredDrain.test_exec_disabled_refuses_without_spawning  # noqa: E501
class DrainError(ErrorSet):
    """Fallible outcomes of spawning or running the detached drain."""

    SpawnRefused = "the detached drain child could not be spawned"
    LandInProgress = (
        "a land is currently in progress -- the drain declined to start "
        "rather than queue or retry"
    )


# frob:doc docs/modules/tickets-verify-sweep.md#automatic-watermark-drain-t-2310
# frob:ticket T-2310
# frob:tests tests/unit/verify/test_drain.py::TestSpawnDeferredDrain.test_spawns_a_detached_child kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_drain.py::TestSpawnDeferredDrain.test_exec_disabled_refuses_without_spawning kind="unit"  # noqa: E501
def spawn_deferred_drain(root: Path, land_ticket_id: str) -> Result[int, DrainError]:
    """Fire the automatic watermark drain into a DETACHED child and
    return its pid immediately (constraint 1/2, this module's own
    docstring). Never gates on land-in-progress here -- see the
    docstring above for why that check belongs in the spawned child,
    never at this call site. Never raises and never blocks: a refused
    spawn is `Err(SpawnRefused)` and the caller (the land path) logs it
    and proceeds -- draining is best-effort, never load-bearing for the
    land that spawned it, matching `spawn_deferred_post_land_sweep`'s own
    posture exactly."""
    from frob.process import exec_enabled

    if not exec_enabled():
        _log.warning(
            "verify drain: %s exec is disabled -- the automatic watermark "
            "drain was NOT spawned; run `frob verify now` by hand",
            land_ticket_id,
        )
        return Err(DrainError.SpawnRefused)

    log_dir = root / _LOG_DIR_REL
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{land_ticket_id}-{int(time.time())}.log"
    argv = [sys.executable, "-m", "frob", "verify", "drain-async"]

    from frob.app.ticket_runner._rapid_sweep import _detached_sweep_env

    try:
        with log_path.open("w", encoding="utf-8") as handle:
            proc = subprocess.Popen(  # noqa: S603
                argv,
                cwd=root,
                env=_detached_sweep_env(root),
                stdout=handle,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
    except OSError as exc:
        _log.error(
            "verify drain: %s deferred drain spawn failed: %s",
            land_ticket_id,
            exc,
        )
        return Err(DrainError.SpawnRefused)

    _log.info(
        "verify drain: %s automatic watermark drain DEFERRED to detached "
        "pid=%d (log: %s) -- land is not waiting on it",
        land_ticket_id,
        proc.pid,
        log_path,
    )
    return Ok(proc.pid)


# frob:doc docs/modules/tickets-verify-sweep.md#automatic-watermark-drain-t-2310
# frob:ticket T-2310
# frob:tests tests/unit/verify/test_drain.py::TestRunDrainAsync.test_declines_while_a_land_is_in_progress kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_drain.py::TestRunDrainAsync.test_runs_one_bounded_round_and_advances_the_watermark kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_drain.py::TestRunDrainAsync.test_never_blocks_or_loops_over_the_backlog kind="unit"  # noqa: E501
def run_drain_async(root: Path):  # noqa: ANN201 -- Result[WorkerOutcome, DrainError | WorkerError]
    """`frob verify drain-async`'s whole body -- the detached child's own
    entrypoint (constraint 3, this module's own docstring): decline
    immediately, one non-blocking probe, no retry loop, if a land is in
    progress anywhere against `root`; otherwise run exactly ONE bounded
    `run_coalesced_verification` round (constraint 4) and return its
    outcome unchanged."""
    from frob.tickets._leases import _probe_land_once

    probed = _probe_land_once(root, quiet=False)
    if probed.is_err:
        _log.info(
            "verify drain: a land is in progress at %s -- declining to "
            "start (not queuing, not retrying)",
            root,
        )
        return Err(DrainError.LandInProgress)

    from frob.verify._worker import run_coalesced_verification

    outcome = run_coalesced_verification(root)
    if outcome.is_err:
        _log.warning(
            "verify drain: round at %s did not complete: %s",
            root,
            outcome.danger_err,
        )
        return outcome

    result = outcome.danger_ok
    _log.info(
        "verify drain: round complete at %s -- status=%s "
        "advanced_watermark=%s commit=%s",
        root,
        result.status,
        result.advanced_watermark,
        result.commit_sha,
    )
    return outcome


__all__ = [
    "DrainError",
    "run_drain_async",
    "spawn_deferred_drain",
]

"""T-2310: the `rapid` profile's automatic verification-debt drain.

T-2406 UPDATE (read this before touching the module docstring's numbered
constraints below -- constraint 3's original wording is now PARTIALLY
SUPERSEDED, not deleted): a direct measurement of 47 real drain attempts
found 23 (49%) refused and DISCARDED the work, of which 13 named the SAME
ticket as the drain log itself -- the detached child's very first probe
racing its own still-cleaning-up originating land (constraint 3's own
"very likely already released" was measured optimistic in practice).
Two fixes, both scoped narrowly on purpose (an exemption shaped like the
normal case would delete the guard, not correct it -- T-1967's own
lesson, cited directly in this ticket):

  - `run_drain_async` now receives the ONE originating land pid that
    spawned it (`spawn_deferred_drain` captures `os.getpid()` -- itself,
    since it always runs INSIDE that land process -- and passes it
    through `FROB_VERIFY_DRAIN_EXCLUDE_PID`) and excludes exactly that
    pid, and no other, from both the flock-holder probe and the `/proc`
    process scan (`frob.tickets._leases`'s new `exclude_pid` parameter,
    threaded through `_land_flock_probe`/`_scan_for_live_land_process`/
    `_probe_land_once`). A GENUINELY different land's pid still refuses
    exactly as before.
  - A refusal caused by that genuinely different land no longer discards
    the attempt outright: `run_drain_async` now waits it out via
    `refuse_if_land_in_progress`'s own existing bounded poll (same
    config-driven timeout ordinary ledger-writing verbs already wait on)
    before giving up, and a refusal that still survives the wait is
    recorded to `.frob/verify-drain-refused.json` (`record_drain_
    refusal`) so `frob verify status` can report it -- see this module's
    `DrainRefusalRecord`. Constraint 3's "never queues, never retry-
    loops" is retired by this update; the module's other four
    constraints (never-block, automatic-not-invoked, one-bounded-round,
    the unrelated soft-warning) are unchanged.

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
    needs: one call verifies once at the queue's tip and durably advances
    the watermark past every queued entry it covers whenever the result
    is genuinely green OR red-but-OWNED (T-2324: a new finding that got
    filed/disposed to a real ticket is accounted for by the ticket
    system, not by pinning the watermark forever -- see `frob.verify.
    _worker._resolve_verification_outcome`'s own docstring for the full
    reasoning; this was the T-2324 fix, since advance-only-on-green alone
    could never drain a backlog under continuous churn). An unmeasurable
    call, an interrupted (killed mid-`verify_fn`) call, or a red result
    whose findings could NOT even be filed leaves the watermark exactly
    where it already was -- never corrupt, never rolled back. Repeated
    per-land spawns (every real rapid land fires one) are what accumulate
    visible progress across a large backlog over time, the same way
    T-1684's sweep already amortizes a large, resumable check across many
    small triggers instead of one monolithic one.
 5. THE SOFT WARNING (T-2290's `rapid_soft_warning`) STAYS UNCHANGED. It
    is the backstop for when the drain cannot keep pace with new commits
    -- unaffected by this module.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger

_log = get_logger(__name__)

#: `.frob/verify-drain/<ticket>-<epoch>.log` -- one log file per detached
#: drain attempt, mirroring `frob.app.ticket_runner._rapid_sweep`'s own
#: `_LOG_DIR_REL` precedent for the sibling post-land sweep.
_LOG_DIR_REL = Path(".frob") / "verify-drain"

#: T-2406: the env var `spawn_deferred_drain` sets to the SPAWNING land
#: process's own pid, and `frob verify drain-async` (`app.verify_runner.
#: _run_drain_async`) reads back to pass as `run_drain_async`'s
#: `exclude_pid` -- the one channel by which a detached, argv-fixed
#: child (`[sys.executable, "-m", "frob", "verify", "drain-async"]`,
#: unchanged so existing log/argv shape stays stable) learns which
#: single pid it must not treat as a competing land.
_EXCLUDE_PID_ENV_VAR = "FROB_VERIFY_DRAIN_EXCLUDE_PID"

#: T-2406: the env var `spawn_deferred_drain` sets to the SPAWNING land's
#: own ticket id -- carried through purely so a refusal recorded by
#: `record_drain_refusal` names the drain's OWN originating ticket in
#: `DrainRefusalRecord.last_refused_ticket_id`, for a human reading
#: `frob verify status` to know which land's drain most recently
#: refused, not just that one did.
_LAND_TICKET_ID_ENV_VAR = "FROB_VERIFY_DRAIN_LAND_TICKET_ID"

#: T-2406: `.frob/verify-drain-refused.json` -- one small durable record
#: of drain refusals since the watermark last advanced, so a refusal that
#: survives `run_drain_async`'s own bounded wait is OBSERVABLE (`frob
#: verify status`) instead of vanishing the way a bare log line does.
#: Reuses `frob.tickets._land_queue.file_lock`/`write_json_records` --
#: the ONE small-JSON-store lock/write implementation this package
#: standardizes on (T-1687's own rule), not a second hand-rolled copy.
_REFUSED_REL = Path(".frob") / "verify-drain-refused.json"
_REFUSED_LOCK_REL = Path(".frob") / "verify-drain-refused.lock"


# frob:doc \
# docs/modules/tickets-verify-sweep.md#automatic-watermark-drain-rapid-only-t-2310
# frob:tests tests/unit/verify/test_drain.py::TestRunDrainAsync.test_declines_while_a_land_is_in_progress  # noqa: E501
# frob:tests tests/unit/verify/test_drain.py::TestSpawnDeferredDrain.test_exec_disabled_refuses_without_spawning  # noqa: E501
class DrainError(ErrorSet):
    """Fallible outcomes of spawning or running the detached drain."""

    SpawnRefused = "the detached drain child could not be spawned"
    LandInProgress = (
        "a land is currently in progress -- the drain waited out its "
        "bounded budget and is now recorded as refused (see `frob verify "
        "status`), not silently discarded"
    )


# frob:doc \
# docs/modules/tickets-verify-sweep.md#automatic-watermark-drain-rapid-only-t-2310
# frob:ticket T-2406
# frob:tests tests/unit/verify/test_drain.py::TestRunDrainAsync.test_a_genuinely_different_land_is_recorded_not_discarded kind="unit"  # noqa: E501
class DrainRefusalRecord(BaseModel):
    """`.frob/verify-drain-refused.json`'s single current record (T-2406):
    how many drain attempts have refused (a genuinely different land was
    still running after the full wait budget) since the watermark last
    advanced. Reset to zero the next time a drain actually RUNS (whether
    that round is green, red, or unmeasurable) -- see `record_drain_
    refusal`/`clear_drain_refusal`. `frob verify status` surfaces this
    directly so the "genuinely blocked" condition this ticket's own body
    measured invisible for 79 minutes can never be silently invisible
    again."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    refused_since_watermark: int
    last_refused_at: str
    last_refused_ticket_id: str


def _refused_path(root: Path) -> Path:
    """The `.frob/verify-drain-refused.json` path for a checkout rooted
    at `root`."""
    return root / _REFUSED_REL


def _refused_lock_path(root: Path) -> Path:
    """The advisory lock file guarding every `.frob/verify-drain-refused.
    json` mutation against `root`."""
    return root / _REFUSED_LOCK_REL


# frob:doc \
# docs/modules/tickets-verify-sweep.md#automatic-watermark-drain-rapid-only-t-2310
# frob:ticket T-2406
# frob:tests tests/unit/verify/test_drain.py::TestRunDrainAsync.test_a_genuinely_different_land_is_recorded_not_discarded kind="unit"  # noqa: E501
def load_drain_refusal(root: Path) -> DrainRefusalRecord | None:
    """The current `DrainRefusalRecord` for `root`, or `None` on a
    missing/corrupt file -- `frob verify status`'s own "nothing to
    report" case, matching this package's standing "cannot read is never
    a claim of zero" posture by simply reporting nothing rather than a
    fabricated zero on a corrupt read (a corrupt file here is not the
    dangerous direction that posture guards against -- it only ever
    understates a refusal COUNT, never the watermark or queue depth
    itself -- so a WARNING-level log, not an `Err`, is proportionate)."""
    path = _refused_path(root)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _log.warning("verify drain: %s failed to parse: %s", path, exc)
        return None
    # `write_json_records` (this store's own writer, see `record_drain_
    # refusal`/`clear_drain_refusal`) always writes a JSON ARRAY, even
    # for this store's single-record contract -- matching every other
    # small-JSON-store in this package that reuses the same writer.
    if not isinstance(raw, list) or not raw or not isinstance(raw[0], dict):
        return None
    try:
        return DrainRefusalRecord.model_validate(raw[0])
    except Exception as exc:  # noqa: BLE001 -- pydantic ValidationError, any shape
        _log.warning("verify drain: %s failed to validate: %s", path, exc)
        return None


# frob:doc \
# docs/modules/tickets-verify-sweep.md#automatic-watermark-drain-rapid-only-t-2310
# frob:ticket T-2406
# frob:tests tests/unit/verify/test_drain.py::TestRunDrainAsync.test_a_genuinely_different_land_is_recorded_not_discarded kind="unit"  # noqa: E501
def record_drain_refusal(root: Path, *, ticket_id: str) -> None:
    """Increment `.frob/verify-drain-refused.json`'s counter (T-2406):
    called once, by `run_drain_async`, exactly when a refusal survives
    the full wait budget -- never on the excluded originating-land case,
    which is not a refusal at all. Best-effort: a write failure here logs
    at WARNING and is otherwise swallowed -- losing VISIBILITY of a
    refusal must never itself become a reason the drain, or the land that
    spawned it, fails."""
    from frob.tickets._land_queue import file_lock, write_json_records

    lock_path = _refused_lock_path(root)
    try:
        with file_lock(lock_path, label="verify-drain-refused"):
            existing = load_drain_refusal(root)
            count = (existing.refused_since_watermark if existing else 0) + 1
            record = DrainRefusalRecord(
                refused_since_watermark=count,
                last_refused_at=datetime.now(UTC).isoformat(),
                last_refused_ticket_id=ticket_id,
            )
            write_json_records(_refused_path(root), (record,))
    except OSError as exc:
        _log.warning(
            "verify drain: %s failed to record drain refusal: %s", root, exc
        )
        return
    _log.info(
        "verify drain: %s refusal recorded (refused_since_watermark=%d) -- "
        "see `frob verify status`",
        root,
        count,
    )


# frob:doc \
# docs/modules/tickets-verify-sweep.md#automatic-watermark-drain-rapid-only-t-2310
# frob:ticket T-2406
# frob:tests tests/unit/verify/test_drain.py::TestDrainAdvancesWatermarkEndToEnd.test_a_round_that_runs_clears_a_prior_refusal_record kind="unit"  # noqa: E501
def clear_drain_refusal(root: Path) -> None:
    """Reset `.frob/verify-drain-refused.json`'s counter to zero (T-2406):
    called once a drain actually RUNS (constraint 4 -- the state a
    non-zero counter is warning about no longer holds once a round has
    executed, regardless of that round's own outcome). A no-op, not an
    error, when there is nothing to clear. Best-effort, same posture as
    `record_drain_refusal`."""
    if not _refused_path(root).exists():
        return
    from frob.tickets._land_queue import file_lock, write_json_records

    try:
        with file_lock(_refused_lock_path(root), label="verify-drain-refused"):
            existing = load_drain_refusal(root)
            if existing is None or existing.refused_since_watermark == 0:
                return
            record = DrainRefusalRecord(
                refused_since_watermark=0,
                last_refused_at=existing.last_refused_at,
                last_refused_ticket_id=existing.last_refused_ticket_id,
            )
            write_json_records(_refused_path(root), (record,))
    except OSError as exc:
        _log.warning("verify drain: %s failed to clear drain refusal: %s", root, exc)


# frob:doc \
# docs/modules/tickets-verify-sweep.md#automatic-watermark-drain-rapid-only-t-2310
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
    posture exactly.

    T-2406: sets `FROB_VERIFY_DRAIN_EXCLUDE_PID` to `os.getpid()` -- THIS
    process's own pid, since `spawn_deferred_drain` only ever runs
    INSIDE the `frob ticket land` process it is spawned from (the land
    path is this function's one caller). The detached child reads it
    back and excludes exactly that one pid from its own land-in-progress
    scan, so it does not self-refuse against the very land that spawned
    it -- see `run_drain_async` and `frob.tickets._leases._refuse_for_
    held_land_lock`'s docstrings for the full mechanism."""
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

    env = _detached_sweep_env(root)
    env[_EXCLUDE_PID_ENV_VAR] = str(os.getpid())
    env[_LAND_TICKET_ID_ENV_VAR] = land_ticket_id

    try:
        with log_path.open("w", encoding="utf-8") as handle:
            proc = subprocess.Popen(  # noqa: S603
                argv,
                cwd=root,
                env=env,
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


# frob:doc \
# docs/modules/tickets-verify-sweep.md#automatic-watermark-drain-rapid-only-t-2310
# frob:ticket T-2310
# frob:tests tests/unit/verify/test_drain.py::TestRunDrainAsync.test_declines_while_a_land_is_in_progress kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_drain.py::TestDrainAdvancesWatermarkEndToEnd.test_green_round_advances_watermark_a_subsequent_round_sees kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_drain.py::TestRunDrainAsync.test_never_blocks_or_loops_over_the_backlog kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_drain.py::TestRunDrainAsync.test_excludes_its_own_originating_land_pid kind="unit"  # noqa: E501
# frob:tests tests/unit/verify/test_drain.py::TestRunDrainAsync.test_a_genuinely_different_land_is_recorded_not_discarded kind="unit"  # noqa: E501
def run_drain_async(
    root: Path,
    *,
    exclude_pid: int | None = None,
    land_ticket_id: str | None = None,
    wait_timeout_s: float | None = None,
):  # noqa: ANN201 -- Result[WorkerOutcome, DrainError | WorkerError]
    """`frob verify drain-async`'s whole body -- the detached child's own
    entrypoint: run exactly ONE bounded `run_coalesced_verification`
    round (constraint 4) and return its outcome unchanged, UNLESS a
    land is genuinely in progress.

    T-2406 (supersedes constraint 3's original "decline immediately, one
    non-blocking probe, no retry loop" wording -- see this module's own
    top-of-file docstring for the measurement that drove this change):
    `exclude_pid`, when given (`app.verify_runner._run_drain_async` reads
    it from `FROB_VERIFY_DRAIN_EXCLUDE_PID`, which `spawn_deferred_drain`
    always sets to its own originating land's pid), is excluded from the
    land-in-progress probe -- so THIS specific land, the one that spawned
    this very drain, is never mistaken for a competing one. A refusal
    caused by any OTHER land now waits it out via `refuse_if_land_in_
    progress`'s existing bounded poll (`wait_timeout_s`, `None` deferring
    to that function's own config-driven default -- the SAME budget an
    ordinary ledger-writing verb already waits on, not a second
    independently-tuned constant) rather than discarding on the first
    probe; a refusal that survives the full wait is recorded (`record_
    drain_refusal`) so it is observable via `frob verify status`, never
    silently lost. This wait runs entirely inside the DETACHED child --
    constraint 1 (never blocks the spawning land) is unaffected."""
    from frob.tickets._leases import LeaseError, refuse_if_land_in_progress

    probed = refuse_if_land_in_progress(
        root, exclude_pid=exclude_pid, wait_timeout_s=wait_timeout_s
    )
    if probed.is_err:
        assert probed.danger_err is LeaseError.LandInProgress  # narrows for typing
        _log.info(
            "verify drain: a genuinely different land is still in "
            "progress at %s after the full wait budget -- recording "
            "the refusal (see `frob verify status`) rather than "
            "discarding it",
            root,
        )
        record_drain_refusal(root, ticket_id=land_ticket_id or "(unknown)")
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

    clear_drain_refusal(root)
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
    "DrainRefusalRecord",
    "clear_drain_refusal",
    "load_drain_refusal",
    "record_drain_refusal",
    "run_drain_async",
    "spawn_deferred_drain",
]

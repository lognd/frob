"""T-1688: the coalescing verify worker -- the trailing-edge-debounce half
of the T-1686 epic, and where the wall-clock saving actually comes from.

THE CONTRACT THIS MODULE MUST NOT VIOLATE: the worker COALESCES, it does
not ITERATE. `run_coalesced_verification` reads the queue exactly once,
looks at only its TIP entry, and calls the verification function exactly
ONCE per invocation -- never once per queued entry. Five lands sitting in
the queue when this function runs produce ONE verification call, not
five, because tree state at the tip is the only input verification ever
needs: a green result at the tip is a green result for every commit that
composes it (T-1686's own framing). This is enforced structurally by the
function's own control flow (`entries[-1]`, a single `verify(...)` call,
no loop over `entries` anywhere in this module) rather than by a
comment asking a future editor to remember not to loop -- see
`tests/unit/verify/test_worker.py::TestRunCoalescedVerification::
test_five_queued_entries_call_verify_exactly_once`, which asserts the
invocation COUNT, not a timing measurement (a timing-based test proves
nothing about whether coalescing happened, only about how fast it was).

THE OTHER CONTRACT: `None` must never advance the watermark.
`verify_fn` returning `None` means "we could not tell" (T-1703's own
incident: a budget-truncated or otherwise partial check must never be
misread as a clean one) -- structurally, not just by convention, this
module's `run_coalesced_verification` returns `Err(WorkerError.
Unmeasurable)` on that branch BEFORE any code path that could reach
`frob.verify.advance_watermark` is even textually possible to execute:
the only call to `advance_watermark` in this file sits in the FINAL
branch of an early-return chain that a `None` result cannot fall through
to. There is no flag to forget to check.

TOUCHED SYMBOLS STAY SYMBOLIC. This module never reduces
`VerifyQueueEntry.touched_symbols` to a file-path list for its own
convenience -- it does not even read that field today (attribution is
explicitly out of this leaf's scope, T-1686's own framing: "verification
at the tip... does NOT give you per-commit attribution -- that is
deliberately deferred to the attribution leaf"). Reducing to paths here
"just to make debugging easier" would throw away exactly the information
T-1690's attribution leaf depends on, silently, long before that leaf is
ever written.

WHAT THIS LEAF REUSES, NOT REINVENTS: T-1684's `_rapid_sweep` module
already has the whole "run one unscoped check, diff against a rolling
baseline, file a regression ticket on new findings, always rebaseline"
sequence (`_read_baseline`/`_write_baseline`/`_file_regression_ticket`,
originally built for a per-land spawn). This module reuses those three
functions directly rather than re-deriving the same rolling-baseline
comparison a second time -- the only genuinely NEW decision this leaf
adds on top is "and if it's green, advance the watermark and compact the
queue", which `_rapid_sweep` has no reason to know about.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.verify._watermark import (
    VerifyQueueEntry,
    advance_watermark,
    compact_queue,
    load_watermark,
    queue_status,
)

_log = get_logger(__name__)

# T-1694 incident this closes: a dead worker (killed between the queue
# read and the watermark write, or anywhere in between) must never leave
# main looking verified past a batch that was never actually confirmed
# green. This marker names the batch (its tip commit) and is written
# BEFORE `verify_fn` is even called -- the moment this run starts making a
# claim about `tip.commit_sha` -- and cleared unconditionally once this
# run reaches ANY stable outcome (green, red, baseline-established,
# unmeasurable, or a raised exception), via a `finally` block mirroring
# `_clear_land_repair_marker`'s/`_clear_post_land_verify_marker`'s own
# unconditional-cleanup shape (T-0907/T-1523 precedent). A marker still
# present at the START of the next `run_coalesced_verification` call means
# a prior run died somewhere inside that window -- `_reconcile_stale_
# in_flight_marker` treats that batch as UNVERIFIED unless the watermark
# it finds on disk already independently confirms the same commit (the
# rare case where the crash landed after `advance_watermark`/
# `compact_queue` both actually completed and only the marker clear
# itself was lost) -- it never assumes green from the marker's mere
# presence.
# frob:ticket T-1694
_IN_FLIGHT_MARKER_REL = Path(".frob") / "verify-in-flight.json"


# frob:ticket T-1694
def _in_flight_marker_path(root: Path) -> Path:
    """The single (root is one `CoalescingWorker` per repo, guarded by the
    daemon's own `acquire_singleton_lock` -- T-1694's own scope note: reuse
    that exclusion, never add a second one) in-flight verification marker
    path for `root`."""
    return root / _IN_FLIGHT_MARKER_REL


# frob:ticket T-1694
def _write_in_flight_marker(root: Path, commit_sha: str, run_id: str) -> None:
    """Record that a coalesced verification pass against `tip.commit_sha`
    is now in flight (T-1694), BEFORE `verify_fn` is called. Written
    write-temp-then-`os.replace` so a crash mid-write can never leave a
    torn, half-written marker for `_reconcile_stale_in_flight_marker` to
    misread -- `os.replace` is atomic on every platform this repo targets
    (POSIX rename semantics). Best-effort like `_write_land_repair_marker`/
    `_write_post_land_verify_marker`: a write failure is logged but never
    stops verification, since a MISSING marker just means this run's own
    crash window loses its recovery aid, not that anything is mutated
    incorrectly -- the watermark is still never advanced without a real
    green result either way."""
    path = _in_flight_marker_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(f".{run_id}.tmp")
        tmp_path.write_text(
            json.dumps({"commit_sha": commit_sha, "run_id": run_id}) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp_path, path)
    except OSError as exc:
        _log.warning(
            "verify worker: could not write in-flight marker for %s (%s) -- "
            "proceeding without the T-1694 crash-recovery aid for this run",
            commit_sha[:12],
            exc,
        )


# frob:ticket T-1694
def _clear_in_flight_marker(root: Path) -> None:
    """Remove the in-flight verification marker, if any (T-1694) -- called
    unconditionally (a `finally` block) once `run_coalesced_verification`
    has reached ANY stable outcome for this run, mirroring `_clear_land_
    repair_marker`'s/`_clear_post_land_verify_marker`'s own shape."""
    path = _in_flight_marker_path(root)
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        _log.warning("verify worker: could not clear in-flight marker: %s", exc)


# frob:ticket T-1694
# frob:tests tests/unit/verify/test_worker.py::TestReconcileStaleInFlightMarker.test_no_marker_is_a_silent_noop  # noqa: E501
# frob:tests tests/unit/verify/test_worker.py::TestReconcileStaleInFlightMarker.test_stale_marker_with_no_matching_watermark_is_reported_unverified  # noqa: E501
# frob:tests tests/unit/verify/test_worker.py::TestReconcileStaleInFlightMarker.test_stale_marker_matching_current_watermark_is_reported_recovered  # noqa: E501
# frob:tests tests/unit/verify/test_worker.py::TestReconcileStaleInFlightMarker.test_unreadable_marker_is_reported_unverified_and_cleared  # noqa: E501
def _reconcile_stale_in_flight_marker(root: Path) -> None:
    """Reconcile a leftover T-1694 in-flight marker under `root`, if any --
    called at the very START of `run_coalesced_verification`, before this
    run reads the queue or writes its own marker. Read-only with respect
    to the queue and watermark (never mutates either): the marker's mere
    PRESENCE never implies a green result. If the marker's `commit_sha`
    already equals the CURRENT watermark's `commit_sha`, the prior run's
    `advance_watermark`+`compact_queue` sequence evidently completed and
    only the marker's own clear was lost -- logged as recovered. In every
    other case (no watermark, a different commit, or an unreadable/corrupt
    marker file) the prior run's batch is UNVERIFIED: nothing here needs
    to explicitly "re-queue" it, since `compact_queue` only ever drops
    entries at-or-before a commit the watermark actually reached -- if
    that never happened, the queue still holds them, and the next
    `run_coalesced_verification` call verifies them again exactly as if
    no prior attempt had ever started. Either way the marker is cleared at
    the end so a stale reconciliation is not repeated forever."""
    path = _in_flight_marker_path(root)
    if not path.exists():
        return

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        marker_commit = str(raw["commit_sha"])
    except (OSError, ValueError, KeyError) as exc:
        _log.error(
            "verify worker: found an unreadable T-1694 in-flight marker at "
            "%s (%s) -- a prior verification run died and left an "
            "unparsable marker; treating its batch as UNVERIFIED (it will "
            "be re-verified on the next wake if still queued)",
            path,
            exc,
        )
        _clear_in_flight_marker(root)
        return

    watermark = load_watermark(root)
    current_commit = (
        watermark.danger_ok.commit_sha
        if watermark.is_ok and watermark.danger_ok is not None
        else None
    )
    if current_commit == marker_commit:
        _log.warning(
            "verify worker: recovered a T-1694 in-flight marker for %s -- "
            "the watermark already names this exact commit, so the prior "
            "run's advance completed and only its marker clear was lost; "
            "no re-verification needed",
            marker_commit[:12],
        )
    else:
        _log.error(
            "verify worker: recovered a T-1694 in-flight marker for %s "
            "with no matching current watermark (watermark=%s) -- a prior "
            "verification run died mid-flight; this batch is UNVERIFIED, "
            "never assumed green, and will be re-verified on the next "
            "wake if it is still queued",
            marker_commit[:12],
            current_commit[:12] if current_commit else None,
        )
    _clear_in_flight_marker(root)


# frob:doc docs/modules/tickets.md#coalescing-verify-worker-t-1688
#: Trailing-edge debounce window (T-1686: "a burst of five lands in ninety
#: seconds produces one verification, not five") -- each `notify()` call
#: pushes the deadline forward by this many seconds from the time of that
#: notify, so a steady trickle of lands keeps deferring the run; only a
#: quiet period this long actually triggers one.
DEFAULT_DEBOUNCE_WINDOW_S = 90.0

# frob:doc docs/modules/tickets.md#coalescing-verify-worker-t-1688
#: Periodic floor (T-1686: "so a stalled watcher cannot leave the window
#: open indefinitely") -- if work has been pending this long with no
#: verification run at all (e.g. the FS-watch signal that would normally
#: quiet down and trigger the debounce never stops arriving, or never
#: arrives at all and only the periodic tick itself is driving `notify`),
#: force a run regardless of how recently the last notify was.
DEFAULT_PERIODIC_FLOOR_S = 300.0


# frob:doc docs/modules/tickets.md#coalescing-verify-worker-t-1688
class WorkerError(ErrorSet):
    """Fallible outcomes of `run_coalesced_verification`."""

    QueueUnreadable = "the verify queue could not be read"
    Unmeasurable = (
        "the verification pass produced no parsable result -- watermark left untouched"
    )
    WatermarkWriteFailed = "advancing the watermark failed after a green verification"


# frob:doc docs/modules/tickets.md#coalescing-verify-worker-t-1688
class WorkerOutcome(BaseModel):
    """One `run_coalesced_verification` call's result, for logging and
    tests -- never persisted (the durable facts it summarizes already
    live in `.frob/verify-watermark.json`/`rapid-debt.jsonl`/the filed
    ticket, not in this transient return value)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: "empty" (nothing queued, verify_fn never called), "baseline-
    #: established" (first-ever run, no prior baseline to compare against
    #: -- NOT a proven-green claim, so the watermark is deliberately left
    #: untouched here too), "red" (new findings vs the rolling baseline,
    #: filed as a ticket, watermark untouched), or "green" (no new
    #: findings, watermark advanced and the queue compacted).
    status: str
    commit_sha: str | None = None
    advanced_watermark: bool = False
    filed_ticket: str | None = None
    findings_count: int = 0


#: `verify_fn(root, commit_sha)` -> the fresh absolute `(rule_id, file)`
#: error-identity set, or `None` if unmeasurable -- the exact contract
#: `frob.app.ticket_runner._land_cmd._unscoped_error_findings` already
#: implements (T-1703's own fix lives there: a budget-truncated run is
#: `None`, never a partial set). Injectable so tests can count calls
#: without spawning a real `frob check` subprocess.
VerifyFn = Callable[[Path, str], "frozenset[tuple[str, str]] | None"]


def _default_verify_fn(
    root: Path, commit_sha: str
) -> frozenset[tuple[str, str]] | None:
    """The production `VerifyFn`: one unscoped, budget-bounded `frob check`
    at `root`'s CURRENT tree state (deferred import -- `frob.verify` must
    not import `frob.app`/`frob.gates` at module scope, the same cycle-
    avoidance rule `frob.testing._coverage_refresh` already documents for
    an identical deferred-import shape). `commit_sha` is accepted for
    logging/signature symmetry with the injectable test double; the real
    check always measures whatever `root` currently has checked out, which
    the caller has already arranged to be `commit_sha` by construction (the
    daemon only calls this against its own live checkout, never a detached
    ref)."""
    from frob.app.ticket_runner._land_cmd import _unscoped_error_findings

    return _unscoped_error_findings(root, commit_sha)


def _findings_digest(findings: frozenset[tuple[str, str]]) -> str:
    """A short, stable digest of `findings` for `Watermark.baseline_digest`
    -- identifies WHAT was compared against without persisting the full
    set a second time (it already lives in `.frob/rapid-sweep-baseline.
    json`); two verification runs against the identical findings set
    always produce the identical digest, so a reader can tell "the same
    baseline, re-confirmed" from "a genuinely different green state"."""
    payload = "\n".join(f"{rule}\t{file}" for rule, file in sorted(findings))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


# frob:doc docs/modules/tickets.md#coalescing-verify-worker-t-1688
# frob:ticket T-1694
# frob:tests tests/unit/verify/test_worker.py::TestRunCoalescedVerification.test_empty_queue_is_a_noop  # noqa: E501
# frob:tests tests/unit/verify/test_worker.py::TestRunCoalescedVerification.test_five_queued_entries_call_verify_exactly_once  # noqa: E501
# frob:tests tests/unit/verify/test_worker.py::TestRunCoalescedVerification.test_unmeasurable_never_advances_watermark  # noqa: E501
# frob:tests tests/unit/verify/test_worker.py::TestRunCoalescedVerification.test_first_run_establishes_baseline_without_advancing  # noqa: E501
# frob:tests tests/unit/verify/test_worker.py::TestRunCoalescedVerification.test_new_findings_file_a_ticket_and_do_not_advance  # noqa: E501
# frob:tests tests/unit/verify/test_worker.py::TestRunCoalescedVerification.test_clean_run_advances_watermark_and_compacts_queue  # noqa: E501
# frob:tests tests/unit/verify/test_worker.py::TestRunCoalescedVerification.test_queue_unreadable_is_an_error  # noqa: E501
def run_coalesced_verification(
    root: Path,
    *,
    verify_fn: VerifyFn | None = None,
) -> Result[WorkerOutcome, WorkerError]:
    """The worker's whole job, one wake: read the queue, look at only its
    TIP entry, verify ONCE, and on a genuinely green result (a real prior
    baseline existed AND nothing new showed up against it) advance the
    watermark past every entry the queue currently holds and compact them
    away. Never loops over `entries` -- see this module's own docstring
    for why that is the one invariant this function may never break.
    Delegates the post-verify baseline-compare/file/advance decision to
    `_resolve_verification_outcome` (ARCH001 split -- this function's own
    job stops at "read the queue and call verify exactly once").

    T-1694 crash safety: reconciles any leftover in-flight marker from a
    prior, dead run FIRST, then writes a fresh marker naming this run's own
    tip commit BEFORE `verify_fn` runs, and clears it unconditionally
    (`finally`) once this call reaches any stable outcome -- see this
    module's own docstring above `_write_in_flight_marker` for the full
    contract. A dead worker can therefore never leave the watermark
    advanced past a batch whose verification did not actually complete."""
    _reconcile_stale_in_flight_marker(root)

    loaded = queue_status(root)
    if loaded.is_err:
        _log.error(
            "verify worker: queue unreadable (%s) -- skipping this wake",
            loaded.danger_err,
        )
        return Err(WorkerError.QueueUnreadable)
    entries: tuple[VerifyQueueEntry, ...] = loaded.danger_ok
    if not entries:
        _log.debug("verify worker: queue empty, nothing to verify")
        return Ok(WorkerOutcome(status="empty"))

    tip = entries[-1]
    _log.info(
        "verify worker: waking with %d queued entr(y/ies), verifying ONCE at "
        "tip commit %s (ticket=%s)",
        len(entries),
        tip.commit_sha[:12],
        tip.ticket_id,
    )
    run_id = uuid.uuid4().hex
    _write_in_flight_marker(root, tip.commit_sha, run_id)
    try:
        fresh = (
            verify_fn(root, tip.commit_sha)
            if verify_fn is not None
            else _default_verify_fn(root, tip.commit_sha)
        )
        if fresh is None:
            # T-1703/T-1688: unmeasurable is never zero, never green, and
            # this early return is the ONLY thing standing between this
            # branch and the rest of the function -- advance_watermark is
            # not even reachable from here.
            _log.error(
                "verify worker: unmeasurable verification at %s -- "
                "watermark and queue left untouched, will retry on the "
                "next wake",
                tip.commit_sha[:12],
            )
            return Err(WorkerError.Unmeasurable)

        return _resolve_verification_outcome(root, tip, fresh)
    finally:
        # T-1694: unconditional -- a raised exception, an early return, or
        # a normal green/red/baseline-established outcome all reach here.
        _clear_in_flight_marker(root)


def _resolve_verification_outcome(
    root: Path, tip: VerifyQueueEntry, fresh: frozenset[tuple[str, str]]
) -> Result[WorkerOutcome, WorkerError]:
    """The baseline-compare/file/advance decision for one MEASURED
    (never-`None`) verification result `fresh` at `tip` -- split out of
    `run_coalesced_verification` (ARCH001) so that function stays focused
    on "read the queue, verify once". Only ever called after a real
    result exists, so this function structurally never sees the `None`
    case -- it has no branch that could even represent it."""
    from frob.app.ticket_runner._rapid_sweep import (
        _file_regression_ticket,
        _read_baseline,
        _write_baseline,
    )

    baseline = _read_baseline(root)
    _write_baseline(root, fresh, tip.commit_sha)

    if baseline is None:
        # A real, measured result -- but with nothing to compare it
        # against, "no new findings" cannot be asserted, only "we have
        # never checked before now". NOT a green claim; the watermark
        # stays untouched, same posture _rapid_sweep._read_baseline's own
        # docstring already establishes for this exact case.
        _log.warning(
            "verify worker: no prior rolling baseline -- recorded %d "
            "error(s) at %s as the baseline; watermark NOT advanced (this "
            "run cannot claim 'no new findings' with nothing to compare "
            "against)",
            len(fresh),
            tip.commit_sha[:12],
        )
        return Ok(
            WorkerOutcome(
                status="baseline-established",
                commit_sha=tip.commit_sha,
                findings_count=len(fresh),
            )
        )

    new_findings = fresh - baseline
    if new_findings:
        filed = _file_regression_ticket(
            root, tip.ticket_id, tip.commit_sha, new_findings
        )
        _log.error(
            "verify worker: %d new finding(s) at %s -- filed as %s; "
            "watermark NOT advanced (a red batch quarantines, it does not "
            "revert -- T-1686's own recorded decision)",
            len(new_findings),
            tip.commit_sha[:12],
            filed or "UNFILED",
        )
        return Ok(
            WorkerOutcome(
                status="red",
                commit_sha=tip.commit_sha,
                filed_ticket=filed,
                findings_count=len(new_findings),
            )
        )

    return _advance_on_green(root, tip, fresh)


def _advance_on_green(
    root: Path, tip: VerifyQueueEntry, fresh: frozenset[tuple[str, str]]
) -> Result[WorkerOutcome, WorkerError]:
    """The ONLY call site of `advance_watermark` in this module (ARCH001
    split of `_resolve_verification_outcome`) -- reached exclusively from
    the genuinely-green branch (a real prior baseline existed AND nothing
    new showed up against it)."""
    advanced = advance_watermark(
        root,
        commit_sha=tip.commit_sha,
        run_id=uuid.uuid4().hex,
        baseline_digest=_findings_digest(fresh),
    )
    if advanced.is_err:
        _log.error(
            "verify worker: green verification at %s but the watermark "
            "write failed (%s) -- queue left uncompacted, will retry",
            tip.commit_sha[:12],
            advanced.danger_err,
        )
        return Err(WorkerError.WatermarkWriteFailed)

    compacted = compact_queue(root)
    if compacted.is_err:
        _log.warning(
            "verify worker: watermark advanced to %s but compact_queue "
            "failed (%s) -- the queue still has entries this watermark "
            "already covers; harmless, the next wake compacts them too",
            tip.commit_sha[:12],
            compacted.danger_err,
        )
    else:
        _log.info(
            "verify worker: GREEN at %s (%d error(s), none new) -- watermark "
            "advanced, %d queue entr(y/ies) compacted",
            tip.commit_sha[:12],
            len(fresh),
            compacted.danger_ok,
        )
    return Ok(
        WorkerOutcome(
            status="green",
            commit_sha=tip.commit_sha,
            advanced_watermark=True,
            findings_count=len(fresh),
        )
    )


# frob:doc docs/modules/tickets.md#coalescing-verify-worker-t-1688
# frob:tests tests/unit/verify/test_worker.py::TestCoalescingWorker.test_notify_then_tick_before_deadline_does_not_run  # noqa: E501
# frob:tests tests/unit/verify/test_worker.py::TestCoalescingWorker.test_notify_then_tick_after_deadline_runs_once  # noqa: E501
# frob:tests tests/unit/verify/test_worker.py::TestCoalescingWorker.test_repeated_notify_pushes_the_deadline_out  # noqa: E501
# frob:tests tests/unit/verify/test_worker.py::TestCoalescingWorker.test_periodic_floor_forces_a_run_under_continuous_notify  # noqa: E501
# frob:tests tests/unit/verify/test_worker.py::TestCoalescingWorker.test_tick_with_nothing_pending_is_a_noop  # noqa: E501
class CoalescingWorker:
    """Trailing-edge debounce state machine over `run_coalesced_verification`
    (T-1688): `notify()` records that a wake condition fired (a queue
    append, the FS-watch `on_change` signal, or the daemon's own periodic
    tick calling `notify()` unconditionally each cycle as the "periodic
    floor" source) without running anything; `tick()` -- called from the
    daemon's existing poll loop, no separate thread of its own needed --
    decides whether enough quiet time has passed (or the periodic floor
    has been hit) to actually run one coalesced verification pass.

    A real wall-clock function (`time.monotonic`, the default) drives
    production use; tests inject `now_fn` for deterministic, sleep-free
    assertions about the debounce/floor DECISION logic -- never a real
    sleep-and-observe timing test (T-1688's own acceptance note: "a
    timing-based test proves nothing here")."""

    def __init__(
        self,
        root: Path,
        *,
        debounce_window_s: float = DEFAULT_DEBOUNCE_WINDOW_S,
        periodic_floor_s: float = DEFAULT_PERIODIC_FLOOR_S,
        verify_fn: VerifyFn | None = None,
        now_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        """Build a worker for `root`. Does not start any thread or run any
        verification itself -- `notify()`/`tick()` are called by the
        daemon's own existing poll loop (`frob.serve._daemon`)."""
        self._root = root
        self._debounce_window_s = debounce_window_s
        self._periodic_floor_s = periodic_floor_s
        self._verify_fn = verify_fn
        self._now_fn = now_fn
        self._lock = threading.Lock()
        self._pending_since: float | None = None
        self._last_notify_at: float | None = None
        self._last_run_at: float | None = None

    # frob:doc docs/modules/tickets.md#coalescing-verify-worker-t-1688
    def notify(self) -> None:
        """Record that a wake condition fired. Cheap and safe to call from
        any thread (an FS-watch callback, the daemon's own poll loop) --
        pushes the trailing-edge debounce deadline out by
        `debounce_window_s` from now, without running anything."""
        now = self._now_fn()
        with self._lock:
            if self._pending_since is None:
                self._pending_since = now
            self._last_notify_at = now
        _log.debug("verify worker: notify() at %s for %s", now, self._root)

    # frob:doc docs/modules/tickets.md#coalescing-verify-worker-t-1688
    def tick(self) -> Result[WorkerOutcome, WorkerError] | None:
        """Called on every daemon poll cycle. Returns `None` (nothing ran)
        unless there is pending work AND either the debounce window has
        gone quiet since the last `notify()`, or the periodic floor has
        elapsed since the last real run while work was still pending --
        in which case it runs exactly one
        `run_coalesced_verification` pass and clears the pending state."""
        now = self._now_fn()
        with self._lock:
            if self._pending_since is None:
                return None
            last_notify = (
                self._last_notify_at if self._last_notify_at is not None else now
            )
            quiet_for = now - last_notify
            pending_for = now - self._pending_since
            floor_elapsed = pending_for >= self._periodic_floor_s
            if quiet_for < self._debounce_window_s and not floor_elapsed:
                return None
            self._pending_since = None
            self._last_notify_at = None
        _log.info(
            "verify worker: tick() triggering a coalesced verification pass "
            "for %s (floor_forced=%s)",
            self._root,
            floor_elapsed and quiet_for < self._debounce_window_s,
        )
        result = run_coalesced_verification(self._root, verify_fn=self._verify_fn)
        with self._lock:
            self._last_run_at = self._now_fn()
        return result


__all__ = [
    "DEFAULT_DEBOUNCE_WINDOW_S",
    "DEFAULT_PERIODIC_FLOOR_S",
    "CoalescingWorker",
    "VerifyFn",
    "WorkerError",
    "WorkerOutcome",
    "run_coalesced_verification",
]

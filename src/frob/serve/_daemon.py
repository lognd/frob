"""Continuous background verification for `frob.serve` (T-0733,
docs/modules/serve.md#daemon-jobs).

`frob serve` used to be purely request/response: every MCP tool call did
its own on-demand work, and nobody re-verified anything until an agent (or
the coordinator) asked. Three gaps this closes, run as periodic background
jobs alongside the stdio transport:

1. POST-LAND RE-VERIFY (`_poll_post_land`): watches `main`'s HEAD; the
   moment it moves (a land happened), refresh the warm state and run one
   delta + touched-set-tests pass, so the coordinator's post-land
   verification is a lookup (`frob_daemon_status`) instead of a fresh
   `frob check` invocation.
2. REBASE-BOT (`_poll_rebase_bot`): for every in-flight worktree branch
   (`frob.tickets.leases.read_all_leases`), simulates a merge of current
   `main` into that branch with `git merge-tree` -- no checkout, no
   scratch clone, nothing touched on disk beyond the read-only subprocess
   -- and publishes a warning the moment that simulated merge would
   conflict, well before the agent working that branch writes its Done
   report.
3. COALESCING VERIFY WORKER (`_poll_verify_worker`, T-1688): the T-1686
   epic's own trailing-edge-debounce worker (`frob.verify._worker.
   CoalescingWorker`). This job does not itself decide WHAT changed --
   `_poll_post_land`'s own HEAD-moved detection is the `notify()` source
   (a land is exactly a queue-append event), and this cycle's own
   unconditional call is the periodic-floor source `docs/modules/
   tickets.md#coalescing-verify-worker-t-1688` documents. `tick()` decides
   whether enough quiet time (or floor time) has passed to actually run
   one coalesced `frob.verify._worker.run_coalesced_verification` pass --
   most cycles it is a no-op. T-1695: even when debounce/floor say "ready",
   `tick()` itself yields (no run, pending state kept, retry next cycle)
   while foreground agent load is high (cross-worktree lease count at or
   above `CoalescingWorker`'s configured ceiling) or available memory is
   below its configured floor -- this daemon poll loop never needs to know
   that decision happened, it just calls `tick()` every cycle regardless.

Foreground agents never compete with this worker for CPU/IO priority
either (T-1695): the first time a verification pass actually runs in this
process, `frob.verify._worker._ensure_reduced_priority` lowers this
process's own `os.nice` value and, where the `ionice` binary exists, its
I/O scheduling class -- every `frob check` subprocess the pass spawns
inherits both via ordinary POSIX fork/exec priority inheritance, so
nothing in this daemon module has to wire priority into the subprocess
call itself.

All three jobs write into `_DaemonStatus`, a single in-process cache keyed
by repo root (mirroring `frob.serve._warm._STATES`'s shape) that
`frob_daemon_status` (`_tools.py`) reads back verbatim -- no disk polling
required to answer the MCP query, only to refresh it.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.serve import _warm

if TYPE_CHECKING:
    from typani.result import Result

    from frob.verify._worker import CoalescingWorker, WorkerError, WorkerOutcome

_log = get_logger(__name__)

# frob:ticket T-0782
# Which (root, ticket id) pairs `_poll_rebase_bot` has already logged a
# TTL-expiry skip for -- same "log once per process" shape as
# `frob.tickets._leases._stale_lease_logged` (T-0773), so a long-lived
# daemon that re-polls the same dead-agent-but-live-worktree lease every
# ~20s cycle forever warns exactly once, not forever.
_ttl_skip_logged: set[tuple[Path, str]] = set()

# frob:doc docs/modules/serve.md#daemon-jobs
DEFAULT_POLL_INTERVAL_S = 20.0


# frob:doc docs/modules/serve.md#daemon-jobs
# frob:waive COV007 reason="T-0871: same -- docs/modules/serve.md#daemon-jobs \
# documents this daemon internal; demoted to private in this ticket (frob-exports: \
# every real caller, including tests, already accessed it module-qualified) but \
# remains the thing the doc section describes, and the doc text/directives were \
# updated to the new name"
class _PostLandVerdict(BaseModel):
    """One post-land re-verify pass's result (T-0733): the `main` HEAD it
    was computed against, when it ran, and the delta/touched-test
    summary -- `frob_daemon_status` returns this verbatim so the
    coordinator's land verification is a lookup, never a fresh `frob
    check`."""

    model_config = ConfigDict(frozen=True)

    head: str
    checked_at: str
    baseline_stale: bool
    delta_count: int
    delta: tuple[dict, ...]
    tests_ok: bool | None


# frob:doc docs/modules/serve.md#daemon-jobs
# frob:waive COV007 reason="T-0871: same -- docs/modules/serve.md#daemon-jobs \
# documents this daemon internal; demoted to private in this ticket (frob-exports: \
# every real caller, including tests, already accessed it module-qualified) but \
# remains the thing the doc section describes, and the doc text/directives were \
# updated to the new name"
class _RebaseWarning(BaseModel):
    """One in-flight worktree branch whose eventual land against `main`
    would (T-0733) conflict, published by `_poll_rebase_bot` before the
    agent working that branch writes its Done report."""

    model_config = ConfigDict(frozen=True)

    ticket_id: str
    worktree: str
    branch: str
    main_head: str
    detected_at: str
    message: str


# frob:doc docs/modules/serve.md#daemon-jobs
# frob:waive COV007 reason="T-0871: same -- docs/modules/serve.md#daemon-jobs \
# documents this daemon internal; demoted to private in this ticket (frob-exports: \
# every real caller, including tests, already accessed it module-qualified) but \
# remains the thing the doc section describes, and the doc text/directives were \
# updated to the new name"
class _DaemonStatus(BaseModel):
    """The daemon's latest post-land verdict and outstanding rebase
    warnings for one repo root (T-0733) -- what `frob_daemon_status`
    hands back verbatim; `None` fields mean the corresponding job has not
    completed a pass yet."""

    model_config = ConfigDict(frozen=True)

    post_land: _PostLandVerdict | None = None
    rebase_warnings: tuple[_RebaseWarning, ...] = ()
    last_poll_at: str | None = None


_STATUS: dict[str, _DaemonStatus] = {}
_LOCK = threading.Lock()


def _now() -> str:
    """Current UTC time as an ISO-8601 string -- the one timestamp format
    every `_daemon` model uses."""
    return datetime.now(UTC).isoformat()


def _get_status(root: Path) -> _DaemonStatus:
    """The cached `_DaemonStatus` for `root`, or a fresh empty one if no
    poll has run yet -- never raises, always a usable value."""
    return _STATUS.get(str(root.resolve()), _DaemonStatus())


def _set_status(root: Path, status: _DaemonStatus) -> None:
    """Replace `root`'s cached `_DaemonStatus` under `_LOCK`, guarding
    against the daemon thread and an MCP tool call racing on the same
    dict."""
    with _LOCK:
        _STATUS[str(root.resolve())] = status


def _main_head(root: Path) -> str | None:
    """`git rev-parse main`'s stdout, stripped, or `None` if `main` cannot
    be resolved (no such branch, not a git repo, git unavailable) --
    `_poll_post_land`/`_poll_rebase_bot` both degrade to a no-op pass rather
    than raising when this is `None`."""
    spawned = run_argv(("git", "-C", str(root), "rev-parse", "main"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning("serve: daemon: could not resolve main HEAD under %s", root)
        return None
    return spawned.danger_ok.stdout.strip()


# frob:doc docs/modules/serve.md#daemon-jobs
# frob:tests tests/test_serve_daemon.py::TestPollPostLand.test_head_unchanged_is_noop \
# kind="unit"
# frob:tests \
# tests/test_serve_daemon.py::TestPollPostLand.test_head_moved_refreshes_verdict \
# kind="unit"
# frob:waive COV007 reason="T-0871: same -- docs/modules/serve.md#daemon-jobs \
# documents this daemon internal; demoted to private in this ticket (frob-exports: \
# every real caller, including tests, already accessed it module-qualified) but \
# remains the thing the doc section describes, and the doc text/directives were \
# updated to the new name"
def _poll_post_land(root: Path, *, run_tests: bool = True) -> _PostLandVerdict | None:
    """One post-land re-verify cycle (T-0733, job 1): if `main`'s HEAD has
    not moved since the last recorded `_PostLandVerdict` for `root`, return
    the cached verdict unchanged (no re-work); otherwise invalidate the
    warm cache, run a fresh `frob_check_delta`-equivalent pass (and,
    unless `run_tests=False`, the touched-set tests against `main`), and
    cache the new verdict. Returns `None` only if `main` itself cannot be
    resolved (no git repo, no `main` branch) -- a degraded environment,
    not a "nothing changed" result."""
    from frob.serve._tools import frob_check_delta, frob_run_touched_tests

    head = _main_head(root)
    if head is None:
        return None

    status = _get_status(root)
    if status.post_land is not None and status.post_land.head == head:
        _log.debug("serve: daemon: post-land: head %s unchanged, cache hit", head[:12])
        return status.post_land

    _log.info("serve: daemon: post-land: main moved to %s, re-verifying", head[:12])
    _warm._invalidate(root)
    delta_result = frob_check_delta(root, None, "main", verify=False)
    if delta_result.is_err:
        _log.error(
            "serve: daemon: post-land: delta failed: %s", delta_result.danger_err
        )
        return status.post_land

    payload = delta_result.danger_ok
    tests_ok: bool | None = None
    if run_tests:
        tests_result = frob_run_touched_tests(root, "main")
        if tests_result.is_ok:
            tests_ok = tests_result.danger_ok["ok"]
        else:
            _log.warning(
                "serve: daemon: post-land: touched tests failed: %s",
                tests_result.danger_err,
            )

    verdict = _PostLandVerdict(
        head=head,
        checked_at=_now(),
        baseline_stale=payload["baseline_stale"],
        delta_count=payload["delta_count"],
        delta=tuple(payload["delta"]),
        tests_ok=tests_ok,
    )
    _set_status(
        root, status.model_copy(update={"post_land": verdict, "last_poll_at": _now()})
    )
    _log.info(
        "serve: daemon: post-land: verdict for %s: delta=%d tests_ok=%s",
        head[:12],
        verdict.delta_count,
        tests_ok,
    )
    return verdict


# frob:ticket T-1688
#: One `CoalescingWorker` per repo root, keyed the same way `_STATUS` is
#: (`str(root.resolve())`) -- a worker's own debounce/floor state
#: (`_pending_since`/`_last_notify_at`/`_last_run_at`) must survive across
#: poll cycles for the SAME root, exactly like `_DaemonStatus` already
#: does; a fresh worker per call would reset the debounce window every
#: 20s and never coalesce anything.
_VERIFY_WORKERS: dict[str, CoalescingWorker] = {}
_VERIFY_WORKERS_LOCK = threading.Lock()

#: The last `main` HEAD `_poll_verify_worker` itself observed per root --
#: separate from `_poll_post_land`'s own head tracking (that one lives
#: inside `_DaemonStatus`/`_STATUS`, a different cache with a different
#: job's own concerns) so this job's "did a land happen" detection never
#: depends on `_poll_post_land` having run first or at all.
_VERIFY_WORKER_LAST_HEAD: dict[str, str] = {}


def _get_verify_worker(root: Path) -> CoalescingWorker:
    """The cached `CoalescingWorker` for `root`, creating one on first use.
    Deferred import (`frob.verify` -> `frob.app.ticket_runner._land_cmd`
    on its own verify path -- keeping `frob.serve` from paying that import
    cost at module load for every caller that never touches this job,
    matching this package's existing lazy-import convention for
    `frob.serve._tools`'s own `frob_check_delta`/`frob_run_touched_tests`
    calls above)."""
    from frob.verify._worker import CoalescingWorker

    key = str(root.resolve())
    with _VERIFY_WORKERS_LOCK:
        worker = _VERIFY_WORKERS.get(key)
        if worker is None:
            worker = CoalescingWorker(root)
            _VERIFY_WORKERS[key] = worker
        return worker


# frob:doc docs/modules/tickets.md#coalescing-verify-worker-t-1688
# frob:tests \
# tests/test_serve_daemon.py::TestPollVerifyWorker.test_head_moved_notifies_the_worker \
# kind="unit"
# frob:tests \
# tests/test_serve_daemon.py::TestPollVerifyWorker.test_head_unchanged_still_ticks \
# kind="unit"
# frob:tests tests/test_serve_daemon.py::TestPollVerifyWorker.test_tick_result_is_returned_when_a_run_happens kind="unit"  # noqa: E501
def _poll_verify_worker(root: Path) -> Result[WorkerOutcome, WorkerError] | None:
    """One coalescing-verify-worker cycle (T-1688, job 3): `notify()` the
    cached `CoalescingWorker` for `root` if `main`'s HEAD moved since the
    last time THIS job looked (a land happened -- the "queue append" wake
    condition, detected the same way `_poll_post_land` detects it, since
    this job's scope does not include `frob.tickets._land`'s own land-time
    call site that would push a real notify), then call `tick()`
    UNCONDITIONALLY every cycle -- `tick()` itself is a no-op unless the
    debounce window has gone quiet or the periodic floor has elapsed, so
    calling it every `DEFAULT_POLL_INTERVAL_S` is cheap and correct; that
    inner decision is where the real debounce/floor logic lives (`frob.
    verify._worker.CoalescingWorker.tick`), not here.

    T-1737: the FS-watch push signal `frob.serve._watch.WatchThread`
    provides IS now wired to this worker's `notify()` -- `WatchThread` is
    instantiated in `frob.serve._socketd.run_socket_daemon`, which calls
    `_get_verify_worker(root).notify()` (this module's own cache, so the
    SAME worker instance this job polls) from its `on_change` callback.
    The HEAD-moved check above and this job's own `DEFAULT_POLL_INTERVAL_S`
    polling cadence remain independent wake conditions -- the FS-watch
    push is an earlier trigger for the exact same debounce window, not a
    replacement for either."""
    head = _main_head(root)
    key = str(root.resolve())
    worker = _get_verify_worker(root)
    if head is not None:
        last_head = _VERIFY_WORKER_LAST_HEAD.get(key)
        if last_head != head:
            _VERIFY_WORKER_LAST_HEAD[key] = head
            worker.notify()
            _log.debug(
                "serve: daemon: verify-worker: head moved to %s, notified", head[:12]
            )
    result = worker.tick()
    if result is not None:
        if result.is_ok:
            _log.info(
                "serve: daemon: verify-worker: tick ran, outcome=%s",
                result.danger_ok.status,
            )
        else:
            _log.warning(
                "serve: daemon: verify-worker: tick ran, error=%s", result.danger_err
            )
    return result


def _worktree_branches(root: Path) -> tuple[tuple[str, str, str], ...]:
    """`(ticket_id, worktree, branch)` for every currently-recorded
    cross-worktree lease visible from `root` (`frob.tickets._leases.
    read_all_leases`, T-0473) -- the same liveness signal `doable` already
    trusts (a lease whose worktree path no longer exists is filtered out,
    and opportunistically unlinked, there), reused here so `_poll_rebase_bot`
    enumerates exactly the in-flight worktrees a coordinator would consider
    live.

    T-0782: `read_all_leases`'s path-existence check alone cannot catch a
    dead agent whose worktree checkout is still sitting on disk (crashed
    or abandoned mid-ticket, never `git worktree remove`d) -- that lease
    reads as perfectly live forever, and this function used to hand every
    such lease straight to `_merge_would_conflict` every ~20s cycle (audit
    M2: 2 `git` spawns per cycle, per dead lease, unbounded). A lease whose
    `recorded_at` is older than `LEASE_TTL_SECONDS` is filtered out here,
    logged once per (root, ticket id) via `_ttl_skip_logged` -- the daemon
    stops re-simulating it, but the lease file itself is left alone (only
    `read_all_leases`'s path-liveness branch unlinks; an over-TTL-but-live
    worktree may still be a real, if slow, in-progress agent -- expiry
    here only affects the daemon's OWN re-simulation cost, never deletes
    anyone's lease)."""
    from frob.tickets._leases import (
        LEASE_TTL_SECONDS,
        is_lease_ttl_expired,
        read_all_leases,
    )

    leases = read_all_leases(root)
    live: list[tuple[str, str, str]] = []
    for lease in leases:
        if is_lease_ttl_expired(lease):
            log_key = (root, lease.ticket_id)
            already_logged = log_key in _ttl_skip_logged
            if not already_logged:
                _ttl_skip_logged.add(log_key)
                _log.info(
                    "serve: daemon: rebase-bot: %s lease is past the %ss "
                    "TTL (recorded_at=%s) -- skipping re-simulation, "
                    "treating as a dead agent",
                    lease.ticket_id,
                    LEASE_TTL_SECONDS,
                    lease.recorded_at,
                )
            continue
        live.append((lease.ticket_id, lease.worktree, lease.branch))
    return tuple(live)


def _merge_would_conflict(root: Path, branch: str, main_head: str) -> bool | None:
    """Whether simulating a merge of `main_head` into `branch` (`git
    merge-tree <merge-base> <branch> <main_head>`, no checkout) would
    conflict -- `True`/`False` on a successful simulation, `None` if the
    merge-base or the simulation itself could not be computed (a branch
    ref missing from `root`'s object store, most often -- a linked
    worktree's branch is fully visible from the shared `.git`, but a
    caller passing the wrong `root` would hit this). Old-style `git
    merge-tree` (this repo's git 2.34 baseline predates the `--write-tree`
    form) always exits 0 and reports conflicts via `<<<<<<<` markers in
    stdout, not the exit code -- detection here matches that behavior.

    `branch` is a lease-sourced string (`_worktree_branches`, ultimately
    `frob.tickets._leases.read_all_leases`) written under a shared,
    peer-writable directory -- ANY co-located worktree agent's process can
    write a `frob-leases/*.json` file (audit M1, T-0780). Two independent
    layers guard against option injection here: (1) `read_all_leases`
    already rejects an option-injection-shaped `branch`/`worktree` (a
    leading `-`) before this function ever sees the record, so `branch`
    is never attacker-controlled in practice by the time it arrives; (2)
    the `merge-base` argv below still terminates its options with `--`
    before the ref operands anyway, as a second, independent line of
    defense. `git merge-tree` (old-style, no `--write-tree`) does NOT
    accept a `--` terminator on this repo's git 2.34 baseline -- verified
    directly: `git merge-tree -- <base> <branch1> <branch2>` fails with a
    usage error on this git version, so adding one there would break
    every simulation rather than harden one; `merge_base` and `main_head`
    are always git-computed/self-resolved values (never read from a lease
    file), so `branch` -- already validated by layer 1 -- is the only
    lease-sourced operand `merge-tree` receives, and layer 1 alone is
    that call's defense."""
    base = run_argv(("git", "-C", str(root), "merge-base", "--", "main", branch))
    if base.is_err or base.danger_ok.returncode != 0:
        _log.warning(
            "serve: daemon: rebase-bot: no merge-base for %s against main under %s",
            branch,
            root,
        )
        return None
    merge_base = base.danger_ok.stdout.strip()
    simulated = run_argv(
        ("git", "-C", str(root), "merge-tree", merge_base, branch, main_head)
    )
    if simulated.is_err:
        _log.warning(
            "serve: daemon: rebase-bot: merge-tree simulation failed for %s: %s",
            branch,
            simulated.danger_err,
        )
        return None
    return "<<<<<<<" in simulated.danger_ok.stdout


# frob:doc docs/modules/serve.md#daemon-jobs
# frob:tests \
# tests/test_serve_daemon.py::TestPollRebaseBot.test_no_leases_is_no_warnings \
# kind="unit"
# frob:tests \
# tests/test_serve_daemon.py::TestPollRebaseBot.test_conflicting_branch_warns \
# kind="unit"
# frob:tests \
# tests/test_serve_daemon.py::TestPollRebaseBot.test_clean_branch_no_warning kind="unit"
# frob:tests tests/test_serve_daemon.py::TestPollRebaseBot.test_ttl_expired_lease_skipped_and_logged_once kind="unit"  # noqa: E501
# frob:waive COV007 reason="T-0871: same -- docs/modules/serve.md#daemon-jobs \
# documents this daemon internal; demoted to private in this ticket (frob-exports: \
# every real caller, including tests, already accessed it module-qualified) but \
# remains the thing the doc section describes, and the doc text/directives were \
# updated to the new name"
def _poll_rebase_bot(root: Path) -> tuple[_RebaseWarning, ...]:
    """One rebase-bot cycle (T-0733, job 2): for every in-flight worktree
    branch (`_worktree_branches`), simulate merging current `main` into it
    (`_merge_would_conflict`) and publish a `_RebaseWarning` for every one
    that would conflict, replacing the cached warning set for `root`
    (stale warnings for branches that resolved clean, or that landed and
    dropped their lease, do not linger). Skips a branch whose simulation
    could not be computed (`_merge_would_conflict` returned `None`)
    rather than guessing."""
    head = _main_head(root)
    if head is None:
        return ()

    warnings: list[_RebaseWarning] = []
    for ticket_id, worktree, branch in _worktree_branches(root):
        if not branch:
            continue
        conflicts = _merge_would_conflict(root, branch, head)
        if conflicts is True:
            warning = _RebaseWarning(
                ticket_id=ticket_id,
                worktree=worktree,
                branch=branch,
                main_head=head,
                detected_at=_now(),
                message=(
                    f"{ticket_id} ({branch}) would conflict merging current main "
                    f"({head[:12]}) -- rebase before finishing"
                ),
            )
            warnings.append(warning)
            _log.warning("serve: daemon: rebase-bot: %s", warning.message)

    status = _get_status(root)
    _set_status(
        root,
        status.model_copy(
            update={"rebase_warnings": tuple(warnings), "last_poll_at": _now()}
        ),
    )
    return tuple(warnings)


# frob:doc docs/modules/serve.md#daemon-jobs
# frob:tests \
# tests/test_serve_daemon.py::TestPollRebaseBot.test_conflicting_branch_warns \
# kind="unit"
def daemon_status(root: Path) -> _DaemonStatus:
    """The cached `_DaemonStatus` for `root` -- what `frob_daemon_status`
    (`_tools.py`) exposes over MCP; a pure read, never triggers a poll."""
    return _get_status(root)


# frob:doc docs/modules/serve.md#daemon-jobs
# frob:tests tests/test_serve_daemon.py::TestRunDaemonCycle.test_runs_both_jobs_and_returns_status kind="unit"  # noqa: E501
# frob:waive COV007 reason="T-0871: same -- docs/modules/serve.md#daemon-jobs \
# documents this daemon internal; demoted to private in this ticket (frob-exports: \
# every real caller, including tests, already accessed it module-qualified) but \
# remains the thing the doc section describes, and the doc text/directives were \
# updated to the new name"
def _run_daemon_cycle(root: Path, *, run_tests: bool = True) -> _DaemonStatus:
    """One full daemon cycle: `_poll_post_land`, `_poll_rebase_bot`, then
    `_poll_verify_worker` (T-1688), all against `root`. The unit both
    `_start_daemon`'s background loop and tests call -- tests call it
    directly (no real sleep, no thread) for a deterministic single-cycle
    assertion; `_start_daemon` calls it repeatedly on a timer.
    `_poll_verify_worker` runs LAST, after `_poll_post_land` has already
    updated its own HEAD-moved detection for this cycle, so a land
    observed this cycle notifies the verify worker in the same pass it
    was detected in rather than one cycle late."""
    _poll_post_land(root, run_tests=run_tests)
    _poll_rebase_bot(root)
    _poll_verify_worker(root)
    return daemon_status(root)


# frob:doc docs/modules/serve.md#daemon-jobs
# frob:tests tests/test_serve_daemon.py::TestStartDaemon.test_background_loop_runs_a_cycle_then_stops kind="unit"  # noqa: E501
# frob:waive COV007 reason="T-0871: same -- docs/modules/serve.md#daemon-jobs \
# documents this daemon internal; demoted to private in this ticket (frob-exports: \
# every real caller, including tests, already accessed it module-qualified) but \
# remains the thing the doc section describes, and the doc text/directives were \
# updated to the new name"
def _start_daemon(
    root: Path,
    *,
    interval_s: float = DEFAULT_POLL_INTERVAL_S,
    run_tests: bool = True,
) -> threading.Event:
    """Start `_run_daemon_cycle` on a repeating background daemon thread
    (T-0733), once every `interval_s` seconds, so a fresh post-land
    verdict and rebase-bot warnings are always available within one
    interval of a change -- well under the ticket's "within a minute"
    acceptance bar at the `DEFAULT_POLL_INTERVAL_S` default. Returns a
    `threading.Event`; setting it (`.set()`) stops the loop after its
    current sleep -- `run_stdio` sets it on shutdown, tests use it to
    tear down cleanly without waiting a full interval."""
    stop = threading.Event()

    def _loop() -> None:
        """The background thread body: cycle, sleep, repeat until `stop` is set."""
        _log.info(
            "serve: daemon: background loop started for %s, interval=%gs",
            root,
            interval_s,
        )
        while not stop.is_set():
            try:
                _run_daemon_cycle(root, run_tests=run_tests)
            except Exception:  # noqa: BLE001
                _log.exception("serve: daemon: cycle raised, continuing loop")
            stop.wait(interval_s)
        _log.info("serve: daemon: background loop stopped for %s", root)

    thread = threading.Thread(target=_loop, name="frob-serve-daemon", daemon=True)
    thread.start()
    return stop


__all__ = [
    "DEFAULT_POLL_INTERVAL_S",
    "_DaemonStatus",
    "_PostLandVerdict",
    "_RebaseWarning",
    "daemon_status",
    "_poll_post_land",
    "_poll_rebase_bot",
    "_poll_verify_worker",
    "_run_daemon_cycle",
    "_start_daemon",
]

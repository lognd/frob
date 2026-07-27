"""Continuous background verification for `frob.serve` (T-0733,
docs/modules/serve.md#daemon-jobs).

`frob serve` used to be purely request/response: every MCP tool call did
its own on-demand work, and nobody re-verified anything until an agent (or
the coordinator) asked. Two gaps this closes, run as periodic background
jobs alongside the stdio transport:

1. POST-LAND RE-VERIFY (`poll_post_land`): watches `main`'s HEAD; the
   moment it moves (a land happened), refresh the warm state and run one
   delta + touched-set-tests pass, so the coordinator's post-land
   verification is a lookup (`frob_daemon_status`) instead of a fresh
   `frob check` invocation.
2. REBASE-BOT (`poll_rebase_bot`): for every in-flight worktree branch
   (`frob.tickets.leases.read_all_leases`), simulates a merge of current
   `main` into that branch with `git merge-tree` -- no checkout, no
   scratch clone, nothing touched on disk beyond the read-only subprocess
   -- and publishes a warning the moment that simulated merge would
   conflict, well before the agent working that branch writes its Done
   report.

Both jobs write into `DaemonStatus`, a single in-process cache keyed by
repo root (mirroring `frob.serve._warm._STATES`'s shape) that
`frob_daemon_status` (`_tools.py`) reads back verbatim -- no disk polling
required to answer the MCP query, only to refresh it.
"""
# frob:waive INV006 reason="T-1023 INV006 burn-down: this file's \
# exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable by \
# reading the code it annotates) rather than a separate cross-module contract needing \
# its own tracked invariant; disposed as a calibration batch, not claim-by-claim, same \
# INV006 first-turn-on-pool disposition this repo already applies elsewhere (T-0585)"

from __future__ import annotations

import threading
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.serve import _warm

_log = get_logger(__name__)

# frob:ticket T-0782
# Which (root, ticket id) pairs `poll_rebase_bot` has already logged a
# TTL-expiry skip for -- same "log once per process" shape as
# `frob.tickets._leases._stale_lease_logged` (T-0773), so a long-lived
# daemon that re-polls the same dead-agent-but-live-worktree lease every
# ~20s cycle forever warns exactly once, not forever.
_ttl_skip_logged: set[tuple[Path, str]] = set()

# frob:doc docs/modules/serve.md#daemon-jobs
DEFAULT_POLL_INTERVAL_S = 20.0


# frob:doc docs/modules/serve.md#daemon-jobs
class PostLandVerdict(BaseModel):
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
class RebaseWarning(BaseModel):
    """One in-flight worktree branch whose eventual land against `main`
    would (T-0733) conflict, published by `poll_rebase_bot` before the
    agent working that branch writes its Done report."""

    model_config = ConfigDict(frozen=True)

    ticket_id: str
    worktree: str
    branch: str
    main_head: str
    detected_at: str
    message: str


# frob:doc docs/modules/serve.md#daemon-jobs
class DaemonStatus(BaseModel):
    """The daemon's latest post-land verdict and outstanding rebase
    warnings for one repo root (T-0733) -- what `frob_daemon_status`
    hands back verbatim; `None` fields mean the corresponding job has not
    completed a pass yet."""

    model_config = ConfigDict(frozen=True)

    post_land: PostLandVerdict | None = None
    rebase_warnings: tuple[RebaseWarning, ...] = ()
    last_poll_at: str | None = None


_STATUS: dict[str, DaemonStatus] = {}
_LOCK = threading.Lock()


def _now() -> str:
    """Current UTC time as an ISO-8601 string -- the one timestamp format
    every `_daemon` model uses."""
    return datetime.now(UTC).isoformat()


def _get_status(root: Path) -> DaemonStatus:
    """The cached `DaemonStatus` for `root`, or a fresh empty one if no
    poll has run yet -- never raises, always a usable value."""
    return _STATUS.get(str(root.resolve()), DaemonStatus())


def _set_status(root: Path, status: DaemonStatus) -> None:
    """Replace `root`'s cached `DaemonStatus` under `_LOCK`, guarding
    against the daemon thread and an MCP tool call racing on the same
    dict."""
    with _LOCK:
        _STATUS[str(root.resolve())] = status


def _main_head(root: Path) -> str | None:
    """`git rev-parse main`'s stdout, stripped, or `None` if `main` cannot
    be resolved (no such branch, not a git repo, git unavailable) --
    `poll_post_land`/`poll_rebase_bot` both degrade to a no-op pass rather
    than raising when this is `None`."""
    spawned = run_argv(("git", "-C", str(root), "rev-parse", "main"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning("serve: daemon: could not resolve main HEAD under %s", root)
        return None
    return spawned.danger_ok.stdout.strip()


# frob:doc docs/modules/serve.md#daemon-jobs
# frob:tests tests/test_serve_daemon.py::TestPollPostLand.test_head_unchanged_is_noop kind="unit"  # noqa: E501
# frob:tests tests/test_serve_daemon.py::TestPollPostLand.test_head_moved_refreshes_verdict kind="unit"  # noqa: E501
def poll_post_land(root: Path, *, run_tests: bool = True) -> PostLandVerdict | None:
    """One post-land re-verify cycle (T-0733, job 1): if `main`'s HEAD has
    not moved since the last recorded `PostLandVerdict` for `root`, return
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
    _warm.invalidate(root)
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

    verdict = PostLandVerdict(
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


def _worktree_branches(root: Path) -> tuple[tuple[str, str, str], ...]:
    """`(ticket_id, worktree, branch)` for every currently-recorded
    cross-worktree lease visible from `root` (`frob.tickets._leases.
    read_all_leases`, T-0473) -- the same liveness signal `doable` already
    trusts (a lease whose worktree path no longer exists is filtered out,
    and opportunistically unlinked, there), reused here so `poll_rebase_bot`
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
# frob:tests tests/test_serve_daemon.py::TestPollRebaseBot.test_no_leases_is_no_warnings kind="unit"  # noqa: E501
# frob:tests tests/test_serve_daemon.py::TestPollRebaseBot.test_conflicting_branch_warns kind="unit"  # noqa: E501
# frob:tests tests/test_serve_daemon.py::TestPollRebaseBot.test_clean_branch_no_warning kind="unit"  # noqa: E501
# frob:tests tests/test_serve_daemon.py::TestPollRebaseBot.test_ttl_expired_lease_skipped_and_logged_once kind="unit"  # noqa: E501
def poll_rebase_bot(root: Path) -> tuple[RebaseWarning, ...]:
    """One rebase-bot cycle (T-0733, job 2): for every in-flight worktree
    branch (`_worktree_branches`), simulate merging current `main` into it
    (`_merge_would_conflict`) and publish a `RebaseWarning` for every one
    that would conflict, replacing the cached warning set for `root`
    (stale warnings for branches that resolved clean, or that landed and
    dropped their lease, do not linger). Skips a branch whose simulation
    could not be computed (`_merge_would_conflict` returned `None`)
    rather than guessing."""
    head = _main_head(root)
    if head is None:
        return ()

    warnings: list[RebaseWarning] = []
    for ticket_id, worktree, branch in _worktree_branches(root):
        if not branch:
            continue
        conflicts = _merge_would_conflict(root, branch, head)
        if conflicts is True:
            warning = RebaseWarning(
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
# frob:tests tests/test_serve_daemon.py::TestPollRebaseBot.test_conflicting_branch_warns kind="unit"  # noqa: E501
def daemon_status(root: Path) -> DaemonStatus:
    """The cached `DaemonStatus` for `root` -- what `frob_daemon_status`
    (`_tools.py`) exposes over MCP; a pure read, never triggers a poll."""
    return _get_status(root)


# frob:doc docs/modules/serve.md#daemon-jobs
# frob:tests tests/test_serve_daemon.py::TestRunDaemonCycle.test_runs_both_jobs_and_returns_status kind="unit"  # noqa: E501
def run_daemon_cycle(root: Path, *, run_tests: bool = True) -> DaemonStatus:
    """One full daemon cycle: `poll_post_land` then `poll_rebase_bot`,
    both against `root`. The unit both `start_daemon`'s background loop
    and tests call -- tests call it directly (no real sleep, no thread)
    for a deterministic single-cycle assertion; `start_daemon` calls it
    repeatedly on a timer."""
    poll_post_land(root, run_tests=run_tests)
    poll_rebase_bot(root)
    return daemon_status(root)


# frob:doc docs/modules/serve.md#daemon-jobs
# frob:tests tests/test_serve_daemon.py::TestStartDaemon.test_background_loop_runs_a_cycle_then_stops kind="unit"  # noqa: E501
def start_daemon(
    root: Path,
    *,
    interval_s: float = DEFAULT_POLL_INTERVAL_S,
    run_tests: bool = True,
) -> threading.Event:
    """Start `run_daemon_cycle` on a repeating background daemon thread
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
                run_daemon_cycle(root, run_tests=run_tests)
            except Exception:  # noqa: BLE001
                _log.exception("serve: daemon: cycle raised, continuing loop")
            stop.wait(interval_s)
        _log.info("serve: daemon: background loop stopped for %s", root)

    thread = threading.Thread(target=_loop, name="frob-serve-daemon", daemon=True)
    thread.start()
    return stop


__all__ = [
    "DEFAULT_POLL_INTERVAL_S",
    "DaemonStatus",
    "PostLandVerdict",
    "RebaseWarning",
    "daemon_status",
    "poll_post_land",
    "poll_rebase_bot",
    "run_daemon_cycle",
    "start_daemon",
]

"""`frob ticket land` -- one-command landing (docs/modules/tickets.md#frob-ticket-land).

The landing procedure used to be manual coordinator surgery repeated per
ticket: wip-commit in the worktree, merge main into it, a deletion-filter
check (a stale worktree base can silently drop files main already has),
squash-apply onto main, a ledger splice on conflict, close (evidence +
Done-report validation), and a conventional commit. `land()` does the
whole chain atomically, with a `--dry-run` mode that runs every check and
every git operation the real run would, then unwinds it, so a dry run can
never green-light a landing that would actually fail (T-0176).

Every abort path logs the exact manual remedy alongside its `Err` -- the
`--dry-run` output IS the incident report a human would otherwise have to
reconstruct by hand.

T-1186 split this module's merge/splice machinery into
`frob.tickets._land_merge`, its post-merge claim reverification into
`frob.tickets._land_verify`, and its finalize/squash-apply/release stage
into `frob.tickets._land_finalize` (following the verbatim-move pattern
`_evidence.py`/`_reporting.py` set at T-1171) -- this module retains the
land lock/repair-marker machinery, the `land()`/`_land_locked`
orchestrator, and the pre-merge preflight validators, importing the
split-out families back in explicitly. T-1334 further split that single
finalize stage into three: `_land_finalize` now holds only the draft-
finalization/sibling-renumbering/close family, `frob.tickets._land_squash`
holds the squash-apply/close family, and `frob.tickets._land_release`
holds the release-bump/uv.lock/native-rebuild family -- this module now
imports `_land_finalize_and_close` from `_land_finalize` and
`_land_squash_apply`/`_v2_effective_scope` from `_land_squash` directly.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import importlib
import json
import os
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType

from typani.result import Err, Ok, Result

from frob.gitio import current_branch, run_argv
from frob.logging import get_logger
from frob.tickets._journal import _clear_intent, _write_intent
from frob.tickets._land_finalize import _land_finalize_and_close
from frob.tickets._land_git_ops import (
    _abort_merge,
    _auto_resolve_out_of_scope_conflicts,
    _committed_out_of_scope_waive_deletions,
    _merge_main_into_worktree,
    _porcelain_dirty,
    _restore_lock_version_only_drift,
    _rev_parse,
    _true_merge_base,
    _uncommitted_out_of_scope_waive_deletions,
    _unowned_deletions,
    _wip_commit,
)
from frob.tickets._land_merge import _validate_closeable

# Re-exported for `frob.tickets.__init__`'s `from frob.tickets._land import
# land, splice_ledger` -- T-1186 moved the implementation to
# `frob.tickets._land_merge`; this module keeps the public import path
# stable.
from frob.tickets._land_merge import splice_ledger as splice_ledger  # noqa: E402
from frob.tickets._land_squash import _land_squash_apply, _v2_effective_scope
from frob.tickets._land_verify import (
    _reverify_done_report_claims_post_merge,
    _reverify_evidence_post_merge,
)
from frob.tickets._models import (
    LandError,
    LandPlanReport,
    LandReport,
    Ticket,
)
from frob.tickets._provisional import is_draft_id
from frob.tickets._store import _store_mode

# T-0577: same posix-only degradation as `frob.tickets._store`'s
# `ledger_lock` -- `_land_lock` degrades to a documented no-op (see its
# docstring) on a platform without `fcntl`, rather than failing import.
fcntl: ModuleType | None
try:
    fcntl = importlib.import_module("fcntl")
except ImportError:  # pragma: no cover -- posix-only in this repo's CI
    fcntl = None

_log = get_logger(__name__)

# T-0577: dedicated lock file for serializing `land()` calls against the
# SAME `root`, deliberately a DIFFERENT name from `_store._lock_path`'s
# `.frob/tickets.lock`. Reusing that exact path was tried first and broke:
# a worktree's own `.frob/tickets.lock` (created the moment ANY ticket
# operation runs in the worktree, then committed into the branch by
# `land`'s own `git add -A` wip-commit/finalize-commit steps) collides,
# by identical relative path, with the untracked lock file `root`'s own
# lock would have created -- git's squash-merge refuses outright ("would
# be overwritten by merge") rather than silently picking a side. A
# distinct filename `root` never shares with anything a worktree branch
# legitimately commits sidesteps that collision entirely.
_LAND_LOCK_REL = Path(".frob") / "land.lock"


def _land_lock_path(root: Path) -> Path:
    """The advisory lock file path `_land_lock` holds, serializing every
    `land()` call against `root` (T-0577)."""
    return root / _LAND_LOCK_REL


# frob:ticket T-1515
# T-1495/T-1515: the 2026-08-04 incident this closes -- an orphaned
# background land driver from a dead conversation was serially landing a
# roster while a NEW coordinator session also wrote to `root`; the
# advisory `flock` above correctly serialized the two writers against
# each other, but neither session could ever tell the other one was a
# FOREIGN, possibly-defunct driver rather than its own prior invocation
# -- a blocking `flock` just queues silently forever. This module-level
# default bounds how long a fresh `land()` call will wait on a lock
# already held by someone else before refusing loudly instead of queuing
# -- generous enough that two legitimate, back-to-back `land()` calls in
# the SAME session (the overwhelmingly common case) never trip it, short
# enough that an orphaned holder is surfaced well within a human's
# attention span rather than discovered by symptom (destroyed commits)
# hours later.
_LAND_LOCK_TIMEOUT_S = 600.0
# frob:ticket T-1495
_LAND_LOCK_POLL_S = 1.0


# frob:doc docs/guides/install.md#live-land-process-report-t-1515
# frob:ticket T-1495
class LandLockTimeout(Exception):
    """T-1515: raised by `_land_lock` when a foreign holder does not
    release `root`'s land.lock within `_LAND_LOCK_TIMEOUT_S` -- `land()`
    catches this and returns `Err(LandError.LandLockTimeout)` instead of
    the pre-T-1515 behavior (block forever, indistinguishable from a
    session's own prior in-flight call). Carries `holder` (the parsed
    metadata of whoever currently holds the lock, or `None` if the lock
    file could not be read/parsed) for the caller's own log line."""

    # frob:ticket T-1495
    def __init__(self, root: Path, holder: dict | None) -> None:
        """Record `root` and the best-effort `holder` metadata dict (pid/
        session_id/started_at, or `None`) this timeout observed."""
        self.root = root
        self.holder = holder
        super().__init__(f"land lock at {root} still held after timeout: {holder}")


# frob:ticket T-1515
def _land_lock_holder_metadata() -> dict:
    """This process's own identity for the land.lock content (T-1515): pid,
    a per-process session id (env `FROB_LAND_SESSION_ID` if a caller/test
    supplies one -- e.g. to give two `land()` calls in the SAME dispatched
    session a shared, human-legible label -- else `pid-<pid>`), and an
    ISO-8601 UTC start timestamp. Read back by a BLOCKED second `land()`
    call to name who it is waiting on, and by `frob doctor` (T-1515) to
    report live land processes. Deliberately no hostname lookup (`socket.
    gethostname()`/similar) -- a bare pid is sufficient to disambiguate
    processes on ONE host, which is this lock file's only real scope (it
    lives under a single checkout's `.frob/`), and skipping it keeps this
    node's SYS100 capability surface at plain `env` (the `FROB_LAND_
    SESSION_ID` read), not `net`."""
    from datetime import datetime, timezone

    pid = os.getpid()
    session_id = (
        # frob:waive SEC110 reason="session identity marker for lock-holder \
        # attribution, not a secret"
        os.environ.get("FROB_LAND_SESSION_ID") or f"pid-{pid}"
    )
    return {
        "pid": pid,
        "session_id": session_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


# frob:ticket T-1515
# frob:waive EXHAUST003 reason="T-1636: leaked Unknown traces to str.strip(), a str \
# method the resolver's curated table does not cover (never raises); the two real \
# raise paths (OSError on read, JSONDecodeError/ValueError on parse) are caught below"
def _read_land_lock_holder(path: Path) -> dict | None:
    """Best-effort read of `path`'s current holder metadata (T-1515) --
    `None` on any read/parse failure (the file may not exist yet, or a
    write may be mid-flight), never raised. Used both by a blocked
    `_land_lock` caller (to log WHO it is waiting on) and by `frob
    doctor`'s live-land-process scan."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


@contextmanager
# frob:ticket T-1495
def _land_lock(root: Path, *, timeout: float = _LAND_LOCK_TIMEOUT_S) -> Iterator[None]:
    """Exclusive, cross-process lock serializing every `land()` call
    against `root` (T-0577) -- see `land`'s docstring for why this closes
    the REL001 version-bump-collision incident class. Degrades to a
    documented no-op (logged at WARNING) on a platform without `fcntl`,
    matching `frob.tickets._store.ledger_lock`'s same documented
    degradation.

    T-1515: no longer an unbounded blocking `flock` -- polls a NON-
    blocking `flock` attempt every `_LAND_LOCK_POLL_S`, logging (once,
    at WARNING) who currently holds the lock the first time this call has
    to wait at all, and raises `LandLockTimeout` (caught by `land()`,
    surfaced as `Err(LandError.LandLockTimeout)`) if `timeout` elapses
    with the lock still held by someone else -- a foreign/orphaned driver
    from a dead session can no longer queue a fresh `land()` call silently
    forever (the exact 2026-08-04 incident, T-1495). On successful
    acquisition, this process's own pid/session/start-time
    (`_land_lock_holder_metadata`) is written into the lock file's
    content, both for a future blocked caller's log line and for `frob
    doctor`'s live-land-process report."""
    if fcntl is None:  # pragma: no cover -- posix-only in this repo's CI
        _log.warning(
            "land: _land_lock: fcntl unavailable on this platform, lock is "
            "a NO-OP -- concurrent `land()` calls against %s are NOT "
            "serialized here",
            root,
        )
        yield
        return
    import time as _time

    path = _land_lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
    deadline = _time.monotonic() + timeout
    logged_holder = False
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError:
            if not logged_holder:
                holder = _read_land_lock_holder(path)
                _log.warning(
                    "land: %s land.lock is held by %s -- waiting up to %.0fs "
                    "before refusing (T-1515: was an unbounded blocking wait)",
                    root,
                    holder
                    if holder is not None
                    else "an unknown process (lock file unreadable/unwritten)",
                    timeout,
                )
                logged_holder = True
            if _time.monotonic() >= deadline:
                os.close(fd)
                raise LandLockTimeout(root, _read_land_lock_holder(path)) from None
            _time.sleep(_LAND_LOCK_POLL_S)
    holder_metadata = _land_lock_holder_metadata()
    try:
        os.ftruncate(fd, 0)
        os.write(fd, (json.dumps(holder_metadata) + "\n").encode("utf-8"))
    except OSError as exc:
        _log.warning(
            "land: %s could not write land.lock holder metadata (%s) -- "
            "T-1515 diagnostics degraded, lock itself still held",
            root,
            exc,
        )
    _log.debug("land: _land_lock acquired (%s) by %s", path, holder_metadata)
    try:
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        _log.debug("land: _land_lock released (%s)", path)


# frob:ticket T-0907
# T-0907 incident: a killed `land()` (SIGTERM/SIGKILL mid-staging) used to
# unwind root's squash-staging via a BARE `git reset --hard` (target
# defaults to whatever `HEAD` resolves to AT THAT MOMENT) -- if root's
# `HEAD`/branch ref was itself corrupted mid-run by the kill (a torn
# ref-update from an interrupted git subprocess sharing the kill's process
# group), that bare reset silently CEMENTED the corruption onto main
# instead of restoring it, observed once as a ~60-commit regression only
# caught because a human happened to check the reflog before the next
# `land` committed anything new. `_verified_reset_root`/the land-repair
# marker below close this two ways: (1) every unwind site now resets to an
# EXPLICIT sha (`pre_land_tip`, captured via `git rev-parse HEAD` once at
# THIS run's start and threaded through as a plain local value -- never
# re-derived from a possibly-corrupted `HEAD` and never stored in shared
# `.frob` state), refusing loudly instead of resetting at all if root's
# current tip has already drifted from that recorded value by the time an
# unwind runs; (2) a marker file recorded under `root`'s `.frob/` BEFORE
# `_land_squash_apply` starts mutating root survives an uncatchable
# SIGKILL (a Python signal handler cannot trap that signal at all) and is
# reconciled by `_repair_stale_land_marker` at the START of the NEXT
# `land()` call against the same `root`/ticket -- the "leave an explicit
# marker the next invocation repairs" half of the T-0907 fix requirement.
_LAND_REPAIR_DIRNAME = "land-repair"


# frob:ticket T-0907
def _land_repair_dir(root: Path) -> Path:
    """`<root>/.frob/land-repair`, where a crashed `land()`'s pre-mutation
    root tip is recorded (T-0907) so a later invocation can reconcile it."""
    return root / ".frob" / _LAND_REPAIR_DIRNAME


# frob:ticket T-0907
def _land_repair_marker_path(root: Path, ticket_id: str) -> Path:
    """The per-ticket land-repair marker path under `root` (T-0907)."""
    return _land_repair_dir(root) / f"{ticket_id}.json"


# frob:ticket T-0907
def _write_land_repair_marker(root: Path, ticket_id: str, pre_land_tip: str) -> None:
    """Record `pre_land_tip` (this run's verified pre-mutation root tip)
    under `root`'s land-repair marker for `ticket_id` (T-0907), BEFORE
    `_land_squash_apply` starts mutating `root` -- so a crash between this
    write and `_clear_land_repair_marker` (including an uncatchable
    SIGKILL) leaves a durable record of what `root`'s tip legitimately was
    before this run touched anything, for `_repair_stale_land_marker` to
    reconcile on the next `land()` call. Best-effort, like the T-0456
    intent journal: a write failure is logged but does not itself fail the
    land, since the pre-existing (pre-T-0907) safety net -- root untouched
    until `_commit_squash_apply`'s final commit -- still holds even with no
    marker recorded; the marker is an ADDITIONAL recovery aid, not the sole
    line of defense."""
    path = _land_repair_marker_path(root, ticket_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"ticket_id": ticket_id, "pre_land_tip": pre_land_tip}) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        _log.warning(
            "land: %s could not write land-repair marker (%s) -- proceeding "
            "without the T-0907 crash-repair aid for this run",
            ticket_id,
            exc,
        )


# frob:ticket T-0907
def _clear_land_repair_marker(root: Path, ticket_id: str) -> None:
    """Remove `ticket_id`'s land-repair marker under `root`, if any
    (T-0907) -- called when `_land_squash_apply` returns for ANY reason
    (success or a clean, handled `Err`), from a `finally` block, mirroring
    `_clear_intent`'s same unconditional-cleanup shape."""
    path = _land_repair_marker_path(root, ticket_id)
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        _log.warning("land: %s could not clear land-repair marker: %s", ticket_id, exc)


# frob:ticket T-0907
# frob:tests tests/test_ticket_land.py::TestLandRepairMarker.test_repair_resets_root_when_current_tip_matches_the_marker  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestLandRepairMarker.test_repair_refuses_loudly_when_current_tip_has_drifted_from_the_marker  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestLandRepairMarker.test_no_marker_is_a_silent_no_op  # noqa: E501
def _repair_stale_land_marker(root: Path) -> Result[None, LandError]:
    """Reconcile every leftover T-0907 land-repair marker under `root`, if
    any exist -- called at the very start of `_land_locked`, under `root`'s
    `_land_lock`, before this run captures its OWN pre-land tip.

    Scans `root`'s ENTIRE land-repair directory rather than looking up one
    marker by THIS call's own `ticket_id`: a crash can happen AFTER
    `_land_finalize_and_close` has already renumbered a draft id to its
    real sequential id (`_write_land_repair_marker` records under the id
    `_land_locked` was CALLED with, which for a draft ticket is the
    pre-finalize draft id), so a human's natural retry -- exactly the
    T-0795 `TestLandRetryAfterFinalizeThenFail` shape this reuses -- passes
    the now-finalized id, which would never match a marker filename keyed
    to the draft id it replaced. `root`'s `_land_lock` guarantees at most
    one `land()` is ever in flight against `root` at a time, so ANY marker
    found here unambiguously belongs to a fully-finished-or-crashed PRIOR
    attempt, never this one -- reconciling all of them, regardless of the
    id in this call, is always correct.

    No marker at all is the overwhelmingly common case and is a silent
    no-op (`Ok(None)`) -- most `land()` calls never crash mid-staging.

    For each marker found: if `root`'s CURRENT tip still equals the
    marker's recorded `pre_land_tip`, the crash happened before any commit
    landed on `root` (the pre-T-0907 safety net -- root is never committed
    to until `_commit_squash_apply`'s final step -- held), so this resets
    `root` to that same tip (explicit, not bare) and cleans any leftover
    staged/conflicted squash state, then clears the marker and continues to
    the next one.

    When `root`'s current tip has DRIFTED from a marker's recorded value,
    this is the exact ambiguous condition the T-0907 incident's reset
    blindly cemented -- refuses loudly (`Err(GitFailed)`) instead of
    resetting anything, naming both shas and pointing at manual
    reflog/log inspection, and leaves that marker (and any not yet
    processed) in place so the next attempt sees the same refusal until a
    human resolves it."""
    marker_dir = _land_repair_dir(root)
    if not marker_dir.is_dir():
        return Ok(None)

    for marker_path in sorted(marker_dir.glob("*.json")):
        reconciled = _reconcile_one_land_repair_marker(root, marker_path)
        if reconciled.is_err:
            return reconciled
    return Ok(None)


# frob:ticket T-0976
def _reconcile_one_land_repair_marker(
    root: Path, marker_path: Path
) -> Result[None, LandError]:
    """One T-0907 land-repair marker's reconciliation:
    `_repair_stale_land_marker`'s per-marker half, split from its
    directory-scan loop. See that function's docstring for the reset-if-
    tip-matches / refuse-if-drifted contract this implements."""
    marker_ticket_id = marker_path.stem
    try:
        raw = json.loads(marker_path.read_text(encoding="utf-8"))
        recorded_tip = str(raw["pre_land_tip"])
    except (OSError, ValueError, KeyError) as exc:
        _log.error(
            "land: found an unreadable T-0907 land-repair marker at %s "
            "(%s) -- a prior `frob ticket land %s` crashed mid-staging "
            "but its recorded pre-land tip could not be read; inspect "
            "%s and `git -C %s reflog`/`git -C %s log --oneline -5` by "
            "hand, confirm %s's tip is sound, then remove %s and retry",
            marker_path,
            exc,
            marker_ticket_id,
            marker_path,
            root,
            root,
            root,
            marker_path,
        )
        return Err(LandError.GitFailed)

    current = _rev_parse(root, "HEAD")
    if current.is_err:
        return Err(current.danger_err)

    if current.danger_ok != recorded_tip:
        _log.error(
            "land: refused -- a prior `frob ticket land %s` crashed "
            "mid-staging (T-0907) with a land-repair marker recording "
            "%s's pre-land tip as %s, but %s's CURRENT tip is %s -- "
            "these differ, so the exact damage cannot be safely "
            "auto-repaired; inspect `git -C %s reflog` and `git -C %s "
            "log --oneline -5` by hand, confirm %s's tip is sound "
            "(recover with `git -C %s reset --hard <known-good-sha>` "
            "if not), then remove %s and retry",
            marker_ticket_id,
            root,
            recorded_tip,
            root,
            current.danger_ok,
            root,
            root,
            root,
            root,
            marker_path,
        )
        return Err(LandError.GitFailed)

    _log.warning(
        "land: repairing a prior crashed `frob ticket land %s` -- %s's "
        "current tip (%s) matches the recorded pre-land tip, resetting "
        "any leftover staged/conflicted state from the crashed run "
        "(T-0907)",
        marker_ticket_id,
        root,
        recorded_tip,
    )
    reset = run_argv(["git", "-C", str(root), "reset", "--hard", recorded_tip])
    if reset.is_err or reset.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    clean = run_argv(["git", "-C", str(root), "clean", "-fd"])
    if clean.is_err or clean.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    marker_path.unlink(missing_ok=True)
    _log.info(
        "land: %s T-0907 land-repair marker cleared, %s cleaned to %s",
        marker_ticket_id,
        root,
        recorded_tip,
    )
    return Ok(None)


# frob:ticket T-1523
#: The T-0907 land-repair marker (above) covers the PRE-commit staging
#: window -- written before `_land_squash_apply` mutates `root`, cleared
#: the moment it returns. That leaves a real, separately-killable gap
#: (T-1495 point 4, the 2026-08-04 incident's own trigger): once the
#: final commit lands, `frob.app.ticket_runner._land_cmd._land` still has
#: to run the post-land unscoped-error sweep, print the `LAND-PROOF:`
#: line, and (with `--finish`) remove the worktree -- a `>540s` SIGTERM
#: during THAT window leaves a real, already-landed commit on `root`
#: with none of that verification ever having run, and nothing durable
#: recording that fact for the next invocation to notice. This marker
#: closes that gap the same way T-0907's does for its own window: written
#: right after the commit exists, cleared once post-land verification
#: actually completes (`frob.app.ticket_runner._land_cmd._land`'s own
#: tail sequence), reconciled (verified + logged, never mutated) at the
#: START of the next `frob ticket land` invocation against the same
#: `root` by `_stale_post_land_verify_markers`.
_LAND_VERIFY_PENDING_DIRNAME = "land-verify-pending"


# frob:ticket T-1523
def _land_verify_pending_dir(root: Path) -> Path:
    """`<root>/.frob/land-verify-pending`, where a landed-but-not-yet-
    verified commit's marker is recorded (T-1523)."""
    return root / ".frob" / _LAND_VERIFY_PENDING_DIRNAME


# frob:ticket T-1523
def _land_verify_pending_marker_path(root: Path, ticket_id: str) -> Path:
    """The per-ticket post-land-verify-pending marker path under `root`
    (T-1523)."""
    return _land_verify_pending_dir(root) / f"{ticket_id}.json"


# frob:ticket T-1523
def _write_post_land_verify_marker(root: Path, ticket_id: str, commit_sha: str) -> None:
    """Record `commit_sha` (the just-landed commit, ALREADY on `root`)
    under `ticket_id`'s post-land-verify-pending marker (T-1523) -- called
    by `_land_cmd._land` immediately after `land()` returns a real,
    non-dry-run success, BEFORE the post-land sweep/`LAND-PROOF`/`--finish`
    tail runs. A SIGTERM anywhere in that tail leaves this marker behind
    for `_stale_post_land_verify_markers` to pick up on the next
    invocation. Best-effort like `_write_land_repair_marker`: a write
    failure is logged but never fails the land itself, since the commit
    it would have tracked is already durably on `root` either way -- this
    marker is purely a recovery AID, not a mutation gate."""
    path = _land_verify_pending_marker_path(root, ticket_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"ticket_id": ticket_id, "commit_sha": commit_sha}) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        _log.warning(
            "land: %s could not write post-land-verify-pending marker "
            "(%s) -- proceeding without the T-1523 crash-recovery aid "
            "for this run",
            ticket_id,
            exc,
        )


# frob:ticket T-1523
def _clear_post_land_verify_marker(root: Path, ticket_id: str) -> None:
    """Remove `ticket_id`'s post-land-verify-pending marker, if any
    (T-1523) -- called once `_land_cmd._land`'s post-land verification
    tail (sweep, `LAND-PROOF`, `--finish`) has actually completed,
    mirroring `_clear_land_repair_marker`'s unconditional-cleanup shape."""
    path = _land_verify_pending_marker_path(root, ticket_id)
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        _log.warning(
            "land: %s could not clear post-land-verify-pending marker: %s",
            ticket_id,
            exc,
        )


# frob:ticket T-1523
# frob:tests tests/test_ticket_land.py::TestPostLandVerifyPendingMarker.test_stale_marker_reports_verified_true_when_commit_is_a_clean_ancestor  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestPostLandVerifyPendingMarker.test_no_marker_is_a_silent_empty_result  # noqa: E501
def _stale_post_land_verify_markers(root: Path) -> tuple[tuple[str, str], ...]:
    """`(ticket_id, commit_sha)` for every leftover T-1523 post-land-
    verify-pending marker under `root`, read-only (never mutates `root`
    or the marker files themselves -- clearing is the caller's own
    responsibility once it has actually acted on what this reports).
    Called at the very start of `_land_cmd._land`, before this invocation
    does any work of its own, so a prior run's SIGTERM-interrupted
    verification tail is surfaced (and reconciled) before anything new
    happens. No marker at all -- the overwhelmingly common case -- returns
    an empty tuple."""
    marker_dir = _land_verify_pending_dir(root)
    if not marker_dir.is_dir():
        return ()
    found: list[tuple[str, str]] = []
    for marker_path in sorted(marker_dir.glob("*.json")):
        try:
            raw = json.loads(marker_path.read_text(encoding="utf-8"))
            found.append((str(raw["ticket_id"]), str(raw["commit_sha"])))
        except (OSError, ValueError, KeyError) as exc:
            _log.error(
                "land: found an unreadable T-1523 post-land-verify-"
                "pending marker at %s (%s) -- a prior `frob ticket land` "
                "landed a commit but crashed before verifying it; "
                "inspect %s and `git -C %s log --oneline -5` by hand, "
                "then remove %s once resolved",
                marker_path,
                exc,
                marker_path,
                root,
                marker_path,
            )
    return tuple(found)


# frob:ticket T-0176
# frob:ticket T-1355
# frob:ticket T-1410
# frob:doc docs/modules/tickets.md#frob-ticket-land
# `dry_run` runs every check and every git mutation the real run would
# (merge, splice, deletion-check) then unwinds it via
# `merge --abort`/`reset --hard`, so a clean dry run is a real guarantee,
# not a guess (T-0176).
# frob:ticket T-1495
def land(
    root: Path,
    ticket_id: str,
    worktree: Path,
    *,
    dry_run: bool = False,
    collected: Callable[[], frozenset[str]] | None = None,
    passed: Callable[[Sequence[str]], frozenset[str]] | None = None,
    covers_scope: Callable[[Ticket], bool | None] | None = None,
    bump_version: Callable[[Path, Ticket, str], Result[str | None, LandError]]
    | None = None,
    rebuild_natives: Callable[[Path], bool] | None = None,
    sync_gate_rules: Callable[[Path, str], Result[tuple[str, ...] | None, LandError]]
    | None = None,
    check_gates: Callable[[], tuple[int, int, int] | None] | None = None,
    check_gate_findings: Callable[[], frozenset[tuple[str, str]] | None] | None = None,
    check_gate_claims: Callable[[Ticket], bool | None] | None = None,
    skip_mutation_evidence: bool = False,
    allow_cross_ticket: bool = False,
    pre_commit_sweep: Callable[[Path, str], bool | None] | None = None,
) -> Result[LandReport, LandError]:
    """T-1514: `pre_commit_sweep(root, final_id)` (opt-in), if supplied, is
    invoked at the last checkpoint before the final squash-apply commit --
    `root`'s working tree already holds the fully staged, uncommitted
    merge-preview changeset at that point, so a refusal there unwinds via
    the same `_verified_reset_root` path every other pre-commit failure
    uses, never a `git reset --hard` of a real, already-landed commit. See
    `_land_squash_apply`'s own docstring for the full rationale. Defaults
    to `None` (skip), matching every other opt-in land callable's posture;
    the `frob ticket land` CLI supplies it by default (`ticket_runner.py`'s
    `_land`).

    T-1355: `allow_cross_ticket` (default `False`) is the escape hatch
    for `_check_cross_ticket_leakage`'s new preflight refusal -- see that
    function's own docstring for what it catches (a multi-ticket series
    worktree landing one ticket while silently carrying a sibling's still-
    open committed work along with it) and why the override is logged
    rather than silent. `frob ticket land --allow-cross-ticket` sets it;
    the default stays strict (refuse) since the whole point of the check
    is to make this leakage class impossible to hit by accident.

    T-1011: `sync_gate_rules(root, pre_land_tip)`, if supplied, runs
    right after `bump_version` (same staged-but-uncommitted point) and
    decides for itself -- by diffing `pre_land_tip`..`root`'s now-squashed
    tree -- whether the landing diff touched `_KNOWN_GATE_RULES`
    (`src/frob/gates/__init__.py`); if so it runs the equivalent of `frob
    registry audit --sync-gate-rules` and stages `check-coverage.yaml`'s
    new rows into the SAME land commit, ending the manual re-sync this
    repo's own history shows drifting twice in one drive
    (docs/audits/coordination-churn.md). Returns `Ok(None)` (no-op) when
    nothing needed syncing, `Ok(rule_ids)` after a real sync, or an `Err`
    that unwinds the staged squash exactly like a `bump_version` failure.
    Defaults to `None` (skip) for the same cycle-avoidance reason as
    `bump_version`/`rebuild_natives` (docs/rework.md) -- the `frob ticket
    land` CLI supplies it by default (see `ticket_runner.py`'s `_land`).

    T-0846: `check_gate_findings` (opt-in, alongside `check_gates`) lets
    a caller with a fresh per-finding (rule id, file) oracle supply it so
    the gate-state claim re-verification can compare identities scoped to
    the ticket's own declared scope instead of a raw scope-wide count --
    see `_reverify_done_report_claims_post_merge`'s own doc for the
    masking gap this closes. Defaults to `None` (skip, same posture as
    every other D-05/T-0754 capture callable) -- falls back to the
    existing count-only comparison unchanged.

    Land `ticket_id` from `worktree` onto `root`'s current branch:
    precheck, wip-commit + merge + deletion-check, finalize + close, then
    squash-apply onto main with a conventional-commit message.

    T-0755 reviewer round 2: `skip_mutation_evidence` (default `False`) is
    the documented escape hatch for the TEST016 mutation-evidence refusal
    (`_check_mutation_evidence`) -- `frob ticket land --skip-mutation-
    evidence` sets it. Every use is logged at WARNING with the ticket id
    naming the override, matching how other land bypasses (e.g. a manual
    `frob:waive`) leave a visible trail rather than a silent skip; this is
    a deliberate escape hatch for a genuinely false-positive finding, not
    a way to make a real confirmatory-evidence problem quietly disappear.

    T-0338: `bump_version` and `rebuild_natives` let a caller fold the two
    remaining coordinator-plumbing steps (REL001 version bump/stamp, and
    a native-extension rebuild trigger) into the same one-command land
    instead of leaving them as manual follow-ups. Both are invoked AFTER
    the squash-apply is staged onto `root` (so their writes land in the
    SAME commit) but BEFORE the T-0463 completeness assertion and the
    final commit -- a failure from either unwinds the squash exactly like
    any other land failure. `bump_version(root, ticket, final_id)`
    computes and applies whatever `frob.release` says the just-squashed
    public API demands (pyproject.toml + CHANGELOG.md + `.frob-release.
    json`, all staged), returning `Ok(new_version)` if a bump was applied,
    `Ok(None)` if none was needed. `rebuild_natives(root)` is invoked only
    when the landed changeset touches a native source tree (frob-core/,
    strata-core/) and returns whether the rebuild succeeded (best-effort:
    a `False` is logged but does not fail the land, matching the T-0248
    stale-native warning's existing non-blocking severity). Both default
    to `None` (skip), matching every caller before T-0338 -- computing
    either needs `frob.release`/`frob.graph`/subprocess access
    `frob.tickets` deliberately does not have (docs/rework.md cycle-
    avoidance); the `frob ticket land` CLI supplies both by default (see
    `ticket_runner.py`'s `_land`).

    D-05: `collected`/`passed`/`covers_scope` let a caller with a fresh
    test-collection/run/graph-binding oracle re-verify the ticket's
    evidence against the POST-MERGE worktree tree (after
    `_merge_main_into_worktree` has run -- NOT the pre-merge worktree
    report `_land_precheck` validated) before it is finalized and closed,
    instead of `land` trusting whatever the worktree's `Done report`
    claims. They are CALLABLES, not precomputed values, because the
    caller cannot know the post-merge tree state before `land` has
    actually performed the merge internally -- `land` invokes them at the
    right point instead: `collected()` (no args, run against `worktree`
    after the merge) re-checks every non-cmd evidence id still resolves;
    `passed(non_cmd_evidence_ids)` (given the reloaded post-merge ticket's
    ids) returns the subset actually observed passing; `covers_scope
    (ticket)` (given the reloaded post-merge ticket) answers the D-02
    scope-binding question the same way `transition`'s own `covers_scope`
    parameter does (`True`/`False`/`None`-skip). T-0774: `_land_precheck`
    ALSO invokes `covers_scope` once more, PRE-merge, against the
    worktree's still-unmerged ticket -- a preflight simulation of this
    same D-02 question that lets a landing refuse (with git log unchanged)
    before `_land_merge_stage` ever runs `git merge`, instead of only
    discovering an uncovered scope after a merge/finalize commit already
    exists; the post-merge invocation here remains the authoritative
    re-check against the tree that will actually land. All three default to
    `None` (skip, matching every caller before D-05) since computing them
    needs `frob.testing`/`frob.graph` access `frob.tickets` deliberately
    does not have (docs/rework.md cycle-avoidance) -- a caller that sits
    above both (today, `frob.gates` for `covers_scope`'s computation, and
    the `frob ticket land` CLI, which supplies all three by default --
    see `ticket_runner.py`'s `_land`) provides them. Passing nothing
    preserves the exact pre-D-05 behavior, which is why the library
    default stays permissive even though the CLI's default is strict.

    T-0754: `check_gates()` re-runs the SAME `frob check --ticket` capture
    `frob ticket done-report` made when the Done report was written,
    against the post-merge tree, and refuses the land (`ClaimDivergence`)
    if the recorded `gate_errors` count no longer matches (warnings/waived
    are recorded but never gate the land -- review round 2 fix #1, they
    legitimately drift on a busy shared branch). The test-count half of
    the SAME claim reuses `passed`'s own post-merge run (review round 2
    fix #3 -- no second collect+run), so it is checked whenever both
    `passed` and `check_gates` are supplied, with no separate parameter of
    its own. A ticket whose Done report carries no Captured claims section
    (predates T-0754, or was written without the capture callables) is
    unaffected. `check_gates` defaults to `None` (skip, same posture as
    `collected`/`passed`) -- the `frob ticket land` CLI supplies it by
    default (see `ticket_runner.py`'s `_land`).

    T-0832: `check_gates()` returns `None` (never a negative sentinel)
    when the fresh check it ran produced no parsable gate-summary; the
    gate-state half of the claim comparison is then skipped with an
    explicit logged notice rather than comparing an unmeasured value
    against anything, and the test-count half is still checked
    independently whenever `passed` was supplied and ran successfully.

    T-1410: `check_gate_claims(ticket)` (given the reloaded post-merge
    ticket, same calling convention as `covers_scope`) lets a caller
    re-verify every acceptance criterion shaped as a package-wide
    gate-outcome claim ("0 <RULE> findings under <glob>",
    `frob.tickets._evidence._gate_claim_criteria`) against the POST-MERGE
    worktree tree, and refuses the land (`ClaimDivergence`, reused rather
    than adding a new `LandError` variant -- both mean "a claimed
    gate/test state does not hold post-merge") when it returns `False` --
    the T-1276 defect this closes: T-1276's own criterion [0] read "0
    TEST005 findings under src/frob/app/**", closed done and landed
    (LAND-PROOF verified) against 116 live TEST005 findings under that
    exact glob, because nothing ever computed this. `None` (default, skip)
    matches every caller before T-1410 -- computing it needs
    `frob.gates`/subprocess access `frob.tickets` deliberately does not
    have (docs/rework.md cycle-avoidance); the `frob ticket land` CLI
    supplies it by default (see `ticket_runner.py`'s `_land`).

    T-0577: the ENTIRE precheck-through-squash-commit body runs under
    `root`'s dedicated `_land_lock` (a cross-process `flock`, same
    primitive family as `frob.tickets._store.ledger_lock`'s T-0458
    single-writer lock but its OWN file -- see `_land_lock`'s doc for why
    it cannot reuse `ledger_lock`'s path) -- a second `land()` against the
    SAME `root` (a different agent/coordinator process landing a different
    ticket concurrently) blocks at the lock acquire instead of racing this
    one. This is what makes the REL001 version bump (`bump_version`,
    computed against `root`'s tree from INSIDE this critical section)
    collision-free: two lands can no longer both read the same
    pre-bump manifest version and each compute the same "next" version,
    the real incident (6 version-number collisions from parallel branches
    in one session) this closes. Manual, non-`land` coordinator surgery
    that mutates `root` while holding no lock is not protected by this --
    only concurrent `land()` calls are serialized against each other."""
    root, worktree = root.resolve(), worktree.resolve()

    # T-1003 (churn item 4): `root` defaults to the invoker's cwd
    # (`ticket_runner.py`'s `_land`) -- running `frob ticket land <id>
    # --worktree <path>` from a shell sitting INSIDE the worktree (rather
    # than cd-ing out to the shared root checkout first, the "chained cd"
    # ritual this ticket retires) makes `root` resolve to the identical
    # path as `worktree`, for free, no misconfigured `--worktree` involved.
    # Resolve the TRUE primary checkout from `worktree`'s own git common
    # dir and use it instead, transparently, whenever that resolves to
    # something OTHER than `worktree` itself -- a real linked worktree,
    # which is the common case this retires the ritual for. When the
    # common-dir resolution ALSO comes back equal to `worktree` (no linked
    # worktree exists at all -- `--worktree` was pointed at the primary
    # checkout itself, the genuinely wrong configuration T-0795 introduced
    # this refusal for), `root` is left as `worktree` unchanged and
    # `_refuse_if_root_is_worktree` still refuses exactly as before.
    if root == worktree:
        resolved_root = _resolve_primary_checkout(worktree)
        if resolved_root is not None and resolved_root != worktree:
            _log.info(
                "land: %s root defaulted to the cwd inside --worktree (%s) "
                "-- resolved the primary checkout %s from its git common "
                "dir instead (T-1003), no manual cd required",
                ticket_id,
                root,
                resolved_root,
            )
            root = resolved_root

    try:
        with _land_lock(root):
            return _land_locked(
                root,
                ticket_id,
                worktree,
                dry_run=dry_run,
                collected=collected,
                passed=passed,
                covers_scope=covers_scope,
                bump_version=bump_version,
                rebuild_natives=rebuild_natives,
                sync_gate_rules=sync_gate_rules,
                check_gates=check_gates,
                check_gate_findings=check_gate_findings,
                check_gate_claims=check_gate_claims,
                skip_mutation_evidence=skip_mutation_evidence,
                allow_cross_ticket=allow_cross_ticket,
                pre_commit_sweep=pre_commit_sweep,
            )
    except LandLockTimeout as exc:
        _log.error(
            "land: %s refused -- %s (T-1515: the pre-T-1515 behavior was "
            "an unbounded blocking wait)",
            ticket_id,
            exc,
        )
        return Err(LandError.LandLockTimeout)


# frob:ticket T-1269
# frob:doc docs/modules/tickets.md#frob-ticket-land---plan-t-1269
# frob:tests tests/test_ticket_land.py::TestLandPlan.test_merges_and_finalizes_every_draft_atomically  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestLandPlan.test_dry_run_unwinds_the_merge  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestLandPlan.test_merge_conflict_aborts_and_refuses  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestLandPlan.test_tick_gate_dirty_unwinds_finalize_but_keeps_the_durable_merge  # noqa: E501
# frob:ticket T-1495
def land_plan(
    root: Path,
    worktree: Path,
    *,
    dry_run: bool = False,
    check_ticks: Callable[[], bool | None] | None = None,
) -> Result[LandPlanReport, LandError]:
    """`frob ticket land --plan --worktree PATH` (T-1269): land a DESIGN-
    PHASE worktree -- docs plus ledger changes, no closeable worked ticket
    -- atomically, instead of the pre-T-1269 manual chain (a guarded plain
    `git merge` plus hand-assigned `frob ticket renumber` calls per draft,
    observed costing 15 hand-assigned renumbers across 4 batches landing
    four planner worktrees in one drive).

    The whole chain -- merge `worktree`'s branch onto `root`'s current
    branch (the registered `tickets.md` merge driver, if any, splices any
    ledger conflict the same way an ordinary `git merge`/`pull` already
    would -- this function performs no ledger surgery of its own), finalize
    EVERY incoming draft id now on `root` to the next free real id in one
    `finalize_draft` call each (T-0162's existing allocator, never a hand-
    assigned id), then an optional `check_ticks()` TICK-gate re-check --
    runs under `root`'s `_land_lock` (T-0577, the same cross-process lock
    `land()` uses) for atomicity against a concurrent `land()`/`land_plan()`
    call against the SAME `root`.

    On a failure AFTER the merge (a finalize error, or `check_ticks()`
    returning `False`), `root` is `git reset --hard`ed back to the MERGE
    COMMIT itself, never past it (T-1522) -- the merge commit is the
    "queue-drain" checkpoint: it already durably carries every OTHER
    ticket's finalized/landed content this worktree's branch accumulated
    (a shared multi-ticket worktree's earlier tickets), and discarding it
    just because a LATER, unrelated step in the SAME invocation failed
    silently ate that content in a real 2026-08-04 incident (T-1199/T-1200
    eaten by two retried land_plan attempts). Only the partially-
    renumbered drafts / TICK-dirty state on top of the merge is undone; a
    genuine merge-step failure (before any commit exists at all) still
    resets all the way back to the pre-merge tip, since there is nothing
    durable to preserve in that case. A merge CONFLICT (before any commit
    exists) is resolved via `git merge --abort` instead, since nothing was
    committed yet.

    `check_ticks` (default `None`, skip -- matching `land`'s own `check_
    gates`/`covers_scope`/etc. cycle-avoidance posture, docs/rework.md:
    `frob.tickets` cannot import `frob.gates` directly) lets a caller with
    a fresh `frob check --only tickets` oracle refuse the plan-land on a
    non-clean TICK gate; `frob ticket land --plan`'s CLI supplies it.
    `dry_run=True` runs the merge and finalize exactly as a real call
    would, then `git reset --hard`s back to the pre-merge tip regardless
    of outcome, returning the report of what WOULD have happened."""
    root, worktree = root.resolve(), worktree.resolve()
    same_path = _refuse_if_root_is_worktree(root, worktree, "<plan>")
    if same_path.is_err:
        return Err(same_path.danger_err)
    dirty = _refuse_if_main_dirty(root, worktree, "<plan>")
    if dirty.is_err:
        return Err(dirty.danger_err)

    try:
        with _land_lock(root):
            return _land_plan_locked(
                root, worktree, dry_run=dry_run, check_ticks=check_ticks
            )
    except LandLockTimeout as exc:
        _log.error(
            "land --plan: refused -- %s (T-1515: the pre-T-1515 behavior "
            "was an unbounded blocking wait)",
            exc,
        )
        return Err(LandError.LandLockTimeout)


# frob:ticket T-1269
def _land_plan_pre_merge_sha(root: Path) -> Result[str, LandError]:
    """`root`'s current `HEAD` sha, resolved BEFORE `land_plan` merges
    anything (T-1269) -- the exact point a failed merge/finalize/TICK-
    check `git reset --hard`s back to."""
    return _rev_parse(root, "HEAD")


# frob:ticket T-1269
def _land_plan_merge_worktree(root: Path, worktree: Path) -> Result[str, LandError]:
    """Merge `worktree`'s current branch onto `root`'s current branch
    (T-1269): a plain `git merge --no-ff` (never a squash -- there is no
    single worked ticket to squash under, unlike `land`'s own per-ticket
    path), relying on the registered `tickets.md` git merge driver
    (docs/modules/tickets.md#git-merge-driver) for any ledger conflict the
    same way an ordinary `git merge`/`pull` already would. `Err
    (MergeConflict)` (after `git merge --abort`, since nothing is
    committed yet) on a real conflict; `Err(GitFailed)` on any other git
    failure. Returns the resulting merge commit sha on success."""
    branch = _rev_parse(worktree, "HEAD")
    if branch.is_err:
        return Err(branch.danger_err)
    worktree_sha = branch.danger_ok
    merged = run_argv(
        [
            "git",
            "-C",
            str(root),
            "merge",
            "--no-ff",
            "-m",
            "chore(tickets): land --plan",
            worktree_sha,
        ]
    )
    if merged.is_err or merged.danger_ok.returncode != 0:
        _abort_merge(root)
        _log.error(
            "land --plan: merging %s (%s) into %s produced a real "
            "conflict -- register the tickets.md merge driver "
            "(docs/modules/tickets.md#git-merge-driver) if this is a "
            "ledger-only conflict, or resolve by hand and retry",
            worktree,
            worktree_sha,
            root,
        )
        return Err(LandError.MergeConflict)
    return _rev_parse(root, "HEAD")


# frob:ticket T-1269
def _land_plan_finalize_drafts(
    root: Path,
) -> Result[tuple[tuple[str, str], ...], LandError]:
    """Finalize EVERY draft id now present in `root`'s merged ledger
    (T-1269), one `finalize_draft` call each (T-0162's existing allocator
    -- never a hand-assigned id), in a stable (sorted) order so a retry
    after an unwind is deterministic. `Err(NotFound)` (propagated from
    `finalize_draft`) on the first failure -- the caller resets `root`
    back to its pre-merge tip, so a partial finalize never survives."""
    from frob.tickets import finalize_draft, load_all

    loaded = load_all(root)
    if loaded.is_err:
        _log.error("land --plan: could not load %s's ledger after merge", root)
        return Err(LandError.GitFailed)
    draft_ids = sorted(tid for tid in loaded.danger_ok if is_draft_id(tid))
    finalized: list[tuple[str, str]] = []
    for draft_id in draft_ids:
        result = finalize_draft(root, draft_id)
        if result.is_err:
            _log.error(
                "land --plan: finalizing draft %s failed (%s) -- unwinding",
                draft_id,
                result.danger_err,
            )
            return Err(LandError.NotFound)
        finalized.append((draft_id, result.danger_ok))
    return Ok(tuple(finalized))


# frob:ticket T-1269
def _land_plan_commit_finalize(
    root: Path, finalized: tuple[tuple[str, str], ...]
) -> Result[None, LandError]:
    """Commit `finalize_draft`'s ledger (and any code-reference) rewrites
    (T-1269) -- `finalize_draft`/`renumber_one` write the tree but do not
    commit it themselves (the same "write, caller commits" convention
    `_wip_commit` already applies elsewhere in this package); a no-op
    (`Ok(None)`, nothing to commit) when `finalized` is empty, so a plan-
    land with no incoming draft ids stays a single (merge-only) commit."""
    if not finalized:
        return Ok(None)
    added = run_argv(["git", "-C", str(root), "add", "-A"])
    if added.is_err or added.danger_ok.returncode != 0:
        _log.error("land --plan: git add -A failed in %s", root)
        return Err(LandError.GitFailed)
    message = "chore(tickets): land --plan finalize " + ", ".join(
        f"{old} -> {new}" for old, new in finalized
    )
    committed = run_argv(["git", "-C", str(root), "commit", "-q", "-m", message])
    if committed.is_err or committed.danger_ok.returncode != 0:
        _log.error("land --plan: finalize commit failed in %s", root)
        return Err(LandError.CommitFailed)
    return Ok(None)


# frob:ticket T-1495
def _assert_reset_only_discards_own_commits(
    root: Path, base_sha: str, own_commits: Sequence[str]
) -> Result[None, LandError]:
    """T-1495 (the 2026-08-04 incident): before ANY `reset --hard` unwind,
    verify `root`'s CURRENT tip is exactly the last commit THIS run's own
    steps produced (`own_commits[-1]`, or `base_sha` itself if
    `own_commits` is empty -- nothing committed yet) -- refuse loudly
    (`Err(GitFailed)`, no reset performed) otherwise.

    Tip equality (not a commit-set diff) is deliberate: a `--no-ff` merge
    commit's SECOND parent chain (the worktree branch's own prior
    commits, e.g. a ticket-creation commit made before the merge ever
    ran) is legitimately part of THIS run's own merge, not a foreign
    interloper, even though those commits were authored in the worktree
    and are correctly reachable from `root`'s new tip once merged -- a
    naive `git rev-list base..HEAD` set-membership check flags them as
    "not one of ours" and refuses a perfectly safe unwind. Once this
    run's own last commit IS `root`'s current tip, nothing else could
    have committed anything further without moving that tip past it
    (git commits are immutable and refs only ever advance under a
    concurrent writer, never silently rewind) -- exactly
    `_verified_reset_root`'s (T-0907) existing tip-equality contract,
    generalized here to the EXPECTED FINAL tip a multi-commit run built
    up, not just its starting one. `land --plan`'s own unwind path
    (`_land_plan_reset_hard`) had NO check of any kind before T-1495 -- a
    foreign commit interleaved onto `root` AFTER this run's own last
    commit (another process's queue-drain land, a manual `frob ticket
    drop`) got silently discarded along with this run's own half-
    finished work on the very next failure-path unwind."""
    current = _rev_parse(root, "HEAD")
    if current.is_err:
        return Err(current.danger_err)
    expected_tip = own_commits[-1] if own_commits else base_sha
    if current.danger_ok == expected_tip:
        return Ok(None)
    _log.error(
        "land: refused to reset %s to %s -- current tip is %s but this "
        "run's own last commit was %s; something else moved %s's tip "
        "since (another process's land, a manual ledger commit) and "
        "resetting would silently destroy it (T-1495, the 2026-08-04 "
        "incident); NOT resetting -- inspect `git -C %s log --oneline "
        "%s..HEAD` by hand before retrying",
        root,
        base_sha,
        current.danger_ok,
        expected_tip,
        root,
        root,
        expected_tip,
    )
    return Err(LandError.GitFailed)


# frob:ticket T-1269
# frob:ticket T-1495
def _land_plan_reset_hard(
    root: Path, sha: str, *, own_commits: Sequence[str] = ()
) -> Result[None, LandError]:
    """`git reset --hard sha` in `root` (T-1269) -- the unwind primitive
    every `land_plan` failure path after a successful merge uses, so a
    finalize error or a dirty `check_ticks()` result never leaves a half-
    merged ledger or a partially-renumbered draft committed.

    T-1495: `own_commits` (the ordered shas THIS invocation's own steps
    committed since `sha`) is verified via
    `_assert_reset_only_discards_own_commits` BEFORE the reset runs --
    see that function's docstring for the incident this closes. Every
    caller now supplies its own accumulated commit list; an empty
    default preserves old behavior only for a caller with nothing of its
    own committed yet (the `_land_plan_pre_merge_sha`-adjacent early
    paths, where `sha` still equals `root`'s tip and there is nothing to
    verify). Returns the assertion's own `Result` so a refusal is visible
    to the caller instead of silently discarding nothing -- callers that
    treat this as a `LandError`-widening unwind must check `is_err`."""
    guarded = _assert_reset_only_discards_own_commits(root, sha, own_commits)
    if guarded.is_err:
        return guarded
    reset = run_argv(["git", "-C", str(root), "reset", "--hard", sha])
    if reset.is_err or reset.danger_ok.returncode != 0:
        _log.error(
            "land --plan: git reset --hard %s in %s FAILED -- manual "
            "recovery required (check `git status`/`git log` in %s)",
            sha,
            root,
            root,
        )
        return Err(LandError.GitFailed)
    return Ok(None)


# frob:ticket T-1495
def _land_plan_merge_and_finalize(
    root: Path, worktree: Path
) -> tuple[Result[tuple[str, tuple[tuple[str, str], ...]], LandError], list[str]]:
    """`_land_plan_locked`'s merge-then-finalize-drafts half (T-1495, split
    out to keep that function under the ARCH001 60-line threshold): merge
    `worktree` onto `root`, finalize every incoming draft, and return
    `(result, own_commits)` -- `result` is `Ok((merge_commit, finalized))`
    on success or the first `Err` hit; `own_commits` is THIS run's own
    commit shas accumulated SO FAR, in order (the merge commit once it
    exists, plus the finalize commit if one was made), returned
    ALONGSIDE `result` regardless of success or failure -- unlike a bare
    `Result`, a failure here does not lose track of a commit this run
    already made (e.g. the merge succeeded but finalize failed
    afterward), so the caller's `_land_plan_reset_hard` unwind still gets
    the right T-1495 unwind-boundary check even on this partial-failure
    path."""
    own_commits: list[str] = []
    merged = _land_plan_merge_worktree(root, worktree)
    if merged.is_err:
        return Err(merged.danger_err), own_commits
    merge_commit = merged.danger_ok
    own_commits.append(merge_commit)

    finalized = _land_plan_finalize_drafts(root)
    if finalized.is_err:
        return Err(finalized.danger_err), own_commits

    committed = _land_plan_commit_finalize(root, finalized.danger_ok)
    if committed.is_err:
        return Err(committed.danger_err), own_commits
    if finalized.danger_ok:
        # `_land_plan_commit_finalize` is a no-op unless `finalized` is
        # non-empty (its own docstring) -- HEAD now names this run's own
        # finalize commit.
        finalize_sha = _rev_parse(root, "HEAD")
        if finalize_sha.is_ok:
            own_commits.append(finalize_sha.danger_ok)

    return Ok((merge_commit, finalized.danger_ok)), own_commits


# frob:ticket T-1495
# frob:ticket T-1522
def _land_plan_unwind_after_merge(
    root: Path, pre_merge_sha: str, own_commits: Sequence[str]
) -> Result[None, LandError]:
    """T-1522: unwind a `land_plan` failure that happens AFTER the merge
    step (`_land_plan_merge_and_finalize`'s first own commit) WITHOUT ever
    discarding that merge commit itself -- see `_land_plan_locked`'s own
    T-1522 docstring note for the 2026-08-04 incident (T-1199/T-1200's
    already-merged content eaten by a later, unrelated failure in the SAME
    invocation) this closes. `own_commits[0]` (when present) is always the
    merge commit (`_land_plan_merge_and_finalize`'s own contract: it is
    the first entry appended, before the finalize commit if any) -- reset
    only as far as THAT, discarding anything committed after it
    (`own_commits[1:]`, e.g. a finalize commit), never further. When
    `own_commits` is empty (the merge step itself never produced a commit
    at all -- `_land_plan_merge_worktree` failed before committing), this
    degrades to the plain pre-T-1522 unwind straight back to
    `pre_merge_sha`, since there is nothing durable yet to preserve."""
    if not own_commits:
        return _land_plan_reset_hard(root, pre_merge_sha, own_commits=own_commits)
    merge_commit = own_commits[0]
    return _land_plan_reset_hard(root, merge_commit, own_commits=own_commits[1:])


# frob:ticket T-1495
# frob:ticket T-1522
def _land_plan_locked(
    root: Path,
    worktree: Path,
    *,
    dry_run: bool,
    check_ticks: Callable[[], bool | None] | None,
) -> Result[LandPlanReport, LandError]:
    """`land_plan`'s body (T-1269), run by the caller already holding
    `root`'s `_land_lock`: merge, finalize every draft, optionally re-check
    TICK-gate cleanliness, and -- for a real (non-dry-run) call -- leave
    the merge commit as `root`'s new tip. T-1495: every unwind path
    threads `own_commits` (`_land_plan_merge_and_finalize`'s own return)
    into `_land_plan_reset_hard`, refusing instead of discarding a foreign
    commit interleaved onto `root` mid-run -- see
    `_assert_reset_only_discards_own_commits`'s doc for the 2026-08-04
    incident this closes.

    T-1522: a failure AFTER the merge already succeeded (a finalize
    error, or `check_ticks()` reporting dirty) no longer resets all the
    way back to `pre_merge_sha` -- `_land_plan_unwind_after_merge` stops
    at the merge commit instead, so content this worktree branch already
    accumulated from OTHER, earlier tickets (a shared multi-ticket
    worktree's queue-drain shape) stays durably on `root` even when the
    finalize/TICK-gate step on top of it fails. `dry_run`'s own
    always-reset path is UNCHANGED by this -- a dry run is deliberately
    "run it, then always revert", not a failure path, so it still resets
    all the way back to `pre_merge_sha` regardless of outcome."""
    pre_merge = _land_plan_pre_merge_sha(root)
    if pre_merge.is_err:
        return Err(pre_merge.danger_err)
    pre_merge_sha = pre_merge.danger_ok

    merged_finalized, own_commits = _land_plan_merge_and_finalize(root, worktree)
    if merged_finalized.is_err:
        _land_plan_unwind_after_merge(root, pre_merge_sha, own_commits)
        return Err(merged_finalized.danger_err)
    merge_commit, finalized_ids = merged_finalized.danger_ok

    if check_ticks is not None:
        clean = check_ticks()
        if clean is False:
            _log.error(
                "land --plan: post-merge TICK gate re-check reported "
                "non-clean -- unwinding to the merge commit %s, keeping "
                "any queue-drained sibling content it already carries "
                "(T-1522)",
                merge_commit,
            )
            unwound = _land_plan_unwind_after_merge(root, pre_merge_sha, own_commits)
            return Err(
                unwound.danger_err if unwound.is_err else LandError.PlanTickGateDirty
            )

    return _land_plan_finish(
        root,
        pre_merge_sha,
        own_commits,
        merge_commit=merge_commit,
        finalized_ids=finalized_ids,
        dry_run=dry_run,
    )


# frob:ticket T-1560
def _land_plan_finish(
    root: Path,
    pre_merge_sha: str,
    own_commits: Sequence[str],
    *,
    merge_commit: str,
    finalized_ids: tuple[tuple[str, str], ...],
    dry_run: bool,
) -> Result[LandPlanReport, LandError]:
    """`_land_plan_locked`'s success tail: build the `LandPlanReport` and,
    for a dry run, always reset back to `pre_merge_sha` (a dry run is
    deliberately "run it, then always revert" -- see the caller's T-1522
    docstring note; this full reset is NOT the failure-path unwind, which
    stops at the merge commit)."""
    if dry_run:
        report = LandPlanReport(
            dry_run=True,
            merge_commit=merge_commit,
            finalized=finalized_ids,
            commit_sha=None,
        )
        unwound = _land_plan_reset_hard(root, pre_merge_sha, own_commits=own_commits)
        if unwound.is_err:
            return Err(unwound.danger_err)
        return Ok(report)

    final_sha = _rev_parse(root, "HEAD")
    return Ok(
        LandPlanReport(
            dry_run=False,
            merge_commit=merge_commit,
            finalized=finalized_ids,
            commit_sha=final_sha.danger_ok if final_sha.is_ok else merge_commit,
        )
    )


# frob:waive ARCH001 reason="already the decomposed orchestrator (T-0577): delegates to _land_precheck/_land_merge_stage/_reverify_evidence_post_merge/_land_finalize_and_close/_land_squash_apply; remaining length is the try/finally intent-marker sequencing plus the D-05/T-0456 ordering-rationale comments themselves, not undecomposed logic"  # noqa: E501
# frob:ticket T-0601
# frob:ticket T-0907
# frob:ticket T-1355
# frob:ticket T-1410
# frob:ticket T-1495
def _land_locked(
    root: Path,
    ticket_id: str,
    worktree: Path,
    *,
    dry_run: bool,
    collected: Callable[[], frozenset[str]] | None,
    passed: Callable[[Sequence[str]], frozenset[str]] | None,
    covers_scope: Callable[[Ticket], bool | None] | None,
    bump_version: Callable[[Path, Ticket, str], Result[str | None, LandError]] | None,
    rebuild_natives: Callable[[Path], bool] | None,
    sync_gate_rules: Callable[[Path, str], Result[tuple[str, ...] | None, LandError]]
    | None = None,
    check_gates: Callable[[], tuple[int, int, int] | None] | None = None,
    check_gate_findings: Callable[[], frozenset[tuple[str, str]] | None] | None = None,
    check_gate_claims: Callable[[Ticket], bool | None] | None = None,
    skip_mutation_evidence: bool = False,
    allow_cross_ticket: bool = False,
    pre_commit_sweep: Callable[[Path, str], bool | None] | None = None,
) -> Result[LandReport, LandError]:
    """`land`'s actual body (T-0577), run by the caller already holding
    `root`'s `ledger_lock` -- split out only so `land`'s docstring can state
    the locking contract once at the public entry point rather than
    interleaved with the implementation.

    T-0907: before anything else, reconciles a leftover land-repair marker
    for `ticket_id` (a prior `land()` against this same `root` that crashed
    mid-staging, see `_repair_stale_land_marker`'s own doc), then captures
    THIS run's own verified pre-mutation root tip (`root_pre_land_tip`) as
    a plain local value -- never re-derived from `root`'s possibly-stale
    `HEAD` later, and never stored in shared `.frob` state -- threaded
    through to `_land_squash_apply` (the only step that mutates `root`) so
    every unwind there resets to this exact sha instead of a bare `git
    reset --hard`."""
    repaired = _repair_stale_land_marker(root)
    if repaired.is_err:
        return Err(repaired.danger_err)

    root_pre_land_tip = _rev_parse(root, "HEAD")
    if root_pre_land_tip.is_err:
        return Err(root_pre_land_tip.danger_err)

    precheck = _land_precheck(
        root,
        worktree,
        ticket_id,
        covers_scope=covers_scope,
        skip_mutation_evidence=skip_mutation_evidence,
        allow_cross_ticket=allow_cross_ticket,
    )
    if precheck.is_err:
        return Err(precheck.danger_err)
    ticket, main_branch_name = precheck.danger_ok

    # T-0456: record that a multi-step land is starting BEFORE any of the
    # steps below mutate the worktree/root -- cleared in the `finally` below
    # on every exit (success or a clean, handled Err) so a marker that
    # OUTLIVES this process means it crashed mid-land, the condition `frob
    # ticket reconcile` surfaces as an anomaly instead of it going unnoticed.
    _write_intent(root, ticket_id, worktree)
    try:
        stage = _land_merge_stage(
            root, worktree, ticket, ticket_id, main_branch_name, dry_run
        )
        if stage.is_err:
            return Err(stage.danger_err)
        wip_committed, did_merge, dry_run_report = stage.danger_ok

        # T-0754 review round 2 fix #4: refresh the pre-work sweep BEFORE
        # any inner check runs `check_gates()` (a live `frob check
        # --ticket` spawn) -- landing can pull in unrelated main-side
        # commits that touch the ticket's scope globs, moving the sweep's
        # scope digest out from under it (see `_refresh_prework_sweep`'s
        # own doc, T-0236); done AFTER that check instead, `check_gates()`
        # would observe a stale-sweep PRE001 the Done report's captured
        # claim never carried, refusing the land on a false divergence.
        # Only for a REAL land (`dry_run_report is None` -- the exact same
        # condition the unconditional call below already required, since a
        # dry run always returns before reaching it): a dry run must still
        # leave the worktree exactly as found, and this call's write is
        # not itself unwound the way the merge commit is.
        if dry_run_report is None:
            _refresh_prework_sweep(worktree, ticket)

        # D-05: re-verify BEFORE the dry-run early return -- otherwise a
        # `--dry-run` would report clean without ever running the
        # post-merge check, defeating T-0176's "a clean dry run is a real
        # guarantee, not a guess" design intent.
        post_merge_check = _reverify_evidence_post_merge(
            worktree, ticket_id, collected, passed
        )
        if post_merge_check.is_err:
            if did_merge:
                _abort_merge(worktree)
            return Err(post_merge_check.danger_err)
        passing_ids = post_merge_check.danger_ok

        # T-0754: re-verify captured Done-report claims (test count, gate
        # state) against the SAME post-merge tree `post_merge_check` just
        # re-verified evidence against -- same ordering rationale (before
        # the dry-run early return, so `--dry-run` stays a real guarantee).
        # T-0754 review round 2 fix #3: the test-count half is DERIVED from
        # `passing_ids` (the exact set D-05's own `passed()` run just
        # computed above), never a second collect+run -- halves the real
        # cost of a `run_tests`-supplying land.
        claims_check = _reverify_done_report_claims_post_merge(
            worktree, ticket_id, passing_ids, check_gates, check_gate_findings
        )
        if claims_check.is_err:
            if did_merge:
                _abort_merge(worktree)
            return Err(claims_check.danger_err)

        # T-1410: re-verify any "0 <RULE> findings under <glob>" acceptance
        # criterion (`_gate_claim_criteria`) against the SAME post-merge
        # tree the checks above just verified against -- same ordering
        # rationale (before the dry-run early return). `check_gate_claims`
        # is given the reloaded post-merge ticket, mirroring `covers_scope`
        # 's own calling convention.
        if check_gate_claims is not None:
            from frob.tickets import _load_one

            reloaded = _load_one(worktree, ticket_id)
            if reloaded.is_err:
                _log.error(
                    "land: %s not found post-merge in %s -- cannot verify "
                    "T-1399 gate-claim criteria",
                    ticket_id,
                    worktree,
                )
                if did_merge:
                    _abort_merge(worktree)
                return Err(LandError.NotFound)
            if check_gate_claims(reloaded.danger_ok) is False:
                _log.error(
                    "land: %s carries an acceptance criterion asserting a "
                    "package-wide gate outcome that the live post-merge "
                    "tree does not establish -- refusing to land (T-1276 "
                    "class defect, see WARNING lines above for which "
                    "criterion/finding)",
                    ticket_id,
                )
                if did_merge:
                    _abort_merge(worktree)
                return Err(LandError.ClaimDivergence)

        if dry_run_report is not None:
            return Ok(dry_run_report)

        finalized = _land_finalize_and_close(
            root,
            worktree,
            ticket_id,
            did_merge,
            main_branch_name,
            covers_scope=covers_scope,
        )
        if finalized.is_err:
            return Err(finalized.danger_err)
        final_id = finalized.danger_ok

        # T-0907: the land-repair marker is written right before the ONLY
        # step that mutates `root` (`_land_squash_apply`) and cleared in
        # this inner `finally` on any exit -- an uncatchable SIGKILL
        # between these two points leaves the marker for
        # `_repair_stale_land_marker` to reconcile on the NEXT `land()`
        # call, closing the "leave an explicit marker the next invocation
        # repairs" half of the T-0907 fix requirement.
        _write_land_repair_marker(root, ticket_id, root_pre_land_tip.danger_ok)
        try:
            return _land_squash_apply(
                root,
                worktree,
                ticket,
                ticket_id,
                final_id,
                wip_committed,
                did_merge,
                main_branch_name,
                pre_land_tip=root_pre_land_tip.danger_ok,
                bump_version=bump_version,
                rebuild_natives=rebuild_natives,
                sync_gate_rules=sync_gate_rules,
                pre_commit_sweep=pre_commit_sweep,
            )
        finally:
            _clear_land_repair_marker(root, ticket_id)
    finally:
        _clear_intent(root, ticket_id)


def _refuse_if_main_dirty(
    root: Path, worktree: Path, ticket_id: str
) -> Result[None, LandError]:
    """`Err(DirtyMain)` if `root` has any uncommitted change.

    Tolerates one specific shape of "dirty" without refusing (T-0793):
    `uv.lock`'s frob-version line flapping on its own, with nothing else
    in the tree touched, from a prior `uv run`/`uv lock` invocation
    against a pyproject a sibling land already bumped. That case is
    auto-restored (`git checkout -- uv.lock`) before the dirty check is
    re-evaluated, rather than refusing the land -- any OTHER dirt (a real
    lock change, any other file) is left alone and still refuses exactly
    as before."""
    main_dirty = _porcelain_dirty(root)
    if main_dirty.is_err:
        return Err(main_dirty.danger_err)
    if main_dirty.danger_ok and _restore_lock_version_only_drift(root):
        _log.info(
            "land: %s auto-restored a uv.lock frob-version-only drift in "
            "%s before the DirtyMain check (T-0793)",
            ticket_id,
            root,
        )
        main_dirty = _porcelain_dirty(root)
        if main_dirty.is_err:
            return Err(main_dirty.danger_err)
    if main_dirty.danger_ok:
        _log.error(
            "land: %s refused -- %s has uncommitted changes; commit or stash "
            "them first (git -C %s status), then retry `frob ticket land %s "
            "--worktree %s`",
            ticket_id,
            root,
            root,
            ticket_id,
            worktree,
        )
        return Err(LandError.DirtyMain)
    return Ok(None)


# frob:ticket T-0795
# frob:ticket T-1003
# frob:tests tests/test_ticket_land.py::TestLandChainedCdRootResolution.test_root_equal_to_a_real_linked_worktree_resolves_and_lands kind="integration"  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestLandChainedCdRootResolution.test_root_equal_to_the_primary_checkout_itself_still_refuses kind="integration"  # noqa: E501
def _resolve_primary_checkout(worktree: Path) -> Path | None:
    """The primary checkout for `worktree`'s clone -- the parent directory
    of `git -C worktree rev-parse --git-common-dir` -- or `None` if that
    git call fails (an unreadable/non-git path; the caller then leaves
    `root` unchanged and downstream checks handle it exactly as before
    this ticket).

    Every git worktree (linked or primary) shares ONE common `.git` dir,
    owned by the primary checkout; `--git-common-dir` is git's own,
    authoritative answer to "where is that," regardless of which worktree
    the command runs from or what the caller's cwd happens to be -- this
    is what lets `land` (T-1003, churn item 4) resolve the true root from
    `worktree` alone, without the caller needing to know or pass it. A
    PRIMARY checkout's own common dir is simply its own `.git`, so calling
    this on a primary checkout returns that same checkout back unchanged
    (the genuinely-no-worktree case `_refuse_if_root_is_worktree` still
    needs to catch)."""
    common_dir = run_argv(["git", "-C", str(worktree), "rev-parse", "--git-common-dir"])
    if common_dir.is_err or common_dir.danger_ok.returncode != 0:
        return None
    raw = common_dir.danger_ok.stdout.strip()
    if not raw:
        return None
    common_dir_path = Path(raw)
    resolved = (
        common_dir_path.resolve()
        if common_dir_path.is_absolute()
        else (worktree / common_dir_path).resolve()
    )
    return resolved.parent


# frob:waive DUP001 reason="T-1186 split-induced false positive: the DUP001 template \
# similarity heuristic matches this guard clause against frob.serve.__getattr__ and \
# frob.strata._threat._flow_completeness_gap purely on control-flow shape (an \
# early-return equality check) -- neither shares this function's domain (refusing a \
# land whose root/worktree paths chain to the same checkout); this function's file \
# location did not move in T-1186, but the split changed which OTHER symbols in this \
# module the DUP scan pairs it against, surfacing a pre-existing pairing freshly"
def _refuse_if_root_is_worktree(
    root: Path, worktree: Path, ticket_id: str
) -> Result[None, LandError]:
    """`Err(IncompleteLand)`, logged with the ACTUAL mistake named, if
    `root` and `worktree` (both already `.resolve()`d by `land`) are the
    identical path (T-0795).

    Before this check, that exact condition (root == worktree) fell
    through all the way to `_worktree_full_changeset`'s much later T-0640/
    T-0761 diagnosis ("`--worktree` almost certainly points at the SAME
    checkout/branch `root` has checked out ... create a real feature
    branch") -- correct for a worktree genuinely pointed at the wrong
    branch, but misleading for the far more common real cause: `root`
    defaults to `cfg.ticket_path or Path(".")` (the invoker's CWD), so
    running `frob ticket land <id> --worktree <path>` from A SHELL SITTING
    INSIDE THE WORKTREE (rather than the shared root checkout) makes
    `root` resolve to `worktree` for free, no misconfigured `--worktree`
    involved. Refusing here, before `_land_merge_stage` runs any git
    mutation, names the actual mistake immediately instead of sending an
    agent chasing the T-0640 "create a real feature branch" remedy for a
    worktree that was never the problem. Reuses `LandError.IncompleteLand`
    (no new enum variant -- both are "this land cannot proceed as
    configured, nothing was committed" outcomes; the log message, not the
    enum tag, carries the corrected diagnosis) rather than the true-
    same-branch check (`_worktree_full_changeset`'s merge-base-equals-HEAD
    test), which still fires unchanged for a distinct-but-branchless
    worktree path further down the pipeline."""
    if root != worktree:
        return Ok(None)
    _log.error(
        "land: %s refused -- root (%s) and --worktree (%s) resolve to the "
        "IDENTICAL path. This is almost always caused by running `frob "
        "ticket land` from a shell whose cwd is INSIDE the worktree "
        "(`root` defaults to cwd) rather than a --worktree pointed at the "
        "wrong branch. Run `frob ticket land %s --worktree %s` from the "
        "ROOT checkout instead -- cd out of %s first, then retry",
        ticket_id,
        root,
        worktree,
        ticket_id,
        worktree,
        worktree,
    )
    return Err(LandError.IncompleteLand)


# frob:ticket T-1323
def _check_uncommitted_waive_deletions(
    worktree: Path, ticket: Ticket, ticket_id: str
) -> Result[None, LandError]:
    """`Err(OutOfScopeWaiveDeletion)` if `worktree`'s UNCOMMITTED changes
    (against `HEAD`, before `_wip_commit` ever runs) delete a `frob:waive`
    directive whose file is neither in `ticket.scope` nor named/declared in
    `ticket.body`'s Done report -- the 2026-07-29 incident's own
    laundering path: a wip-snapshot commit folds unattributed uncommitted
    edits into the merge, and nothing before this check ever inspected
    what a wip-commit was ABOUT to capture. Runs at `_land_precheck` time,
    strictly before any git mutation (`_wip_commit`/`_merge_main_into_
    worktree`), so the refusal fires with the worktree still dirty and
    untouched -- nothing to unwind, unlike `_check_unowned_deletions`
    (which necessarily runs post-merge and aborts a staged merge on
    refusal)."""
    found = _uncommitted_out_of_scope_waive_deletions(worktree, ticket)
    if found.is_err:
        return Err(found.danger_err)
    if found.danger_ok:
        _log.error(
            "land: %s refused -- worktree has uncommitted frob:waive "
            "deletion(s) outside scope %s and undeclared by the Done "
            "report: %s. If intentional, add the file to the ticket's "
            "scope or name it/the rule in the Done report; if accidental, "
            "restore it: cd %s && git checkout -- <file> ; then retry "
            "`frob ticket land %s --worktree %s`",
            ticket_id,
            list(ticket.scope),
            [f"{file}:{rule}" for file, rule in found.danger_ok],
            worktree,
            ticket_id,
            worktree,
        )
        return Err(LandError.OutOfScopeWaiveDeletion)
    return Ok(None)


# frob:ticket T-1326
def _check_committed_waive_deletions(
    worktree: Path, ticket: Ticket, ticket_id: str, main_branch: str
) -> Result[None, LandError]:
    """`Err(OutOfScopeWaiveDeletion)` if `worktree`'s branch history --
    `git diff <merge-base>..HEAD`, i.e. commits ALREADY made on the
    ticket's branch, not merely uncommitted worktree state -- deletes a
    `frob:waive` directive whose file is neither in `ticket.scope` nor
    declared by `ticket.body`'s Done report. Extends `_check_uncommitted_
    waive_deletions` (T-1323) to close the reviewer-flagged laundering gap
    left open at that ticket's approval: a `frob:waive` deletion COMMITTED
    mid-ticket (an agent's own `git commit`, a tool, an earlier wip-commit
    from a prior land attempt on this same branch) was invisible to a
    check that only ever inspected `git diff HEAD`, so it rode the merge
    in unattributed exactly like the uncommitted case T-1323 closed.

    Runs at `_land_precheck` time, strictly before any git mutation.
    `_true_merge_base(worktree, main_branch)` is still resolved here for
    the refusal log line's own "commits since merge-base" context, but
    (T-1550) the deletion scan itself is diffed against `main_branch`'s
    LIVE tip, not this stale merge-base: on a shared multi-ticket
    worktree, `merge_base..HEAD` still contains every commit an
    already-landed SIBLING ticket made on this same branch, including any
    `frob:waive` deletion it committed -- re-diffing from the original
    merge-base re-discovers that already-landed deletion and re-attributes
    it to whichever ticket lands next (T-1225, T-1444's re-declare-round
    incidents). A deletion already reflected on `main_branch` (because the
    sibling's own land already squash-applied it there) shows no delta at
    all against the live tip, so it is structurally excluded without any
    ancestry walk or commit-to-ticket attribution -- see
    `_committed_waive_deletions`'s own T-1550 docstring note. A
    `frob:waive` line deleted on main's own unrelated history (main
    dropped the waiver on ITS branch, never touched by this ticket) is
    likewise never in `main_branch..HEAD` at all (both sides already
    agree) and is correctly NOT counted against the landing ticket."""
    merge_base = _true_merge_base(worktree, main_branch)
    if merge_base.is_err:
        return Err(merge_base.danger_err)
    found = _committed_out_of_scope_waive_deletions(worktree, ticket, main_branch)
    if found.is_err:
        return Err(found.danger_err)
    if found.danger_ok:
        _log.error(
            "land: %s refused -- branch history (commits since merge-base "
            "%s) contains frob:waive deletion(s) outside scope %s and "
            "undeclared by the Done report: %s. If intentional, add the "
            "file to the ticket's scope or name it/the rule in the Done "
            "report; if accidental, revert the offending commit on this "
            "branch before retrying `frob ticket land %s --worktree %s`",
            ticket_id,
            merge_base.danger_ok,
            list(ticket.scope),
            [f"{file}:{rule}" for file, rule in found.danger_ok],
            ticket_id,
            worktree,
        )
        return Err(LandError.OutOfScopeWaiveDeletion)
    return Ok(None)


def _validate_scope_covered_preflight(
    ticket: Ticket, covers_scope: Callable[[Ticket], bool | None] | None
) -> Result[None, LandError]:
    """`Err(NotCloseable)` if `covers_scope(ticket)` answers `False` against
    the PRE-merge worktree ticket (T-0774): D-05's `covers_scope` callable
    was previously only ever invoked POST-merge (`_land_finalize_and_close`,
    against the graph rebuilt from the just-merged tree, after `git commit`
    had already made a merge commit) -- correct for the graph itself
    (`frob.gates` needs the post-merge tree to know what actually landed),
    but it left a residual fail-after-merge class T-0763's acceptance/
    evidence preflight did not close: a ticket whose evidence is bound but
    does not cover its own scope still merged+committed before failing.

    Invoking the SAME callable again here, before `_land_merge_stage` ever
    runs `git merge`, is a PREFLIGHT SIMULATION against the pre-merge
    worktree tree, not a replacement for the post-merge re-check
    `_land_finalize_and_close` still performs unconditionally afterward --
    for the common case (the ticket's scope files are untouched by any
    concurrent main-side change), the pre-merge tree already answers the
    same D-02 scope-binding question, so a landing whose evidence does not
    cover its scope now refuses here, with git log unchanged on both sides,
    instead of only after a merge/finalize commit already exists. A
    concurrent main-side edit to a scope file between this preflight and
    the real merge can still only be caught by the existing post-merge
    check, which is untouched by this addition. `covers_scope=None` (skip,
    matching every caller before D-02) or a `True`/`None` answer leaves this
    preflight silent, exactly like the post-merge check's own tri-state
    contract (`_done_transition_guard`)."""
    if covers_scope is None:
        return Ok(None)
    if covers_scope(ticket) is False:
        _log.error(
            "land: %s cannot land -- no evidence id covers a touched/scope "
            "symbol (scope=%s); bind evidence to the uncovered scope "
            "(`frob ticket evidence %s <node-id>...`) and retry "
            "`frob ticket land %s`",
            ticket.id,
            list(ticket.scope),
            ticket.id,
            ticket.id,
        )
        return Err(LandError.NotCloseable)
    return Ok(None)


# frob:ticket T-1518
# frob:tests tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd.test_close_refuses_when_evidence_passes_at_parent  # noqa: E501
# frob:tests tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd.test_close_succeeds_when_evidence_fails_at_parent  # noqa: E501
def _check_mutation_evidence(
    worktree: Path,
    ticket: Ticket,
    base_ref: str,
    *,
    skip: bool = False,
) -> Result[None, LandError]:
    """T-0755: run the diff-scoped adversarial evidence obligation
    (`frob.gates.mutation_evidence_violations`) against `ticket`'s current
    worktree tree, and (T-1427) the bug/security-kind repro-at-parent
    obligation (`frob.gates.bug_repro_violations`, BUG002, T-1421) --
    complementary, not duplicative: TEST016 proves the diff is
    mutation-detectable by its own bound evidence, BUG002 proves that same
    evidence actually fails on the commit BEFORE the fix, closing the
    "mutation-detectable but nothing calls it" gap TEST016 cannot see.
    Both feed the SAME error/warn accounting and the SAME
    `--skip-mutation-evidence` escape hatch below -- no parallel mechanism.

    T-1575: if `frob.tickets._profile.effective_profile(worktree)` reads
    `rapid`, TEST016 is skipped ENTIRELY -- no synchronous mutation
    subprocess for any kind (including `security`) and no deferred sweep
    entry -- per that ticket's own "no TEST016 on the land path" text.
    BUG002 is unaffected by the profile and still runs/blocks for bug/
    security kind regardless.

    T-1518 narrowed the SYNCHRONOUS half of this obligation (the actual
    mutation subprocess, `mutation_evidence_violations`/TEST016) to
    `security`-kind tickets only (`frob.tickets._mutation_sweep_queue.
    SYNC_BLOCKING_KINDS`) -- the most expensive, least incremental land
    stage, whose marginal value is test-strength validation, not main-
    correctness. A `security`-kind ticket whose bound evidence killed zero
    mutants (TEST016 at ERROR severity, see `frob.gates._mutation_evidence`'s
    module docstring for why that severity split, not the ratchet-pool
    mechanism, is the right tool here) still REFUSES the land inline -- the
    same "knowable before any git mutation" posture `_validate_closeable`
    and `_validate_scope_covered_preflight` already hold. Every OTHER
    kind's TEST016 obligation is deferred entirely: `_check_mutation_
    evidence` enqueues a `mutation_sweep_queue.SweepEntry` instead of
    running the subprocess inline, and a later batch pass (`mutation_
    sweep_queue.run_pending_sweep`, driven from the merge-queue drain
    cadence, T-1444) evaluates it retroactively -- a bug-kind finding
    there files a new ticket against the offending land rather than
    refusing it after the fact (see that module's own docstring). BUG002
    (`bug_repro_violations`) is UNCHANGED by this ticket -- it stays
    synchronous and ERROR-always for bug/security kind, since it is cheap
    (re-runs already-bound evidence against a single prior commit, no
    mutation subprocess) and proves a different, complementary property
    (the fix actually fixes something) than TEST016's "is this evidence
    adversarial" question.

    `skip=True` (T-0755 reviewer round 2, `frob ticket land
    --skip-mutation-evidence`) is the documented escape hatch for the
    still-synchronous `security`-kind path: the check still RUNS (so its
    findings are still logged and visible) but never refuses the land.
    Every use is logged at WARNING naming the ticket, so a bypass always
    leaves a trail -- this is for a genuinely false-positive finding (e.g.
    a mutation-testing gap the reviewer has not yet closed), never a
    silent way to wave through real confirmatory evidence.

    T-1593: the profile/kind DECISION (does this ticket owe a synchronous
    mutation subprocess at all) is split into `_mutation_evidence_sync_
    decision` below; the deferred and synchronous evidence paths are
    `_mutation_evidence_deferred`/`_mutation_evidence_synchronous`. This
    function is now purely the dispatch between them -- pure extraction,
    same call order and return values as before the split."""
    rapid, owes_sync = _mutation_evidence_sync_decision(worktree, ticket)
    if not owes_sync:
        return _mutation_evidence_deferred(worktree, ticket, base_ref, rapid)
    return _mutation_evidence_synchronous(worktree, ticket, base_ref, skip)


# frob:ticket T-1593
def _mutation_evidence_sync_decision(
    worktree: Path, ticket: Ticket
) -> tuple[bool, bool]:
    """Decision half of `_check_mutation_evidence` (T-1593 split): whether
    `worktree` is under T-1575's rapid profile, and whether `ticket` owes a
    SYNCHRONOUS mutation subprocess at all (T-1518's `SYNC_BLOCKING_KINDS`
    narrowing) -- returns `(rapid, owes_sync)`. `owes_sync=False` routes
    the caller to the deferred-sweep path instead of running the
    subprocess inline; mirrors the original inline
    `rapid or ticket.kind not in SYNC_BLOCKING_KINDS` condition exactly
    (owes_sync is the negation of that condition)."""
    from frob.tickets._mutation_sweep_queue import SYNC_BLOCKING_KINDS
    from frob.tickets._profile import ProfileName, effective_profile

    profile = effective_profile(worktree)
    rapid = profile.is_ok and profile.danger_ok is ProfileName.RAPID
    if rapid:
        _log.info(
            "land: %s TEST016 skipped entirely (mutation subprocess AND "
            "the deferred batch sweep) -- effective profile is rapid "
            "(T-1575); BUG002 is unaffected and still runs",
            ticket.id,
        )
    owes_sync = (not rapid) and ticket.kind in SYNC_BLOCKING_KINDS
    return rapid, owes_sync


# frob:ticket T-1593
def _mutation_evidence_deferred(
    worktree: Path, ticket: Ticket, base_ref: str, rapid: bool
) -> Result[None, LandError]:
    """Deferred half of `_check_mutation_evidence` (T-1593 split): enqueue
    a `mutation_sweep_queue.SweepEntry` for the later batch pass (skipped
    entirely under `rapid`, per T-1575) and still run/classify BUG002
    synchronously regardless of profile -- pure extraction of the original
    `if rapid or ticket.kind not in SYNC_BLOCKING_KINDS:` branch body,
    unchanged."""
    from frob.gates import bug_repro_violations
    from frob.tickets._mutation_sweep_queue import enqueue_pending_sweep

    if not rapid:
        enqueued = enqueue_pending_sweep(worktree, ticket.id, base_ref, ticket.kind)
        if enqueued.is_err:
            _log.warning(
                "land: %s failed to enqueue a deferred TEST016 sweep "
                "(%s) -- TEST016 will not be evaluated for this land "
                "at all until this is investigated",
                ticket.id,
                enqueued.danger_err,
            )
    bug002_only = bug_repro_violations(worktree, ticket, base_ref)
    errors = [v for v in bug002_only if v.severity == "error"]
    for v in bug002_only:
        _log.warning("land: %s %s %s", ticket.id, v.rule, v.message)
    if errors:
        _log.error(
            "land: %s cannot land -- %d BUG002 finding(s) (kind=%s); "
            "TEST016 was deferred to the batch mutation sweep, BUG002 "
            "is unaffected and still blocks",
            ticket.id,
            len(errors),
            ticket.kind,
        )
        return Err(LandError.EvidenceConfirmatoryOnly)
    return Ok(None)


# frob:ticket T-1593
def _mutation_evidence_synchronous(
    worktree: Path, ticket: Ticket, base_ref: str, skip: bool
) -> Result[None, LandError]:
    """Synchronous half of `_check_mutation_evidence` (T-1593 split): run
    the actual TEST016 mutation subprocess plus BUG002 and classify the
    result, including the `--skip-mutation-evidence` override -- pure
    extraction of the original `else` branch body, unchanged."""
    from frob.gates import bug_repro_violations, mutation_evidence_violations

    violations = mutation_evidence_violations(
        worktree, ticket, base_ref
    ) + bug_repro_violations(worktree, ticket, base_ref)
    if not violations:
        return Ok(None)
    errors = [v for v in violations if v.severity == "error"]
    for v in violations:
        _log.warning("land: %s %s %s", ticket.id, v.rule, v.message)
    if errors and skip:
        _log.warning(
            "land: %s --skip-mutation-evidence set -- %d ERROR-severity "
            "TEST016 finding(s) logged above are NOT blocking this land "
            "(justification required: this bypass is for a genuinely "
            "false-positive finding, never a way to wave through real "
            "confirmatory evidence)",
            ticket.id,
            len(errors),
        )
        return Ok(None)
    if errors:
        _log.error(
            "land: %s cannot land -- %d confirmatory-only evidence finding(s) "
            "at ERROR severity (kind=%s); remedies: (1) strengthen the "
            "named evidence tests so at least one fails on a mutant of the "
            "changed lines (see the TEST016 lines above for exact "
            "file:line + mutation), then retry `frob ticket land %s`; or "
            "(2) if this is a genuine false positive, retry with `frob "
            "ticket land %s --skip-mutation-evidence` (logs a loud, "
            "justification-required override, does not suppress the "
            "finding)",
            ticket.id,
            len(errors),
            ticket.kind,
            ticket.id,
            ticket.id,
        )
        return Err(LandError.EvidenceConfirmatoryOnly)
    return Ok(None)


def _check_live_tracker_citations(
    worktree: Path, ticket: Ticket, base_ref: str
) -> Result[None, LandError]:
    """T-0854: refuse to land while a registry `deferred:`/`tracked_by:`
    disposition or a waiver `ticket=` attribute in `worktree`'s tree still
    cites `ticket.id` as its live tracker, AND that exact citation already
    existed unchanged at `base_ref` (`frob.tickets._live_tracker.
    live_tracker_citations`'s diff-aware grep-shaped scan, T-0854 rework)
    -- the T-0605-orphaned-41-rows incident class, caught BEFORE the merge
    that makes those citations stale, not one `frob check` later. A
    citation this same diff freshly introduces (never present at
    `base_ref`) is not reported -- see the T-0854 rework note in
    `frob.tickets._live_tracker`'s module docstring for why a scope-based
    exemption was rejected as gameable in favor of this diff-aware one."""
    from frob.tickets._live_tracker import live_tracker_citations

    citations = live_tracker_citations(worktree, ticket.id, base_ref=base_ref)
    if not citations:
        return Ok(None)
    _log.error(
        "land: %s cannot land -- %d site(s) still cite it as their live "
        "tracker (registry deferred:/tracked_by: disposition or a waiver "
        "ticket= attribute): %s -- file a successor ticket and re-point "
        "these rows, or re-point them in this same change, then retry "
        "`frob ticket land %s`",
        ticket.id,
        len(citations),
        list(citations),
        ticket.id,
    )
    return Err(LandError.LiveTrackerCited)


# frob:ticket T-1355
def _branch_changed_files(
    worktree: Path, base_ref: str
) -> Result[frozenset[str], LandError]:
    """The set of paths `worktree`'s current branch has committed changes
    to since it diverged from `base_ref` (T-1355), via `git diff --name-
    only <base_ref>...HEAD` (three-dot: the merge-base diff, so a
    worktree that has since merged `base_ref` back in does not report
    every file `base_ref` itself touched). `Err(GitFailed)` on a git
    failure; an empty set (never an error) when the branch has committed
    nothing new."""
    diffed = run_argv(
        ["git", "-C", str(worktree), "diff", "--name-only", f"{base_ref}...HEAD"]
    )
    if diffed.is_err or diffed.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    return Ok(
        frozenset(
            line.strip()
            for line in diffed.danger_ok.stdout.splitlines()
            if line.strip()
        )
    )


# frob:ticket T-1390
def _ledger_ticket_at_merge_base(
    worktree: Path, base_ref: str, ticket_id: str
) -> Ticket | None:
    """`ticket_id`'s ticket record as it existed in `worktree`'s ledger at
    the point `worktree`'s branch actually DIVERGED from `base_ref` (T-1390)
    -- `git merge-base base_ref HEAD`, not `base_ref` itself, so a
    worktree that has since `git merge`d `base_ref` back in (agent-
    playbook.md section 1b's sanctioned mid-ticket sync) is compared
    against the true fork point, not whatever `base_ref` has advanced to
    since. Returns `None` when the ref/ledger is unreadable or the id did
    not exist there yet (a ticket created fresh on this branch has no
    prior record to compare against, so any scope-matching hit against it
    is real work done here, never a false positive) -- the caller treats
    `None` the same as "changed" (fail toward still flagging a candidate
    leak, never toward silently clearing one)."""
    from frob.tickets._store import _parse_ledger

    merge_base = run_argv(["git", "-C", str(worktree), "merge-base", base_ref, "HEAD"])
    if merge_base.is_err or merge_base.danger_ok.returncode != 0:
        return None
    sha = merge_base.danger_ok.stdout.strip()
    if not sha:
        return None
    shown = run_argv(["git", "-C", str(worktree), "show", f"{sha}:tickets.md"])
    if shown.is_err or shown.danger_ok.returncode != 0:
        return None
    parsed = _parse_ledger(shown.danger_ok.stdout)
    if parsed.is_err:
        return None
    return parsed.danger_ok.get(ticket_id)


# frob:ticket T-1390
def _leaked_hits_for_candidate(
    worktree: Path,
    landing_id: str,
    other_id: str,
    other: Ticket,
    changed_paths: frozenset[str],
    base_ref: str,
) -> list[str] | None:
    """The sorted hit-path list for ONE candidate sibling `other_id`, or
    `None` if it is not actually leaked (T-1390: split out of `_find_
    leaked_tickets` to keep that function's own per-candidate exemption
    logic readable and under ARCH001's line threshold, zero behavior
    change to any exemption's own semantics) -- exempts a sibling leased
    to the SAME worktree as `landing_id` (T-1370), then requires BOTH a
    declared-`scope` hit against `changed_paths` AND `other`'s own ledger
    record to have actually changed since this branch forked from
    `base_ref` (T-1390, via `_ledger_ticket_at_merge_base`) -- a scope hit
    alone is never enough; see `_find_leaked_tickets`'s own docstring for
    the false-positive class this second requirement closes."""
    from frob.tickets._models import scope_matches
    from frob.tickets._scope import _same_worktree_lease

    if _same_worktree_lease(worktree, landing_id, other_id):
        _log.info(
            "land: %s cross-ticket leakage check exempting %s "
            "(T-1370: both tickets are leased to the same worktree "
            "-- one agent landing its own tickets back to back, not "
            "a real cross-agent leak)",
            landing_id,
            other_id,
        )
        return None
    hits = [
        path
        for path in changed_paths
        if scope_matches(path, other.scope, kind=other.kind)
    ]
    if not hits:
        return None
    base_ticket = _ledger_ticket_at_merge_base(worktree, base_ref, other_id)
    if base_ticket is not None and base_ticket == other:
        _log.info(
            "land: %s cross-ticket leakage check exempting %s (T-1390: "
            "its ledger record is unchanged since this branch forked "
            "from %s -- its declared scope matches %d changed path(s), "
            "but it was never actually worked on this branch)",
            landing_id,
            other_id,
            base_ref,
            len(hits),
        )
        return None
    return sorted(hits)


# frob:ticket T-1355
# frob:ticket T-1370
# frob:ticket T-1390
def _find_leaked_tickets(
    worktree: Path,
    landing_id: str,
    worktree_tickets: dict[str, Ticket],
    root_tickets: dict[str, Ticket],
    changed_paths: frozenset[str],
    base_ref: str,
) -> dict[str, list[str]]:
    """The `{other_ticket_id: [leaked_path, ...]}` map `_check_cross_
    ticket_leakage` refuses on (T-1355: split out to keep the parent under
    ARCH001's line threshold, zero behavior change) -- every OTHER ticket
    in `worktree_tickets` that is still open (root's copy of it, when
    root already knows the id, is the AUTHORITATIVE state -- a ticket
    landed done through its own separate `frob ticket land` call is
    terminal even if this worktree's pre-pull copy still shows it
    in-progress), whose declared `scope` matches at least one path in
    `changed_paths`, AND whose own ledger record has actually CHANGED on
    this branch since it forked from `base_ref` (T-1390, both checked by
    `_leaked_hits_for_candidate`, one candidate at a time).

    T-1390: declared `scope` is an intention, not evidence that a sibling
    ticket's work is actually present on this branch -- measured across a
    real session, siblings that merely declare a broad scope (`src/**`,
    `tests/**`) matched almost every land's changed files even though
    they never contributed a single commit here, forcing
    `allow_cross_ticket=True` on every single land (the exact
    reflex-override habit this guard exists to prevent). The added
    signal: has `other`'s OWN ledger record actually moved since this
    branch forked (`_ledger_ticket_at_merge_base`)? A sibling ticket that
    genuinely got worked ON THIS BRANCH (the real T-1352/T-1276 shape --
    started, evidence recorded, Done report written, all via the ticket
    CLI, all of which rewrite its ledger block) always leaves that trail;
    an unrelated ticket sitting open elsewhere, never touched here, does
    not -- its record at the fork point and its record now are byte-
    identical. A ticket record identical since the fork is skipped even
    if its declared scope happens to match a changed path.

    T-1370: a sibling ticket LEASED TO THE SAME WORKTREE as `landing_id`
    (`_scope._same_worktree_lease`, the exact T-1356 precedent this
    mirrors) is never reported as leaked, no matter its state -- two
    tickets sharing one series worktree is one agent landing its own
    tickets back to back, not a real cross-agent leak. Without this, two
    open siblings in the same worktree whose scopes overlap mutually
    deadlock: landing either one refuses because the other is still
    open, and there is no way to land either first."""
    from frob.tickets._models import TicketState

    leaked: dict[str, list[str]] = {}
    for other_id, other in worktree_tickets.items():
        if other_id == landing_id:
            continue
        effective_state = (
            root_tickets[other_id].state if other_id in root_tickets else other.state
        )
        if effective_state in (TicketState.DONE, TicketState.DROPPED):
            continue
        if not other.scope:
            continue
        hits = _leaked_hits_for_candidate(
            worktree, landing_id, other_id, other, changed_paths, base_ref
        )
        if hits:
            leaked[other_id] = hits
    return leaked


# frob:ticket T-1355
def _check_cross_ticket_leakage(
    root: Path,
    worktree: Path,
    ticket: Ticket,
    base_ref: str,
    *,
    allow_cross_ticket: bool = False,
) -> Result[None, LandError]:
    """Refuse (T-1355) when `worktree`'s branch has committed changes
    covered by a DIFFERENT ticket's declared `scope`, and that other
    ticket is still open (not `done`/`dropped`) on `root`'s ledger --
    the incident class where landing one ticket out of a multi-ticket
    series worktree silently carries a sibling's still-open work onto
    main (T-1352's land of worktree t-1276 carrying T-1276's own
    committed files while T-1276 stayed `in-progress`).

    Scans `_branch_changed_files(worktree, base_ref)` against every OTHER
    ticket in `worktree`'s CURRENT ledger -- deliberately the WORKTREE's
    copy, not `root`'s: a sibling ticket held open in the same series
    worktree (T-1276's shape) generally has NOT been landed yet, so it
    does not exist in `root`'s ledger at all until THIS land's own
    squash-splice merges it in; `worktree`'s ledger is the one place that
    already knows about it, pre-merge. Falls back to `root`'s ledger only
    if `worktree`'s is unreadable. Matching uses the shared `scope_matches`
    implementation -- the same one `frob.gates`' own SCOPE001/PRE001 checks
    use, so this can never drift from what "covered by that ticket's
    scope" means anywhere else in the codebase. A ticket with no declared
    `scope` at all matches nothing (an empty scope is never treated as
    "matches everything"). A scope-match ALONE is not enough to flag a
    ticket (T-1390): `_find_leaked_tickets` also requires the sibling's
    own ledger record to have actually changed on this branch since it
    forked from `base_ref` -- a declared scope is an intention, not
    evidence that the sibling's work is present here; only a ticket that
    was genuinely started/worked (its ledger block moved) on this exact
    branch counts as leaked.

    `allow_cross_ticket=True` is the escape hatch (T-1355, mirroring
    `skip_mutation_evidence`'s pattern) for a genuinely intentional
    landing (e.g. two tickets deliberately meant to land together in one
    commit) -- the check still RUNS and logs what it found, but does not
    refuse. Every use is logged at WARNING naming the ticket(s), so a
    bypass always leaves a trail. Any lookup failure (root's ledger
    unreadable) is logged and treated as `Ok(None)` -- this is an
    additional safety net on top of the existing scope/evidence gates,
    not a replacement for their own hard-fail paths if the ledger itself
    cannot be read."""
    from frob.tickets._models import LEDGER_PATH
    from frob.tickets._store import archive_path

    changed = _branch_changed_files(worktree, base_ref)
    if changed.is_err:
        return Err(changed.danger_err)
    # T-1355: the ledger (and its archive) is implicitly in EVERY ticket's
    # scope (`scope_matches`'s always-in-scope rule) and is expected to
    # change on every single land -- it is not "a sibling's own work",
    # and the ledger's own per-id splice already handles ticket state
    # correctly. Excluded here so a ledger-only diff never false-positives
    # this check against every other open ticket in the worktree.
    archive_rel = archive_path(worktree).relative_to(worktree).as_posix()
    relevant = frozenset(changed.danger_ok) - {LEDGER_PATH, archive_rel}
    if not relevant:
        return Ok(None)

    worktree_tickets, root_tickets = _load_leakage_ledgers(root, worktree, ticket.id)
    if worktree_tickets is None:
        return Ok(None)
    leaked = _find_leaked_tickets(
        worktree, ticket.id, worktree_tickets, root_tickets, relevant, base_ref
    )
    if not leaked:
        return Ok(None)

    return _report_leaked_tickets(
        ticket.id, leaked, allow_cross_ticket=allow_cross_ticket
    )


# frob:ticket T-1355
def _load_leakage_ledgers(
    root: Path, worktree: Path, ticket_id: str
) -> tuple[dict[str, Ticket] | None, dict[str, Ticket]]:
    """The ledger-loading half of `_check_cross_ticket_leakage` (T-1355:
    split out to keep the parent under ARCH001's line threshold, zero
    behavior change) -- `worktree`'s tickets (falling back to `root`'s if
    unreadable, `None` if NEITHER is readable) plus `root`'s tickets
    (empty dict if unreadable) for the caller's authoritative-state
    lookup."""
    from frob.tickets._store import load_all

    loaded = load_all(worktree)
    if loaded.is_err:
        loaded = load_all(root)
    if loaded.is_err:
        _log.debug(
            "land: %s cross-ticket leakage check skipped -- neither "
            "worktree's nor root's ledger is readable (%s)",
            ticket_id,
            loaded.danger_err,
        )
        return None, {}

    root_loaded = load_all(root)
    return loaded.danger_ok, (root_loaded.danger_ok if root_loaded.is_ok else {})


# frob:ticket T-1355
def _report_leaked_tickets(
    landing_id: str,
    leaked: dict[str, list[str]],
    *,
    allow_cross_ticket: bool,
) -> Result[None, LandError]:
    """Log every leaked-ticket hit and either return `Ok(None)`
    (`allow_cross_ticket=True`, with a WARNING trail) or `Err
    (LandError.CrossTicketLeakage)` (T-1355: split out of `_check_cross_
    ticket_leakage` to keep it under ARCH001's line threshold, zero
    behavior change)."""
    for other_id, paths in sorted(leaked.items()):
        _log.error(
            "land: %s branch carries %d file(s) covered by %s's own "
            "declared scope, and %s is still open on main -- landing "
            "would silently ship %s's work ahead of its own close: %s",
            landing_id,
            len(paths),
            other_id,
            other_id,
            other_id,
            paths,
        )
    if allow_cross_ticket:
        _log.warning(
            "land: %s allow_cross_ticket set -- the cross-ticket leakage "
            "above is NOT blocking this land (justification required: "
            "this is for a genuinely intentional joint landing, never a "
            "way to silently ship a sibling's held-back work)",
            landing_id,
        )
        return Ok(None)
    _log.error(
        "land: %s cannot land -- resolve by either dropping the leaked "
        "file(s) from this branch (commit them separately once the "
        "sibling ticket closes), or landing the sibling ticket(s) first, "
        "or -- if this joint landing is genuinely intentional -- passing "
        "the explicit override",
        landing_id,
    )
    return Err(LandError.CrossTicketLeakage)


# frob:ticket T-1326
def _load_ticket_for_land(worktree: Path, ticket_id: str) -> Result[Ticket, LandError]:
    """Load `ticket_id` from `worktree`'s store, run `_validate_closeable`,
    and run the uncommitted-waive-deletion check (T-1323) against it --
    split out of `_land_precheck` purely to keep that function under the
    ARCH001 line-count threshold once the T-1326 committed-history check
    was added alongside it."""
    from frob.tickets import _load_one

    loaded = _load_one(worktree, ticket_id)
    if loaded.is_err:
        _log.error("land: %s not found in worktree store at %s", ticket_id, worktree)
        return Err(LandError.NotFound)
    ticket = loaded.danger_ok

    validated = _validate_closeable(ticket)
    if validated.is_err:
        return Err(validated.danger_err)

    waive_deletion_check = _check_uncommitted_waive_deletions(
        worktree, ticket, ticket_id
    )
    if waive_deletion_check.is_err:
        return Err(waive_deletion_check.danger_err)

    return Ok(ticket)


# frob:ticket T-1326
def _resolve_main_branch_for_land(
    root: Path, worktree: Path, ticket: Ticket, ticket_id: str
) -> Result[str, LandError]:
    """Resolve `root`'s current branch name AND run `_check_committed_
    waive_deletions` against it -- split out of `_land_precheck` purely to
    keep that function under the ARCH001 line-count threshold; the two
    steps are inseparable (the committed-waiver check needs the resolved
    branch name to compute a true merge-base) so they are kept together
    here rather than split further."""
    main_branch = current_branch(root)
    if main_branch.is_err:
        return Err(LandError.GitFailed)
    committed_waive_deletion_check = _check_committed_waive_deletions(
        worktree, ticket, ticket_id, main_branch.danger_ok
    )
    if committed_waive_deletion_check.is_err:
        return Err(committed_waive_deletion_check.danger_err)
    return Ok(main_branch.danger_ok)


# frob:ticket T-1355
def _land_precheck(
    root: Path,
    worktree: Path,
    ticket_id: str,
    *,
    covers_scope: Callable[[Ticket], bool | None] | None = None,
    skip_mutation_evidence: bool = False,
    allow_cross_ticket: bool = False,
) -> Result[tuple[Ticket, str], LandError]:
    """Refuse on root/worktree being the same path (T-0795) or a dirty
    main, load+validate the worktree's ticket is closeable (including,
    T-0774, a `covers_scope` preflight simulation, T-0755's diff-scoped
    mutation-evidence obligation, bypassable via `skip_mutation_evidence`,
    T-0854's live-tracker-citation preflight, and T-1355's cross-ticket
    leakage preflight, bypassable via `allow_cross_ticket`), and resolve
    main's current branch name -- everything `land` must check BEFORE any
    git mutation."""
    same_path_check = _refuse_if_root_is_worktree(root, worktree, ticket_id)
    if same_path_check.is_err:
        return Err(same_path_check.danger_err)

    dirty_check = _refuse_if_main_dirty(root, worktree, ticket_id)
    if dirty_check.is_err:
        return Err(dirty_check.danger_err)

    loaded_ticket = _load_ticket_for_land(worktree, ticket_id)
    if loaded_ticket.is_err:
        return Err(loaded_ticket.danger_err)
    ticket = loaded_ticket.danger_ok

    # T-1326: main_branch is resolved here, ahead of its original position
    # further down, purely so the committed-waiver check (which needs it
    # to compute the true merge-base) can run in this same preflight
    # pass, still strictly before any git mutation.
    main_branch_resolved = _resolve_main_branch_for_land(
        root, worktree, ticket, ticket_id
    )
    if main_branch_resolved.is_err:
        return Err(main_branch_resolved.danger_err)
    main_branch_name = main_branch_resolved.danger_ok

    scope_preflight = _validate_scope_covered_preflight(ticket, covers_scope)
    if scope_preflight.is_err:
        return Err(scope_preflight.danger_err)

    remaining = _land_precheck_remaining_checks(
        root,
        worktree,
        ticket,
        main_branch_name,
        skip_mutation_evidence=skip_mutation_evidence,
        allow_cross_ticket=allow_cross_ticket,
    )
    if remaining.is_err:
        return Err(remaining.danger_err)

    return Ok((ticket, main_branch_name))


# frob:ticket T-1355
def _land_precheck_remaining_checks(
    root: Path,
    worktree: Path,
    ticket: Ticket,
    main_branch_name: str,
    *,
    skip_mutation_evidence: bool,
    allow_cross_ticket: bool,
) -> Result[None, LandError]:
    """The tail half of `_land_precheck`'s check sequence (T-1355: split
    out to keep the parent under ARCH001's line threshold, zero behavior
    change) -- live-tracker citations, T-1355's cross-ticket leakage
    preflight, then the diff-scoped mutation-evidence obligation, in that
    order, exactly as they ran inline before this split."""
    live_tracker_check = _check_live_tracker_citations(
        worktree, ticket, main_branch_name
    )
    if live_tracker_check.is_err:
        return Err(live_tracker_check.danger_err)

    leakage_check = _check_cross_ticket_leakage(
        root,
        worktree,
        ticket,
        main_branch_name,
        allow_cross_ticket=allow_cross_ticket,
    )
    if leakage_check.is_err:
        return Err(leakage_check.danger_err)

    return _check_mutation_evidence(
        worktree,
        ticket,
        main_branch_name,
        skip=skip_mutation_evidence,
    )


# frob:ticket T-1258
# frob:doc docs/design/ledger-v2.md#5-merge-story-the-frob-ledger-driver-retired
# frob:tests tests/test_ticket_land.py::TestLedgerV2LandMergeStory.test_disjoint_v2_tickets_land_with_no_custom_merge  # noqa: E501
# frob:waive COV007 reason="T-1636: docs/design/ledger-v2.md's Merge story section \
# (T-1136/T-1258) is a deliberate design doc walking through this exact private \
# v2-mode merge counterpart's own contract -- same T-0524/T-0529 per-function \
# architecture-doc precedent every other COV007 waiver in this repo already carries, \
# not accidental drift onto a private helper"
def _merge_main_into_worktree_v2(
    worktree: Path, ticket: Ticket, main_branch: str
) -> Result[bool, LandError]:
    """v2-mode counterpart to `_merge_main_into_worktree` (design section
    5): a plain `git merge --no-commit --no-ff` -- no `tickets.md`/
    `tickets-archive.md` splice at all, since disjoint `tickets/T-####/`
    directories are ordinary git objects that merge cleanly on their own
    (AC2: two branches editing DIFFERENT ticket directories produce zero
    conflicts, no custom driver invoked). Any conflict outside the
    ticket's own directory is auto-resolved by taking main's side (mirrors
    `_merge_main_into_worktree`'s `keep="theirs"` convention); a conflict
    INSIDE the ticket's own directory (two branches both editing the SAME
    ticket) is left conflicted and surfaced loudly (AC3), never
    resolved by picking a side."""
    merged = run_argv(
        ["git", "-C", str(worktree), "merge", "--no-commit", "--no-ff", main_branch]
    )
    if merged.is_err:
        return Err(LandError.GitFailed)
    if (
        merged.danger_ok.returncode == 0
        and "up to date" in merged.danger_ok.stdout.lower()
    ):
        return Ok(False)

    widened = _v2_effective_scope(ticket)
    resolved = _auto_resolve_out_of_scope_conflicts(worktree, widened, keep="theirs")
    if resolved.is_err:
        _abort_merge(worktree)
        return Err(resolved.danger_err)
    remaining = resolved.danger_ok
    if remaining:
        _abort_merge(worktree)
        _log.error(
            "land: %s merging %s into %s conflicts in scoped file(s) "
            "(v2 mode, no ledger splice applies): %s -- resolve manually "
            "(cd %s && git merge %s), commit, then retry "
            "`frob ticket land %s --worktree %s`",
            ticket.id,
            main_branch,
            worktree,
            sorted(remaining),
            worktree,
            main_branch,
            ticket.id,
            worktree,
        )
        return Err(LandError.MergeConflict)
    return Ok(True)


def _land_merge_stage(
    root: Path,
    worktree: Path,
    ticket: Ticket,
    ticket_id: str,
    main_branch_name: str,
    dry_run: bool,
) -> Result[tuple[bool, bool, LandReport | None], LandError]:
    """wip-commit, merge main into the worktree, and check for unowned
    deletions; returns `(wip_committed, did_merge, dry_run_report)` where
    `dry_run_report` is the early-return report for a clean dry run, else
    `None`.

    T-1258: dispatches to the v2-mode merge path (`_merge_main_into_
    worktree_v2`, no ledger splice) whenever `root` is in v2-mode storage
    (`_store_mode(root) == "v2"`); a v1 (monofile) `root` keeps the
    existing `_merge_main_into_worktree` splice path unchanged."""
    wip = _wip_commit(worktree, ticket_id, dry_run=dry_run)
    if wip.is_err:
        return Err(wip.danger_err)
    wip_committed = wip.danger_ok

    merged = (
        _merge_main_into_worktree_v2(worktree, ticket, main_branch_name)
        if _store_mode(root) == "v2"
        else _merge_main_into_worktree(root, worktree, ticket, main_branch_name)
    )
    if merged.is_err:
        return Err(merged.danger_err)
    did_merge = merged.danger_ok

    unowned_check = _check_unowned_deletions(
        root, worktree, ticket, ticket_id, main_branch_name, did_merge
    )
    if unowned_check.is_err:
        return Err(unowned_check.danger_err)

    if not dry_run:
        return Ok((wip_committed, did_merge, None))

    report = _dry_run_report(
        worktree, ticket_id, main_branch_name, wip_committed, did_merge
    )
    return Ok((wip_committed, did_merge, report))


# frob:ticket T-0236
def _refresh_prework_sweep(worktree: Path, ticket: Ticket) -> None:
    """Re-record `ticket`'s pre-work sweep against the just-merged worktree
    state, post-merge and pre-close.

    Landing can pull in unrelated main commits that touch the ticket's scope
    globs, moving the recorded sweep's scope digest out from under it -- if
    `land` then fails before reaching close (evidence or Done-report issue),
    the ticket is left in-progress carrying a sweep that `frob check`'s
    PRE001 will flag as stale on the very next check, even though nothing
    about THIS ticket's own work was actually un-swept (T-0236). Refreshing
    here, unconditionally, before the close attempt below means a retried
    land (or a reviewer's `frob check --ticket` in the interim) sees a sweep
    that matches the current tree, not a stale one caused by drift outside
    this ticket's control.

    Best-effort: a refresh failure is logged and does not block landing --
    the close step's own evidence/Done-report gates are what actually gate
    `land`, not this sweep's freshness.
    """
    from frob.gates import sweep_ticket

    swept = sweep_ticket(worktree, ticket)
    if swept.is_err:
        _log.warning(
            "land: %s post-merge pre-work sweep refresh failed (%s) -- "
            "PRE001 may report staleness until `frob ticket sweep %s` "
            "is run manually",
            ticket.id,
            swept.danger_err,
            ticket.id,
        )


def _dry_run_report(
    worktree: Path,
    ticket_id: str,
    main_branch_name: str,
    wip_committed: bool,
    did_merge: bool,
) -> LandReport:
    """Abort any staged merge and build the early-return `LandReport` for a
    clean dry run."""
    if did_merge:
        _abort_merge(worktree)
    _log.info(
        "land: %s dry-run clean -- would merge=%s, would close, would "
        "squash-apply onto %s",
        ticket_id,
        did_merge,
        main_branch_name,
    )
    return LandReport(
        ticket_id=ticket_id,
        final_id=ticket_id,
        dry_run=True,
        wip_committed=wip_committed,
        merged_main_into_worktree=did_merge,
        ledger_spliced=did_merge,
        unowned_deletions=(),
    )


def _check_unowned_deletions(
    root: Path,
    worktree: Path,
    ticket: Ticket,
    ticket_id: str,
    main_branch_name: str,
    did_merge: bool,
) -> Result[None, LandError]:
    """`Err(UnownedDeletions)` (aborting the merge first) if the worktree
    deletes any file outside `ticket.scope`."""
    unowned = _unowned_deletions(root, worktree, ticket.scope, main_branch_name)
    if unowned.is_err:
        if did_merge:
            _abort_merge(worktree)
        return Err(unowned.danger_err)
    if unowned.danger_ok:
        if did_merge:
            _abort_merge(worktree)
        _log.error(
            "land: %s refused -- worktree deletes file(s) outside its scope "
            "%s: %s. If intentional, add the path(s) to the ticket's scope; "
            "if accidental (a stale worktree base), restore them: "
            "cd %s && git checkout %s -- %s ; then retry "
            "`frob ticket land %s --worktree %s`",
            ticket_id,
            list(ticket.scope),
            list(unowned.danger_ok),
            worktree,
            main_branch_name,
            " ".join(unowned.danger_ok),
            ticket_id,
            worktree,
        )
        return Err(LandError.UnownedDeletions)
    return Ok(None)

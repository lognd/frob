"""`frob ticket land` -- one-command landing
(docs/modules/tickets-landing.md#frob-ticket-land).

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

from __future__ import annotations

import importlib
import json
import os
import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

from pydantic import BaseModel
from typani.result import Err, Ok, Result

if TYPE_CHECKING:
    # frob:ticket T-2215
    from frob.gates import Violation

    # frob:ticket T-1979
    from frob.testing._models import CollectedTests

from frob.gitio import current_branch, run_argv
from frob.logging import get_logger
from frob.tickets._journal import _clear_intent, _write_intent
from frob.tickets._land_finalize import _land_finalize_and_close
from frob.tickets._land_git_ops import (
    _abort_merge,
    _auto_resolve_out_of_scope_conflicts,
    _commit_rapid_debt_only_drift,
    _committed_out_of_scope_waive_deletions,
    _merge_main_into_worktree,
    _porcelain_dirty,
    _restore_lock_version_only_drift,
    _rev_parse,
    _true_merge_base,
    _uncommitted_out_of_scope_waive_deletions,
    _unowned_deletions,
    _unstage_index_only,
    _wip_commit,
    detect_duplicate_ticket_id_collisions,
    reclaim_orphaned_squash_residue,
)
from frob.tickets._land_ledger_merge import _STATE_RANK
from frob.tickets._land_merge import _validate_closeable

# Re-exported for `frob.tickets.__init__`'s `from frob.tickets._land import
# land, splice_ledger` -- T-1186 moved the implementation to
# `frob.tickets._land_merge`; this module keeps the public import path
# stable.
from frob.tickets._land_merge import splice_ledger as splice_ledger  # noqa: E402
from frob.tickets._land_squash import _land_squash_apply, _v2_effective_scope
from frob.tickets._land_verify import (
    _ClaimsReverifyOutcome,
    _reverify_done_report_claims_post_merge,
    _reverify_evidence_post_merge,
)
from frob.tickets._leases import LAND_LOCK_REL, read_all_leases
from frob.tickets._models import (
    LandError,
    LandPlanReport,
    LandReport,
    Ticket,
    TicketError,
)
from frob.tickets._provisional import is_draft_id
from frob.tickets._store import _TICKET_ID_RE, _parse_ticket_file, _store_mode, load_all

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
#
# T-1619: the path constant itself now lives in `frob.tickets._leases`
# (`LAND_LOCK_REL`) -- that module is the single home every OTHER ledger-
# committing verb's auto-commit choke point
# (`_leases._add_and_commit_tickets_md`) probes via `refuse_if_land_in_
# progress` before writing its own commit, so both sides of the
# exclusivity check must agree on exactly one path, never two
# independently-defined copies that could silently drift apart.
_LAND_LOCK_REL = LAND_LOCK_REL


def _land_lock_path(root: Path) -> Path:
    """The advisory lock file path `_land_lock` holds, serializing every
    `land()` call against `root` (T-0577)."""
    return root / _LAND_LOCK_REL


# frob:ticket T-2091
# frob:tests tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome.test_skipped_unmeasured_is_not_printed_as_verified_true  # noqa: E501
# frob:tests tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome.test_passed_healthy_path_is_unchanged  # noqa: E501
_LAST_CLAIMS_OUTCOME: dict[str, _ClaimsReverifyOutcome] = {}
"""T-2091: the most recent `_ClaimsReverifyOutcome` `land()` observed for a
given `ticket_id`, in THIS process. `LandReport` (`frob.tickets._models`)
is frozen/`extra=forbid` and constructed inside `_land_squash.py` at both
its call sites -- neither file is in this ticket's scope, and the ticket's
own directive is to thread the value T-2083 ALREADY computes through
without spawning a new subprocess or widening the write lease onto a third
file. This process-local side channel does that: `land()` writes it the
moment `_reverify_done_report_claims_post_merge` returns `Ok(...)`, and
`_print_land_proof` (`frob.app.ticket_runner._land_cmd`, same process,
called synchronously after `land()` returns) reads and pops it by
`report.ticket_id` to decide whether `LAND-PROOF:` may say
`verified=True` at all. Never persisted to disk and never read across a
process boundary -- a land that crashes before printing loses the entry
same as it loses the rest of the tail, no different from any other
in-memory land state."""


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
# frob:ticket T-1619
def _land_lock_holder_metadata(ticket_id: str | None = None) -> dict:
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
    SESSION_ID` read), not `net`.

    T-1619: `ticket_id` (the ticket THIS `land()` call is landing, when
    known) is also recorded so a REFUSED sibling ledger-writing verb
    (`frob.tickets._leases.refuse_if_land_in_progress`) can name it in its
    own refusal message ("a land is in progress for T-####") instead of
    only pointing at an opaque pid. `None` (the pre-T-1619 shape, e.g. a
    caller that only wants a bare probe) omits the field from the dict
    entirely rather than writing a `null` a reader would have to special-
    case."""
    from datetime import datetime, timezone

    pid = os.getpid()
    session_id = (
        # frob:waive SEC110 reason="session identity marker for lock-holder \
        # attribution, not a secret"
        os.environ.get("FROB_LAND_SESSION_ID") or f"pid-{pid}"
    )
    metadata = {
        "pid": pid,
        "session_id": session_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    if ticket_id is not None:
        metadata["ticket_id"] = ticket_id
    return metadata


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


# frob:ticket T-1634
# frob:tests \
# tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess.test_dead_holder_pid_is_re\
# ported_dead_but_self_healing_and_healthy
# frob:tests \
# tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess.test_live_holder_pid_is_re\
# ported_alive_and_healthy
# frob:tests \
# tests/system/test_cli_doctor.py::TestDoctorLiveLandProcess.test_ambiguous_holder_live\
# ness_is_reported_unhealthy
# frob:tests \
# tests/test_ticket_land.py::TestLandLockHolderMetadataAndTimeout.test_orphaned_lock_fr\
# om_a_confirmed_dead_pid_is_reclaimed_and_logged
def _probe_land_lock_pid_liveness(pid: int) -> bool | None:
    """Three-state liveness probe for a land.lock holder's pid (T-1634):
    `True` (alive), `False` (CONFIRMED dead -- `os.kill(pid, 0)` raised
    `ProcessLookupError`), or `None` (ambiguous -- `PermissionError`/other
    `OSError`, e.g. no permission to signal a pid owned by another user, or
    pid recycling noise). Mirrors the confirmed_absent/ambiguous split
    `frob.tickets._leases._probe_worktree_liveness` already draws for
    worktree leases (T-0782/T-0584): only a CONFIRMED-dead holder is ever
    safe to reclaim automatically; an ambiguous probe must never be treated
    as license to reclaim anything, exactly like that function's own
    contract. Shared by `frob.doctor.scan_live_land_processes` and
    `_land_lock`'s own post-acquire reclaim-logging below, so this repo has
    exactly one pid-liveness notion for land.lock, not two."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (PermissionError, OSError):
        return None
    return True


@contextmanager
# frob:ticket T-1495
# frob:ticket T-1634
# frob:ticket T-1619
def _land_lock(
    root: Path, ticket_id: str | None = None, *, timeout: float = _LAND_LOCK_TIMEOUT_S
) -> Iterator[None]:
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
    doctor`'s live-land-process report.

    T-1634: a successful acquisition -- whether immediate (the common case:
    the OS itself already released a dead prior holder's `flock` the
    instant that process exited, SIGKILL included) or after waiting out a
    genuinely-held lock -- checks the file's PRIOR content (if any) before
    overwriting it. If that prior holder's pid is CONFIRMED dead
    (`_probe_land_lock_pid_liveness` returns `False`) and is not this
    process's own pid, this logs the loud WARNING reclaim message a human
    used to have to notice and act on by hand via `frob doctor`'s
    remediation hint alone -- the acquisition itself was never actually
    blocked by a dead holder (the kernel already freed the `flock`), so
    this is disclosure, not a new code path that bypasses the lock; an
    AMBIGUOUS or genuinely-alive prior holder never logs this line."""
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
    # T-1634: log-only reclaim disclosure -- this call already holds
    # `fd`'s flock and is about to overwrite the file's content below via
    # that SAME fd (the actual reclaim), so there is nothing left to
    # unlink here; unlinking by PATH would sever the path from the inode
    # `fd` is about to write into, leaving the fresh holder metadata
    # invisible to any reader of `path`.
    prior_holder = _read_land_lock_holder(path)
    if prior_holder is not None:
        prior_pid = prior_holder.get("pid")
        if isinstance(prior_pid, int) and prior_pid != os.getpid():
            if _probe_land_lock_pid_liveness(prior_pid) is False:
                _log.warning(
                    "land: %s reclaiming orphaned land.lock -- prior holder "
                    "pid %s (session %s, started %s) confirmed NOT running",
                    root,
                    prior_holder.get("pid"),
                    prior_holder.get("session_id"),
                    prior_holder.get("started_at"),
                )
    holder_metadata = _land_lock_holder_metadata(ticket_id)
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
# frob:ticket T-1963
# frob:tests tests/test_ticket_land.py::TestLandRepairMarker.test_repair_resets_root_when_current_tip_matches_the_marker  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestLandRepairMarker.test_repair_recovers_even_when_current_tip_has_drifted_from_the_marker  # noqa: E501
# frob:tests \
# tests/test_ticket_land.py::TestLandRepairMarker.test_no_marker_is_a_silent_no_op
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

    T-1963: every marker found is now repaired UNCONDITIONALLY (see
    `_reconcile_one_land_repair_marker`'s own docstring for the full
    reasoning) by resetting `root` to its CURRENT `HEAD` and cleaning any
    leftover staged/conflicted squash state, whether or not that `HEAD`
    still equals the marker's recorded `pre_land_tip`. Before T-1963, a
    DRIFTED tip (another land legitimately committing onto `root` while
    this one sat crashed) refused loudly instead -- correct in isolation
    (the recorded tip is no longer safe to reset to), but since this scan
    runs at the start of EVERY `land()` call, that refusal blocked every
    OTHER agent's land too, not just a retry of the crashed ticket, until
    a human intervened. Resetting to current `HEAD` is safe in both cases
    because the crashed run itself never advanced `HEAD` (T-0907's
    guarantee: `root` is never committed to until `_commit_squash_apply`'s
    own final commit) -- there is no longer a case that needs the stale
    recorded tip as a reset target, or a refusal."""
    marker_dir = _land_repair_dir(root)
    if not marker_dir.is_dir():
        return Ok(None)

    for marker_path in sorted(marker_dir.glob("*.json")):
        reconciled = _reconcile_one_land_repair_marker(root, marker_path)
        if reconciled.is_err:
            return reconciled
    return Ok(None)


# frob:ticket T-0976
# frob:ticket T-1963
def _reconcile_one_land_repair_marker(
    root: Path, marker_path: Path
) -> Result[None, LandError]:
    """One T-0907 land-repair marker's reconciliation:
    `_repair_stale_land_marker`'s per-marker half, split from its
    directory-scan loop.

    T-1963: repairs unconditionally by resetting to `root`'s CURRENT
    `HEAD` -- never to the marker's `recorded_tip` -- and cleaning any
    untracked leftovers, regardless of whether `HEAD` still equals
    `recorded_tip` or has drifted since (another land committed onto
    `root` while this one was crashed). This is always safe: `root` is
    NEVER committed to until `_commit_squash_apply`'s own final commit
    (the same T-0907 guarantee `_write_land_repair_marker` documents), so
    a land whose marker is still present crashed strictly BEFORE that
    commit -- it never advanced `HEAD` itself, only staged (uncommitted)
    index/working-tree state on top of whatever `HEAD` happened to be at
    crash time. Resetting to CURRENT `HEAD` therefore always discards
    exactly that crashed run's own uncommitted mess and nothing else,
    whether or not some OTHER, unrelated land legitimately advanced
    `HEAD` in between -- there is no longer a drifted-tip case that needs
    a different, more dangerous target (the marker's stale recorded tip)
    or a refusal.

    Before this fix, a drifted tip (the ordinary case under parallel
    dispatch, where lands are near-continuous) refused wholesale
    (`Err(GitFailed)`), leaving `root` dirty until a human intervened --
    and since this reconciliation runs at the very start of EVERY
    `land()` call (`_repair_stale_land_marker`, invoked before this run's
    own pre-land tip is even captured), that refusal blocked every
    subsequent land attempt by any agent, not just a retry of the crashed
    ticket (T-1963's own measured incident)."""
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

    if current.danger_ok == recorded_tip:
        _log.warning(
            "land: repairing a prior crashed `frob ticket land %s` -- %s's "
            "current tip (%s) matches the recorded pre-land tip, resetting "
            "any leftover staged/conflicted state from the crashed run "
            "(T-0907)",
            marker_ticket_id,
            root,
            recorded_tip,
        )
    else:
        # frob:ticket T-1963
        _log.warning(
            "land: repairing a prior crashed `frob ticket land %s` -- %s's "
            "tip has moved since the recorded pre-land tip (%s -> %s, "
            "other land(s) landed meanwhile) -- resetting only the "
            "crashed run's OWN uncommitted staged/working-tree state to "
            "%s's CURRENT HEAD, never to the stale recorded tip (which "
            "would destroy the commit(s) landed in between); the crashed "
            "run itself never advanced HEAD (T-0907's own guarantee), so "
            "this is safe regardless of the drift (T-1963)",
            marker_ticket_id,
            root,
            recorded_tip,
            current.danger_ok,
            root,
        )

    reset = run_argv(["git", "-C", str(root), "reset", "--hard", "HEAD"])
    if reset.is_err or reset.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    clean = run_argv(["git", "-C", str(root), "clean", "-fd"])
    if clean.is_err or clean.danger_ok.returncode != 0:
        return Err(LandError.GitFailed)
    marker_path.unlink(missing_ok=True)
    _log.info(
        "land: %s T-0907 land-repair marker cleared, %s cleaned to its "
        "current HEAD (%s)",
        marker_ticket_id,
        root,
        current.danger_ok,
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
# frob:waive DEAD001 reason="genuinely called directly from \
# src/frob/app/ticket_runner/_land_cmd.py's post-land verification tail, but the \
# best-effort callgraph (frob.graph.callgraph) does not trace this cross-package \
# private import -- same class of gap as this repo's other cross-package DEAD001 \
# waivers (T-1024 precedent)"
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
# frob:waive DEAD001 reason="genuinely called directly from \
# src/frob/app/ticket_runner/_land_cmd.py's post-land verification tail, but the \
# best-effort callgraph (frob.graph.callgraph) does not trace this cross-package \
# private import -- same class of gap as this repo's other cross-package DEAD001 \
# waivers (T-1024 precedent)"
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
# frob:doc docs/modules/tickets-landing.md#frob-ticket-land
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
    """T-1618/T-1675: `_land_precheck` runs an early, distinct refusal
    (`LandError.AlreadyLandedOnMain`) when the ticket's own declared scope
    has no changes on this branch relative to main AND the ticket's own
    record already shows `done` on main -- the common consequence of a
    passenger-ticket land (see `PassengerTickets` above) that already
    carried this ticket's content onto main ahead of its own close. See
    `_check_already_landed`'s own docstring for the positive-signal check
    this now always runs (T-1675 removed the `--check-already-landed`
    opt-in flag once the check stopped inferring from an empty diff
    alone).

    T-1514: `pre_commit_sweep(root, final_id)` (opt-in), if supplied, is
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

    # T-2170: reclaim any DEAD prior land's orphaned squash residue in
    # `root` BEFORE this land's own `_land_lock` acquire below --
    # `reclaim_orphaned_squash_residue` distinguishes "dead" from "live"
    # by taking a NON-BLOCKING flock on that exact same lock file (T-2157's
    # docstring), so it must run while the lock is still free; calling it
    # from inside `_land_lock`'s own critical section would make its
    # liveness probe always observe itself as the holder and treat every
    # residue as live, defeating the whole point. A genuinely live
    # concurrent land is untouched (`Ok(False)`, no side effect) -- this
    # only ever clears residue nothing currently holds the lock for.
    reclaim = reclaim_orphaned_squash_residue(root, ticket_id)
    if reclaim.is_err:
        _log.error(
            "land: %s pre-lock reclaim of orphaned squash residue in %s failed: %s",
            ticket_id,
            root,
            reclaim.danger_err,
        )
        return Err(reclaim.danger_err)

    try:
        with _land_lock(root, ticket_id):
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
# frob:doc docs/modules/tickets-landing.md#frob-ticket-land---plan-t-1269
# frob:tests tests/test_ticket_land.py::TestLandPlan.test_merges_and_finalizes_every_draft_atomically  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestLandPlan.test_dry_run_unwinds_the_merge
# frob:tests \
# tests/test_ticket_land.py::TestLandPlan.test_merge_conflict_aborts_and_refuses
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
        with _land_lock(root, "<plan>"):
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
    (docs/modules/tickets-merge-driver.md#git-merge-driver) for any ledger conflict the
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
            "(docs/modules/tickets-merge-driver.md#git-merge-driver) if this is a "
            "ledger-only conflict, or resolve by hand and retry",
            worktree,
            worktree_sha,
            root,
        )
        return Err(LandError.MergeConflict)
    return _rev_parse(root, "HEAD")


# frob:ticket T-1269
def _land_plan_finalize_drafts(
    root: Path, merge_commit: str
) -> Result[tuple[tuple[str, str], ...], LandError]:
    """Finalize EVERY draft id now present in `root`'s merged ledger
    (T-1269), one `finalize_draft` call each (T-0162's existing allocator
    -- never a hand-assigned id), in a stable (sorted) order so a retry
    after an unwind is deterministic. `Err(NotFound)` (propagated from
    `finalize_draft`) on the first failure -- the caller resets `root`
    back to its pre-merge tip, so a partial finalize never survives.

    T-2220: each newly-finalized ticket also gets its own `land_commit`
    field set to `merge_commit` here, in-memory, before the caller
    (`_land_plan_commit_finalize`) stages and commits the finalize
    rewrite -- `merge_commit` is ALREADY a real, prior commit by the time
    this runs (the merge step that produced it committed before finalize
    ever starts), so baking its sha into a ticket record finalize is
    about to commit is not the self-reference problem `_record_land_
    commit` (`frob.tickets._land_squash`) exists to avoid for a
    SQUASH-APPLY land's own commit -- this is a different, already-known
    sha. This is the concrete fix for the ticket's own measured defect:
    a `--plan` land's commit subject (`chore(tickets): land --plan
    finalize ...`) carries no ticket id at all, so a finalized ticket's
    `land_commit` field is the ONLY way `scripts/verify_lands.py`/
    `_find_landing_commit` can ever resolve it by id."""
    from frob.tickets import _load_one, finalize_draft, load_all
    from frob.tickets._store import write_ticket

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
        final_id = result.danger_ok
        finalized.append((draft_id, final_id))
        reloaded = _load_one(root, final_id)
        if reloaded.is_err:
            _log.error(
                "land --plan: %s not found immediately after its own "
                "finalize -- cannot record land_commit (T-2220); the "
                "finalize itself already succeeded, this is a best-effort "
                "augmentation only",
                final_id,
            )
            continue
        stamped = reloaded.danger_ok.model_copy(update={"land_commit": merge_commit})
        written = write_ticket(root, stamped)
        if written.is_err:
            _log.error(
                "land --plan: %s land_commit write failed (%s) -- %s "
                "finalized correctly, only the T-2220 record field is "
                "missing",
                final_id,
                written.danger_err,
                final_id,
            )
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
    # frob:ticket T-1740
    # T-1740: unstage BEFORE refusing -- the same fix `_verified_reset_
    # root`'s drift branch got, applied here since `land --plan` runs a
    # SEPARATE unwind primitive (T-1495) with the identical structural
    # gap: a refusal that leaves `land --plan`'s own staged finalize
    # content sitting in root's index is not a refusal, it is a partial
    # apply with an error message. Best-effort -- its own failure only
    # logs, never masks the real refusal below.
    unstaged = _unstage_index_only(root)
    if unstaged.is_err:
        _log.warning(
            "land --plan: could not unstage %s's index after detecting "
            "drift (%s) -- staged content may still be present",
            root,
            unstaged.danger_err,
        )
    _log.error(
        "land: refused to reset %s to %s -- current tip is %s but this "
        "run's own last commit was %s; something else moved %s's tip "
        "since (another process's land, a manual ledger commit) and "
        "resetting would silently destroy it (T-1495, the 2026-08-04 "
        "incident); NOT resetting, but the INDEX has been unstaged "
        "(T-1740) so nothing this run staged can ride into someone "
        "else's next commit -- inspect `git -C %s log --oneline "
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

    finalized = _land_plan_finalize_drafts(root, merge_commit)
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
# frob:ticket T-2189
def _land_plan_unwind_after_merge(
    root: Path, pre_merge_sha: str, own_commits: Sequence[str], *, dry_run: bool
) -> Result[None, LandError]:
    """T-1522: unwind a `land_plan` failure that happens AFTER the merge
    step (`_land_plan_merge_and_finalize`'s first own commit).

    T-2189: `dry_run` decides WHICH unwind a failure gets, and this is now
    the ONLY place that decision is made -- both of `_land_plan_locked`'s
    failure branches (a merge/finalize error, and `check_ticks() is
    False`/`PlanTickGateDirty`) call this function, and prior to T-2189
    NEITHER branch knew `dry_run` at all: every failure, dry run or not,
    got the T-1522 "stop at the merge commit" unwind below, which is only
    correct for a REAL land. A dry run that hit `PlanTickGateDirty` after
    a successful merge left that merge commit sitting on `root`'s tip --
    a real commit on `main` from a call that claimed to mutate nothing,
    with the finalize step (and the draft ids it would have finalized)
    never reached because the dirty check fired first. Confirmed live:
    `PlanTickGateDirty` reported, `git log` on `root` showed the merge
    commit anyway.

    `dry_run=True`: full reset straight back to `pre_merge_sha`,
    discarding `own_commits` in their entirety including the merge commit
    -- a dry run is "run it, then always revert" regardless of WHY it is
    reverting (this mirrors `_land_plan_finish`'s existing dry-run success
    tail exactly; that tail's own reset is now this same call with
    `dry_run=True` in all but name). `root`'s tip must never move as a
    result of a `--dry-run` invocation, whether it fails or succeeds.

    `dry_run=False`: unchanged T-1522 behavior -- WITHOUT ever discarding
    the merge commit itself (see `_land_plan_locked`'s own T-1522
    docstring note for the 2026-08-04 incident, T-1199/T-1200's already-
    merged content eaten by a later, unrelated failure in the SAME
    invocation, this closes). `own_commits[0]` (when present) is always
    the merge commit (`_land_plan_merge_and_finalize`'s own contract: it
    is the first entry appended, before the finalize commit if any) --
    reset only as far as THAT, discarding anything committed after it
    (`own_commits[1:]`, e.g. a finalize commit), never further.

    Either way, when `own_commits` is empty (the merge step itself never
    produced a commit at all -- `_land_plan_merge_worktree` failed before
    committing), this degrades to the plain unwind straight back to
    `pre_merge_sha`, since there is nothing durable yet to preserve."""
    if dry_run or not own_commits:
        return _land_plan_reset_hard(root, pre_merge_sha, own_commits=own_commits)
    merge_commit = own_commits[0]
    return _land_plan_reset_hard(root, merge_commit, own_commits=own_commits[1:])


# frob:ticket T-1522
# frob:ticket T-2189
def _land_plan_tick_gate_dirty(
    root: Path,
    pre_merge_sha: str,
    own_commits: Sequence[str],
    *,
    merge_commit: str,
    dry_run: bool,
) -> Result[None, LandError]:
    """`_land_plan_locked`'s `check_ticks() is False` branch (T-2189, split
    out to keep that function under the ARCH001 60-line threshold): log
    the outcome (which differs by `dry_run` -- a dry run fully reverts,
    a real land keeps the durable merge commit per T-1522) and unwind via
    `_land_plan_unwind_after_merge`. Returns `Ok(None)` if the unwind
    itself succeeded (the caller then reports `PlanTickGateDirty`), or the
    unwind's own `Err` if THAT failed."""
    if dry_run:
        _log.error(
            "land --plan --dry-run: post-merge TICK gate re-check "
            "reported non-clean -- fully reverting to the pre-merge tip "
            "%s (T-2189: a dry run leaves no trace, including its own "
            "merge commit %s)",
            pre_merge_sha,
            merge_commit,
        )
    else:
        _log.error(
            "land --plan: post-merge TICK gate re-check reported "
            "non-clean -- unwinding to the merge commit %s, keeping "
            "any queue-drained sibling content it already carries "
            "(T-1522)",
            merge_commit,
        )
    return _land_plan_unwind_after_merge(
        root, pre_merge_sha, own_commits, dry_run=dry_run
    )


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
    `root`'s `_land_lock`: merge, finalize every draft, optionally
    re-check TICK-gate cleanliness, and -- for a real (non-dry-run) call
    -- leave the merge commit as `root`'s new tip. T-1495: every unwind
    path threads `own_commits` into `_land_plan_reset_hard`, refusing
    instead of discarding a foreign commit interleaved onto `root`
    mid-run. Both failure branches (merge/finalize error, and
    `check_ticks() is False`) delegate their unwind decision to
    `_land_plan_unwind_after_merge`, which is where the T-1522 (durable
    merge commit on a real failure) vs T-2189 (full revert on a dry-run
    failure) policy actually lives -- see that function's own docstring,
    not duplicated here."""
    pre_merge = _land_plan_pre_merge_sha(root)
    if pre_merge.is_err:
        return Err(pre_merge.danger_err)
    pre_merge_sha = pre_merge.danger_ok

    merged_finalized, own_commits = _land_plan_merge_and_finalize(root, worktree)
    if merged_finalized.is_err:
        _land_plan_unwind_after_merge(root, pre_merge_sha, own_commits, dry_run=dry_run)
        return Err(merged_finalized.danger_err)
    merge_commit, finalized_ids = merged_finalized.danger_ok

    if check_ticks is not None and check_ticks() is False:
        unwound = _land_plan_tick_gate_dirty(
            root,
            pre_merge_sha,
            own_commits,
            merge_commit=merge_commit,
            dry_run=dry_run,
        )
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
# frob:ticket T-1736
# frob:ticket T-2076
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

        # T-1932/T-1931: re-run the cross-ticket leakage guard AGAIN, here,
        # AFTER `_land_merge_stage`'s wip-commit has captured every mutation
        # into `worktree`'s HEAD -- see `_reverify_cross_ticket_leakage_
        # post_mutation`'s own docstring for the ordering invariant this
        # closes (`_land_precheck`'s own copy of this same check, run
        # earlier, only ever sees COMMITTED history; anything a caller's
        # pre-land auto-fix absorption left as an UNCOMMITTED disk write --
        # `frob ticket land`'s own T-1175 `_absorb_pre_land_fixes`, e.g. the
        # T-1931 incident -- is invisible to that earlier check and only
        # becomes part of history at the wip-commit just above). Placed
        # BEFORE the dry-run early return for the same D-05 reason every
        # other post-mutation re-check below is: a `--dry-run` must preview
        # the exact refusal a real run would hit, not skip it.
        leakage_recheck = _reverify_cross_ticket_leakage_post_mutation(
            root, worktree, ticket, main_branch_name, allow_cross_ticket
        )
        if leakage_recheck.is_err:
            if did_merge:
                _abort_merge(worktree)
            return Err(leakage_recheck.danger_err)

        # frob:ticket T-1940
        # T-1940: passenger-tickets' own post-mutation twin, registered in
        # `_COMMITTED_DIFF_GUARDS` -- same T-1932 ordering invariant, same
        # placement (right alongside the leakage re-check, before the
        # dry-run early return) as its worked precedent above.
        passenger_recheck = _reverify_passenger_tickets_post_mutation(
            worktree, ticket, main_branch_name, allow_cross_ticket
        )
        if passenger_recheck.is_err:
            if did_merge:
                _abort_merge(worktree)
            return Err(passenger_recheck.danger_err)

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
        #
        # T-2064/T-2076 CORRECTION: the T-2064 probe that used to sit here
        # compared `root`'s live HEAD against `root_pre_land_tip` and read
        # "equal" as proof the check_gates() spawn observes root's
        # PRE-land tree via `cwd=root`. That comparison is a tautology --
        # `root` is never mutated before `_land_squash_apply` runs (this
        # module's own comment, a few lines below, names it as the ONLY
        # step that touches `root`), so `root`'s HEAD is trivially
        # unchanged here NO MATTER what `cwd` the spawn actually uses; the
        # "equal" reading proved nothing about the spawn itself and was a
        # false positive. T-2076 traced the real caller wiring
        # (`_land_core_invoke`, src/frob/app/ticket_runner/_land_cmd.py)
        # and confirmed directly (a probe on a real spawn, plus a fixture-
        # repo reproduction) that `check_gates`/`check_gate_findings`
        # already spawn with `cwd=worktree` -- the correctly-merged tree
        # -- by the time this point in `_land_locked` runs. The real
        # defect was a DIFFERENT silent failure mode entirely: `frob
        # check`'s own `_refuse_full_check_for_agent` (T-0627) refuses
        # this spawn's unchunked shape whenever the caller's shell carries
        # `FROB_AGENT` (true for every dispatched worktree agent), which
        # made `check_gates()` return `None` ("unmeasured") on every land
        # run from an agent shell -- see `_shared_check_spawn_fn`'s own
        # docstring (`src/frob/app/ticket_runner/_verify.py`) for the full
        # account and the fix (`FROB_ALLOW_FULL_CHECK=1` in the spawn's
        # own child env, unconditionally).
        claims_check = _reverify_done_report_claims_post_merge(
            worktree, ticket_id, passing_ids, check_gates, check_gate_findings
        )
        if claims_check.is_err:
            if did_merge:
                _abort_merge(worktree)
            return Err(claims_check.danger_err)
        # T-2091: record the outcome T-2083 already computed so
        # `_print_land_proof` can surface a SKIPPED_UNMEASURED claims
        # re-verification on the LAND-PROOF line instead of silently
        # discarding it here as before -- see `_LAST_CLAIMS_OUTCOME`'s own
        # docstring for why this is a process-local dict rather than a new
        # `LandReport` field.
        _LAST_CLAIMS_OUTCOME[ticket_id] = claims_check.danger_ok

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
            squash_result = _land_squash_apply(
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
        if squash_result.is_ok:
            # T-1736: feed the T-1686 watermark epic's verify queue --
            # best-effort, never gates an already-sealed land.
            _record_verify_intent_for_landed_commit(
                root, final_id, squash_result.danger_ok, root_pre_land_tip.danger_ok
            )
        return squash_result
    finally:
        _clear_intent(root, ticket_id)


# frob:ticket T-1736
# frob:doc \
# docs/modules/tickets-verify-sweep.md#verification-watermark-t-1687-foundation-of-the-\
# t-1686-epic
# frob:tests tests/test_ticket_land.py::TestRecordVerifyIntentForLandedCommit.test_dry_run_is_a_noop  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestRecordVerifyIntentForLandedCommit.test_real_land_records_an_intent_entry  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestRecordVerifyIntentForLandedCommit.test_no_resolvable_symbols_records_nothing  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestRecordVerifyIntentForLandedCommit.test_diff_failure_is_logged_not_raised  # noqa: E501
def _record_verify_intent_for_landed_commit(
    root: Path, ticket_id: str, report: LandReport, pre_land_tip: str
) -> None:
    """T-1736: the T-1686 epic's missing enqueue side -- WITHOUT this, the
    coalescing verify worker (T-1688, already draining/advancing/compacting
    against `.frob/verify-queue.json`) never has anything to drain, no
    matter how many lands happen. Called once, right after a REAL
    (non-dry-run) `_land_squash_apply` success, from `_land_locked` itself
    -- never from inside `_land_squash_apply` (out of this ticket's own
    declared scope, `src/frob/tickets/_land.py` alone).

    `report.commit_sha` is already durably on `root` by the time this
    runs (this function reads, never mutates git state) -- `working_diff
    (root, pre_land_tip)` computes `merge-base(HEAD, pre_land_tip)` first;
    since `pre_land_tip` is `root`'s own tip captured before this land's
    squash-apply started, it is a direct ancestor of the just-sealed
    commit, so the merge-base IS `pre_land_tip` itself and the resulting
    diff is exactly this land's own delta -- not a re-derivation of some
    other window.

    Best-effort throughout: a diff/graph-build failure, an empty touched-
    symbol set, or a `record_intent` failure are each logged and
    swallowed, never raised -- the land already succeeded and sealed a
    real commit; an unfed verify queue is a visible, bounded liability
    (T-1697 surfaces queue depth/age), never a reason to fail an
    already-sealed land."""
    if report.dry_run or report.commit_sha is None:
        return

    from frob.gitio import working_diff

    diff = working_diff(root, pre_land_tip)
    if diff.is_err:
        _log.warning(
            "land: %s: could not compute the landed commit's diff for "
            "verify-queue intent (%s) -- the T-1686 watermark epic will "
            "not see %s until a later land succeeds",
            ticket_id,
            diff.danger_err,
            report.commit_sha[:12],
        )
        return

    snapshot = _load_snapshot_for_intent(root, ticket_id, report.commit_sha)
    if snapshot is None:
        return

    touched = _touched_symrefs_for_intent(diff.danger_ok, snapshot)
    if not touched:
        _log.info(
            "land: %s: landed commit %s touched no resolvable symbols -- "
            "no verify-queue intent recorded",
            ticket_id,
            report.commit_sha[:12],
        )
        return

    _record_intent_or_log(root, ticket_id, report.commit_sha, touched)


# frob:ticket T-1736
def _load_snapshot_for_intent(root: Path, ticket_id: str, commit_sha: str):  # noqa: ANN201 -- GraphSnapshot | None, deferred-import type
    """`_record_verify_intent_for_landed_commit`'s own ARCH001 split: load
    (or build, on a cold `.frob/cache.db`) the graph snapshot -- the same
    load-or-build shape every other graph-backed caller in this repo
    shares. `None` on any build failure, logged, never raised."""
    from frob.graph import build_graph, load_graph

    cache = root / ".frob" / "cache.db"
    loaded = load_graph(cache)
    if loaded.is_ok:
        return loaded.danger_ok
    built = build_graph(root, cache)
    if built.is_err:
        _log.warning(
            "land: %s: graph unavailable for verify-queue intent (%s) -- "
            "%s will not be recorded",
            ticket_id,
            built.danger_err,
            commit_sha[:12],
        )
        return None
    return built.danger_ok


# frob:ticket T-1736
def _record_intent_or_log(
    root: Path, ticket_id: str, commit_sha: str, touched: set[str]
) -> None:
    """`_record_verify_intent_for_landed_commit`'s own ARCH001 split: the
    actual `record_intent` call plus its success/failure logging."""
    from frob.tickets._profile import effective_profile
    from frob.verify import record_intent

    profile_result = effective_profile(root)
    profile = profile_result.danger_ok.value if profile_result.is_ok else "unknown"
    recorded = record_intent(
        root,
        commit_sha=commit_sha,
        ticket_id=ticket_id,
        touched_symbols=tuple(sorted(touched)),
        profile=profile,
    )
    if recorded.is_err:
        _log.warning(
            "land: %s: record_intent failed (%s) for %s -- the T-1686 "
            "watermark epic will not see this land",
            ticket_id,
            recorded.danger_err,
            commit_sha[:12],
        )
    else:
        _log.info(
            "land: %s: recorded verify-queue intent for %s (%d touched "
            "symbol(s), profile=%s)",
            ticket_id,
            commit_sha[:12],
            len(touched),
            profile,
        )


# frob:ticket T-1736
# frob:waive DUP001 reason="a near-identical span-overlap match to \
# frob.gates._touched_symrefs/_overlaps -- this ticket's own declared scope is \
# src/frob/tickets/_land.py alone, src/frob/gates/__init__.py is out of it, so this \
# reimplements rather than cross-package-imports a private helper; see this function's \
# own docstring"
def _touched_symrefs_for_intent(diff, snapshot) -> set[str]:  # noqa: ANN001
    """Every symbol in `snapshot` whose span overlaps a `diff` hunk in the
    same file -- the identical span-overlap match `frob.gates.
    _touched_symrefs`/`_overlaps` already implement for AFFECT001/AFFECT002,
    reimplemented here (see the `frob:waive DUP001` above this function for
    why: a cross-package private import was out of this ticket's own scope
    to fix at the source instead)."""
    hunks_by_file: dict[str, list[tuple[int, int]]] = {}
    for hunk in diff.hunks:
        hunks_by_file.setdefault(hunk.file, []).append(hunk.span)
    touched: set[str] = set()
    for record in snapshot.symbols.values():
        for span in hunks_by_file.get(record.id.path, ()):
            if span[0] <= record.span[1] and record.span[0] <= span[1]:
                touched.add(record.symref)
                break
    return touched


# frob:ticket T-1699
# frob:ticket T-1736
_NON_TERMINAL_TICKET_STATES = frozenset({"queued", "planned", "in-progress", "blocked"})


# frob:ticket T-1699
def _dirt_owned_by_no_open_ticket(root: Path, dirty_paths: tuple[str, ...]) -> bool:
    """True when NONE of `dirty_paths` falls inside any currently open
    (non-terminal) ticket's declared `scope` -- the signal
    `_refuse_if_main_dirty` uses to tell a crashed land's residue (which
    DOES belong to some ticket's scope, since a land only ever touches
    files that ticket's own work declared) apart from dirt belonging to
    NO ticket at all -- most often the coordinator working directly on
    the shared root checkout outside the ticket workflow entirely (T-1699's
    second, process-shaped finding: three agents in one session each
    independently misdiagnosed exactly this shape as "a crashed land").

    Best-effort and fail-CLOSED: if the ledger cannot be read at all,
    returns `False` (do not claim "owned by no ticket" on missing data --
    the ordinary, less specific refusal message is always safe to fall
    back to)."""
    from frob.tickets._models import scope_matches
    from frob.tickets._store import load_all

    loaded = load_all(root)
    if loaded.is_err:
        return False
    for ticket in loaded.danger_ok.values():
        if ticket.state not in _NON_TERMINAL_TICKET_STATES:
            continue
        if any(scope_matches(p, ticket.scope, kind=ticket.kind) for p in dirty_paths):
            return False
    return True


# frob:ticket T-2026
_ORPHANED_NEW_TICKET_DIR_RE = re.compile(rf"^tickets/({_TICKET_ID_RE})/$")


# frob:ticket T-2026
# frob:ticket T-2046
# frob:ticket T-2075
def _orphaned_new_ticket_dir_candidates(
    root: Path, ticket_id: str
) -> tuple[list[str], list[str]] | None:
    """The validate half of the T-2026/T-2046 orphaned-new-ticket-dir
    auto-heal, split out of `_commit_orphaned_new_ticket_dir_only_drift`
    to keep that function under ARCH001's line threshold (T-2026's
    follow-up residue) -- pure read/parse, no git mutation. `None` unless
    EVERY dirty path in the tree (ignoring `.frob/`) is an untracked
    `tickets/T-####/` directory (`?? tickets/T-####/`) whose only entry
    is a `ticket.md` that parses cleanly via `_parse_ticket_file` with an
    id matching its own directory name -- all-or-nothing, ANY unmatched
    dirty path (a modified TRACKED file, a torn/partial `ticket.md`, an
    extra file in the directory, or simply no dirty paths at all) means
    `None`, never a partial list. On a match, returns `(orphan_paths,
    orphan_ids)` in the SAME order, ready for the caller's own stage-and-
    commit step."""
    status = run_argv(["git", "-C", str(root), "status", "--porcelain"])
    if status.is_err or status.danger_ok.returncode != 0:
        return None
    dirty_lines = [
        line
        for line in status.danger_ok.stdout.splitlines()
        if line.strip() and not line[3:].strip().startswith(".frob/")
    ]
    if not dirty_lines:
        return None
    orphan_paths: list[str] = []
    orphan_ids: list[str] = []
    for line in dirty_lines:
        if not line.startswith("??"):
            return None
        path = line[3:].strip()
        match = _ORPHANED_NEW_TICKET_DIR_RE.match(path)
        if match is None:
            return None
        orphan_id = match.group(1)
        dir_path = root / path
        try:
            entries = [p.name for p in dir_path.iterdir()]
        except OSError:
            return None
        if entries != ["ticket.md"]:
            return None
        parsed = _parse_ticket_file(dir_path / "ticket.md")
        if parsed.is_err:
            _log.error(
                "land: %s found an orphaned new-ticket directory %s that "
                "does NOT parse cleanly (%s) -- refusing to auto-heal ANY "
                "of the %d orphaned dir(s) found, the ordinary DirtyMain "
                "refusal stands (T-2026/T-2046)",
                ticket_id,
                path,
                parsed.danger_err,
                len(dirty_lines),
            )
            return None
        if parsed.danger_ok.id != orphan_id:
            return None
        orphan_paths.append(path)
        orphan_ids.append(orphan_id)
    return orphan_paths, orphan_ids


# frob:ticket T-2026
# frob:ticket T-2046
def _commit_orphaned_new_ticket_dir_only_drift(root: Path, ticket_id: str) -> bool:
    """Auto-commit `root`'s orphaned NEW ticket directories (T-2026,
    widened by T-2046 from one to N) when `_orphaned_new_ticket_dir_
    candidates` finds EVERY dirty path in the tree qualifies -- the
    window `frob ticket new` (`frob.app.ticket_runner._new._new`) leaves
    open between writing `tickets/T-####/ticket.md` to disk (`write_
    ticket`'s v2-mode body, `_write_ticket_v2_mode`) and its own final
    `commit_ticket_ledger_change` call. If the process is killed in
    between -- the observed 2026-08-10 incident was a coordinator retry
    loop around `new`, needed because the verb refuses under
    `LandInProgress` almost continuously at high agent counts, killed
    mid-run -- the untracked directory survives with no commit, and
    `DirtyMain` refuses every subsequent land repo-wide with no
    agent-reachable recovery (only the ROOT checkout's own owner can
    `git add`/`git commit` it by hand; T-2017 was cleared this way, by
    hand, after an agent with finished, gate-clean work sat blocked 7+
    minutes).

    T-2046 widened the match from SOLE (one named file, mirroring
    `_restore_lock_version_only_drift`/`_commit_rapid_debt_only_drift`
    above) to CLASS-WIDE (any untracked, cleanly-parsing new ticket
    directory) after the original SOLE restriction was measured
    declining in exactly the load it was built for -- two independently
    interrupted `new` invocations left TWO orphaned dirs coexisting 30
    minutes after T-2026 landed. The safety argument (a freshly created
    untracked directory has no prior state to clobber, so committing it
    once it parses is always safe) holds identically for N directories
    as for one. Scoped to the untracked-NEW case only, deliberately: an
    interrupted write to an EXISTING tracked ticket.md cannot be told
    apart from a genuine mid-write tear without per-verb transition
    validation, and auto-healing that case on a guess would be a
    strictly worse failure mode than the deadlock it prevents (T-2026's
    own explicit scope cut, not yet observed as a live incident, and
    unchanged by T-2046).

    LOUD by design (T-2026): both the commit message and the log line
    name this as an auto-heal of ANOTHER process's residue, never a
    silent repair -- a quiet auto-heal would turn a visible deadlock
    into an invisible recurring anomaly, and the whole point is keeping
    the underlying rate measurable, the same posture `_commit_rapid_
    debt_only_drift`'s own `_log.info` call at its call site already
    takes."""
    candidates = _orphaned_new_ticket_dir_candidates(root, ticket_id)
    if candidates is None:
        return False
    orphan_paths, orphan_ids = candidates
    staged = run_argv(["git", "-C", str(root), "add", "--", *orphan_paths])
    if staged.is_err or staged.danger_ok.returncode != 0:
        return False
    ids_desc = ", ".join(orphan_ids)
    committed = run_argv(
        [
            "git",
            "-C",
            str(root),
            "commit",
            "-m",
            f"chore(tickets): auto-commit orphaned {ids_desc} director"
            f"{'y' if len(orphan_ids) == 1 else 'ies'} (T-2026/T-2046 "
            "DirtyMain auto-heal of interrupted `frob ticket new` "
            "invocation(s))",
            "--",
            *orphan_paths,
        ]
    )
    return committed.is_ok and committed.danger_ok.returncode == 0


def _refuse_if_main_dirty(
    root: Path, worktree: Path, ticket_id: str
) -> Result[None, LandError]:
    """`Err(DirtyMain)` if `root` has any uncommitted change.

    Tolerates three specific shapes of "dirty" without refusing:

    - (T-0793) `uv.lock`'s frob-version line flapping on its own, with
      nothing else in the tree touched, from a prior `uv run`/`uv lock`
      invocation against a pyproject a sibling land already bumped.
      Auto-restored (`git checkout -- uv.lock`, discarding the flap)
      before the dirty check is re-evaluated.
    - (T-1699) `rapid-debt.jsonl` alone, dirty because a DIFFERENT
      concurrent land's own two-step append-then-commit
      (`_commit_rapid_debt`, deliberately outside the land lock so the
      detached post-land sweep phase never re-serializes -- T-1684) was
      observed mid-window. Auto-COMMITTED (`_commit_rapid_debt_only_
      drift`, never discarded -- unlike the uv.lock flap, this content
      is real and land-owned) before the dirty check is re-evaluated.
    - (T-2026, widened by T-2046) every dirty path being an orphaned,
      untracked `tickets/T-####/` directory left by an INTERRUPTED
      (killed mid-run) `frob ticket new`, each whose `ticket.md` parses
      cleanly and whose id matches its directory name -- the DEAD-process
      mirror of T-1699's shape above (a living process's own commit
      racing a concurrent land) rather than the same failure: nothing is
      alive here to finish the commit itself, so THIS check is the only
      place that ever will. Auto-COMMITTED (`_commit_orphaned_new_
      ticket_dir_only_drift`, never discarded -- it is real, already-
      filed ticket(s), T-2017 was cleared this exact way by hand before
      this existed) before the dirty check is re-evaluated. ANY dirty
      path that does not qualify (fails to parse, is not an orphaned
      ticket dir, etc.) means NOTHING is committed -- see that function's
      own docstring for the full all-or-nothing contract.

    Any OTHER dirt (a real lock change, any other file, any of these
    three alongside anything else) is left alone and still refuses
    exactly as before."""
    main_dirty = _apply_dirty_main_auto_heals(root, ticket_id)
    if main_dirty.is_err:
        return Err(main_dirty.danger_err)
    if main_dirty.danger_ok:
        _log_dirty_main_refusal(root, worktree, ticket_id)
        return Err(LandError.DirtyMain)
    return Ok(None)


# frob:ticket T-2026
# frob:ticket T-2075
def _apply_dirty_main_auto_heals(root: Path, ticket_id: str) -> Result[bool, LandError]:
    """The auto-heal-attempt half of `_refuse_if_main_dirty`, split out to
    keep that function under ARCH001's line threshold (T-2026's follow-up
    residue): runs each of the three narrow guards in turn -- uv.lock
    restore (T-0793), rapid-debt.jsonl commit (T-1699), orphaned new-
    ticket-dir commit (T-2026/T-2046) -- re-checking dirtiness after each
    one that actually acts, exactly as `_refuse_if_main_dirty` itself
    used to inline. Returns the FINAL dirtiness (`True` still dirty,
    `False` clean) for the caller to decide refuse-or-not; `Err` only on
    a `_porcelain_dirty` git failure, never swallowed."""
    main_dirty = _porcelain_dirty(root)
    if main_dirty.is_err:
        return main_dirty
    if main_dirty.danger_ok and _restore_lock_version_only_drift(root):
        _log.info(
            "land: %s auto-restored a uv.lock frob-version-only drift in "
            "%s before the DirtyMain check (T-0793)",
            ticket_id,
            root,
        )
        main_dirty = _porcelain_dirty(root)
        if main_dirty.is_err:
            return main_dirty
    if main_dirty.danger_ok and _commit_rapid_debt_only_drift(root):
        _log.info(
            "land: %s auto-committed a stray rapid-debt.jsonl append in "
            "%s before the DirtyMain check (T-1699)",
            ticket_id,
            root,
        )
        main_dirty = _porcelain_dirty(root)
        if main_dirty.is_err:
            return main_dirty
    if main_dirty.danger_ok and _commit_orphaned_new_ticket_dir_only_drift(
        root, ticket_id
    ):
        _log.info(
            "land: %s auto-committed an orphaned new-ticket directory left "
            "by an INTERRUPTED `frob ticket new` in %s before the "
            "DirtyMain check (T-2026 auto-heal of another process's "
            "residue)",
            ticket_id,
            root,
        )
        main_dirty = _porcelain_dirty(root)
        if main_dirty.is_err:
            return main_dirty
    return main_dirty


# frob:ticket T-1698
# frob:ticket T-1699
def _log_dirty_main_refusal(root: Path, worktree: Path, ticket_id: str) -> None:
    """The `DirtyMain` refusal log line for `_refuse_if_main_dirty`, split
    out to keep that function under ARCH001's line threshold.

    T-1698: names the offending paths. A bare "has uncommitted changes"
    deadlocked a three-agent wave on ONE one-line file nobody could
    identify from the refusal alone.

    T-1699: when NONE of the dirty paths falls inside any currently open
    ticket's declared scope, this is NOT a crashed land's leftover -- a
    land only ever touches files its own ticket's scope covers, so
    orphaned dirt belongs to whoever is working the root checkout
    directly outside the ticket workflow (a coordinator's own
    in-progress edits, most often). Three agents this session each
    misdiagnosed that exact shape as "a crashed land left dirt" and
    burned their budget looking for one; naming the real cause
    explicitly is the fix."""
    from frob.tickets._land_git_ops import _porcelain_dirty_paths, describe_root_dirt

    dirty_paths = _porcelain_dirty_paths(root)
    if _dirt_owned_by_no_open_ticket(root, dirty_paths):
        _log.error(
            "land: %s refused -- %s has uncommitted work belonging to "
            "NO open ticket's scope: %s; this is NOT a crashed land -- "
            "whoever owns the root checkout directly (most often the "
            "coordinator) must commit or stash it, an agent cannot fix "
            "this by retrying (git -C %s status), then retry `frob "
            "ticket land %s --worktree %s`",
            ticket_id,
            root,
            describe_root_dirt(root),
            root,
            ticket_id,
            worktree,
        )
    else:
        _log.error(
            "land: %s refused -- %s has uncommitted changes in: %s; "
            "commit or stash them first (git -C %s status), then "
            "retry `frob ticket land %s --worktree %s`",
            ticket_id,
            root,
            describe_root_dirt(root),
            root,
            ticket_id,
            worktree,
        )


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
    identical path (T-0795), OR (T-1638) if `root` -- while different from
    `worktree` -- is itself some OTHER registered worktree of the same
    repository rather than the true primary checkout.

    Before this check, the root==worktree condition fell through all the
    way to `_worktree_full_changeset`'s much later T-0640/T-0761 diagnosis
    ("`--worktree` almost certainly points at the SAME checkout/branch
    `root` has checked out ... create a real feature branch") -- correct
    for a worktree genuinely pointed at the wrong branch, but misleading
    for the far more common real cause: `root` defaults to `cfg.
    ticket_path or Path(".")` (the invoker's CWD), so running `frob
    ticket land <id> --worktree <path>` from A SHELL SITTING INSIDE THE
    WORKTREE (rather than the shared root checkout) makes `root` resolve
    to `worktree` for free, no misconfigured `--worktree` involved.
    Refusing here, before `_land_merge_stage` runs any git mutation, names
    the actual mistake immediately instead of sending an agent chasing
    the T-0640 "create a real feature branch" remedy for a worktree that
    was never the problem.

    T-1638: `root` defaulting to cwd has a second, more dangerous shape
    the root==worktree check above never catches -- a shell whose cwd sat
    inside worktree A (a DIFFERENT ticket's worktree, not the one being
    landed) runs `frob ticket land <id> --worktree B`. `root` (A) and
    `worktree` (B) are trivially unequal, so the check above passes clean,
    yet `root` is still wrong: it silently treats A -- a linked worktree,
    not the shared primary checkout -- as though it were "main", merging
    B's branch into A's own checked-out branch instead of the real one.
    Caught the same way T-1003 (`land`'s own caller) resolves the
    root==worktree case: `_resolve_primary_checkout(root)` asks git's own
    `--git-common-dir` what the TRUE primary checkout is; if that differs
    from `root` itself, `root` is a linked worktree, not the primary, and
    this refuses rather than silently substituting the resolved primary
    -- unlike the T-1003 case (where cwd-inside-`worktree` unambiguously
    means "the caller forgot to cd out", so auto-resolving is safe), a
    root that is some THIRD worktree is genuinely ambiguous: the caller's
    intent might have been to land into that worktree's own branch, so
    guessing silently risks merging into the wrong repository exactly
    like the incident this ticket records.

    Reuses `LandError.IncompleteLand` for both shapes (no new enum
    variant -- both are "this land cannot proceed as configured, nothing
    was committed" outcomes; the log message, not the enum tag, carries
    the corrected diagnosis) rather than the true-same-branch check
    (`_worktree_full_changeset`'s merge-base-equals-HEAD test), which
    still fires unchanged for a distinct-but-branchless worktree path
    further down the pipeline."""
    if root == worktree:
        _log.error(
            "land: %s refused -- root (%s) and --worktree (%s) resolve to "
            "the IDENTICAL path. This is almost always caused by running "
            "`frob ticket land` from a shell whose cwd is INSIDE the "
            "worktree (`root` defaults to cwd) rather than a --worktree "
            "pointed at the wrong branch. Run `frob ticket land %s "
            "--worktree %s` from the ROOT checkout instead -- cd out of "
            "%s first, then retry",
            ticket_id,
            root,
            worktree,
            ticket_id,
            worktree,
            worktree,
        )
        return Err(LandError.IncompleteLand)

    # frob:ticket T-1638
    primary = _resolve_primary_checkout(root)
    if primary is not None and primary != root:
        _log.error(
            "land: %s refused -- root (%s) is not the primary checkout; "
            "it is itself a DIFFERENT registered worktree of this "
            "repository (its own primary checkout resolves to %s). "
            "--worktree (%s) names yet a third path. This is almost "
            "always caused by running `frob ticket land` from a shell "
            "whose cwd is sitting inside ANOTHER ticket's worktree rather "
            "than the shared root checkout -- cd to %s (or pass it as "
            "root) first, then retry `frob ticket land %s --worktree %s`",
            ticket_id,
            root,
            primary,
            worktree,
            primary,
            ticket_id,
            worktree,
        )
        return Err(LandError.IncompleteLand)

    return Ok(None)


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
    own_findings = _restrict_to_branch_own_files(
        worktree, ticket_id, main_branch, found.danger_ok
    )
    if own_findings:
        from frob.tickets._land_git_ops import _commits_touching_path

        # frob:ticket T-1799
        # Name the ACTUAL commit(s) that touched each offending file --
        # not a guess at who wrote them -- so "revert the offending
        # commit" names something concrete instead of sending an agent to
        # reconstruct it by hand.
        attribution = {
            file: _commits_touching_path(worktree, main_branch, file)
            for file, _rule in own_findings
        }
        _log.error(
            "land: %s refused -- branch history (commits since merge-base "
            "%s) contains frob:waive deletion(s) outside scope %s and "
            "undeclared by the Done report: %s (real commits touching "
            "each file since %s: %s). If intentional, add the file to "
            "the ticket's scope or name it/the rule in the Done report; "
            "if accidental, revert the offending commit on this branch "
            "before retrying `frob ticket land %s --worktree %s`",
            ticket_id,
            merge_base.danger_ok,
            list(ticket.scope),
            [f"{file}:{rule}" for file, rule in own_findings],
            main_branch,
            attribution,
            ticket_id,
            worktree,
        )
        return Err(LandError.OutOfScopeWaiveDeletion)
    return Ok(None)


# frob:ticket T-1922
# frob:doc docs/modules/tickets-landing.md#outofscopewaivedeletion-false-refusal-on-a-stale-worktree-t-1922  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal.test_unrelated_upstream_waiver_reword_on_a_file_this_branch_never_touched_does_not_refuse  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal.test_a_genuine_committed_deletion_the_branch_made_itself_still_refuses  # noqa: E501
def _restrict_to_branch_own_files(
    worktree: Path,
    ticket_id: str,
    main_branch: str,
    findings: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, str], ...]:
    """T-1922: `_committed_waive_deletions`'s T-1550 two-dot diff
    (`main_branch..HEAD`) is a plain CONTENT diff between two commits, not
    an ancestry-scoped one -- it reports a line as "deleted" whenever
    `main_branch`'s CURRENT tip has it and `HEAD` does not, regardless of
    WHICH side actually changed. When `main_branch` has moved forward
    (an unrelated, already-landed ticket edited a `frob:waive` comment's
    text on a file this branch never touched at all) while this worktree
    has not yet merged that forward, the two-dot diff reads main's own
    new text as though HEAD deleted it -- attributing an entirely
    unrelated, already-landed edit to whichever ticket happens to retry a
    land next, off a worktree whose last `git merge main` predates it.
    The real 2026-08 incident: T-1918 reworded an `AFFECT001` waiver's
    reason string in `_renumber_v2.py`; two UNRELATED worktrees
    (T-1911's, T-1904's), neither of which had ever touched that file,
    both got refused with `OutOfScopeWaiveDeletion` naming it, purely
    because their own merge-base predated T-1918's land. The confirmed
    workaround (`git merge main` immediately before retrying) worked
    every time specifically because it moved the two-dot diff's LEFT side
    forward past the unrelated edit -- it never touched what the check
    was actually measuring.

    T-1550's own two-dot-against-live-tip design is NOT reverted here --
    it is exactly what makes an already-landed SIBLING ticket's deletion
    (on this same branch) invisible once main independently reflects the
    same state (`_committed_waive_deletions`'s own T-1550 docstring).
    Replacing it with a naive three-dot `main_branch...HEAD` diff
    (ancestry-scoped, i.e. re-diffing from the STALE fork point) would
    silently UNDO that fix and reintroduce the T-1225/T-1444 re-
    attribution bug T-1550 closed -- a worktree that has not rebased
    keeps the same old merge-base either way, so a three-dot diff from it
    would show the sibling's already-landed commits all over again.

    The actual missing filter is orthogonal to both: does `findings`'
    file even belong to something THIS BRANCH'S OWN COMMITS changed at
    all? `_branch_changed_files(worktree, main_branch)` (the same
    three-dot `main_branch...HEAD` --name-only diff `_check_cross_ticket_
    leakage` already uses for an identical "what did this branch itself
    commit" question) answers exactly that, independent of content
    equality -- a file this branch's own history never touched can never
    appear in it, no matter how stale the worktree's last merge is or how
    much main has moved. `findings` entries whose file is NOT in that set
    are dropped here: they are provably not this branch's own doing, only
    an artifact of the two-dot diff's content-comparison semantics
    picking up main's independent evolution. A finding whose file DOES
    appear in `_branch_changed_files` is kept unchanged -- this never
    weakens the check for a deletion the branch genuinely committed
    itself, including the T-1550 already-landed-sibling case (which is
    still excluded upstream, by the two-dot diff itself showing no delta
    once main already reflects it, not by this filter).

    Best-effort: a `_branch_changed_files` failure (git spawn error, no
    merge-base) degrades to the pre-T-1922 UNFILTERED findings, logged at
    WARNING -- this filter can only ever narrow a refusal, never widen
    one, so failing open here means "fall back to the old, occasionally
    over-broad behavior", never "silently drop a real finding this branch
    committed itself"."""
    if not findings:
        return findings
    own_changed = _branch_changed_files(worktree, main_branch)
    if own_changed.is_err:
        _log.warning(
            "land: %s could not compute this branch's own touched-file "
            "set (%s) to narrow the T-1922 committed-waive-deletion scan "
            "-- falling back to the unfiltered (possibly stale-merge-base "
            "over-broad) finding set",
            ticket_id,
            own_changed.danger_err,
        )
        return findings
    changed = own_changed.danger_ok
    return tuple((file, rule) for file, rule in findings if file in changed)


# frob:ticket T-1681
def _land_is_rapid(worktree: Path, ticket_id: str) -> bool:
    """Whether `worktree` runs the `rapid` profile, recording the
    relaxation as debt when it does (T-1681). Best-effort: an unreadable
    profile resolves to NOT rapid, so a broken config can only make the
    land stricter."""
    from frob.tickets._evidence import record_rapid_debt
    from frob.tickets._profile import ProfileName, effective_profile

    resolved = effective_profile(worktree)
    if not (resolved.is_ok and resolved.danger_ok is ProfileName.RAPID):
        return False
    record_rapid_debt(worktree, ticket_id, "land-evidence-scope-unbound")
    return True


def _validate_scope_covered_preflight(
    ticket: Ticket,
    covers_scope: Callable[[Ticket], bool | None] | None,
    *,
    rapid: bool = False,
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
    if covers_scope(ticket) is False and rapid:
        _log.warning(
            "land: %s landing with no evidence id covering a touched/scope "
            "symbol -- profile=rapid (T-1681), recorded in rapid-debt.jsonl",
            ticket.id,
        )
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


# frob:ticket T-2215
_BUG003_WAIVER_RE = re.compile(r'frob:waive\s+BUG003\s+reason="([^"]*)"')


# frob:ticket T-2215
# frob:tests tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWaiver.test_reason_present_suppresses  # noqa: E501
# frob:tests tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWaiver.test_bare_directive_without_reason_does_not_suppress  # noqa: E501
def _must_still_pass_waiver_reason(ticket: Ticket) -> str | None:
    """The `reason="..."` text of a `frob:waive BUG003 reason="..."` line
    found anywhere in `ticket.body`, or `None` if no such (well-formed)
    waiver is present. Mirrors `frob.gates._mutation_evidence.
    _bug002_waiver_reason`'s body-text-directive shape exactly (same
    regex form, same "malformed directive does not suppress" posture),
    but lives here rather than in `_mutation_evidence.py`: T-2193 (which
    built `must_still_pass_violations`/BUG003 itself) declared its own
    scope as that single gate module alone, so this wiring ticket's own
    scope (`_land.py`, `_close_cmd.py`, `_waive.py`) is where BUG003's
    land/close-time escape hatch has to live instead."""
    match = _BUG003_WAIVER_RE.search(ticket.body)
    return match.group(1) if match else None


# frob:ticket T-2215
# frob:tests tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWiring.test_land_refuses_when_control_broke_at_fix  # noqa: E501
# frob:tests tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWiring.test_land_succeeds_when_gate_reports_clean  # noqa: E501
# frob:tests tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWaiver.test_reason_present_suppresses  # noqa: E501
def _must_still_pass_land_violations(
    root: Path, ticket: Ticket, base_ref: str
) -> tuple[Violation, ...]:
    """T-2215: wires `frob.gates.must_still_pass_violations` (BUG003,
    T-2193) into the land path -- the positive-direction control that had
    zero callers before this ticket. Runs unconditionally (BUG003 is not
    kind-restricted -- see that function's own docstring: absence of a
    `frob:must-still-pass` directive in `ticket.body` is always `()`, for
    any kind, so this call is a no-op for the overwhelming majority of
    tickets that never declare the directive) and applies the same
    `frob:waive BUG003 reason="..."` body-text escape hatch BUG002 uses
    (`_must_still_pass_waiver_reason` above) -- a waived finding is still
    logged at WARNING, never silently dropped, mirroring
    `_mutation_evidence_synchronous`'s own `--skip-mutation-evidence`
    logging posture for BUG002/TEST016."""
    # T-2230: `must_still_pass_violations` is now re-exported from the
    # `frob.gates` package surface (was a deep import into the private
    # `_mutation_evidence` submodule, an asymmetric omission alongside
    # `bug_repro_violations`/`mutation_evidence_violations` T-2193's own
    # land left unfixed -- see T-2230's Done report for the measured
    # gap).
    from frob.gates import must_still_pass_violations

    violations = must_still_pass_violations(root, ticket, base_ref)
    if not violations:
        return ()
    waiver_reason = _must_still_pass_waiver_reason(ticket)
    if waiver_reason is not None:
        for v in violations:
            _log.warning(
                "land: %s BUG003 finding waived (reason=%r): %s",
                ticket.id,
                waiver_reason,
                v.message,
            )
        return ()
    return violations


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

    T-2215 additionally wires `frob.gates.must_still_pass_violations`
    (BUG003, T-2193) alongside BUG002 in both the deferred and
    synchronous branches below (`_must_still_pass_land_violations`) --
    same ERROR-always severity posture, same
    `frob:waive BUG003 reason="..."` body-text escape hatch shape as
    BUG002's own `_BUG002_WAIVER_RE`, not kind-restricted (unlike
    BUG002/TEST016: BUG003 fires for any kind that declares a
    `frob:must-still-pass` directive).

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
# frob:ticket T-2215
# frob:tests tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassCombinesWithBug002.test_land_deferred_refuses_on_bug003_alone  # noqa: E501
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
    bug002_only = bug_repro_violations(
        worktree, ticket, base_ref
    ) + _must_still_pass_land_violations(worktree, ticket, base_ref)
    errors = [v for v in bug002_only if v.severity == "error"]
    for v in bug002_only:
        _log.warning("land: %s %s %s", ticket.id, v.rule, v.message)
    if errors:
        _log.error(
            "land: %s cannot land -- %d BUG002/BUG003 finding(s) (kind=%s); "
            "TEST016 was deferred to the batch mutation sweep, BUG002/"
            "BUG003 are unaffected and still block",
            ticket.id,
            len(errors),
            ticket.kind,
        )
        return Err(LandError.EvidenceConfirmatoryOnly)
    return Ok(None)


# frob:ticket T-1593
# frob:ticket T-2215
# frob:tests tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassCombinesWithBug002.test_land_synchronous_refuses_on_bug003_alone  # noqa: E501
def _mutation_evidence_synchronous(
    worktree: Path, ticket: Ticket, base_ref: str, skip: bool
) -> Result[None, LandError]:
    """Synchronous half of `_check_mutation_evidence` (T-1593 split): run
    the actual TEST016 mutation subprocess plus BUG002 and classify the
    result, including the `--skip-mutation-evidence` override -- pure
    extraction of the original `else` branch body, unchanged."""
    from frob.gates import bug_repro_violations, mutation_evidence_violations

    violations = (
        mutation_evidence_violations(worktree, ticket, base_ref)
        + bug_repro_violations(worktree, ticket, base_ref)
        + _must_still_pass_land_violations(worktree, ticket, base_ref)
    )
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


# frob:ticket T-1856
# frob:doc docs/modules/tickets.md#public-api
# frob:tests \
# tests/test_tickets_live_tracker.py::TestAnchorMarker.test_terminal_land_refused
def _refuse_anchor_terminal_land(ticket: Ticket) -> Result[None, LandError]:
    """T-1856: refuse a land that would move an `anchor=True` ticket to a
    TERMINAL state (`done`/`dropped`), unconditionally -- the first-class
    twin of `_check_live_tracker_citations`'s inferred-from-a-live-grep
    check. An anchor ticket's entire purpose is to sit open forever as a
    valid `follow_up="<id>"` target for a PERMANENT `frob:waive`
    (WIRE002 disqualifies terminal targets, T-1490/T-1488's 16-waiver-
    orphan incident, `docs/modules/gates.md`'s T-1558 "waiver home"
    precedent) -- T-1853's body records the near-miss this closes: an
    agent was instructed to close T-1820 "to drain the queue," and it was
    caught only by a different agent noticing prose in the body, not by
    the tool. A land that leaves the ticket non-terminal
    (`queued`/`in-progress`/`blocked`) is unaffected, same posture
    `_check_live_tracker_citations` already established for the citation
    check it complements."""
    from frob.tickets._models import TicketState

    if not ticket.anchor:
        return Ok(None)
    if ticket.state not in (TicketState.DONE, TicketState.DROPPED):
        return Ok(None)
    _log.error(
        "land: %s cannot land as %s -- it is marked anchor=True (%s) and "
        "must never reach a terminal state; clear the marker first via "
        "set_anchor(root, %s, anchor=False, reason=...) if it genuinely "
        "no longer needs to anchor a waiver, or land it as "
        "queued/in-progress/blocked instead",
        ticket.id,
        ticket.state,
        ticket.anchor_reason,
        ticket.id,
    )
    return Err(LandError.AnchorTerminalLand)


# frob:ticket T-1856
# frob:doc docs/modules/tickets.md#public-api
# frob:tests \
# tests/test_tickets_live_tracker.py::TestAnchorMarker.test_set_anchor_requires_reason
# frob:tests \
# tests/test_tickets_live_tracker.py::TestAnchorMarker.test_set_anchor_round_trips
def set_anchor(
    root: Path, ticket_id: str, *, anchor: bool, reason: str
) -> Result[Ticket, TicketError]:
    """`frob ticket anchor <id> --set/--clear --reason TEXT` (CLI wiring
    is a follow-up, see T-1856's Done report): set or clear the `anchor`
    marker in one ledger-locked write, mirroring `set_scope_breadth_ack`'s
    (T-1484) "no silent flag flip" shape -- a blank/whitespace-only
    `reason` is rejected the same way. Declaring intent explicitly here is
    the whole point of T-1856: before this existed, nothing stopped a
    well-meaning agent from closing a permanent-waiver-anchor ticket in
    the name of draining the queue (the T-1820 near-miss T-1853's body
    documents)."""
    from frob.tickets import _load_ticket_and_queue
    from frob.tickets._store import ledger_lock, write_ticket
    from frob.tickets._worktree_guard import enforce_worktree_lease

    if not reason.strip():
        return Err(TicketError.AnchorReasonMissing)
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)

    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok
        updated = ticket.model_copy(
            update={
                "anchor": anchor,
                "anchor_reason": reason if anchor else None,
            }
        )
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info("tickets: %s anchor set to %s (reason=%s)", ticket_id, anchor, reason)
    return Ok(updated)


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
    exemption was rejected as gameable in favor of this diff-aware one.

    T-1853: only fires when `ticket.state` is TERMINAL (`done`/`dropped`).
    An anchor ticket -- one whose entire purpose is to sit open forever so
    a permanent-by-design `frob:waive ... follow_up="<id>"` has a valid,
    non-orphaning target (WIRE002 disqualifies `done`/`dropped` follow_up
    targets, the T-1490/T-1488 16-waiver-orphan incident) -- is cited by
    design and never stops being cited. Refusing EVERY land of such a
    ticket, including a `queued`/`in-progress`/`blocked` land that
    threatens no citation at all, made its own ledger record (a `fail`
    attempt log, a scope change, an evidence binding) permanently
    unlandable -- a silent data-loss path of the same shape T-1818 closed
    for fail records generally. A land that leaves the ticket
    non-terminal cannot orphan the citation it is refusing over, so this
    check is skipped for it; a land that WOULD move the ticket to
    `done`/`dropped` still needs the citations resolved first."""
    from frob.tickets._live_tracker import live_tracker_citations
    from frob.tickets._models import TicketState

    if ticket.state not in (TicketState.DONE, TicketState.DROPPED):
        return Ok(None)

    citations = live_tracker_citations(worktree, ticket.id, base_ref=base_ref)
    if not citations:
        return Ok(None)
    _log.error(
        "land: %s cannot land as %s -- %d site(s) still cite it as their "
        "live tracker (registry deferred:/tracked_by: disposition or a "
        "waiver ticket= attribute): %s -- if this ticket is meant to stay "
        "open forever as a permanent waiver anchor, land it as "
        "queued/in-progress/blocked instead of %s; otherwise file a "
        "successor ticket and re-point these rows, or re-point them in "
        "this same change, then retry `frob ticket land %s`",
        ticket.id,
        ticket.state,
        len(citations),
        list(citations),
        ticket.state,
        ticket.id,
    )
    return Err(LandError.LiveTrackerCited)


# frob:ticket T-1355
def _branch_changed_files(
    worktree: Path, base_ref: str, ref: str = "HEAD"
) -> Result[frozenset[str], LandError]:
    """THE canonical answer to "which files did THIS BRANCH'S OWN COMMITS
    change" (T-1966): the set of paths `ref` (default `HEAD`, i.e.
    `worktree`'s currently checked-out branch) has committed changes to
    since it diverged from `base_ref` (T-1355), via `git diff --name-only
    <base_ref>...<ref>` (three-dot: the merge-base diff, so a worktree
    that has since merged `base_ref` back in does not report every file
    `base_ref` itself touched -- T-1550/T-1922's own lesson). `Err
    (GitFailed)` on a git failure; an empty set (never an error) when the
    branch has committed nothing new.

    T-1966: this used to have a second, independent implementation in
    `frob.tickets._unlanded` (`_branch_own_changed_files`, T-1955's own
    fix for the SAME two-dot/three-dot lesson landing a second time in a
    different consumer) -- that module now delegates here instead of
    keeping its own `git diff` spawn. The `ref` parameter (added for that
    consolidation, defaulting to `HEAD` so every existing `_land.py` call
    site is unaffected) is what makes one function serve both shapes: a
    `_land.py` caller runs `worktree` checked out AT the branch already
    (land-time, implicit `HEAD`), while `_unlanded.py`'s shared-root scan
    needs to diff an ARBITRARY branch name from whatever `root` happens
    to be checked out to right now -- passing `ref=<branch name>`
    explicitly makes that not require a checkout at all, since `git diff`
    only needs the ref to exist, never to be checked out."""
    diffed = run_argv(
        ["git", "-C", str(worktree), "diff", "--name-only", f"{base_ref}...{ref}"]
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


# frob:ticket T-1675
def _ledger_ticket_at_ref(worktree: Path, ref: str, ticket_id: str) -> Ticket | None:
    """`ticket_id`'s ticket record as it exists in the ledger AT `ref`
    itself (T-1675), read directly via `git show <ref>:tickets.md` -- the
    primitive `_ledger_ticket_at_merge_base` below builds on for the
    fork-point variant. Returns `None` when the ref/ledger is unreadable
    or the id does not exist there (never landed, or landed under a
    different id) -- callers decide what `None` means for their own
    check; this function only ever reports what it can positively read."""
    from frob.tickets._store import _parse_ledger

    shown = run_argv(["git", "-C", str(worktree), "show", f"{ref}:tickets.md"])
    if shown.is_err or shown.danger_ok.returncode != 0:
        return None
    parsed = _parse_ledger(shown.danger_ok.stdout)
    if parsed.is_err:
        return None
    return parsed.danger_ok.get(ticket_id)


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
    merge_base = run_argv(["git", "-C", str(worktree), "merge-base", base_ref, "HEAD"])
    if merge_base.is_err or merge_base.danger_ok.returncode != 0:
        return None
    sha = merge_base.danger_ok.stdout.strip()
    if not sha:
        return None
    return _ledger_ticket_at_ref(worktree, sha, ticket_id)


# frob:ticket T-1855
def _scope_claim_reason(path: str, ticket: Ticket) -> str:
    """Classify WHY `path` is in `ticket`'s effective scope: `"declared"`
    (an explicit glob in `ticket.scope`, including the always-on
    ledger/own-shard rules), `"implicit-cli-wiring"` (matches ONLY via the
    FEATURE-kind `CLI_WIRING_FILES` grant, T-0446/T-1848), or
    `"unclaimed"` (matches neither -- callers should not normally reach
    this branch, since they only call this on a known hit).

    T-1855: "declared" and "implicit-cli-wiring" are different problems
    with different remedies -- a declared-scope hit is fixable by
    `frob ticket scope --remove`; an implicit-cli-wiring hit is not (the
    grant is a function of `ticket.kind`, not the declared glob list), so
    a refusal or `frob ticket show` that collapses both into one
    undifferentiated `scope=[...]` list sends an agent to fix the wrong
    thing. Ledger/own-shard always-on rules are folded into "declared"
    here (they are unconditional, not kind-gated, so there is nothing an
    agent could narrow to lose them -- the CLI-wiring/declared split is
    the one that matters for a fixable remedy)."""
    from frob.tickets._models import scope_matches

    if scope_matches(path, ticket.scope, ticket_id=ticket.id):
        return "declared"
    if scope_matches(path, ticket.scope, kind=ticket.kind, ticket_id=ticket.id):
        return "implicit-cli-wiring"
    return "unclaimed"


# frob:ticket T-1855
def _explicitly_used_wiring_path(other: Ticket, path: str) -> bool:
    """T-1855 grant-on-use: whether `other` has actually put `path` to use
    -- either via an explicit `frob ticket scope --add` audited in
    `other.scope_changes` (a `ScopeChangeOp.ADD` entry whose glob overlaps
    `path`), or because `path` is already part of `other`'s OWN declared
    scope (checked by the caller via `_scope_claim_reason` before this is
    ever consulted). Used to downgrade an implicit-CLI-wiring-only hit
    from "leaked" to "never actually used" in `_leaked_hits_for_candidate`
    -- the FEATURE-kind grant exists so a ticket CAN reach a wiring file
    without ceremony, not so every open FEATURE ticket permanently reserves
    it against every sibling's land whether or not it ever touched it."""
    from frob.tickets._models import _globs_intersect

    for entry in other.scope_changes:
        if entry.op.value == "add" and _globs_intersect(entry.glob, path):
            return True
    return False


# frob:ticket T-2111
def _effective_leakage_scope(
    root: Path, other_id: str, other: Ticket
) -> tuple[str, ...]:
    """T-2111: the scope `_leaked_hits_for_candidate` should test against
    for sibling `other_id` -- `other`'s DECLARED scope, unless a LIVE
    cross-worktree lease (`read_all_leases`, T-0473) for the same id is
    currently recorded, in which case the lease's own scope wins.

    T-2095 already established this precedent for `_scope_add_conflicts`
    (a narrowing published to the live lease side-channel takes effect
    for the fleet immediately, without waiting for that ticket's own
    land) -- this check answered the SAME question ("which files does
    `other_id` claim?") from a DIFFERENT, stale source: `worktree`'s (or
    `root`'s) copy of `other`'s ledger record, which only reflects a
    narrowing once something merges it back in. Measured 2026-08-11: a
    ticket narrowed its scope, the narrowing published to its lease file
    immediately, and `frob ticket land` for an UNRELATED ticket touching
    the released path still refused with `CrossTicketLeakage` naming the
    stale declared scope -- a narrowing that already freed a file still
    blocked every other ticket on it until the narrowing ticket's own
    land, exactly defeating the reason to narrow at all. The live lease
    is authoritative when present (it is the single side-channel every
    OTHER `frob ticket` verb already trusts for "what does this ticket
    currently claim") -- never unioned with the declared scope, since a
    union could only ever keep the stale, broader path alive."""
    for lease in read_all_leases(root):
        if lease.ticket_id == other_id:
            return lease.scope
    return other.scope


# frob:ticket T-1390
# frob:ticket T-1855
def _leaked_hits_for_candidate(
    root: Path,
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
    change to any exemption's own semantics) -- requires BOTH a
    scope hit against `changed_paths` AND `other`'s own ledger record to
    have actually changed since this branch forked from `base_ref`
    (T-1390, via `_ledger_ticket_at_merge_base`) -- a scope hit alone is
    never enough; see `_find_leaked_tickets`'s own docstring for the
    false-positive class this second requirement closes.

    T-1967: a sibling leased to the SAME worktree as `landing_id` used to
    be exempted here unconditionally (T-1370) -- "one agent landing its
    own tickets back to back, not a real cross-agent leak". Measured
    2026-08-10: that exemption is exactly the guard hole that let a
    docs-only ticket's land silently carry a sibling's ENTIRE production
    change (T-1958 carrying T-1956's `_evidence.py`/`_models.py`/
    `_new_gate_rule_acceptance.py` plus its own tests and Done report)
    onto main with no flag and no warning printed at all -- sharing a
    worktree across a ticket series is the NORMAL dispatch pattern here,
    which made this the default configuration, not an edge case. Removed:
    a same-worktree sibling with real committed hits now flows into the
    exact same `leaked` reporting/refusal path a cross-worktree sibling
    already does (`_report_leaked_tickets`), so carrying it either
    requires the existing `--allow-cross-ticket` acknowledgment (an
    affirmative, logged statement for a genuinely intentional joint land)
    or refuses. This does not reintroduce T-1370's original deadlock
    concern: a sibling only ever counts as leaked once it is genuinely
    `IN_PROGRESS` with real content change since the fork (see
    `_find_leaked_tickets`), and the moment the first of two mutually-
    scoped same-worktree tickets lands (with `--allow-cross-ticket`, or
    because the second was never actually started), the second's own
    later land finds the first already `DONE` and exempt -- there is
    always a way through, it just now requires being told.

    T-1855 grant-on-use: a hit that matches ONLY via the implicit
    FEATURE-kind CLI-wiring grant (`_scope_claim_reason` returns
    `"implicit-cli-wiring"`) is dropped UNLESS `other` has actually put
    that path to use (`_explicitly_used_wiring_path`) -- the blanket
    grant-on-kind used to let any open FEATURE ticket permanently reserve
    `__main__.py`/`config.py`/`ticket_runner/__init__.py` against every
    sibling's land whether or not it had ever touched them."""
    from frob.tickets._models import scope_matches

    # frob:ticket T-2111
    effective_scope = _effective_leakage_scope(root, other_id, other)
    hits = [
        path
        for path in changed_paths
        if scope_matches(path, effective_scope, kind=other.kind)
    ]
    kept: list[str] = []
    for path in hits:
        if _scope_claim_reason(path, other) != "implicit-cli-wiring":
            kept.append(path)
            continue
        if _explicitly_used_wiring_path(other, path):
            kept.append(path)
            continue
        _log.info(
            "land: %s cross-ticket leakage check exempting %s's claim on "
            "%s (T-1855 grant-on-use: only the implicit FEATURE-kind "
            "CLI-wiring grant covers this path, and %s has never actually "
            "used it -- an unused implicit grant is not a real claim)",
            landing_id,
            other_id,
            path,
            other_id,
        )
    hits = kept
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
# frob:ticket T-1639
# frob:ticket T-1967
# frob:doc \
# docs/modules/tickets-landing.md#cross-ticket-leakage-only-refuses-on-an-in_progress-s\
# ibling-t-1639
def _find_leaked_tickets(
    root: Path,
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

    T-1370/T-1967: a sibling ticket LEASED TO THE SAME WORKTREE as
    `landing_id` used to be exempted here unconditionally, no matter its
    state (`_scope._same_worktree_lease`, the exact T-1356 precedent this
    mirrored) -- "two tickets sharing one series worktree is one agent
    landing its own tickets back to back, not a real cross-agent leak".
    T-1967 found and removed that exemption: it was the exact silent
    guard hole that let a docs-only ticket's land carry a sibling's
    entire production change onto main with no flag and no warning at
    all, because sharing a worktree across a ticket series is the
    NORMAL, endorsed dispatch pattern here, not an edge case. A
    same-worktree sibling now goes through the SAME `IN_PROGRESS` +
    ledger-record-changed gate as any other candidate below, and a real
    hit against it flows into the same refusal/`--allow-cross-ticket`
    path as a cross-worktree leak. This does not reintroduce the
    mutual-deadlock concern T-1370 originally worried about: a hit only
    ever exists once a sibling has genuinely been worked on this branch,
    and `--allow-cross-ticket` remains the explicit, logged way through
    for a genuinely intentional joint land.

    T-1639: a scope hit is only ever REFUSED when the sibling is
    `IN_PROGRESS` -- the same "declared scope is a claim only once a
    ticket is actually being worked" line `frob.tickets._leases` already
    draws (a lease exists ONLY for an `IN_PROGRESS` ticket, never a
    queued/planned/blocked one). `QUEUED`/`PLANNED`/`BLOCKED` siblings
    scope-match all the time -- filing a ticket with a broad, honestly-
    generous scope used to reserve that scope against every other land
    immediately, before a single commit existed for it (measured
    2026-08-06: a freshly filed, unstarted ticket blocked an unrelated
    land over 12 files that only overlapped by declaration). A hit
    against a non-`IN_PROGRESS` sibling is still surfaced -- at INFO, not
    the ERROR `_report_leaked_tickets` logs for a real refusal -- naming
    the ticket and its state, so the overlap is disclosed without being
    treated as evidence of a concurrent writer. This does not touch the
    T-1618 case CrossTicketLeakage exists for (a shared series worktree
    carrying a sibling's COMMITTED work onto main): that shape always
    involves a sibling that was actually started, so it is always
    `IN_PROGRESS` (or already `DONE`/`DROPPED`, both already exempted
    above) by the time it could leak anything.

    T-1999: `IN_PROGRESS` here means `frob.tickets._leases.
    is_effectively_in_progress` -- state alone is not enough. `root`'s
    ledger only observes a worktree's `IN_PROGRESS` transition once
    something merges/lands that worktree's copy of `tickets.md` back in,
    so a sibling that took its lease locally but has not yet been
    observed by `root` used to read as `planned`/`queued` here and slip
    through unrefused (T-1977's land of `f3257572a`, the measured
    T-1999 repro). `is_effectively_in_progress` also treats a live
    cross-worktree lease (`read_all_leases`) as `IN_PROGRESS`, closing
    that window without touching the DONE/DROPPED skip above or the
    genuinely-dormant (no lease, no IN_PROGRESS state) case T-1639
    already carved out."""
    from frob.tickets._leases import is_effectively_in_progress
    from frob.tickets._models import TicketState

    leaked: dict[str, list[str]] = {}
    for other_id, other in worktree_tickets.items():
        if other_id == landing_id:
            continue
        ledger_state = (
            root_tickets[other_id].state if other_id in root_tickets else other.state
        )
        if ledger_state in (TicketState.DONE, TicketState.DROPPED):
            continue
        # frob:ticket T-2111
        if not _effective_leakage_scope(root, other_id, other):
            continue
        hits = _leaked_hits_for_candidate(
            root, worktree, landing_id, other_id, other, changed_paths, base_ref
        )
        if not hits:
            continue
        # frob:ticket T-1999
        if not is_effectively_in_progress(root, other_id, ledger_state):
            # frob:ticket T-1639
            _log.info(
                "land: %s cross-ticket leakage check found %s (state=%s) "
                "scope-overlaps %d changed path(s), but %s is not "
                "IN_PROGRESS (ledger or live lease) -- a declared scope "
                "on a ticket nobody has started is an intention, not a "
                "claim; not refusing: %s",
                landing_id,
                other_id,
                ledger_state.value,
                len(hits),
                other_id,
                hits,
            )
            continue
        leaked[other_id] = hits
    return leaked


# frob:ticket T-1618
# frob:doc docs/modules/tickets-landing.md#passenger-ticket-disclosure-t-1618
_DIRECTIVE_TICKET_ID_RE = re.compile(r"frob:ticket\s+(T-[A-Za-z0-9_-]+)")


# frob:ticket T-2082
# frob:doc docs/modules/tickets-landing.md#passenger-ticket-disclosure-t-1618
def _passenger_ids_from_line_buckets(
    added_lines: dict[str, list[str]], removed_lines: dict[str, list[str]]
) -> frozenset[str]:
    """The T-2082 discriminator: which ids in `added_lines` (ticket id ->
    every added line naming it) are GENUINE passengers, given the matching
    `removed_lines` from the same diff.

    An id whose `+`-occurrence count strictly EXCEEDS its `-`-occurrence
    count is unambiguously a passenger (its count increased) -- this is
    exactly the 2026-08-05 WAIVE004 incident's shape: T-1579's code was
    physically ADDED with no matching removal, so old and new logic agree
    it must refuse. An id with EQUAL counts is exempted only when the
    exact MULTISET of added lines equals the exact multiset of removed
    lines (full text, whitespace included) -- i.e. the directive moved
    VERBATIM. A relocation that also edits the directive line itself in
    the same motion (folds it into another comment, reworks the line it
    sits on) keeps the same count but fails this verbatim check and is
    still reported: T-2082 deliberately errs toward refusing whenever the
    two sides are not an exact textual match, since a false refusal costs
    one `--allow-cross-ticket` flag and a false pass costs an incident.
    Do NOT weaken this to bare count equality."""
    passengers: set[str] = set()
    for directive_id, adds in added_lines.items():
        removes = removed_lines.get(directive_id, [])
        # frob:waive PERF004 reason="adds/removes are this directive_id's own small \
        # distinct per-id line list (typically 1-2 entries), not a shared collection \
        # re-sorted identically across iterations -- same posture as every other \
        # per-key-distinct-set PERF004 waiver in this codebase"
        if len(adds) > len(removes) or sorted(adds) != sorted(removes):
            passengers.add(directive_id)
        # else: equal counts AND identical line text on both sides -- a
        # pure relocation of a pre-existing directive. Not a passenger.
    return frozenset(passengers)


_HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _strip_ab_prefix(path: str) -> str:
    """Strip git diff's leading `a/`/`b/` path prefix, or return `path` unchanged."""
    if path.startswith(("a/", "b/")):
        return path[2:]
    return path


# frob:ticket T-2183
def _raw_tree_for_worktree_file(worktree: Path, rel_path: str):  # noqa: ANN202
    """`frob.lang.raw_tree`'s `Result` for `rel_path` as it currently
    sits on disk in `worktree` (HEAD content), or `None` if the path is
    not a real file there -- the `ref=None` half of `_raw_tree_for_ref`,
    split into its own function purely so neither half mixes ARCH103's
    I/O-plus-branching in one body."""
    from frob.lang import raw_tree

    source_path = worktree / rel_path
    if not source_path.is_file():
        return None
    return raw_tree(source_path)


# frob:ticket T-2183
def _raw_tree_for_temp_source(content: str, suffix: str):  # noqa: ANN202
    """`frob.lang.raw_tree`'s `Result` for `content`, materialized into a
    throwaway temp file (named with `suffix` so `frob.lang`'s extension
    dispatch still resolves the right grammar) and cleaned up
    afterwards -- the temp-file create/parse/cleanup half of
    `_raw_tree_for_ref_content`, split into its own function purely so
    neither half mixes ARCH103's I/O-plus-branching in one body."""
    import tempfile

    from frob.lang import raw_tree

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        return raw_tree(Path(tmp_path))
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# frob:ticket T-2183
def _raw_tree_for_ref_content(worktree: Path, ref: str, rel_path: str):  # noqa: ANN202
    """`frob.lang.raw_tree`'s `Result` for `rel_path`'s content at git
    revision `ref` (via `git show`), or `None` on a `git show` failure --
    the ref-content half of `_raw_tree_for_ref`, split into its own
    function purely so neither half mixes ARCH103's I/O-plus-branching
    in one body."""
    shown = run_argv(["git", "-C", str(worktree), "show", f"{ref}:{rel_path}"])
    if shown.is_err or shown.danger_ok.returncode != 0:
        return None
    return _raw_tree_for_temp_source(shown.danger_ok.stdout, Path(rel_path).suffix)


# frob:ticket T-2183
def _raw_tree_for_ref(worktree: Path, ref: str | None, rel_path: str):  # noqa: ANN202
    """`frob.lang.raw_tree`'s `Result` for `rel_path`, sourced from the
    worktree's current (HEAD) content on disk when `ref is None`
    (`_raw_tree_for_worktree_file`), or from that git revision's content
    otherwise (`_raw_tree_for_ref_content`) -- the I/O half of
    `_genuine_comment_lines`, dispatching to whichever source applies."""
    if ref is None:
        return _raw_tree_for_worktree_file(worktree, rel_path)
    return _raw_tree_for_ref_content(worktree, ref, rel_path)


# frob:ticket T-2183
def _comment_lines_in_tree(tree, language_label: str) -> frozenset[int]:  # noqa: ANN001
    """1-based line numbers `tree` places inside a real grammar COMMENT
    node, per `frob.lang.COMMENT_TYPES[language_label]` -- the pure
    tree-walk half of `_genuine_comment_lines`, split out from the I/O
    half (`_raw_tree_for_ref`) purely to keep each under ARCH001's line
    threshold."""
    from frob.lang import COMMENT_TYPES

    comment_types = COMMENT_TYPES.get(language_label, frozenset())
    if not comment_types:
        return frozenset()
    lines: set[int] = set()
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type in comment_types:
            lines.update(range(node.start_point[0] + 1, node.end_point[0] + 2))
        stack.extend(node.children)
    return frozenset(lines)


# frob:ticket T-2183
def _genuine_comment_lines(
    worktree: Path, ref: str | None, rel_path: str
) -> frozenset[int]:
    """1-based source line numbers of `rel_path` that fall inside a real
    grammar COMMENT node -- `ref=None` reads the worktree's current
    (HEAD) content, any other `ref` reads that git revision's content
    (`_raw_tree_for_ref` owns both I/O paths); `_comment_lines_in_tree`
    owns the actual tree-walk.

    Deliberately uses `frob.lang.COMMENT_TYPES` (the raw grammar
    comment-node set: python's `comment`, rust's `line_comment`/
    `block_comment`, etc.) and NOT `frob.lang._extract._DOCSTRING_
    COMMENT_WALKERS` -- T-0342's python docstring-directive walker treats
    a docstring's `frob:` line as directive-bearing for `frob.graph`'s
    doc-coverage/xref purposes, which is correct there (a docstring IS
    documentation), but is exactly the wrong answer for a PASSENGER
    check (T-2183): citing a historical ticket id in a docstring for
    context is the documentation practice this repo actively encourages,
    not a sign the diff carries that ticket's code. A path whose
    extension has no registered grammar (`.md`, `.toml`, ...) yields an
    empty set here -- `frob.lang.raw_tree` would return
    `Err(UnsupportedLanguage)` for it anyway, so prose in
    `tickets/**/*.md` (or any other unsupported-extension file) can
    never register as a comment-positioned line, regardless of what it
    says. Checked via `tree_sitter_extensions()` BEFORE calling
    `raw_tree` (rather than just letting that `Err` happen) so the
    overwhelmingly common per-land case -- `tickets.md`, touched by
    nearly every land -- never trips `frob.lang`'s own loud
    "no grammar registered" WARNING log line; that warning is meant to
    flag a genuinely unexpected unsupported path reaching a parse
    call, not to fire on every single land's routine ledger diff."""
    from frob.lang import tree_sitter_extensions

    if Path(rel_path).suffix.lower() not in tree_sitter_extensions():
        return frozenset()

    tree_result = _raw_tree_for_ref(worktree, ref, rel_path)
    if tree_result is None or tree_result.is_err:
        return frozenset()
    tree, _source, language_label = tree_result.danger_ok
    return _comment_lines_in_tree(tree, language_label)


# frob:ticket T-2183
class _DiffLineTracker:
    """Mutable per-diff scan state for `_bucket_directive_lines`'s
    sequential line-by-line walk (T-2183): the current file's old/new
    paths, each side's genuine-comment-line set, and each side's running
    1-based line counter, plus the id->added/removed-line buckets being
    built up. A tiny stateful class instead of a growing tuple of locals
    threaded through one large loop body, so each per-line-kind handler
    below can update just its own piece and stay under ARCH001's line
    threshold individually."""

    def __init__(self, worktree: Path, base_ref: str) -> None:
        """Fresh tracker for one `git diff` scan against `base_ref` in `worktree`."""
        self.worktree = worktree
        self.base_ref = base_ref
        self.added_lines: dict[str, list[str]] = {}
        self.removed_lines: dict[str, list[str]] = {}
        self.old_path: str | None = None
        self.new_comment_lines: frozenset[int] = frozenset()
        self.old_comment_lines: frozenset[int] = frozenset()
        self.new_lineno = 0
        self.old_lineno = 0

    def _on_file_header(self) -> None:
        """Reset per-file state at a `diff --git` boundary."""
        self.old_path = None
        self.new_comment_lines = frozenset()
        self.old_comment_lines = frozenset()

    def _on_old_path(self, raw: str) -> None:
        """A `--- ` header: resolve the old path and its `base_ref` comment-line set."""
        self.old_path = None if raw == "/dev/null" else _strip_ab_prefix(raw)
        self.old_comment_lines = (
            _genuine_comment_lines(self.worktree, self.base_ref, self.old_path)
            if self.old_path is not None
            else frozenset()
        )

    def _on_new_path(self, raw: str) -> None:
        """A `+++ ` header: resolve the new path and its HEAD comment-line set."""
        new_path = None if raw == "/dev/null" else _strip_ab_prefix(raw)
        self.new_comment_lines = (
            _genuine_comment_lines(self.worktree, None, new_path)
            if new_path is not None
            else frozenset()
        )

    def _on_hunk_header(self, match: re.Match[str]) -> None:
        """A `@@ -old +new @@` header: reset both sides' running line counters."""
        self.old_lineno = int(match.group(1))
        self.new_lineno = int(match.group(2))

    def _on_content_line(self, line: str) -> None:
        """A `+`/`-`/context line: bucket a directive-bearing `+`/`-` line
        only when its own position is a genuine comment, then advance
        whichever side's line counter(s) this line consumes."""
        if line.startswith("+"):
            text = line[1:]
            if self.new_lineno in self.new_comment_lines:
                for directive_id in _DIRECTIVE_TICKET_ID_RE.findall(text):
                    self.added_lines.setdefault(directive_id, []).append(text)
            self.new_lineno += 1
        elif line.startswith("-"):
            text = line[1:]
            if self.old_lineno in self.old_comment_lines:
                for directive_id in _DIRECTIVE_TICKET_ID_RE.findall(text):
                    self.removed_lines.setdefault(directive_id, []).append(text)
            self.old_lineno += 1
        else:
            self.new_lineno += 1
            self.old_lineno += 1


# frob:ticket T-2183
def _bucket_directive_lines(
    diff_text: str, worktree: Path, base_ref: str
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Walk `diff_text` (a `git diff base_ref...HEAD` unified diff) line by
    line via `_DiffLineTracker`, returning its final (added, removed)
    directive-id buckets -- the sequential-scan half of
    `_directive_ticket_ids_in_diff`, split out purely to keep that
    function's own body under ARCH001's line threshold."""
    tracker = _DiffLineTracker(worktree, base_ref)
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            tracker._on_file_header()
        elif line.startswith("--- "):
            tracker._on_old_path(line[4:])
        elif line.startswith("+++ "):
            tracker._on_new_path(line[4:])
        elif (hunk_match := _HUNK_HEADER_RE.match(line)) is not None:
            tracker._on_hunk_header(hunk_match)
        elif line.startswith("\\"):
            # "\ No newline at end of file" -- not a real source line on
            # either side, must not perturb the line-number counters.
            continue
        else:
            tracker._on_content_line(line)
    return tracker.added_lines, tracker.removed_lines


# frob:ticket T-1618
# frob:ticket T-2082
# frob:ticket T-2183
# frob:doc docs/modules/tickets-landing.md#passenger-ticket-disclosure-t-1618
def _directive_ticket_ids_in_diff(worktree: Path, base_ref: str) -> frozenset[str]:
    """Every ticket id named by a `frob:ticket <id>` directive that is a
    GENUINE passenger of `worktree`'s full committed diff against
    `base_ref` (T-1618, discriminator fixed T-2082 -- see
    `_passenger_ids_from_line_buckets` for the exact rule) -- `git diff
    base_ref...HEAD`, the three-dot merge-base diff, NOT `--name-only`
    like `_branch_changed_files` (T-1355) uses: this needs the actual
    hunk CONTENT, since a `frob:ticket` directive is a source line, not a
    file path.

    This is a deliberately DIFFERENT, complementary signal from
    `_check_cross_ticket_leakage`'s scope-glob-plus-ledger-record-diff
    heuristic (T-1355/T-1390/T-1639): a declared `scope` is an intention a
    sibling ticket's author wrote down, and that check explicitly exempts
    a sibling once its ledger state reaches DONE/DROPPED. A `frob:ticket`
    directive is the OPPOSITE kind of signal -- it is written into the
    source hunk itself and says nothing about the sibling ticket's
    CURRENT ledger state at all. This is precisely the T-1618 incident
    gap: T-1579 was reverted in its own worktree and judged unsafe, but
    its ledger state (or the revert's own diff canceling out that file's
    net change) meant a sibling whose CODE was still physically present
    was never surfaced. Scanning the diff's own directive lines catches
    that regardless of ledger state -- this function NEVER consults any
    id's ledger state, and that blindness is deliberate (see
    `_check_passenger_tickets`'s own docstring); do not re-introduce a
    DONE/DROPPED exemption here.

    T-2183: only a line that `_genuine_comment_lines` places inside a
    real grammar COMMENT node (of its own file version: the worktree's
    HEAD content for an added `+` line, `base_ref`'s content for a
    removed `-` line) is ever bucketed at all -- a `frob:ticket` directive
    written into prose (a `.md` file, a docstring) is not a passenger
    signal no matter how it reads lexically, because it never carries the
    sibling ticket's CODE onto main; see `_genuine_comment_lines`'s own
    docstring for exactly why the docstring case is deliberately excluded
    even though `frob.lang` CAN recognize a python docstring directive
    for other purposes. This is the WHERE-a-directive-is-recognised fix,
    not a WHICH-ids-are-exempt one -- the DONE/DROPPED blindness above is
    untouched.

    Degrades to an empty set (never refuses, never raises) on a `git
    diff` failure -- this is an additional disclosure layer on top of
    `_check_cross_ticket_leakage`'s own hard-fail path, not a replacement
    for it if the git call itself cannot run at all."""
    diffed = run_argv(["git", "-C", str(worktree), "diff", f"{base_ref}...HEAD"])
    if diffed.is_err or diffed.danger_ok.returncode != 0:
        return frozenset()
    added_lines, removed_lines = _bucket_directive_lines(
        diffed.danger_ok.stdout, worktree, base_ref
    )
    return _passenger_ids_from_line_buckets(added_lines, removed_lines)


# frob:ticket T-1618
# frob:doc docs/modules/tickets-landing.md#passenger-ticket-disclosure-t-1618
# frob:tests tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets.test_refuses_and_lists_every_passenger_by_id  # noqa: E501
# frob:tests tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets.test_allow_cross_ticket_logs_and_proceeds  # noqa: E501
# frob:tests tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets.test_no_op_when_only_the_landing_tickets_own_directives_are_present  # noqa: E501
# frob:tests tests/unit/test_land_cross_ticket_leakage.py::TestPassengerTickets.test_a_dropped_siblings_still_present_code_is_still_reported  # noqa: E501
def _check_passenger_tickets(
    worktree: Path, ticket: Ticket, base_ref: str, *, allow_cross_ticket: bool = False
) -> Result[None, LandError]:
    """Refuse (T-1618) when `worktree`'s branch diff carries ANY OTHER
    ticket's `frob:ticket` directive additions -- landing silently, with
    no disclosure at all, is the exact bug the 2026-08-05 incident hit:
    landing T-1581 out of a shared series worktree carried T-1579's
    already-reverted-in-worktree WAIVE004 change onto main, where it went
    on to delete 55 live `frob:waive` directives across five gate families
    before anyone noticed.

    Unlike `_check_cross_ticket_leakage`, this check does not consult
    EITHER ticket's ledger state at all (see `_directive_ticket_ids_in_
    diff`'s own docstring for why that is the point, not an oversight) --
    a passenger is a passenger regardless of whether its own ticket record
    currently reads QUEUED, IN_PROGRESS, or DONE/DROPPED. `allow_cross_
    ticket=True` (the SAME escape hatch `_check_cross_ticket_leakage`
    already uses, `frob ticket land --allow-cross-ticket`) logs every
    passenger id at WARNING and proceeds -- this is the "operator
    acknowledges the passengers" path the ticket's own acceptance
    criterion describes; the two checks share one flag rather than
    stacking a second, differently-named override a caller would have to
    learn."""
    passengers = _directive_ticket_ids_in_diff(worktree, base_ref) - {ticket.id}
    if not passengers:
        return Ok(None)
    sorted_passengers = sorted(passengers)
    if allow_cross_ticket:
        _log.warning(
            "land: %s carrying %d passenger ticket(s) onto main: %s -- "
            "--allow-cross-ticket acknowledges this explicitly (T-1618)",
            ticket.id,
            len(sorted_passengers),
            sorted_passengers,
        )
        return Ok(None)
    _log.error(
        "land: %s refused -- this branch's diff carries frob:ticket "
        "directive addition(s) naming %d OTHER ticket id(s): %s -- these "
        "are about to ride onto main as UNDISCLOSED passengers of %s's "
        "land (T-1618: landing a worktree branch merges everything "
        "committed on it, not just %s's own commits). If this is "
        "deliberate (a series worktree meant to land together), re-run "
        "with --allow-cross-ticket to acknowledge and proceed; otherwise "
        "land or verify each passenger ticket on its own first",
        ticket.id,
        len(sorted_passengers),
        sorted_passengers,
        ticket.id,
        ticket.id,
    )
    return Err(LandError.PassengerTickets)


# frob:ticket T-1618
# frob:ticket T-1675
# frob:ticket T-1950
# frob:doc \
# docs/modules/tickets-landing.md#already-landed-on-main-first-class-outcome-t-1618
# frob:tests tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain.test_refuses_with_a_diagnostic_message_when_scope_diff_is_empty  # noqa: E501
# frob:tests tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain.test_no_op_when_the_ticket_has_real_changes_in_its_own_scope  # noqa: E501
# frob:tests tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain.test_no_op_when_the_ticket_declares_no_scope_at_all  # noqa: E501
# frob:tests tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain.test_no_op_for_a_docs_only_ticket_whose_scope_diff_is_empty_but_not_yet_landed  # noqa: E501
# frob:tests tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain.test_refuses_when_a_sibling_carried_this_tickets_content_before_it_ever_landed  # noqa: E501
# frob:tests tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain.test_no_op_when_no_frob_ticket_directive_for_this_id_exists_on_main  # noqa: E501
def _check_already_landed(
    worktree: Path, ticket: Ticket, base_ref: str
) -> Result[None, LandError]:
    """Refuse with a DISTINCT, self-explaining outcome (T-1618) when
    `ticket`'s content is POSITIVELY already present on `base_ref` -- a
    sibling's land already carried it, so this ticket's own later `frob
    ticket land` finds an empty diff in its own scope, which otherwise
    falls through into a confusing BUG002/TEST016 refusal.

    Requires ONE of two independent POSITIVE signals alongside the empty
    scope-diff (never the empty diff alone -- T-1675 found that
    indistinguishable from a legitimate docs/ledger-only first land):
    (1) T-1675: `ticket.id`'s ledger record on `base_ref` already shows
    `state: done`. (2) T-1950: `_ticket_directive_present_on_ref` --
    covers a ticket carried by a SIBLING's `--allow-cross-ticket` land
    BEFORE this ticket itself ever landed, so it has no `done` state of
    its own yet. See that function's docstring and docs/modules/tickets.
    md#already-landed-on-main-first-class-outcome-t-1618 for the full
    writeup and the measured T-1720/T-1922 incident. Neither signal
    proves the content is CORRECT on `base_ref`, only PRESENT.

    No-op (`Ok(None)`) when `ticket.scope` is empty or `worktree` has
    UNCOMMITTED changes (`_porcelain_dirty` -- runs before `land`'s own
    wip-commit stage, so uncommitted real work must not look identical
    to "already landed")."""
    from frob.tickets._models import LEDGER_PATH, TicketState, scope_matches
    from frob.tickets._store import archive_path

    if not ticket.scope:
        return Ok(None)
    dirty = _porcelain_dirty(worktree)
    if dirty.is_err or dirty.danger_ok:
        return Ok(None)
    changed = _branch_changed_files(worktree, base_ref)
    if changed.is_err:
        # Best-effort: a git failure surfaces via another preflight step.
        return Ok(None)
    # The ledger is implicitly in EVERY ticket's scope (scope_matches'
    # always-in-scope rule) and changes on every land -- excluded here.
    archive_rel = archive_path(worktree).relative_to(worktree).as_posix()
    relevant = frozenset(changed.danger_ok) - {LEDGER_PATH, archive_rel}
    hits = [
        path for path in relevant if scope_matches(path, ticket.scope, kind=ticket.kind)
    ]
    if hits:
        return Ok(None)
    # T-1675's first positive signal.
    on_main = _ledger_ticket_at_ref(worktree, base_ref, ticket.id)
    if on_main is not None and on_main.state is TicketState.DONE:
        return _refuse_already_landed(ticket.id, base_ref, "T-1675's positive signal")
    # T-1950's second positive signal (see _ticket_directive_present_on_ref).
    if _ticket_directive_present_on_ref(worktree, base_ref, ticket.id):
        return _refuse_already_landed(
            ticket.id,
            base_ref,
            "T-1950's positive signal: a frob:ticket directive naming "
            f"{ticket.id} already exists on {base_ref}",
        )
    return Ok(None)


# frob:ticket T-1950
def _ticket_directive_present_on_ref(
    worktree: Path, base_ref: str, ticket_id: str
) -> bool:
    """Whether `base_ref`'s CURRENT tree already contains a literal
    `frob:ticket <ticket_id>` directive line anywhere under `src/` (T-1950)
    -- the second positive signal `_check_already_landed` needs for a
    ticket whose content rode onto main under a SIBLING's land before this
    ticket itself ever closed, so it has no `done` state of its own to
    check. Uses `git grep`, degrading to `False` (never refuses, never
    raises) on any failure -- an additional disclosure layer on top of the
    DONE-state signal, not a replacement for it if git itself cannot
    answer."""
    found = run_argv(
        [
            "git",
            "-C",
            str(worktree),
            "grep",
            "-q",
            "-F",
            f"frob:ticket {ticket_id}",
            base_ref,
            "--",
            "src/",
        ]
    )
    if found.is_err:
        return False
    return found.danger_ok.returncode == 0


# frob:ticket T-1950
def _refuse_already_landed(
    ticket_id: str, base_ref: str, signal: str
) -> Result[None, LandError]:
    """Shared refusal tail for `_check_already_landed`'s two positive
    signals (T-1675's DONE-state check and T-1950's frob:ticket-directive
    check) -- same message shape, same remedy, only the `signal` text
    naming which one fired differs."""
    _log.warning(
        "land: %s refused -- this branch has NO changes inside %s's own "
        "declared scope relative to %s (T-1618), AND %s -- its content is "
        "very likely ALREADY on %s, most often because a sibling ticket's "
        "earlier land already carried it there (the passenger-ticket "
        "class T-1618's own %s check exists to stop, going forward). "
        "Verify by hand that %s's evidence/acceptance criteria genuinely "
        "hold against %s's current tree, then close directly: `frob "
        "ticket close %s` (add --skip-mutation-evidence if TEST016 also "
        "reports an empty diff) -- do not keep retrying this land",
        ticket_id,
        ticket_id,
        base_ref,
        signal,
        base_ref,
        LandError.PassengerTickets.name,
        ticket_id,
        base_ref,
        ticket_id,
    )
    return Err(LandError.AlreadyLandedOnMain)


# frob:ticket T-1355
# frob:ticket T-1639
# frob:ticket T-1855
# frob:doc \
# docs/modules/tickets-landing.md#cross-ticket-leakage-only-refuses-on-an-in_progress-s\
# ibling-t-1639
# frob:waive AFFECT001 reason="T-1855 added per-path reason disclosure (declared vs \
# implicit-cli-wiring) to this function's refusal; docs/modules/tickets.md was leased \
# to in-progress T-1686 and could not be edited here -- follow-up draft filed to \
# update the anchor once free"
# frob:ticket T-2121
#: Paths `_check_cross_ticket_leakage` must never treat as "claimed" by
#: any ticket's declared (or live-lease) scope, because no ticket's own
#: committed work can legitimately explain a change to them in the first
#: place -- they are written EXCLUSIVELY by land/sweep machinery itself,
#: never by a worktree agent's intentional edit. Two already-recognized
#: land-owned families, combined: `_LAND_OWNED_RELEASE_FILES` minus
#: `pyproject.toml` (that module's own T-1805 comment: `pyproject.toml`
#: is only PARTIALLY land-owned -- its `version = ` line -- every OTHER
#: field is legitimate ticket territory, so the file as a whole must stay
#: leakage-checkable, unlike `CHANGELOG.md`/`.frob-release.json`, which
#: are wholly land-owned in practice and refused outright by the T-0731
#: scaffolded pre-commit hook for ANY worktree commit that touches them
#: at all) plus `rapid-debt.jsonl` (T-1699's deferred-debt append,
#: written exclusively by `record_rapid_debt`/the detached post-land
#: sweep, never by a ticket's own hand -- the T-2121 field incident: an
#: unrelated open ticket happened to declare it in its own scope, and
#: every OTHER rapid land in the fleet started refusing with
#: CrossTicketLeakage over a file its own author never touched by hand).
#:
#: Deliberately NOT `uv.lock`: unlike these three, a stale `uv.lock` is
#: harmless and gets unconditionally re-synced from `pyproject.toml` at
#: land time regardless of which side's copy staged (see
#: `_LAND_OWNED_RELEASE_FILES`'s own module comment) -- excluding it here
#: would buy nothing a real ticket could ever collide on.
#:
#: This is a small, individually-justified ALLOWLIST, not a broad
#: exemption rule -- a ticket's declared/live-lease scope still counts as
#: a real claim on every path OUTSIDE this set, including every ordinary
#: source/test/doc file no machinery ever writes to. Do not special-case
#: a bare filename here without adding it to one of the two land-owned
#: families above first (or documenting a THIRD family with the same
#: "no ticket can legitimately explain this" property) -- an ad hoc
#: string here is exactly the fragile, one-file-at-a-time fix this
#: ticket's own body says not to write.
def _machinery_owned_leakage_exempt_paths() -> frozenset[str]:
    """The `_check_cross_ticket_leakage` machinery-owned-path allowlist
    (T-2121) -- see the module-level comment directly above this
    function for the full rationale; kept as a function (not a bare
    module constant) so it always reflects `_LAND_OWNED_RELEASE_FILES`'s
    current membership rather than a copy that could silently drift."""
    from frob.tickets._land_release import _LAND_OWNED_RELEASE_FILES

    return frozenset(
        {p for p in _LAND_OWNED_RELEASE_FILES if p != "pyproject.toml"}
        | {"rapid-debt.jsonl"}
    )


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
    ticket is `IN_PROGRESS` (T-1639: not merely "not done/dropped" --
    see `_find_leaked_tickets`'s own docstring for why a queued/planned/
    blocked sibling's scope hit is disclosed, not refused) on `root`'s
    ledger -- the incident class where landing one ticket out of a
    multi-ticket series worktree silently carries a sibling's still-open
    work onto main (T-1352's land of worktree t-1276 carrying T-1276's
    own committed files while T-1276 stayed `in-progress`).

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
    # frob:ticket T-2121
    relevant = (
        frozenset(changed.danger_ok)
        - {LEDGER_PATH, archive_rel}
        - _machinery_owned_leakage_exempt_paths()
    )
    if not relevant:
        return Ok(None)

    worktree_tickets, root_tickets = _load_leakage_ledgers(root, worktree, ticket.id)
    if worktree_tickets is None:
        return Ok(None)
    leaked = _find_leaked_tickets(
        root, worktree, ticket.id, worktree_tickets, root_tickets, relevant, base_ref
    )
    if not leaked:
        return Ok(None)

    return _report_leaked_tickets(
        ticket.id, leaked, worktree_tickets, allow_cross_ticket=allow_cross_ticket
    )


# frob:ticket T-1932
# frob:ticket T-1931
# frob:doc docs/modules/tickets-landing.md#post-mutation-reverification-t-1932
# frob:tests tests/unit/test_land_step_ordering.py::TestCrossTicketLeakagePostMutationRecheck.test_guard_refusal_survives_an_uncommitted_reintroduction  # noqa: E501
# frob:tests tests/unit/test_land_step_ordering.py::TestCrossTicketLeakagePostMutationRecheck.test_clean_land_is_unaffected  # noqa: E501
def _reverify_cross_ticket_leakage_post_mutation(
    root: Path,
    worktree: Path,
    ticket: Ticket,
    base_ref: str,
    allow_cross_ticket: bool,
) -> Result[None, LandError]:
    """T-1932's general fix, applied to T-1931's concrete instance: re-run
    `_check_cross_ticket_leakage` a SECOND time, AFTER `_land_merge_stage`'s
    wip-commit, so its refusal cannot be silently undone by a mutation that
    ran between the first (preflight) check and the commit that actually
    lands.

    THE INVARIANT (T-1932): on the land path, no mutation may run after a
    guard whose decision that mutation can invalidate. `_check_cross_
    ticket_leakage`'s own diff source, `_branch_changed_files`, reads ONLY
    committed history (`git diff base_ref...HEAD`) -- it is blind to any
    uncommitted disk write, by construction. `frob ticket land`'s own
    T-1175 pre-land auto-fix absorption (`_absorb_pre_land_fixes`: `frob
    fmt` + the T-1138 Tier-A deterministic auto-fix handlers) runs BEFORE
    `land()` is even called, and leaves its rewrites as ordinary
    UNCOMMITTED changes for `land()`'s own wip-commit to pick up later --
    so `_land_precheck`'s copy of this same check (run before any git
    mutation, deliberately, so it can refuse cheaply) can only ever see
    the world as it stood BEFORE that absorption's uncommitted output
    exists in history. The T-1931 incident is exactly this: a human
    reverted a leaked line and committed the revert; the preflight check
    passed against that clean commit; `_absorb_pre_land_fixes` then
    silently re-wrote the SAME leaked content back to disk (uncommitted,
    Tier-A regenerating an interface edge from still-live source); and
    nothing re-examined the diff after that write became part of history
    at the wip-commit -- so the leak landed anyway, having been refused
    once and never refused again.

    This function is that missing re-examination: called from
    `_land_locked` immediately after `_land_merge_stage` returns (the
    wip-commit has already run by then, so ANY prior uncommitted mutation
    -- Tier-A's, fmt's, or a hand edit -- is now part of `worktree`'s
    committed history and visible to `_branch_changed_files` exactly like
    a preflight check would see it), and again before the dry-run early
    return (D-05's own rule: a `--dry-run` must preview the exact refusal
    a real run would hit). A refusal here aborts the just-created merge
    commit via the caller's existing `_abort_merge` unwind, identical to
    every other post-merge check in `_land_locked` -- no new unwind path.

    Pure re-invocation of `_check_cross_ticket_leakage` with the same
    arguments the preflight call used (`root`, `worktree`, `ticket`,
    `base_ref`, `allow_cross_ticket`) -- there is no separate "post-
    mutation" variant of the check itself, only a second call site at a
    point in the sequence where its answer cannot go stale again before
    the commit that actually reaches main. See
    `docs/guides/agent-playbook.md`'s land-path ordering note and
    `docs/modules/tickets-landing.md#post-mutation-reverification-t-1932` for how
    a FUTURE guard or auto-fix handler added to the land path is expected
    to reason about this same hazard (T-1932 acceptance criterion 4)."""
    return _check_cross_ticket_leakage(
        root, worktree, ticket, base_ref, allow_cross_ticket=allow_cross_ticket
    )


# frob:ticket T-1940
def _reverify_passenger_tickets_post_mutation(
    worktree: Path, ticket: Ticket, base_ref: str, allow_cross_ticket: bool
) -> Result[None, LandError]:
    """T-1940's first concrete application of the generalized registry
    (`_COMMITTED_DIFF_GUARDS`): `_check_passenger_tickets`'s own post-
    mutation twin, mirroring `_reverify_cross_ticket_leakage_post_
    mutation`'s exact shape and rationale one guard over.

    Same T-1932 invariant, same hazard: `_check_passenger_tickets`'s diff
    source, `_directive_ticket_ids_in_diff`, reads ONLY committed history
    -- it is blind to `_absorb_pre_land_fixes`'s (T-1175's `frob fmt` +
    Tier-A auto-fix) uncommitted rewrites, which run BEFORE `land()` is
    even called and only become part of committed history at `_land_
    merge_stage`'s wip-commit. A Tier-A handler regenerating a `frob:
    ticket <id>` directive line for some OTHER ticket (the same shape
    T-1931 hit for a `frob:enumerates` edge) would silently carry that id
    onto main as an undisclosed passenger, refused once at preflight and
    never refused again -- exactly the class T-1932 exists to close, just
    for `_check_passenger_tickets` instead of `_check_cross_ticket_
    leakage`.

    Pure re-invocation with the same arguments the preflight call used,
    called from `_land_locked` immediately alongside the leakage re-
    check -- no separate unwind path, no new refusal semantics."""
    return _check_passenger_tickets(
        worktree, ticket, base_ref, allow_cross_ticket=allow_cross_ticket
    )


# frob:ticket T-1940
class _CommittedDiffGuard(BaseModel):
    """One entry in `_COMMITTED_DIFF_GUARDS` (T-1940): `name` is the
    preflight guard function's own name (as it appears called from
    `_land_precheck`/`_land_precheck_remaining_checks`); `post_mutation_
    check` is that guard's registered post-mutation twin -- the T-1932
    worked pattern, a pure re-invocation of the SAME guard called again
    after `_land_merge_stage`'s wip-commit -- or `None` if no twin exists
    yet, in which case `exemption_reason` MUST explain why (never blank:
    `TestCommittedDiffGuardRegistryCompleteness` in tests/test_ticket_
    land.py enforces this, closing T-1932 acceptance criterion 4
    mechanically for every future guard added to either preflight
    sequence -- a new guard with neither a twin nor a stated reason fails
    that test, forcing an explicit decision instead of a silent gap)."""

    model_config = {}

    name: str
    post_mutation_check: str | None = None
    exemption_reason: str | None = None


# frob:ticket T-1940
# NOTE: no frob:doc anchor here -- docs/modules/tickets.md was held by a
# LIVE cross-worktree lease (T-1696, in-progress) at fix time and could
# not be added to T-1940's own scope; a follow-up doc pass should add a
# section describing this registry alongside the existing T-1932
# post-mutation-reverification anchor.
_COMMITTED_DIFF_GUARDS: tuple[_CommittedDiffGuard, ...] = (
    _CommittedDiffGuard(
        name="_check_cross_ticket_leakage",
        post_mutation_check="_reverify_cross_ticket_leakage_post_mutation",
    ),
    _CommittedDiffGuard(
        name="_check_passenger_tickets",
        post_mutation_check="_reverify_passenger_tickets_post_mutation",
    ),
    _CommittedDiffGuard(
        name="_check_already_landed",
        exemption_reason=(
            "T-1940: identified as diff-content-reading (base_ref-scoped "
            "_branch_changed_files) and therefore subject to the same "
            "T-1932 hazard, but NOT yet closed here -- a post-mutation "
            "twin risks a DIFFERENT false-positive class (a Tier-A "
            "rewrite landing between the preflight and the wip-commit "
            "could make a genuinely-not-yet-landed ticket's scope diff "
            "look transiently empty), which needs its own investigation "
            "rather than a blind copy of the leakage/passenger pattern. "
            "Tracked as an acknowledged, explicit gap rather than a "
            "silent one -- a future ticket closes it."
        ),
    ),
    _CommittedDiffGuard(
        name="_check_live_tracker_citations",
        exemption_reason=(
            "T-1940: diff-content-reading (base_ref-scoped) and subject "
            "to the same T-1932 hazard in principle, but only ever fires "
            "for a TERMINAL (done/dropped) land (T-1853) -- a narrower "
            "blast radius than leakage/passenger, which fire for any "
            "land. Tracked as an acknowledged, explicit gap; a future "
            "ticket closes it."
        ),
    ),
    _CommittedDiffGuard(
        name="_check_orphaned_evidence_deletion",
        exemption_reason=(
            "T-1940: diff-content-reading (base_ref-scoped _branch_"
            "changed_files, same source as leakage) and subject to the "
            "same T-1932 hazard in principle. Tracked as an "
            "acknowledged, explicit gap rather than a silent one; a "
            "future ticket closes it."
        ),
    ),
    _CommittedDiffGuard(
        name="_check_mutation_evidence",
        exemption_reason=(
            "T-1940: diff-content-reading and subject to the same T-1932 "
            "hazard in principle, but its own escape hatch (skip_"
            "mutation_evidence) and BUG002's independent land-time gate "
            "already cover most of the same ground a post-mutation "
            "re-check would. Tracked as an acknowledged, explicit gap "
            "rather than a silent one; a future ticket closes it."
        ),
    ),
    _CommittedDiffGuard(
        name="_refuse_anchor_terminal_land",
        exemption_reason=(
            "Reads only ticket.state (an in-memory field, not committed "
            "diff content) -- structurally immune to the T-1932 hazard, "
            "no twin needed."
        ),
    ),
)


# frob:ticket T-1946
# frob:ticket T-1979
# frob:ticket T-2017
# frob:doc docs/modules/tickets-landing.md#orphaned-evidence-deletion-t-1946
def _check_orphaned_evidence_deletion(
    worktree: Path, ticket: Ticket, base_ref: str
) -> Result[None, LandError]:
    """T-1946: refuse when this branch's OWN committed changes
    (`_branch_changed_files`, three-dot -- so only paths THIS diff touched
    can ever trigger this, mirroring `_check_cross_ticket_leakage`'s own
    diff source) delete or rename a pytest test node bound as evidence on
    a DIFFERENT, still-open-or-done ticket, such that the other ticket's
    evidence no longer resolves against `worktree`'s currently collected
    tests.

    MEASURED (T-1946's own brief): two independent actors, one hour,
    orphaned 3 unrelated tickets' evidence in one deletion each -- a
    coordinator's file cleanup and a legitimate test replacement in an
    unrelated ticket's land, neither of which could see the hazard: the
    orphaned tickets were outside both diffs' declared scope, and a
    deletion diff carries no signal pointing at what else cites the
    deleted node.

    T-2017 ROOT CAUSE (measured, not one of the two hypotheses that ticket
    started from -- neither a stale collection cache nor a rename
    mis-parsed as add+delete): this check used `load_all(worktree)`,
    which for a v2-mode repo globs ONLY `tickets/T-####/ticket.md` (the
    ACTIVE tree) -- an ARCHIVED ticket's evidence was never even a
    candidate `_orphaned_evidence_findings` could flag, regardless of
    collection freshness or how the diff was shaped. T-0907 (the T-1963
    incident's own orphaned ticket) was archived at the v1->v2 migration,
    long before T-1963 ever ran, so it was structurally invisible to this
    guard from the day this check was written -- `frob check`'s own
    COV003 (`_cov003` in `frob.gates`) caught the SAME orphan on its next
    unscoped run only because it loads via `frob.tickets._archive.
    load_queue` (active+archive merged, `TicketQueue`), the authoritative
    source this check now also uses.

    Deliberately NOT a rewrite/auto-repoint of the stale evidence (the
    WAIVE004 lesson: a "safe" auto-cleanup silently destroyed 55 live
    waivers; evidence is the only record a ticket was ever proven, so
    repointing it automatically would fabricate proof) -- this only
    refuses and names the affected ticket(s)/evidence id(s), leaving the
    human/agent decision (re-point to the replacement test, or re-scope
    and record fresh evidence) to whoever resolves it. `cmd:` evidence
    entries (T-0215, docs-kind) are never node ids and are skipped
    outright -- they cannot be "deleted" by a test-file diff.

    Best-effort like every other land-time check here: a `_branch_
    changed_files` or `collect_python_tests` failure is logged and
    treated as `Ok(None)` rather than blocking the land on an unrelated
    tooling problem -- this check is an additional safety net, not a
    replacement for COV003's own authoritative sweep, which still runs
    at `frob check` regardless.

    T-2060: `changed_paths` is FILE-granular
    (`_branch_changed_files`), but a genuine "this branch deleted/renamed
    the node" claim needs NODE granularity -- a candidate evidence node
    whose FILE happens to be in `changed_paths` for an entirely unrelated
    edit, but which was ALREADY missing before this branch's own commits
    (broken by some earlier, unrelated main commit), is not this branch's
    fault and must not refuse its land. `_orphaned_evidence_findings`
    narrows each file-level candidate with a merge-base presence check
    (`_test_node_existed_at_ref`) before flagging it -- see that
    function's own docstring for the full narrowing contract. Computing
    `merge_base` failing degrades to the OLD, more conservative
    file-level-only behavior (never a crash, never a silent pass on a
    tooling problem) rather than skipping the whole check."""
    changed = _branch_changed_files(worktree, base_ref)
    if changed.is_err:
        _log.debug(
            "land: %s orphaned-evidence check skipped -- diff unreadable (%s)",
            ticket.id,
            changed.danger_err,
        )
        return Ok(None)
    if not changed.danger_ok:
        return Ok(None)

    from frob.testing import collect_python_tests

    collected = collect_python_tests(worktree)
    if collected.is_err:
        _log.debug(
            "land: %s orphaned-evidence check skipped -- test collection failed (%s)",
            ticket.id,
            collected.danger_err,
        )
        return Ok(None)

    # frob:ticket T-2017
    from frob.tickets._archive import load_queue

    loaded = load_queue(worktree)
    if loaded.is_err:
        _log.debug(
            "land: %s orphaned-evidence check skipped -- ledger unreadable (%s)",
            ticket.id,
            loaded.danger_err,
        )
        return Ok(None)

    merge_base = _true_merge_base(worktree, base_ref)
    merge_base_ref = merge_base.danger_ok if merge_base.is_ok else None
    if merge_base.is_err:
        _log.debug(
            "land: %s orphaned-evidence node-granularity narrowing skipped -- "
            "merge-base unreadable (%s), falling back to file-level matching",
            ticket.id,
            merge_base.danger_err,
        )

    orphaned = _orphaned_evidence_findings(
        ticket.id,
        loaded.danger_ok.tickets,
        changed.danger_ok,
        collected.danger_ok,
        worktree,
        merge_base_ref,
    )
    if not orphaned:
        return Ok(None)
    return _refuse_orphaned_evidence(ticket.id, orphaned)


# frob:ticket T-1979
def _orphaned_evidence_findings(
    landing_id: str,
    queue: Mapping[str, Ticket],
    changed_paths: frozenset[str],
    tests: CollectedTests,
    worktree: Path | None = None,
    merge_base: str | None = None,
) -> dict[str, list[str]]:
    """`other_ticket_id -> [orphaned evidence id, ...]` for every OTHER
    ticket in `queue` whose non-cmd evidence file lies under `changed_
    paths` (T-1946's own diff-scoping) but no longer resolves against
    `tests` (`_evidence_valid_for_ticket`) -- the pure-data half of
    `_check_orphaned_evidence_deletion`, split out to keep that function
    under ARCH001's line threshold (T-1979).

    T-2060 NODE-LEVEL NARROWING: `changed_paths` only
    proves the FILE was touched by this branch, not that THIS branch's
    diff is what removed the specific node -- a file this branch edits
    for an unrelated reason can share a candidate node that was already
    missing before this branch's own commits (broken by some earlier,
    independent main commit). When `worktree`/`merge_base` are both
    given (the normal call path -- `None`/`None` only when the caller's
    own merge-base lookup failed, T-1969's/etc. degrade-gracefully
    posture), a file-level candidate is flagged ONLY if `_test_node_
    existed_at_ref(worktree, merge_base, evidence)` is NOT `False` --
    i.e. the node was present (or its presence could not be determined,
    which conservatively still flags, matching this check's existing
    prove-fresh-or-refuse posture for anything it cannot positively rule
    out) at the point THIS branch actually diverged. A node CONFIRMED
    absent already at merge-base is pre-existing breakage this branch
    did not cause and is never flagged, regardless of which file it
    lives in. `worktree`/`merge_base` both `None` reproduces the OLD,
    strictly file-level-only behavior for a caller that has no merge-base
    to offer (or an existing test constructing this function directly,
    pre-T-2060) -- never a behavior change for that
    caller, only an added narrowing when the extra context is present."""
    from frob.gates import _evidence_valid_for_ticket
    from frob.tickets._models import is_cmd_evidence

    orphaned: dict[str, list[str]] = {}
    for other_id, other in queue.items():
        if other_id == landing_id:
            continue
        for evidence in other.evidence:
            if is_cmd_evidence(evidence):
                continue
            node_path = evidence.split("::", 1)[0]
            if node_path not in changed_paths:
                continue
            if _evidence_valid_for_ticket(evidence, other, tests):
                continue
            if (
                worktree is not None
                and merge_base is not None
                and _test_node_existed_at_ref(worktree, merge_base, evidence) is False
            ):
                continue
            orphaned.setdefault(other_id, []).append(evidence)
    return orphaned


# frob:ticket T-2060
def _test_node_existed_at_ref(worktree: Path, ref: str, evidence: str) -> bool | None:
    """Best-effort, syntactic (NOT a pytest collection): whether
    `evidence`'s own test file, as it existed AT `ref`, already contained
    a definition matching its trailing method/function name --
    `_orphaned_evidence_findings`'s node-level narrowing, cheap enough to
    run on every land-time check (unlike a real `pytest --collect-only`
    at an arbitrary ref, which needs a full isolated checkout, T-1929's
    `_checkout_bug_repro_worktree` pattern -- far too costly to pay per
    candidate on every single land).

    `False` ONLY on a confirmed, readable absence -- the file read
    cleanly at `ref` and the name genuinely does not appear as a `def`
    there. `True` when the name DOES appear (present at the fork point --
    a real candidate for this branch having removed/renamed it since).
    `None` (git show failed, or the evidence id has no `::` split at all)
    on anything unresolvable -- the caller treats `None` the SAME as
    `True` (still flags), since an unreadable ref must never be silently
    read as proof a test never existed; this function only ever narrows
    the refusal on a POSITIVE, confirmed absence, never on ambiguity."""
    parts = evidence.split("::")
    if len(parts) < 2:
        return None
    path, name = parts[0], parts[-1]
    shown = run_argv(["git", "-C", str(worktree), "show", f"{ref}:{path}"])
    if shown.is_err or shown.danger_ok.returncode != 0:
        return None
    pattern = re.compile(
        rf"^\s*(?:async\s+)?def\s+{re.escape(name)}\s*\(", re.MULTILINE
    )
    return bool(pattern.search(shown.danger_ok.stdout))


# frob:ticket T-1979
def _refuse_orphaned_evidence(
    landing_id: str, orphaned: dict[str, list[str]]
) -> Result[None, LandError]:
    """Log every orphaned-evidence hit and return `Err(LandError.
    OrphanedEvidenceDeletion)` (T-1946, split out of `_check_orphaned_
    evidence_deletion` per T-1979's ARCH001 fix, zero behavior change)."""
    for other_id, evidence_ids in sorted(orphaned.items()):
        _log.error(
            "land: %s branch deletes or renames test node(s) bound as "
            "evidence on %s, which no longer resolve: %s -- re-point "
            "%s's evidence to the replacement test (in this same diff), "
            "or re-scope %s and record fresh evidence, before landing",
            landing_id,
            other_id,
            evidence_ids,
            other_id,
            other_id,
        )
    return Err(LandError.OrphanedEvidenceDeletion)


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
# frob:ticket T-1855
def _report_leaked_tickets(
    landing_id: str,
    leaked: dict[str, list[str]],
    worktree_tickets: dict[str, Ticket],
    *,
    allow_cross_ticket: bool,
) -> Result[None, LandError]:
    """Log every leaked-ticket hit and either return `Ok(None)`
    (`allow_cross_ticket=True`, with a WARNING trail) or `Err
    (LandError.CrossTicketLeakage)` (T-1355: split out of `_check_cross_
    ticket_leakage` to keep it under ARCH001's line threshold, zero
    behavior change).

    T-1855: each path is logged with its `_scope_claim_reason` against
    `worktree_tickets[other_id]` -- "declared" (narrow `other`'s own
    scope) vs "implicit-cli-wiring" (a FEATURE-kind grant, not fixable by
    narrowing `other`'s scope at all) are different problems with
    different remedies, and a refusal that names only the file used to
    send an agent to fix the wrong one."""
    for other_id, paths in sorted(leaked.items()):
        other = worktree_tickets.get(other_id)
        annotated = (
            [f"{p} ({_scope_claim_reason(p, other)})" for p in paths]
            if other is not None
            else paths
        )
        _log.error(
            "land: %s branch carries %d file(s) covered by %s's own "
            "scope, and %s is still open on main -- landing would "
            "silently ship %s's work ahead of its own close: %s",
            landing_id,
            len(paths),
            other_id,
            other_id,
            other_id,
            annotated,
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


# frob:ticket T-1616
# frob:tests \
# tests/test_ticket_evidence.py::TestKindHistoryLandNotice.test_notice_logged_at_land
# frob:tests \
# tests/test_ticket_evidence.py::TestKindHistoryLandNotice.test_no_history_no_notice
def _warn_kind_history_at_land(ticket: Ticket) -> None:
    """T-1616: log a loud, un-missable notice at land time for every
    `kind_history` entry a ticket carries -- "this was kind X when the
    work was done and became kind Y before it landed" instead of a
    reviewer discovering the reclassification only by reading
    frontmatter. A no-op when `kind_history` is empty (the overwhelmingly
    common case: no post-evidence reclassification ever happened)."""
    for entry in ticket.kind_history:
        _log.warning(
            "land: %s was reclassified AFTER evidence/Done-report existed: %s "
            "-- review whether the new kind's evidence obligations (e.g. "
            "BUG002) are still honestly satisfied",
            ticket.id,
            entry,
        )


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
    T-0854's live-tracker-citation preflight, T-1355's cross-ticket
    leakage preflight (bypassable via `allow_cross_ticket`), and T-1618/
    T-1675's already-landed preflight), and resolve main's current branch
    name -- everything `land` must check BEFORE any git mutation.

    `_check_already_landed` (T-1618, positive-signal fix T-1675) always
    runs now -- no opt-in flag; see that function's own docstring for why
    requiring a positive on-main `done` state alongside the empty
    scope-diff makes an unconditional default safe."""
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
    _warn_kind_history_at_land(ticket)

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

    scope_preflight = _validate_scope_covered_preflight(
        ticket, covers_scope, rapid=_land_is_rapid(worktree, ticket.id)
    )
    if scope_preflight.is_err:
        return Err(scope_preflight.danger_err)

    already_landed_check = _check_already_landed(worktree, ticket, main_branch_name)
    if already_landed_check.is_err:
        return Err(already_landed_check.danger_err)

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
# frob:ticket T-1856
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
    order, exactly as they ran inline before this split.

    T-1856: `_refuse_anchor_terminal_land` runs FIRST, ahead of even the
    live-tracker check -- it is the first-class, structural twin of what
    `_check_live_tracker_citations` can only infer from a live grep: an
    anchor ticket refuses a terminal land unconditionally, whether or not
    any citation currently resolves, closing the T-1853-documented gap
    where a well-meaning agent could still be instructed to close one."""
    anchor_check = _refuse_anchor_terminal_land(ticket)
    if anchor_check.is_err:
        return Err(anchor_check.danger_err)

    live_tracker_check = _check_live_tracker_citations(
        worktree, ticket, main_branch_name
    )
    if live_tracker_check.is_err:
        return Err(live_tracker_check.danger_err)

    passenger_check = _check_passenger_tickets(
        worktree,
        ticket,
        main_branch_name,
        allow_cross_ticket=allow_cross_ticket,
    )
    if passenger_check.is_err:
        return Err(passenger_check.danger_err)

    leakage_check = _check_cross_ticket_leakage(
        root,
        worktree,
        ticket,
        main_branch_name,
        allow_cross_ticket=allow_cross_ticket,
    )
    if leakage_check.is_err:
        return Err(leakage_check.danger_err)

    orphan_check = _check_orphaned_evidence_deletion(worktree, ticket, main_branch_name)
    if orphan_check.is_err:
        return Err(orphan_check.danger_err)

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
    root: Path, worktree: Path, ticket: Ticket, main_branch: str
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
    resolved by picking a side.

    T-2105: BEFORE the merge runs, `detect_duplicate_ticket_id_
    collisions` compares every `tickets/<id>/ticket.md` blob directly
    between `worktree` and `root`. This is the v2-mode counterpart's own
    version of the exact field incident this ticket exists to close --
    a v2-mode `tickets/<id>/` directory is disjoint from every OTHER
    ticket's directory, so a same-id collision here never even reaches
    `git merge` as a textual conflict at all (add/add on two DIFFERENT
    paths never conflicts); the old code had no mechanism that could ever
    catch it, silently letting `_auto_resolve_out_of_scope_conflicts`
    (or, for a clean add/add, git's own merge) keep whichever side it
    keeps. Refusing here, ahead of the merge, closes that gap."""
    collisions = detect_duplicate_ticket_id_collisions(
        worktree, root, ticket.id, main_branch
    )
    if collisions:
        _log.error(
            "land: %s refusing to merge %s into %s -- ticket id(s) %s have "
            "DIFFERENT tickets/<id>/ticket.md content on the worktree's "
            "side vs %s's (T-2105 duplicate-id collision, v2 mode: two "
            "distinct records were independently written at the same id) "
            "-- resolve by hand (compare `git -C %s show "
            "HEAD:tickets/<id>/ticket.md` against `git -C %s show "
            "HEAD:tickets/<id>/ticket.md` for each id above, then "
            "renumber whichever record should not have this id via "
            "`frob ticket renumber`) before retrying",
            ticket.id,
            main_branch,
            worktree,
            sorted(collisions),
            main_branch,
            worktree,
            root,
        )
        return Err(LandError.MergeConflict)
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


# frob:ticket T-1914
# frob:tests tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard.test_pre_fix_shape_would_have_silently_reverted_sibling  # noqa: E501
def _sibling_ticket_states(worktree: Path, landing_id: str) -> dict[str, str]:
    """Every OTHER ticket id's current on-disk state under `worktree`,
    excluding `landing_id` itself (T-1914). A load failure (corrupt/
    unparseable ledger) degrades to an empty map -- the same fail-open
    posture `_tick005_land_regressions` already uses for its own parse
    failures, rather than blocking every land on a ledger the rest of
    `land()` already tolerates parsing failures around elsewhere."""
    loaded = load_all(worktree)
    if loaded.is_err:
        return {}
    return {
        tid: t.state.value for tid, t in loaded.danger_ok.items() if tid != landing_id
    }


# frob:ticket T-1914
# frob:tests tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard.test_regressed_sibling_is_detected_by_rank_comparison  # noqa: E501
# frob:tests tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard.test_no_regression_when_sibling_state_only_improves_or_holds  # noqa: E501
def _assert_no_sibling_state_regression(
    worktree: Path, landing_id: str, pre_states: dict[str, str]
) -> tuple[str, ...]:
    """The ids in `pre_states` whose state RANK (`_STATE_RANK`, shared with
    the v1 ledger-splice `_newer`/TICK005 machinery) has DROPPED in
    `worktree`'s CURRENT on-disk ticket store relative to what it was
    before this land's internal `_merge_main_into_worktree[_v2]` call
    (T-1914) -- e.g. a sibling ticket the worktree had already closed
    (`done`) reverting to main's stale `queued` copy. A sibling id no
    longer present post-merge (should not happen for a v2 directory-per-
    ticket store, which never deletes a ticket's own directory via an
    ordinary merge) is skipped, not treated as a regression -- there is
    nothing to compare a rank against. Sorted for a stable, grep-able log
    line at the call site."""
    from frob.tickets._models import TicketState

    post_states = _sibling_ticket_states(worktree, landing_id)
    regressed = []
    for ticket_id, pre_state in pre_states.items():
        post_state = post_states.get(ticket_id)
        if post_state is None:
            continue
        if _STATE_RANK[TicketState(post_state)] < _STATE_RANK[TicketState(pre_state)]:
            regressed.append(ticket_id)
    return tuple(sorted(regressed))


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
    existing `_merge_main_into_worktree` splice path unchanged.

    T-1914: `_sibling_ticket_states(worktree, ticket_id)` is snapshotted
    BEFORE the merge and re-checked immediately AFTER it
    (`_assert_no_sibling_state_regression`) -- the v2-mode merge path has
    no ledger splice at all (disjoint `tickets/T-####/` directories are
    ordinary git objects) and its own out-of-scope conflict auto-resolve
    (`_auto_resolve_out_of_scope_conflicts(..., keep="theirs")`) blindly
    takes main's side of ANY conflicting file not in the landing ticket's
    own scope, including a SIBLING ticket's own directory -- confirmed
    root cause of a real incident where landing one ticket silently
    reverted another, already-closed sibling ticket's `done` state back
    to main's stale `queued` copy, with no conflict ever surfaced to the
    operator. A regression here aborts the merge and refuses the land
    (`LandError.TerminalStateRegression`) instead of committing over lost
    sibling state."""
    wip = _wip_commit(worktree, ticket_id, dry_run=dry_run)
    if wip.is_err:
        return Err(wip.danger_err)
    wip_committed = wip.danger_ok

    pre_merge_sibling_states = _sibling_ticket_states(worktree, ticket_id)

    merged = (
        _merge_main_into_worktree_v2(root, worktree, ticket, main_branch_name)
        if _store_mode(root) == "v2"
        else _merge_main_into_worktree(root, worktree, ticket, main_branch_name)
    )
    if merged.is_err:
        return Err(merged.danger_err)
    did_merge = merged.danger_ok

    if did_merge:
        regressed = _assert_no_sibling_state_regression(
            worktree, ticket_id, pre_merge_sibling_states
        )
        if regressed:
            _log.error(
                "land: %s refused -- merging main into the worktree "
                "would silently regress sibling ticket(s) %s to an "
                "earlier state (T-1914 sibling-state-regression guard); "
                "resolve the ledger conflict by hand (keep the newer "
                "state per playbook section 10) before retrying "
                "`frob ticket land %s --worktree %s`",
                ", ".join(regressed),
                ticket_id,
                ticket_id,
                worktree,
            )
            _abort_merge(worktree)
            return Err(LandError.TerminalStateRegression)

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

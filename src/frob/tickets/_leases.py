"""Cross-worktree scope-lease side-channel under the git COMMON dir (T-0473).

`frob ticket start`'s in-progress scope-lease (T-0453) lives entirely in
`tickets.md`, a file that is per-branch: an isolated worktree's checkout of
`tickets.md` never sees another worktree's `IN_PROGRESS` transition until
one of them merges/lands into the other's view of the ledger. In a
multi-agent session where every agent works in its own worktree (this
repo's normal dispatch pattern), that makes the T-0453 collision-aware
`doable` filter INERT across worktrees -- two agents can be handed
overlapping-scope tickets and neither's local `tickets.md` shows the
other's lease.

`git rev-parse --git-common-dir` resolves to the ONE `.git` directory every
worktree of a repository shares (a linked worktree's own `.git` is just a
pointer file to it) -- unlike `.git` itself, which is per-worktree for a
linked worktree, `.git/frob-leases/` under the common dir is visible from
every worktree. One small JSON file per held ticket id there
(`<ticket-id>.json`) records which worktree/branch holds it and its scope,
independent of and in addition to the ledger -- `frob.tickets.transition`
writes/removes it exactly when a ticket enters/leaves `IN_PROGRESS`, and
`leased_by` (T-0453) reads every worktree's files, not just the local
ledger's own `IN_PROGRESS` rows, to compute collisions.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import threading
import tomllib
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

from pydantic import BaseModel
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob import gitio
from frob.gitio import GitError, ProcResult
from frob.logging import get_logger

# frob:ticket T-1619
# Same posix-only degradation as `frob.tickets._land`'s own `fcntl` import
# (T-0577) -- `refuse_if_land_in_progress` degrades to a logged-once no-op
# (never refuses) on a platform without `fcntl`, matching how the land.lock
# it probes already degrades on the same platform.
fcntl: ModuleType | None
try:
    fcntl = importlib.import_module("fcntl")
except ImportError:  # pragma: no cover -- posix-only in this repo's CI
    fcntl = None

_log = get_logger(__name__)

# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
LEASES_DIRNAME = "frob-leases"


# frob:ticket T-1680
def _refuse_for_held_land_lock(root: Path, path: Path) -> Result[None, LeaseError]:
    """The refusal `_land_flock_probe` returns when the land lock is held
    by a live process (T-1680, split out for ARCH103): reads the holder
    record purely to NAME the landing ticket in the message, so an
    operator learns which land to wait on rather than only that some land
    exists. An unreadable holder record still refuses -- the lock being
    held is the fact that matters; the record only improves the wording."""
    holder = _read_land_lock_holder_json(path)
    landing_ticket = holder.get("ticket_id") if holder else None
    _log.warning(
        "tickets: %s refused -- a land is in progress for %s "
        "(land.lock held by %s) -- retry after it completes",
        root,
        landing_ticket if landing_ticket else "an unknown ticket",
        holder if holder is not None else "an unreadable/unwritten lock",
    )
    return Err(LeaseError.LandInProgress)


# frob:ticket T-1680
def _land_flock_probe(root: Path) -> Result[None, LeaseError]:
    """The `flock` half of `refuse_if_land_in_progress` (T-1619), split out
    to keep that function under the ARCH001 threshold (T-1680).

    `Err(LandInProgress)` iff a LIVE process holds `LAND_LOCK_REL`. Every
    other outcome is `Ok(None)`: no `fcntl` on this platform, no lock file
    yet (a fresh checkout that has never landed), an unopenable file, or a
    lock this process could itself acquire -- all of which mean "no live
    land", and none of which may block an ordinary `frob ticket new`. The
    acquire is a PROBE and is released immediately; the real land-side
    critical section is `_land.py`'s own `_land_lock`."""
    if fcntl is None:
        return Ok(None)
    path = root / LAND_LOCK_REL
    if not path.exists():
        return Ok(None)
    try:
        fd = os.open(path, os.O_RDWR)
    except OSError:
        return Ok(None)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return _refuse_for_held_land_lock(root, path)
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)
    return Ok(None)


# frob:ticket T-1619
# frob:doc docs/modules/tickets.md#land-exclusivity-lease-t-1619
# Canonical home for `frob ticket land`'s advisory `flock` path (T-0577,
# originally defined only in `frob.tickets._land`). Moved here so this
# module -- the single home for every OTHER ledger-writing verb's
# auto-commit choke point (`_add_and_commit_tickets_md`) -- can probe the
# SAME file `_land.py`'s `_land_lock` holds, instead of a second,
# independently-invented lock/lease mechanism. `frob.tickets._land`
# imports this constant rather than keeping its own copy.
LAND_LOCK_REL = Path(".frob") / "land.lock"

# frob:ticket T-0782
# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# Default staleness horizon for a LIVE-path lease's `recorded_at` (T-0476
# full reconcile): a worktree whose path still exists on disk but whose
# lease has not been refreshed (re-`record_lease`d, e.g. by `mutate_scope`
# or a fresh `frob ticket start`) in this long is treated as belonging to
# a dead/abandoned agent, not an active one -- the daemon's
# `poll_rebase_bot` (`frob.serve._daemon`) stops re-simulating a merge for
# it every ~20s cycle forever (audit M2: 2 git spawns per cycle, per dead
# lease, unbounded). 6 hours is deliberately generous relative to a single
# dispatched ticket's typical wall-clock lifetime (usually well under an
# hour, per this repo's own Done-report timestamps) -- the goal is to
# reclaim leases from agents that crashed or were abandoned mid-ticket,
# never to expire a slow-but-live one out from under it.
LEASE_TTL_SECONDS = 6 * 60 * 60

# frob:ticket T-0773
# Process-lifetime memoization for the hot, previously-uncached read on
# this module's critical path (the 2026-07-22 incident: a single `frob
# ticket list`/`doable` re-scanned the leases directory once per
# candidate/ticket row). The git-common-dir half of this memo moved to
# `frob.gitio.git_common_dir` (T-0784, the single-seam promotion) -- this
# module now delegates to it instead of keeping its own copy.
#
# `read_all_leases`'s per-file cache (`_lease_file_cache`) is a DIFFERENT
# shape than a plain "compute once, keep forever" memo: it is keyed by
# leases directory -> {file path: (stat key, parsed record)} and is
# re-validated against the CURRENT directory listing + per-file
# mtime/size on every call (T-0773 round 2 -- the reviewer-caught daemon-
# blindness bug: `frob.serve`'s `poll_rebase_bot` calls `read_all_leases`
# in a loop for the DAEMON's entire lifetime, and a lease written or
# removed by a SIBLING process -- a different worktree's CLI invocation
# -- is never this process's own `record_lease`/`release_lease` call, so
# there is no local write event to invalidate on). Only the expensive
# part (globbing + JSON-parsing a file whose stat is UNCHANGED since the
# last call) is skipped; the directory's current entry set and every
# file's current stat are always re-read. This is the same "cache the
# expensive step, never cache the liveness-relevant step" split
# `read_all_leases`'s own docstring already argues for the worktree-
# existence check -- extended here to the lease FILE SET itself.
#
# `_cache_lock` (T-0125 precedent, `quiet_stdout_logs`) serializes this
# module's own caches' reads/writes: `frob.serve`'s daemon thread and a
# gate pool's worker processes/threads can call into this module
# concurrently, and a plain dict has no atomicity guarantee across the
# read-check-then-write sequences below (CPython's GIL makes a SINGLE
# dict `__setitem__`/`__getitem__` atomic, but the multi-step "check stat,
# maybe parse, write back" sequence in `read_all_leases` is not one
# operation and must not interleave with another thread's).
_cache_lock = threading.Lock()
_lease_file_cache: dict[
    Path, dict[Path, tuple[tuple[int, int], _LeaseRecord | None]]
] = {}
_stale_lease_logged: set[tuple[Path, str]] = set()
# frob:ticket T-0780
# Which lease files this process has already logged a shape-rejection
# for -- same "log once per process" shape as `_stale_lease_logged`
# (T-0773), so a daemon that re-reads the SAME peer-written evil lease
# every poll cycle warns exactly once, not forever.
_rejected_lease_logged: set[Path] = set()
# frob:ticket T-0782
# Which (leases directory, ticket id) pairs have already had an AMBIGUOUS
# (non-ENOENT) worktree-liveness probe failure logged -- same log-once
# shape as `_stale_lease_logged`, for `_probe_worktree_liveness`'s
# "ambiguous" outcome (T-0584: a slow/flaky mount raising `PermissionError`
# or another transient `OSError` must not be silently re-logged every poll
# cycle, but must also never be silent the FIRST time it happens, since it
# is the signal that a lease is being conservatively kept rather than
# reconciled).
_ambiguous_liveness_logged: set[tuple[Path, str]] = set()

# frob:ticket T-0780
# Conservative allowlist for a lease record's `branch`/`worktree` fields
# before they are ever admitted (`read_all_leases`, `_read_one_lease`) and
# can flow on into `frob.serve._daemon`'s `git merge-base`/`git merge-tree`
# argv (audit M1, docs/audits/frob-blindspots-2026-07-23.md): every
# worktree agent can write under the shared `.git` common dir's
# `frob-leases/` directory (T-0473's whole design), so a lease file's
# content is PEER-WRITABLE, not just self-written -- a crafted
# branch="--output=/tmp/x" must never reach a git argv as an operand.
# Deliberately NOT full `git check-ref-format` conformance (this repo
# never shells out to that plumbing command just to validate a string):
# the allowlist is ASCII alnum/dot/underscore/slash/hyphen, with a leading
# '-' rejected outright regardless of what follows -- narrow enough that
# nothing matching it can be parsed as a git option (no leading dash), and
# permissive enough to admit every real ref shape this repo's lease
# writer actually produces, including the detached-HEAD sentinel
# `branch="HEAD"` (T-0784) and an absolute worktree path. `check-ref-
# format`-level details (no double-dots, no trailing `.lock`, no `@{`)
# are NOT enforced here -- rejecting those too would risk false-positive
# rejections of a legitimate lease over a shape that is annoying, not an
# injection vector; leading-dash rejection is the actual security
# property this ticket needs (option injection), not ref-format purity.
_REF_ALLOWLIST_RE = re.compile(r"^[A-Za-z0-9._/-]+$")


# frob:ticket T-0780
def _looks_like_a_safe_git_argv_operand(value: str) -> bool:
    """`True` iff `value` is safe to later interpolate into a `git` argv
    call as a bare ref/path operand (T-0780) -- non-empty, does not start
    with `-` (so it can never be parsed as an option/flag), and matches
    `_REF_ALLOWLIST_RE`. See that pattern's comment for why this is a
    conservative injection guard, not full `git check-ref-format`
    conformance."""
    if not value or value.startswith("-"):
        return False
    return bool(_REF_ALLOWLIST_RE.match(value))


# frob:ticket T-0780
# frob:ticket T-0601
def _lease_shape_is_safe(record: _LeaseRecord) -> bool:
    """`True` iff `record`'s `branch` and `worktree` fields are both safe
    argv operands (T-0780) -- the admission check `read_all_leases` and
    `_read_one_lease` run on every parsed record BEFORE returning it, so
    an option-injection payload smuggled through the peer-writable lease
    side-channel is dropped here and never reaches `frob.serve._daemon`'s
    `git merge-base`/`git merge-tree` calls at all."""
    return _looks_like_a_safe_git_argv_operand(
        record.branch
    ) and _looks_like_a_safe_git_argv_operand(record.worktree)


# frob:ticket T-0780
# frob:ticket T-0601
def _log_rejected_lease_once(path: Path, record: _LeaseRecord) -> None:
    """Warn, once per process per lease file path (T-0780, same pattern as
    `_stale_lease_logged`/T-0773), that a lease record failed
    `_lease_shape_is_safe` and was dropped rather than admitted -- a
    peer-writable file under the shared leases directory must never be
    silently trusted, but a long-lived daemon re-reading the same bad
    file every poll cycle must not spam the log forever either."""
    with _cache_lock:
        already_logged = path in _rejected_lease_logged
        if not already_logged:
            _rejected_lease_logged.add(path)
    if not already_logged:
        _log.warning(
            "tickets: rejected lease file %s for ticket %s -- unsafe "
            "branch=%r or worktree=%r shape, dropped (never admitted)",
            path,
            record.ticket_id,
            record.branch,
            record.worktree,
        )


# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:ticket T-1054
class LeaseError(ErrorSet):
    """Fallible outcomes of the cross-worktree lease side-channel (T-0473)."""

    GitCommonDirUnavailable = "could not resolve the shared git common dir"
    WriteFailed = "writing the lease file failed"
    NoLeaseForTicket = "the ticket has no recorded lease at all"
    LeaseWorktreeMismatch = "the ticket's recorded lease belongs to another worktree"
    CommitFailed = "committing the start transition into root's ledger failed"
    # frob:ticket T-1619
    LandInProgress = (
        "a land is in progress for this repository; retry after it completes"
    )


# frob:ticket T-0601
class _LeaseRecord(BaseModel):
    """One held cross-worktree scope-lease (T-0473): the ticket id, its
    declared scope at the moment the lease was (re)recorded, and which
    worktree/branch holds it -- read back by `leased_by` in every OTHER
    worktree of the same repository so collision-aware `doable` sees an
    in-progress ticket regardless of which worktree started it."""

    model_config = {}

    ticket_id: str
    scope: tuple[str, ...]
    worktree: str
    branch: str
    recorded_at: str


# frob:ticket T-0782
# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests \
# tests/test_tickets_leases.py::TestLeaseTtl.test_age_seconds_computes_elapsed_time \
# kind="unit"
# frob:tests tests/test_tickets_leases.py::TestLeaseTtl.test_age_seconds_none_for_unparseable_timestamp kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestLeaseAgeSecondsExceptionBranch.test_none_when_recorded_at_is_not_a_string kind="unit"  # noqa: E501
# frob:ticket T-0601
# frob:waive AFFECT001 reason="T-1371 only widens the already-documented 'defensive, a \
# lease file is peer-writable' None-on-failure contract to cover any unresolvable \
# timestamp, not just ValueError -- no observable behavior change, so \
# docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473 needs no update -- \
# doc edits are owned by the concurrent T-1372 DOC006 drain, out of this ticket's scope"
def lease_age_seconds(
    record: _LeaseRecord, *, now: datetime | None = None
) -> float | None:
    """Seconds elapsed since `record.recorded_at`, or `None` if that field
    cannot be parsed as an ISO-8601 timestamp (defensive -- a lease file is
    peer-writable, T-0780) -- `now` is injectable for tests, defaulting to
    the current UTC time. Used by `is_lease_ttl_expired` to judge a
    live-path lease's staleness (T-0782/T-0476) without duplicating the
    parse-and-subtract logic at each call site."""
    try:
        recorded = datetime.fromisoformat(record.recorded_at)
    except ValueError:
        return None
    except Exception:
        # "Defensive -- a lease file is peer-writable" (this function's
        # own docstring) covers any genuinely unresolvable timestamp
        # surprise too, not just `ValueError` (EXHAUST001, T-1371).
        return None
    if recorded.tzinfo is None:
        recorded = recorded.replace(tzinfo=UTC)
    current = now if now is not None else datetime.now(UTC)
    return (current - recorded).total_seconds()


# frob:ticket T-0782
# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests tests/test_tickets_leases.py::TestLeaseTtl.test_expired_past_ttl \
# kind="unit"
# frob:tests tests/test_tickets_leases.py::TestLeaseTtl.test_not_expired_within_ttl \
# kind="unit"
# frob:ticket T-0601
def is_lease_ttl_expired(
    record: _LeaseRecord,
    *,
    now: datetime | None = None,
    ttl_seconds: float = LEASE_TTL_SECONDS,
) -> bool:
    """`True` iff `record`'s `recorded_at` is older than `ttl_seconds`
    (default `LEASE_TTL_SECONDS`) as of `now` (T-0782, the deferred T-0476
    dead-agent-with-a-live-worktree case: `read_all_leases`'s existing
    worktree-path liveness check cannot catch this, since the path still
    exists -- only staleness of the lease's OWN timestamp can). An
    unparseable `recorded_at` (see `lease_age_seconds`) is treated as NOT
    expired -- a malformed timestamp is a shape problem `read_all_leases`'s
    admission check does not currently police, and defaulting to "keep
    considering it live" is the safe direction (never silently drops a
    real lease over a parse quirk)."""
    age = lease_age_seconds(record, now=now)
    if age is None:
        return False
    return age > ttl_seconds


# frob:tests tests/test_ticket_leases_cross_worktree.py::TestGitCommonDir.test_shared_across_linked_worktrees kind="unit"  # noqa: E501
# frob:ticket T-0601
def _git_common_dir(root: Path) -> Result[Path, LeaseError]:
    """The shared `.git` directory for `root`'s repository, resolved to an
    absolute path -- identical across every linked worktree of the same
    repo, unlike `root / ".git"` itself (a linked worktree's `.git` is a
    pointer file, not the shared directory). `Err(GitCommonDirUnavailable)`
    if `root` is not inside a git work tree or the git call fails.

    Thin `LeaseError`-typed wrapper (T-0784) over the single canonical
    `frob.gitio.git_common_dir` -- this module used to keep its own
    process-lifetime memoization (T-0773); that cache moved into
    `frob.gitio` alongside the implementation it memoizes so there is
    exactly one git-common-dir resolver and one cache, not three
    near-identical copies (this module, `frob.gates._exclude_hazard`, and
    a third in `frob.gitio` itself) that could silently desync."""
    resolved = gitio.git_common_dir(root)
    if resolved.is_err:
        _log.warning("tickets: git-common-dir lookup failed under %s", root)
        return Err(LeaseError.GitCommonDirUnavailable)
    return Ok(resolved.danger_ok)


# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.test_lease_written_in_one_worktree_seen_in_another kind="unit"  # noqa: E501
# frob:ticket T-0601
def leases_dir(root: Path) -> Result[Path, LeaseError]:
    """`<git-common-dir>/frob-leases`, the directory every worktree of
    `root`'s repository shares (T-0473) -- created on first write, not
    here, so a read-only caller (`read_all_leases`) never has the side
    effect of creating it."""
    common = _git_common_dir(root)
    if common.is_err:
        return Err(common.danger_err)
    return Ok(common.danger_ok / LEASES_DIRNAME)


def _lease_path(leases_root: Path, ticket_id: str) -> Path:
    """The per-ticket lease file path under `leases_root`."""
    return leases_root / f"{ticket_id}.json"


# frob:ticket T-0782
def _probe_worktree_liveness(worktree: str) -> str:
    """Classifies `worktree`'s on-disk presence as exactly one of
    `"present"`, `"confirmed_absent"`, or `"ambiguous"` (T-0782 reviewer
    fix): `Path.exists()` alone cannot be trusted to gate a destructive
    unlink, because it swallows EVERY `OSError` -- a `PermissionError`, a
    transient stat failure, a stale NFS handle, or a mid-`git worktree
    move` race all read identically to a genuine ENOENT (T-0584's known
    slow-mount concern; the audit's L2 TOCTOU note) and would silently
    make `read_all_leases` delete a perfectly LIVE peer's lease.

    `"present"`: `os.stat(worktree)` succeeded -- the path is there.
    `"confirmed_absent"`: `os.stat(worktree)` raised `FileNotFoundError`
    (the ONLY trustworthy absence signal) AND the PARENT directory itself
    still stats successfully -- this second check exists so a wholesale
    mount failure (the parent itself unreachable) can never be
    misread as "just this one worktree is gone"; only a parent that is
    itself reachable but a specific child that is provably missing counts.
    `"ambiguous"`: any other `OSError` (on either stat) -- the safe,
    conservative fallback that a caller must treat as "cannot confirm
    either way", never as license to delete anything."""
    path = Path(worktree)
    try:
        os.stat(path)
    except FileNotFoundError:
        pass
    except OSError:
        return "ambiguous"
    except Exception:
        # This function's own contract is "the safe, conservative
        # fallback that a caller must treat as cannot confirm either
        # way" for ANY other stat surprise (docstring) -- a non-OSError
        # surprise is the same "do not risk a destructive unlink" outcome
        # (EXHAUST001, T-1371).
        return "ambiguous"
    else:
        return "present"
    try:
        os.stat(path.parent)
    except OSError:
        return "ambiguous"
    except Exception:
        return "ambiguous"
    return "confirmed_absent"


# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.test_lease_written_in_one_worktree_seen_in_another kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches.test_record_lease_degrades_on_mkdir_failure kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches.test_record_lease_degrades_on_write_failure kind="unit"  # noqa: E501
# frob:ticket T-0601
def record_lease(
    root: Path, ticket_id: str, scope: tuple[str, ...]
) -> Result[None, LeaseError]:
    """Write (or overwrite) `ticket_id`'s cross-worktree lease file recording
    `scope` and this worktree's own path/branch (T-0473) -- called by
    `frob.tickets.transition` whenever a ticket enters `IN_PROGRESS`, and by
    `mutate_scope` when an in-progress ticket's scope changes, so the
    lease's recorded scope never drifts from the ledger's.

    Best-effort by design: a `root` that is not a git work tree (a test
    fixture with no `.git`, or a checkout that predates `git init`)
    degrades to a logged warning and `Ok(None)` rather than blocking the
    state transition it rides along with -- the ledger transition itself
    is the source of truth; this side-channel exists to make OTHER
    worktrees aware of it sooner; it is never allowed to be the thing that
    turns a same-worktree `start`/`scope` failure-mode into a NEW failure
    mode.

    T-0784: resolves the common dir and current branch in ONE `git` spawn
    (`gitio.common_dir_and_branch`) rather than the old back-to-back
    `rev-parse --git-common-dir` + `branch --show-current` calls."""
    combined = gitio.common_dir_and_branch(root)
    if combined.is_err:
        _log.warning(
            "tickets: %s lease not recorded (no shared git dir under %s) -- "
            "cross-worktree collision detection degraded for this ticket",
            ticket_id,
            root,
        )
        return Ok(None)
    common_dir, branch = combined.danger_ok
    leases_root = common_dir / LEASES_DIRNAME
    try:
        leases_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _log.warning("tickets: could not create %s: %s", leases_root, exc)
        return Ok(None)

    record = _LeaseRecord(
        ticket_id=ticket_id,
        scope=scope,
        worktree=str(root.resolve()),
        branch=branch,
        recorded_at=datetime.now(UTC).isoformat(),
    )
    try:
        _lease_path(leases_root, ticket_id).write_text(
            record.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        _log.warning("tickets: could not write lease for %s: %s", ticket_id, exc)
        return Ok(None)
    _log.info(
        "tickets: %s lease recorded (worktree=%s branch=%s)",
        ticket_id,
        record.worktree,
        record.branch,
    )
    # T-0773 round 2: no explicit cache invalidation needed here any more
    # -- `read_all_leases`'s per-file stat check picks up this write (new
    # mtime/size, or a brand-new path in the directory listing) on its own
    # next call, from THIS process or any sibling one.
    return Ok(None)


# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.test_release_on_close_removes_the_lease kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches.test_release_lease_degrades_on_unlink_failure kind="unit"  # noqa: E501
def release_lease(root: Path, ticket_id: str) -> Result[None, LeaseError]:
    """Remove `ticket_id`'s cross-worktree lease file, if any (T-0473) --
    called by `frob.tickets.transition` whenever a ticket LEAVES
    `IN_PROGRESS` (closed, requeued, failed, blocked). A missing file (never
    recorded, or already removed) is not an error -- `release_lease` is
    always safe to call unconditionally on any exit from `IN_PROGRESS`."""
    resolved = leases_dir(root)
    if resolved.is_err:
        return Ok(None)
    path = _lease_path(resolved.danger_ok, ticket_id)
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        _log.warning("tickets: could not remove lease for %s: %s", ticket_id, exc)
        return Ok(None)
    # T-0773 round 2: same as `record_lease` -- no explicit invalidation
    # needed, the next `read_all_leases` call (this process or a sibling
    # one) sees the path missing from the current directory listing and
    # drops it from `_lease_file_cache` on its own.
    return Ok(None)


# frob:ticket T-1789
# frob:doc docs/modules/tickets.md#orphaned-lease-detection-and-release-t-1779-finding-7
# frob:tests tests/test_ticket_leases.py::TestOrphanedLeases.test_finds_a_lease_pointing_at_a_gone_worktree  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestOrphanedLeases.test_live_worktree_lease_is_not_orphaned  # noqa: E501
def orphaned_leases(root: Path) -> tuple[_LeaseRecord, ...]:
    """Every lease `read_all_leases(root)` reports whose recorded
    `worktree` path no longer exists on disk at all (T-1779 finding 7):
    T-1766 was held by a lease naming a NESTED worktree
    (`.../agent-X/.claude/worktrees/t-1766`) whose PARENT worktree had
    already been retired and removed, taking the nested one with it --
    `frob ticket doable` correctly refused to offer T-1766 forever, and
    nothing in the system ever reported why.

    Deliberately built on the RAW parse (`_parse_lease_files_cached`),
    NOT `read_all_leases` -- this is the exact bug T-1766 hit. `read_
    all_leases`'s own liveness filter (`_live_leases_pruning_stale`) is
    tuned for SAFE UNLINKING, not reporting: a `"confirmed_absent"` lease
    is unlinked and never appears in its return value at all, but an
    `"ambiguous"` one (T-1766's actual shape -- the PARENT worktree was
    ALSO removed, so `_probe_worktree_liveness`'s own parent-must-be-
    reachable requirement for a trustworthy absence signal could not
    confirm it) is SILENTLY DROPPED from every consumer's view (`doable`
    included) and never unlinked either -- it persists on disk, invisible,
    forever. That is precisely "a gate that lies by omission": nothing
    ever reports it, and no amount of waiting clears it. This function
    surfaces BOTH shapes (confirmed-absent-not-yet-unlinked-this-pass,
    and ambiguous) via a cheaper, unambiguous question a REPORT actually
    wants answered -- `Path(lease.worktree).exists()` -- deliberately
    simpler than `_probe_worktree_liveness`'s three-way split, since a
    report (never a destructive unlink) can afford to treat "cannot
    confirm" the same as "looks gone" and let a human decide via
    `release_orphaned_lease`'s own confirmation step."""
    resolved = leases_dir(root)
    if resolved.is_err:
        return ()
    leases_root = resolved.danger_ok
    if not leases_root.is_dir():
        return ()
    current_paths = sorted(leases_root.glob("*.json"))
    parsed = _parse_lease_files_cached(leases_root, current_paths)
    return tuple(record for record in parsed if not Path(record.worktree).exists())


# frob:ticket T-1789
# frob:doc docs/modules/tickets.md#orphaned-lease-detection-and-release-t-1779-finding-7
# frob:tests tests/test_ticket_leases.py::TestReleaseOrphanedLease.test_releases_a_genuinely_orphaned_lease  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestReleaseOrphanedLease.test_refuses_a_live_worktree_lease  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestReleaseOrphanedLease.test_refuses_an_unknown_ticket_id  # noqa: E501
def release_orphaned_lease(root: Path, ticket_id: str) -> Result[None, LeaseError]:
    """`frob worktree release-lease TICKET-ID` (T-1779 finding 7): the
    SAFE, scoped alternative to a coordinator deleting a lease file by
    hand (`rm .git/frob-leases/T-1766.json`, the actual recovery T-1779's
    sixth incident forced) -- releases exactly ONE ticket's lease, and
    ONLY if `orphaned_leases` confirms its recorded worktree path is
    genuinely gone. Unlike the unconditional `release_lease` (called
    internally by `transition` on every exit from `IN_PROGRESS`, where
    unconditional-safety is the correct contract), this refuses to touch
    a lease still pointing at a real, existing worktree -- the whole
    point of a TARGETED release verb is that a coordinator holding
    several live agents can free one confirmed-dead lease without a
    fleet-wide `frob worktree sweep` (unsafe with live agents) and
    without a risk of releasing a live one by mistake.

    `Err(NoLeaseForTicket)` if `ticket_id` has no lease at all.
    `Err(LeaseWorktreeMismatch)` (repurposed here as "not orphaned" --
    the lease's worktree path DOES exist) if the lease is not actually
    orphaned; the caller wanting to release a live worktree's lease
    anyway should use `frob worktree remove <path> --force` plus the
    ordinary ticket-close path, not this verb.

    Looks the lease up via the SAME raw-parse path `orphaned_leases`
    uses (`_parse_lease_files_cached`), not `read_all_leases` -- a ghost
    lease whose liveness reads `"ambiguous"` (T-1766's actual shape) is
    silently absent from `read_all_leases`'s own return value, which
    would make this function wrongly report `NoLeaseForTicket` for the
    exact lease it exists to release."""
    resolved = leases_dir(root)
    lease: _LeaseRecord | None = None
    if resolved.is_ok:
        leases_root = resolved.danger_ok
        if leases_root.is_dir():
            current_paths = sorted(leases_root.glob("*.json"))
            parsed = _parse_lease_files_cached(leases_root, current_paths)
            lease = next(
                (entry for entry in parsed if entry.ticket_id == ticket_id), None
            )
    if lease is None:
        return Err(LeaseError.NoLeaseForTicket)
    if Path(lease.worktree).exists():
        _log.warning(
            "tickets: %s refused to release lease for %s -- its recorded "
            "worktree %s still exists; not orphaned",
            root,
            ticket_id,
            lease.worktree,
        )
        return Err(LeaseError.LeaseWorktreeMismatch)
    _log.info(
        "tickets: releasing orphaned lease for %s (worktree %s no longer exists)",
        ticket_id,
        lease.worktree,
    )
    return release_lease(root, ticket_id)


# frob:ticket T-1743
# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests tests/test_ticket_leases_cross_worktree.py::TestLeaseAttributionProvenance.test_cross_worktree_holder_names_its_worktree kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases_cross_worktree.py::TestLeaseAttributionProvenance.test_local_only_holder_has_no_worktree kind="unit"  # noqa: E501
def lease_holder_worktree(root: Path, ticket_id: str) -> str | None:
    """The worktree path recorded in `ticket_id`'s CURRENT cross-worktree
    lease file, or `None` if no such file exists (T-1743).

    Exists so a caller attributing a `doable --show-blocked` collision to
    `ticket_id` can name WHERE the block actually comes from, rather than a
    bare id with no provenance -- the exact gap the T-1743 incident hit: an
    id named as the holder that, on inspection (`frob ticket show`), had a
    declared scope that could never have produced the collision. A `None`
    return means the attribution's `all_leases` entry for `ticket_id` came
    from the LOCAL ledger's own `IN_PROGRESS` row (`frob.tickets._doable.
    _in_progress_leases`), not a cross-worktree lease file -- worth
    surfacing explicitly, since a local ledger view can be stale relative
    to `main` (this module's own top-of-file docstring) in a way a live
    lease file, actively written/pruned by every worktree, is not."""
    leases = read_all_leases(root)
    for record in leases:
        if record.ticket_id == ticket_id:
            return record.worktree
    return None


# frob:ticket T-1743
# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests tests/test_ticket_leases_cross_worktree.py::TestForceReleaseLease.test_removes_an_existing_lease_file kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases_cross_worktree.py::TestForceReleaseLease.test_no_op_when_no_lease_file_exists kind="unit"  # noqa: E501
# frob:waive WIRE001 reason="the supported release path for an orphaned lease (T-1743) \
# is a deliberate Python-API-level primitive, meant to be called by an operator or a \
# future CLI verb -- wiring an actual 'frob ticket lease release <id>' command needs \
# src/frob/_cli_parsers/_ticket/** and src/frob/app/config.py, neither of which \
# T-1743's declared scope covers" follow_up="T-1777"
def force_release_lease(root: Path, ticket_id: str) -> Result[bool, LeaseError]:
    """The supported release path for an ORPHANED lease (T-1743): removes
    `ticket_id`'s cross-worktree lease file unconditionally, independent of
    that ticket's own declared `scope` -- `frob ticket scope <id> --remove
    <glob>` refuses (`ScopeRemoveNotDeclared`) the moment the glob is not
    literally in the ticket's own scope list, which makes it structurally
    unable to reach a lease whose holder's scope does not match what a
    caller expected (the T-1743 incident: the real holder, T-1629, had to
    be cleared by deleting its git worktree by hand, an operation no
    worktree-isolated agent can perform). This function operates on the
    lease side-channel file directly, the same primitive `release_lease`
    already uses for a ticket's own clean exit from `IN_PROGRESS` --
    unlike `release_lease`, this is meant to be called by an OPERATOR
    (or a future CLI verb, T-1743's own residue) clearing SOMEONE ELSE's
    lease, so every call is logged at WARNING, naming exactly which
    ticket's lease was released and from where.

    Deliberately does NOT transition `ticket_id`'s own ledger state --
    releasing the lease only stops it from blocking `doable`'s collision
    filter; if the underlying work is genuinely abandoned, the caller
    still owns requeuing the ticket itself (`frob ticket reconcile` or
    `frob ticket requeue <id>`) as a separate, deliberate step.

    Returns `Ok(True)` if a lease file actually existed and was removed,
    `Ok(False)` if there was nothing to release (idempotent -- releasing an
    already-clear lease is not an error, matching `release_lease`'s own
    convention)."""
    resolved = leases_dir(root)
    if resolved.is_err:
        return Err(resolved.danger_err)
    leases_root = resolved.danger_ok
    path = _lease_path(leases_root, ticket_id)
    existed = path.exists()
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        _log.warning(
            "tickets: could not force-release lease for %s: %s", ticket_id, exc
        )
        return Err(LeaseError.WriteFailed)
    if existed:
        with _cache_lock:
            file_cache = _lease_file_cache.get(leases_root)
            if file_cache is not None:
                file_cache.pop(path, None)
        _log.warning(
            "tickets: %s lease FORCE-RELEASED (%s removed) -- this does not "
            "change the ticket's own ledger state; requeue it separately "
            "(frob ticket reconcile / frob ticket requeue) if the "
            "underlying work is abandoned",
            ticket_id,
            path,
        )
    else:
        _log.info(
            "tickets: %s had no lease file to force-release (already clear)",
            ticket_id,
        )
    return Ok(existed)


# frob:ticket T-1173
# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests tests/test_ticket_leases.py::TestRenameLease.test_rename_migrates_the_lease_file_and_updates_its_ticket_id_field kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestRenameLease.test_rename_is_a_no_op_when_no_lease_exists_for_old_id kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches.test_rename_lease_degrades_on_malformed_old_record kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches.test_rename_lease_degrades_on_write_failure kind="unit"  # noqa: E501
def rename_lease(root: Path, old_id: str, new_id: str) -> Result[None, LeaseError]:
    """Migrate `old_id`'s cross-worktree lease file (if any) to `new_id`
    (T-1173): `renumber_one`'s draft-to-final rename rewrites the ticket's
    id everywhere in the ledger and code references, but the lease side-
    channel (T-0473) is keyed by ticket id too -- left un-renamed, a
    worktree that held the draft's lease (`frob ticket start
    T-draft-XXXXXXXX`) looks lease-less the moment `frob ticket land`
    renumbers it to a real id in the SAME worktree, and a subsequent `frob
    check --ticket T-####` there spuriously reports "no recorded lease"
    even though the worktree genuinely holds the ticket.

    A missing old-id lease file (the common case for a ticket that never
    entered `IN_PROGRESS`, or whose lease was already released before this
    rename ran) is not an error -- this is always safe to call
    unconditionally on every `renumber_one`, mirroring `release_lease`'s
    same missing-file tolerance. Best-effort like `record_lease`/
    `release_lease`: a `root` with no shared git dir, an unreadable/
    malformed old record, or an OS-level write/rename failure, degrades to
    a logged warning and `Ok(None)` rather than failing the renumber it
    rides along with.

    Rewrites the record's own `ticket_id` FIELD to `new_id`, not just the
    file's name -- a bare filesystem rename alone would leave the OLD id
    embedded in the JSON body, so a reader that trusts the parsed record's
    `ticket_id` over the path it came from (as `read_all_leases` does)
    would still report the stale id."""
    resolved = leases_dir(root)
    if resolved.is_err:
        return Ok(None)
    leases_root = resolved.danger_ok
    old_path = _lease_path(leases_root, old_id)
    if not old_path.exists():
        return Ok(None)
    try:
        record = _LeaseRecord.model_validate_json(old_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _log.warning(
            "tickets: could not read lease %s to rename to %s: %s",
            old_id,
            new_id,
            exc,
        )
        return Ok(None)
    renamed = record.model_copy(update={"ticket_id": new_id})
    new_path = _lease_path(leases_root, new_id)
    try:
        new_path.write_text(renamed.model_dump_json(indent=2) + "\n", encoding="utf-8")
        old_path.unlink()
    except OSError as exc:
        _log.warning(
            "tickets: could not rename lease %s -> %s: %s", old_id, new_id, exc
        )
        return Ok(None)
    _log.info("tickets: %s lease renamed -> %s", old_id, new_id)
    # T-0773 round 2: same as `record_lease`/`release_lease` -- no explicit
    # cache invalidation needed, the next `read_all_leases` call sees the
    # old path gone and the new path present in the directory listing.
    return Ok(None)


# frob:ticket T-1054
# frob:doc docs/modules/tickets.md#start-transition-auto-commit-t-1054
# frob:tests tests/test_ticket_leases.py::TestCommitStartTransition.test_commits_dirty_ledger_with_expected_message kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestCommitStartTransition.test_no_op_when_ledger_already_clean kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestCommitStartTransition.test_reports_exact_recovery_command_on_commit_failure kind="unit"  # noqa: E501
def commit_start_transition(root: Path, ticket_id: str) -> Result[None, LeaseError]:
    """Commit `root`'s just-written `queued -> in-progress` (or
    `planned -> in-progress`) ledger line, the way `land`'s own
    `_commit_finalize_writes` commits its working-tree writes (T-1054).

    `frob.tickets.transition` writes `tickets.md` straight to `root`'s
    working tree but never commits it -- before this fix, that left `root`
    dirty the moment `frob ticket start` returned, and the FIRST subsequent
    `frob ticket land` (by any agent, often a different worktree entirely)
    refused with `DirtyMain` until a human noticed and hand-committed the
    stray line (the recurring 2026-07-27 incident this ticket exists to
    close -- diagnosed explicitly during the T-1023 land, worked around by
    the coordinator hand-committing 52419399). `start` now owns this commit
    itself, the same way `land` already owns its own ledger commits.

    No-ops (`Ok(None)`) if `root`'s `tickets.md` is not actually dirty --
    a `root` that is not a git work tree, or one where `transition`'s write
    happened to be a no-op byte-for-byte (never observed in practice, but
    not assumed impossible), must not manufacture an empty commit or a
    spurious failure. `Err(LeaseError.CommitFailed)` is returned (and
    LOUDLY logged with the exact recovery command) only when `tickets.md`
    IS dirty and either `git add` or `git commit` itself fails -- the
    caller (`ticket_runner._start`) is expected to surface this as a hard
    `sys.exit(1)`, never a silently-swallowed warning, since a failure here
    is exactly the DirtyMain-at-next-land bug reproducing itself.

    T-1059: also runs `warn_if_worktree_stale` unconditionally, before the
    dirty-ledger short-circuit below, so a stale-base worktree (T-1030) is
    flagged on every `start` regardless of whether this particular ticket
    happens to be the first one committed in it."""
    warn_if_worktree_stale(root, ticket_id)
    if not _tickets_md_dirty(root, ticket_id):
        return Ok(None)
    return _add_and_commit_tickets_md(
        root, ticket_id, f"chore(tickets): record {ticket_id} start transition"
    )


# frob:ticket T-1059
_STALE_WORKTREE_WARN_COMMITS_DEFAULT = 20


# frob:ticket T-1059
# frob:doc docs/modules/tickets.md#stale-worktree-cut-warning-t-1059
# frob:tests tests/test_ticket_leases.py::TestLoadPositiveIntConfig.test_returns_default_when_frob_toml_absent kind="unit"  # noqa: E501
# frob:tests \
# tests/test_ticket_leases.py::TestLoadPositiveIntConfig.test_reads_configured_value \
# kind="unit"
# frob:tests tests/test_ticket_leases.py::TestLoadPositiveIntConfig.test_non_positive_value_falls_back_to_default kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestLoadPositiveIntConfig.test_malformed_toml_falls_back_to_default kind="unit"  # noqa: E501
def load_positive_int_config(root: Path, key: str, default: int) -> int:
    """Read `[tickets] <key>` from `root`'s `frob.toml` as a positive `int`
    (T-1059): the shared degrade-quietly `frob.toml` reader every optional
    `[tickets]` integer tunable uses (`_load_large_glob_max_files`'s
    `large_glob_max_files`, `_load_stale_worktree_warn_commits`'s
    `stale_worktree_warn_commits`) -- extracted here (DUP001) rather than
    each caller re-parsing the same absent-file/malformed-TOML/non-positive-
    value fallback chain. Absent config, an unreadable/malformed file, or a
    non-positive (or bool, since `bool` is an `int` subclass in Python) value
    all fall back to `default` rather than erroring."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return default
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("tickets: could not parse %s: %s", toml_path, exc)
        return default
    value = doc.get("tickets", {}).get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return default
    return value


# frob:ticket T-1059
def _load_stale_worktree_warn_commits(root: Path) -> int:
    """`[tickets] stale_worktree_warn_commits` from `frob.toml` (T-1059) --
    the commits-behind-main-tip threshold `warn_if_worktree_stale` warns at.
    Thin wrapper over `load_positive_int_config` binding its own key/default."""
    return load_positive_int_config(
        root, "stale_worktree_warn_commits", _STALE_WORKTREE_WARN_COMMITS_DEFAULT
    )


# frob:ticket T-1059
# frob:doc docs/modules/tickets.md#stale-worktree-cut-warning-t-1059
# frob:tests tests/test_ticket_leases.py::TestWarnIfWorktreeStale.test_warns_when_behind_threshold kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestWarnIfWorktreeStale.test_silent_when_within_threshold kind="unit"  # noqa: E501
# frob:tests \
# tests/test_ticket_leases.py::TestWarnIfWorktreeStale.test_silent_on_non_git_root \
# kind="unit"
# frob:tests tests/test_ticket_leases.py::TestWarnIfWorktreeStale.test_respects_configured_threshold kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestWarnIfWorktreeStaleFailureBranches.test_silent_when_main_ref_does_not_exist kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestWarnIfWorktreeStaleFailureBranches.test_silent_when_rev_list_count_fails kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestWarnIfWorktreeStaleFailureBranches.test_silent_when_count_is_not_numeric kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestWarnIfWorktreeStaleFailureBranches.test_silent_when_config_lookup_raises kind="unit"  # noqa: E501
# frob:waive AFFECT001 reason="T-1371 only widens the already-documented 'best-effort \
# and non-fatal' silent-no-op contract to cover any git-result-shape surprise, not \
# just the .is_err-checked cases -- no observable behavior change, so \
# docs/modules/tickets.md#stale-worktree-cut-warning-t-1059 needs no update -- doc \
# edits are owned by the concurrent T-1372 DOC006 drain, out of this ticket's scope"
def warn_if_worktree_stale(
    root: Path, ticket_id: str, *, main_ref: str = "main"
) -> None:
    """T-1059/T-1030: warn LOUDLY when `root`'s HEAD is `[tickets]
    stale_worktree_warn_commits`-or-more commits behind `main_ref`'s tip
    (measured from `git merge-base HEAD <main_ref>` to `<main_ref>`) -- the
    stale-worktree-cut hazard T-1030 root-caused (a dispatch harness's
    `EnterWorktree` defaulting to `origin/<default-branch>` instead of local
    HEAD, T-1030 measured 81 commits behind at incident time) caught at
    `start` time instead of silently carried through a whole session,
    pointing at the exact recovery step
    (docs/guides/agent-playbook.md#1-worktree-warm-up).

    Best-effort and non-fatal: any git failure (non-git `root`, missing
    `main_ref`, unparsable count) degrades to a silent no-op, matching this
    module's other optional-signal helpers (`_tickets_md_dirty`) -- this is a
    detector, not a gate, and must never block `start` itself."""
    try:
        threshold = _load_stale_worktree_warn_commits(root)
        merge_base_result = gitio.run_argv(
            ["git", "-C", str(root), "merge-base", "HEAD", main_ref]
        )
        if merge_base_result.is_err or merge_base_result.danger_ok.returncode != 0:
            return
        merge_base = merge_base_result.danger_ok.stdout.strip()
        if not merge_base:
            return
        count_result = gitio.run_argv(
            ["git", "-C", str(root), "rev-list", "--count", f"{merge_base}..{main_ref}"]
        )
        if count_result.is_err or count_result.danger_ok.returncode != 0:
            return
        try:
            behind = int(count_result.danger_ok.stdout.strip())
        except ValueError:
            return
        if behind < threshold:
            return
        _log.warning(
            "ticket start: %s worktree is %d commit(s) behind %s's tip "
            "(merge-base %s) -- this repo has repeatedly been bitten by "
            "worktrees cut from a stale base (T-1030); run `git merge %s` "
            "and re-verify `git log --oneline -1` shows (or descends from) "
            "%s's tip before continuing "
            "(docs/guides/agent-playbook.md#1-worktree-warm-up)",
            ticket_id,
            behind,
            main_ref,
            merge_base[:8],
            main_ref,
            main_ref,
        )
    except (KeyError, TypeError):
        # "Best-effort and non-fatal: any git failure ... degrades to a
        # silent no-op" (this function's own docstring) -- a surprising
        # subprocess-result shape is the same outcome class as the
        # `.is_err`-checked failures above, not a crash of `ticket start`
        # itself (EXHAUST001/EXHAUST002, T-1371).
        return
    except Exception:
        return


# frob:ticket T-1054
# frob:ticket T-1130
def _ledger_pathspecs(root: Path, ticket_id: str) -> tuple[str, ...]:
    """The git pathspec(s) holding `ticket_id`'s ledger content in `root`,
    per the repo's storage backend (T-1553's fresh-repo v2 default made
    this store-mode-dependent).

    v1/'single' and legacy 'dir' repos keep everything in the `tickets.md`
    monofile. A v2 repo keeps it under `tickets/T-####/` (ticket.md,
    done-report.md, attachments) and, once archived, under
    `tickets/archive/T-####/`; a mid-migration repo can still have a live
    monofile alongside either. Only paths that EXIST on disk are returned:
    `git commit -- <pathspec>` is fatal on a pathspec matching nothing, so
    listing every candidate unconditionally would turn each auto-commit
    into a hard `CommitFailed` in exactly the fresh v2 repos this exists
    to serve.

    Hardcoding `tickets.md` here (the pre-T-1553 shape) silently no-opped
    EVERY auto-commit in a v2 repo -- `git status --porcelain -- tickets.md`
    reported clean while the real write landed in `tickets/T-####/`, so
    close/evidence/requeue/done-report all left the ledger uncommitted
    with no error surfaced anywhere."""
    from frob.tickets._store import _store_mode

    if _store_mode(root) != "v2":
        return ("tickets.md",)
    candidates = (
        f"tickets/{ticket_id}",
        f"tickets/archive/{ticket_id}",
        "tickets.md",
    )
    return tuple(rel for rel in candidates if (root / rel).exists())


# frob:ticket T-1615
def _full_ledger_pathspecs(root: Path) -> tuple[str, ...]:
    """The git pathspec(s) covering the WHOLE ledger surface, active AND
    archive, in `root` -- for a verb whose write is not scoped to one
    ticket id (`archive`, which MOVES potentially many done/dropped
    tickets from active into archive in one operation; `migrate`/
    `renumber`'s whole-ledger forms are deliberately excluded from
    auto-commit entirely, see `frob.app.ticket_runner._LEDGER_
    TRANSACTIONAL_VERBS`'s own docstring for why).

    v1/'single': `tickets.md` + `tickets-archive.md`. v2: the whole
    `tickets/` directory as one pathspec -- `archive` renames
    `tickets/T-####/` to `tickets/archive/T-####/`, and `git add
    tickets/` stages both the removal and the addition of a rename in one
    call, simpler and safer than tracking the exact before/after path set
    for a move. Only paths that EXIST on disk are returned, same
    reasoning as `_ledger_pathspecs`."""
    from frob.tickets._store import _store_mode

    if _store_mode(root) != "v2":
        candidates = ("tickets.md", "tickets-archive.md")
    else:
        candidates = ("tickets",)
    return tuple(rel for rel in candidates if (root / rel).exists())


def _tickets_md_dirty(root: Path, ticket_id: str) -> bool:
    """Whether `root`'s ledger storage for `ticket_id` has an uncommitted
    change (T-1054, now shared by `commit_start_transition` AND
    `commit_ticket_ledger_change`, T-1130; store-mode-aware since T-1553's
    v2 default) -- `False` (best-effort, logged) whenever `root` is not a
    git work tree, so a caller degrades to a no-op instead of erroring on
    a non-git fixture root.

    An EMPTY pathspec set (no ledger storage on disk for this ticket yet)
    is `False` rather than an unrestricted `git status`: a bare status
    would report the whole worktree dirty and hand the commit step a
    pathspec-less `git commit` that sweeps in every unrelated staged
    file -- the exact T-1432 poisoning this path is pathspec-limited to
    prevent."""
    pathspecs = _ledger_pathspecs(root, ticket_id)
    if not pathspecs:
        _log.debug(
            "tickets: %s ledger-change commit skipped (no ledger storage "
            "on disk yet under %s)",
            ticket_id,
            root,
        )
        return False
    status = gitio.run_argv(
        ["git", "-C", str(root), "status", "--porcelain", "--", *pathspecs]
    )
    if status.is_err:
        _log.warning(
            "tickets: %s ledger-change commit skipped (git status failed "
            "under %s, likely not a git work tree)",
            ticket_id,
            root,
        )
        return False
    if not status.danger_ok.stdout.strip():
        _log.debug(
            "tickets: %s ledger-change commit skipped (tickets.md already "
            "clean under %s)",
            ticket_id,
            root,
        )
        return False
    return True


# frob:ticket T-1054
@contextmanager
def _without_agent_commit_guard() -> Iterator[None]:
    """Suspend `FROB_AGENT` for the duration of ONE internal `git commit`
    spawn (T-1054), restoring it (or its absence) on exit.

    The scaffolded `pre-commit` hook (T-0431, `frob.scaffold.project`)
    unconditionally refuses any commit made while `FROB_AGENT` is set in
    the environment `git commit` inherits -- a guard against a dispatched
    agent's shell accidentally running a RAW `git commit` against the
    wrong checkout. `commit_start_transition`'s own commit is not that: it
    is `start`'s own internal ledger-commit machinery, the exact same
    "frob verb owns its own git plumbing" shape `land`'s
    `_commit_finalize_writes` already gets via `FROB_LAND_INTERNAL=1` for
    the T-0731 land-owned-files half of the same hook -- but the hook's
    `FROB_AGENT` block has no override flag at all (unconditional,
    unlike the land-owned-files block below it), so the only way for this
    module's OWN commit to not collide with it is to not carry `FROB_AGENT`
    into the `git commit` child process in the first place. Scoped to just
    the commit spawn (not `git add`, which the hook does not gate) so a
    concurrent thread's own `FROB_AGENT` read is never affected for longer
    than necessary."""
    # frob:waive SEC110 reason="FROB_AGENT is a dispatch-context marker (T-0574), \
    # carries no sensitive value"
    prior = os.environ.get("FROB_AGENT")
    if prior is not None:
        # frob:waive SEC110 reason="removing a dispatch-context marker, carries no \
        # sensitive value"
        del os.environ["FROB_AGENT"]
    try:
        yield
    finally:
        if prior is not None:
            # frob:waive SEC110 reason="restoring a dispatch-context marker, carries \
            # no sensitive value"
            os.environ["FROB_AGENT"] = prior


# frob:ticket T-1321
# frob:tests tests/test_ticket_leases.py::TestCommitTicketLedgerChange.test_identity_less_environment_falls_back_to_throwaway_git_identity  # noqa: E501
def _retry_commit_with_fallback_identity(
    root: Path,
    message: str,
    committed: Result[ProcResult, GitError],
    pathspecs: tuple[str, ...],
) -> Result[ProcResult, GitError]:
    """A bare CI runner has no `user.name`/`user.email` in its git config
    (no developer machine's global config to fall back to), so `git
    commit` fails rc=128 with "Author identity unknown" -- T-1321. Retries
    once, ONLY on that specific failure shape, with a throwaway `-c`
    identity scoped to this single invocation (never written to any
    config file) so the ledger commit still succeeds in an identity-less
    environment. Any other failure (a genuine merge conflict, a missing
    repo, etc.) is returned unchanged -- this never masks a real error.

    `pathspecs` must be the SAME set the first attempt used
    (`_ledger_pathspecs`): a retry limited to a different pathspec would
    either commit nothing or sweep in unrelated staged files."""
    if committed.is_ok and committed.danger_ok.returncode == 0:
        return committed
    if committed.is_err:
        return committed
    stderr = committed.danger_ok.stderr
    if "Author identity unknown" not in stderr and "user.email" not in stderr:
        return committed
    _log.warning(
        "tickets: %s has no git user.name/user.email configured -- "
        "retrying the ledger commit with a throwaway frob-bot identity",
        root,
    )
    return gitio.run_argv(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=frob-bot",
            "-c",
            "user.email=frob-bot@example.invalid",
            "commit",
            "-m",
            message,
            "--",
            *pathspecs,
        ]
    )


# frob:ticket T-1619
def _read_land_lock_holder_json(path: Path) -> dict | None:
    """Best-effort read of `path`'s current land.lock holder metadata
    (T-1619) -- mirrors `frob.tickets._land._read_land_lock_holder`'s exact
    parse contract (any read/parse failure is `None`, never raised) so a
    caller here reports the same holder shape (`pid`/`session_id`/
    `started_at`/`ticket_id`) `land()`'s own diagnostics use, without this
    module importing `frob.tickets._land` (which itself imports THIS
    module -- importing back would be a cycle)."""
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


# frob:ticket T-1619
def _proc_cmdline(pid: int) -> tuple[str, ...] | None:
    """`/proc/<pid>/cmdline`'s argv, NUL-split (T-1619) -- `None` on any
    read failure (pid gone, no permission, non-Linux with no `/proc`)."""
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return None
    return tuple(
        part.decode("utf-8", errors="replace") for part in raw.split(b"\0") if part
    )


# frob:ticket T-1619
def _proc_cwd(pid: int) -> Path | None:
    """`/proc/<pid>/cwd`'s resolved target (T-1619) -- `None` on any
    readlink failure (pid gone, no permission, non-Linux)."""
    try:
        return Path(os.readlink(f"/proc/{pid}/cwd")).resolve()
    except OSError:
        return None


# frob:ticket T-1619
_TICKET_ID_ARGV_RE = re.compile(r"^T-\d+$")


# frob:ticket T-1715
# frob:doc docs/modules/tickets.md#worktree-liveness-scan-t-1715-t-1739
# frob:tests tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess.test_finds_a_process_cwd_into_the_path  # noqa: E501
# frob:tests tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess.test_none_when_no_process_matches  # noqa: E501
def scan_for_live_worktree_process(
    path: Path,
) -> tuple[int, tuple[str, ...] | None] | None:
    """Generalizes T-1619's `_scan_for_live_land_process` `/proc` walk for
    T-1715/T-1739: find the first LIVE process -- ANY process, not just a
    `frob ticket land` invocation -- whose `/proc/<pid>/cwd` resolves to
    `path`. Built directly on this module's existing `_proc_cwd` primitive
    and the exact same degrade-to-no-finding contract: `/proc` missing, an
    unreadable pid, or simply no match all return `None`, never a refusal
    by themselves -- an inability to scan must never itself become "proven
    dead".

    Both `frob ticket land --finish` (T-1715, refusing to remove a
    worktree a live process is still cwd'd into out from under it) and
    `frob worktree sweep` (T-1739, the fleet-scale version of the exact
    same hazard) call this single function rather than each re-deriving
    their own `/proc` walk -- there is intentionally only ever one
    process-liveness scanner in this module; `_scan_for_live_land_process`
    below stays a distinct function because it ALSO filters by argv shape
    for land's own belt-and-braces exclusivity check, a different question
    ("is a *land* running against *root*") from this one ("is *anything*
    running in *path*").

    Returns `(pid, argv)` for the first match (`argv` is `None` only if
    that pid's own `/proc/<pid>/cmdline` could not be read, e.g. a
    permissions race between the cwd read and the cmdline read) -- or
    `None` if no live process is cwd'd into `path`."""
    proc_dir = Path("/proc")
    if not proc_dir.is_dir():
        return None
    resolved = path.resolve()
    self_pid = os.getpid()
    try:
        entries = tuple(proc_dir.iterdir())
    except OSError:
        return None
    for entry in entries:
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid == self_pid:
            continue
        if _proc_cwd(pid) != resolved:
            continue
        return (pid, _proc_cmdline(pid))
    return None


# frob:ticket T-1619
# frob:doc docs/modules/tickets.md#land-exclusivity-lease-t-1619
# frob:tests tests/test_ticket_leases.py::TestRefuseIfLandInProgress.test_belt_and_braces_process_scan_without_the_lock_file  # noqa: E501
def _scan_for_live_land_process(root: Path) -> tuple[int, str | None] | None:
    """Belt-and-braces fallback (T-1619, the repo owner's explicit second
    requirement): find a currently-running `frob ticket land` process whose
    cwd is `root`, INDEPENDENT of whether it has (yet, or ever will, e.g. on
    a platform where `fcntl` degrades to a no-op) acquired `LAND_LOCK_REL`.
    Linux-only (`/proc`); degrades to `None` (no finding, never refuses)
    the instant `/proc` itself is unavailable or any per-process read fails
    -- this is a defense-in-depth backstop over the flock probe above, not
    a replacement for it, and must never itself become a reason to block a
    command over an inability to scan.

    Matches a process whose argv contains the literal tokens `"ticket"` and
    `"land"` (the shape `uv run frob ticket land T-#### --worktree ...`
    always produces, argv-split) AND whose `/proc/<pid>/cwd` resolves to
    `root` -- `frob ticket land` is invoked from the primary checkout's own
    directory by convention (playbook section 0), so this is a precise
    enough match for a backstop without needing to parse the full argv
    grammar. Returns `(pid, ticket_id)` where `ticket_id` is the first
    `T-####`-shaped argv token found (or `None` if none matched, e.g. a
    `--plan`/`--queue`/`--drain` invocation with no positional ticket id)."""
    proc_dir = Path("/proc")
    if not proc_dir.is_dir():
        return None
    resolved_root = root.resolve()
    self_pid = os.getpid()
    try:
        entries = tuple(proc_dir.iterdir())
    except OSError:
        return None
    for entry in entries:
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid == self_pid:
            continue
        argv = _proc_cmdline(pid)
        if not argv or "ticket" not in argv or "land" not in argv:
            continue
        if _proc_cwd(pid) != resolved_root:
            continue
        ticket_id = next((arg for arg in argv if _TICKET_ID_ARGV_RE.match(arg)), None)
        return (pid, ticket_id)
    return None


# frob:ticket T-1619
# frob:doc docs/modules/tickets.md#land-exclusivity-lease-t-1619
# frob:tests tests/test_ticket_leases.py::TestRefuseIfLandInProgress.test_refuses_while_land_lock_held  # noqa: E501
# frob:tests \
# tests/test_ticket_leases.py::TestRefuseIfLandInProgress.test_allows_when_no_lock_file
# frob:tests tests/test_ticket_leases.py::TestRefuseIfLandInProgress.test_allows_after_a_killed_lands_lock_is_os_released  # noqa: E501
def refuse_if_land_in_progress(root: Path) -> Result[None, LeaseError]:
    """`Err(LeaseError.LandInProgress)` iff `root` currently has a LIVE
    `frob ticket land` holding its `LAND_LOCK_REL` advisory `flock`
    (T-0577/T-1619) -- the exclusive repository lease every OTHER ledger-
    committing verb (`_add_and_commit_tickets_md`, so `new`/`close`/`drop`/
    `fail`/`requeue`/`block`/`start`/`evidence`/`done-report`, every one of
    them) must check before writing a commit onto `root`'s branch. `Ok
    (None)` otherwise -- no lock file at all, or a lock file whose `flock`
    this process can itself acquire (see below for why that is always safe).

    Crash-safety without a timeout or a separate liveness probe (T-1619's
    explicit requirement: reuse this module's existing liveness machinery
    rather than inventing a second mechanism): a POSIX advisory `flock` is
    released by the kernel itself the instant its holding process exits,
    by ANY means, including an uncatchable `SIGKILL` mid-land -- so a
    non-blocking acquire attempt on `LAND_LOCK_REL` is already a
    structurally trustworthy liveness probe, with none of the confirmed_
    absent/ambiguous uncertainty `_probe_worktree_liveness` has to draw
    for a plain on-disk path (a worktree directory does not vanish just
    because the process that created it died). Failing to acquire the
    lock here can only mean a currently-alive process holds it -- there is
    no "dead holder, lock still held" state for `flock` to be ambiguous
    about, so a probe-and-release attempt is both sufficient and correct
    without polling, without a TTL, and without touching the pid-liveness
    probing `frob.tickets._land._probe_land_lock_pid_liveness` uses purely
    for its own RECLAIM-DISCLOSURE logging (a separate, best-effort
    diagnostic concern this refusal check does not need).

    T-1619 (repo owner's explicit second requirement, "belt and braces
    during the transition"): even when the `flock` probe above finds no
    live holder, this ALSO runs `_scan_for_live_land_process` -- a
    `/proc`-based backstop that catches the two gaps a pure `flock` check
    cannot: the narrow race window between a land PROCESS starting and its
    first `_land_lock` acquisition, and a platform where `fcntl` degrades
    to a no-op (in which case the flock check above never engages at all).
    A finding there refuses exactly like a held flock does, naming the
    ticket id parsed from the process's own argv when one was found.

    Best-effort like every other lease primitive in this module: a `root`
    where the lock file cannot even be opened (permissions, a genuinely
    missing `.frob/` directory, `fcntl` unavailable on this platform)
    degrades to running the process-scan backstop alone rather than
    refusing outright over an inability to probe -- the flock file itself
    is created by `_land_lock` on the land side, so a fresh checkout that
    has never landed anything has no lock file to probe at all, which must
    never block a first `frob ticket new`."""
    probed = _land_flock_probe(root)
    if probed.is_err:
        return Err(probed.danger_err)
    found = _scan_for_live_land_process(root)
    if found is not None:
        pid, landing_ticket = found
        _log.warning(
            "tickets: %s refused -- a `frob ticket land` process (pid %s) "
            "is running against this repository for %s, even though its "
            "land.lock is not currently held (T-1619 belt-and-braces "
            "process scan) -- retry after it completes",
            root,
            pid,
            landing_ticket if landing_ticket else "an unknown ticket",
        )
        return Err(LeaseError.LandInProgress)
    return Ok(None)


# frob:ticket T-1715
# frob:doc docs/modules/tickets.md#worktree-liveness-scan-t-1715-t-1739
class WorktreeInUseError(ErrorSet):
    """Fallible outcomes of `refuse_if_worktree_in_use` (T-1715): the two
    liveness signals this repo can actually prove -- a live process
    physically cwd'd into the worktree, and an active cross-worktree
    lease still pinned to it."""

    LiveProcess = "a live process is still cwd'd into the worktree"
    LiveLease = "the worktree still holds an active cross-worktree lease"


# frob:ticket T-1715
# frob:tests tests/unit/test_land_finish_guard.py::TestLiveLeaseForWorktree.test_finds_a_live_lease_pinned_to_the_worktree  # noqa: E501
def _live_lease_for_worktree(
    worktree: Path,
    leases: tuple[_LeaseRecord, ...],
    *,
    now: datetime | None = None,
) -> _LeaseRecord | None:
    """The first LIVE (unexpired, `is_lease_ttl_expired`) lease among
    `leases` whose recorded worktree path resolves to `worktree`, or
    `None`. Factored out of `_sweep_verdict_for_worktree` (T-0836) so
    T-1715's `--finish` liveness refusal makes the EXACT SAME lease-
    liveness judgment `frob worktree sweep` already makes for its own
    `kept:lease` verdict, rather than a second, possibly-diverging copy
    of the same loop -- `_sweep_verdict_for_worktree` now calls this too."""
    resolved = worktree.resolve()
    for record in leases:
        try:
            record_path = Path(record.worktree).resolve()
        except OSError:
            continue
        if record_path != resolved:
            continue
        if not is_lease_ttl_expired(record, now=now):
            return record
    return None


# frob:ticket T-1715
# frob:doc docs/modules/tickets.md#worktree-liveness-scan-t-1715-t-1739
# frob:tests tests/unit/test_land_finish_guard.py::TestRefuseIfWorktreeInUse.test_refuses_on_a_live_process_and_names_the_pid  # noqa: E501
# frob:tests tests/unit/test_land_finish_guard.py::TestRefuseIfWorktreeInUse.test_refuses_on_a_live_lease  # noqa: E501
# frob:tests tests/unit/test_land_finish_guard.py::TestRefuseIfWorktreeInUse.test_allows_when_neither_signal_fires  # noqa: E501
def refuse_if_worktree_in_use(
    root: Path, worktree: Path, *, now: datetime | None = None
) -> Result[None, WorktreeInUseError]:
    """`Err(...)` iff `worktree` is provably still in use, by either of
    the two signals this repo can actually check (T-1715, reused verbatim
    by T-1739's sweep): a live process cwd'd into it
    (`scan_for_live_worktree_process`), or a live cross-worktree lease
    still pinned to it (`_live_lease_for_worktree` over
    `read_all_leases`). `Ok(None)` only when NEITHER signal fires --
    "could not determine liveness" is not a state this function can even
    produce, by construction: both checks are best-effort and degrade to
    `None`/no-match rather than raising, and a `None`/no-match result
    from either one is treated as "not proven in use", never as "proven
    not in use" -- the caller (`_finish_worktree`'s `--finish` guard,
    `_sweep_verdict_for_worktree`'s `kept:live` verdict) is the one that
    turns an `Ok(None)` here into an actual removal; this function only
    ever answers the liveness question, it never removes anything itself.

    Every refusal logs (at ERROR) the pid or the pinning ticket id by
    name -- playbook precedent (T-1698/T-1699's DirtyMain lesson): an
    error that does not name its own cause is what has cost agents their
    entire budget, repeatedly."""
    found = scan_for_live_worktree_process(worktree)
    if found is not None:
        pid, argv = found
        argv_str = " ".join(argv) if argv else "argv unknown"
        _log.error(
            "tickets: refusing to remove %s -- pid %s has it as its cwd "
            "(%s); land/sweep without removing it, retry once that "
            "process exits, or pass --force if you have independently "
            "confirmed it is stale",
            worktree,
            pid,
            argv_str,
        )
        return Err(WorktreeInUseError.LiveProcess)
    leases = read_all_leases(root)
    live_lease = _live_lease_for_worktree(worktree, leases, now=now)
    if live_lease is not None:
        _log.error(
            "tickets: refusing to remove %s -- it still holds an active "
            "lease for %s (recorded %s); pass --force if you have "
            "independently confirmed the lease is stale",
            worktree,
            live_lease.ticket_id,
            live_lease.recorded_at,
        )
        return Err(WorktreeInUseError.LiveLease)
    return Ok(None)


# frob:ticket T-1054
# frob:ticket T-1432
# frob:tests tests/test_ticket_leases.py::TestCommitTicketLedgerChange.test_pre_staged_unrelated_file_never_rides_along_into_the_commit  # noqa: E501
# T-1432 fix: the commit step is pathspec-limited (`git commit -m message
# -- <pathspecs>`, git's documented `--only`-equivalent form for a bare
# `-- <pathspec>` after the message) rather than a bare `git commit -m
# message`, which commits the ENTIRE index regardless of what was
# actually staged for THIS change. The T-1403 c2fd45da incident: anything
# ALREADY staged in the checkout for an unrelated reason (a conflicted
# `git stash pop` auto-stages every file that merged cleanly, section 1b2
# of `docs/guides/agent-playbook.md`) rode along into the ledger commit
# under a `chore(tickets): ...` message that had nothing to do with it,
# poisoning `git blame`/bisect archaeology for whatever it swept in.
# Pathspec-limiting means this commit can now NEVER contain anything but
# its own declared pathspecs' change -- any other staged content stays
# staged, untouched, exactly as `git commit -- <pathspec>`'s own
# documented contract guarantees.
#
# T-1619: refuses BEFORE touching git at all (`Err(LandInProgress)`,
# never `CommitFailed`) whenever `root` currently has a live `frob ticket
# land` holding its exclusive `LAND_LOCK_REL` flock
# (`refuse_if_land_in_progress`) -- this is the single choke point every
# ledger-committing verb funnels through (`commit_ticket_ledger_change`/
# `commit_start_transition`/T-1615's `commit_full_ledger_change`), so
# this one check closes the concurrent-write hazard for every one of them
# at once, without each verb's own call site needing to remember to
# check separately.
def _add_and_commit_tickets_md(
    root: Path,
    ticket_id: str,
    message: str,
    *,
    pathspecs: tuple[str, ...] | None = None,
) -> Result[None, LeaseError]:
    """`git add <pathspecs> && git commit -m message -- <pathspecs>` in
    `root` (T-1054, generalized T-1130 to take an explicit `message`
    rather than always hardcoding "start transition" -- `commit_start_
    transition` and `commit_ticket_ledger_change` both funnel through this
    one add+commit primitive with their own message text). `Err(
    CommitFailed)`, loudly logged with the exact recovery command, if
    either step fails.

    `pathspecs=None` computes `_ledger_pathspecs(root, ticket_id)`;
    `commit_full_ledger_change` (T-1615, a whole-ledger write not scoped
    to one ticket, e.g. `archive`) passes `_full_ledger_pathspecs(root)`
    explicitly instead, reusing this same core. See the module comment
    directly above this function for the T-1432/T-1619 rationale."""
    land_check = refuse_if_land_in_progress(root)
    if land_check.is_err:
        return Err(land_check.danger_err)
    if pathspecs is None:
        pathspecs = _ledger_pathspecs(root, ticket_id)
    added = gitio.run_argv(["git", "-C", str(root), "add", *pathspecs])
    if added.is_ok and added.danger_ok.returncode == 0:
        with _without_agent_commit_guard():
            committed = gitio.run_argv(
                ["git", "-C", str(root), "commit", "-m", message, "--", *pathspecs]
            )
            committed = _retry_commit_with_fallback_identity(
                root, message, committed, pathspecs
            )
    else:
        committed = added
    if (
        added.is_err
        or added.danger_ok.returncode != 0
        or committed.is_err
        or committed.danger_ok.returncode != 0
    ):
        _log_ledger_commit_failure(ticket_id, root, message, pathspecs)
        return Err(LeaseError.CommitFailed)

    _log.info(
        "tickets: %s ledger change committed in %s (%s)",
        ticket_id,
        root,
        message,
    )
    return Ok(None)


def _log_ledger_commit_failure(
    ticket_id: str, root: Path, message: str, pathspecs: tuple[str, ...]
) -> None:
    """The DirtyMain-causing failure log `_add_and_commit_tickets_md`
    emits when its own `git add`/`git commit` step fails -- split out
    only to keep that function under the ARCH001 line threshold, names
    the exact recovery command every time."""
    _log.error(
        "tickets: %s ledger change left %s DIRTY -- the commit step "
        "failed. Run this by hand before anything else lands: "
        'git -C %s add %s && git -C %s commit -m "%s" -- %s',
        ticket_id,
        root,
        root,
        " ".join(pathspecs),
        root,
        message,
        " ".join(pathspecs),
    )


# frob:ticket T-1130
# frob:ticket T-1615
# frob:doc docs/modules/tickets.md#newdropfail-auto-commit-t-1130
# frob:tests tests/test_ticket_leases.py::TestCommitTicketLedgerChange.test_commits_dirty_ledger_with_given_message kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestCommitTicketLedgerChange.test_no_op_when_ledger_already_clean kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestCommitTicketLedgerChange.test_no_commit_flag_skips_entirely_even_when_dirty kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestCommitTicketLedgerChange.test_no_commit_flag_warns_when_dirty kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestCommitTicketLedgerChange.test_no_commit_flag_does_not_warn_when_clean kind="unit"  # noqa: E501
def commit_ticket_ledger_change(
    root: Path, ticket_id: str, message: str, *, no_commit: bool = False
) -> Result[None, LeaseError]:
    """Auto-commit `root`'s just-written `tickets.md` change with `message`
    (T-1130, parity with T-1054's `commit_start_transition` for `frob
    ticket new`/`drop`/`fail`'s own ledger writes -- these three verbs
    used to leave `tickets.md` dirty the same way `start` did before
    T-1054, and "commit before dispatching" was coordinator memory rather
    than something the tool itself guaranteed; T-1018 is the incident this
    closes for the remaining verbs). T-1615 made this THE single choke
    point every ledger-mutating verb in the dispatch table funnels
    through (`_auto_commit_ledger_after_dispatch` in
    `frob.app.ticket_runner`), so this docstring's warning behavior below
    now applies uniformly to every one of them, not just the original
    new/drop/fail/close/start/requeue/evidence/done-report set.

    `no_commit=True` (the opt-out flag, `frob ticket new/drop/fail
    --no-commit`) skips the commit itself without even checking
    dirtiness for THAT purpose -- for a caller that wants to batch
    several ledger writes into one commit of its own. T-1615: it still
    checks dirtiness ONCE, purely to decide whether to WARN -- a silent
    opt-out reproduces the exact 2026-08-06 incident this ticket exists
    to close (an uncommitted `tickets.md` DirtyMain-blocking every
    concurrent `frob ticket land`) with an extra step, so leaving the
    ledger dirty on purpose must never be quiet. Otherwise a no-op (`Ok
    (None)`) whenever `tickets.md` is not actually dirty (same reasoning
    as `commit_start_transition`: a `root` that is not a git work tree,
    or a write that happened to be a no-op, must never manufacture an
    empty commit). `Err(LeaseError.CommitFailed)` only when `tickets.md`
    IS dirty and either `git add`/`git commit` itself fails -- callers
    are expected to surface this as a hard `sys.exit(1)`, the same
    posture `commit_start_transition`'s own callers already have."""
    if no_commit:
        if _tickets_md_dirty(root, ticket_id):
            pathspecs = _ledger_pathspecs(root, ticket_id)
            _log.warning(
                "tickets: %s ledger change left DIRTY by --no-commit -- "
                "this WILL DirtyMain-block every concurrent `frob ticket "
                "land` in %s until it is committed. Fix: git -C %s add %s "
                '&& git -C %s commit -m "%s" -- %s',
                ticket_id,
                root,
                root,
                " ".join(pathspecs),
                root,
                message,
                " ".join(pathspecs),
            )
        return Ok(None)
    if not _tickets_md_dirty(root, ticket_id):
        return Ok(None)
    return _add_and_commit_tickets_md(root, ticket_id, message)


# frob:ticket T-1615
# frob:doc \
# docs/modules/tickets.md#every-ledger-writing-verb-auto-commits-uniformly-t-1615
# frob:tests tests/test_ticket_leases.py::TestCommitFullLedgerChange.test_commits_dirty_whole_ledger kind="unit"  # noqa: E501
# frob:tests \
# tests/test_ticket_leases.py::TestCommitFullLedgerChange.test_no_op_when_clean \
# kind="unit"
# frob:tests tests/test_ticket_leases.py::TestCommitFullLedgerChange.test_no_commit_flag_warns_when_dirty kind="unit"  # noqa: E501
def commit_full_ledger_change(
    root: Path, message: str, *, no_commit: bool = False
) -> Result[None, LeaseError]:
    """`commit_ticket_ledger_change`'s twin for a write that is NOT scoped
    to one ticket id (T-1615) -- `frob ticket archive`, which moves every
    done/dropped ticket from active into archive in one operation, so
    `_ledger_pathspecs(root, one_ticket_id)` would only ever catch ONE of
    potentially many moved tickets. Uses `_full_ledger_pathspecs` (the
    whole active+archive ledger surface) instead, otherwise identical
    shape: `no_commit=True` still warns (never silently) when it leaves
    the ledger dirty, a no-op when nothing changed, `Err(CommitFailed)`
    only on a real git failure.

    `migrate`/`renumber`'s whole-ledger forms deliberately do NOT call
    this (or `commit_ticket_ledger_change`) -- see `frob.app.ticket_
    runner._LEDGER_TRANSACTIONAL_VERBS`'s own docstring: both rewrite
    potentially many files' `frob:ticket`/`frob:tests`/... directive
    references across the WHOLE tracked tree, not just the ledger, so a
    ledger-only commit here would split one atomic rename into two,
    landing half of it uncommitted -- worse than leaving all of it
    uncommitted together for the caller to commit as one change."""
    pathspecs = _full_ledger_pathspecs(root)
    if no_commit:
        if pathspecs and _full_ledger_dirty(pathspecs, root=root):
            _log.warning(
                "tickets: whole-ledger change left DIRTY by --no-commit -- "
                "this WILL DirtyMain-block every concurrent `frob ticket "
                "land` in %s until it is committed. Fix: git -C %s add %s "
                '&& git -C %s commit -m "%s" -- %s',
                root,
                root,
                " ".join(pathspecs),
                root,
                message,
                " ".join(pathspecs),
            )
        return Ok(None)
    if not pathspecs or not _full_ledger_dirty(pathspecs, root=root):
        return Ok(None)
    return _add_and_commit_tickets_md(
        root, "<whole-ledger>", message, pathspecs=pathspecs
    )


def _full_ledger_dirty(pathspecs: tuple[str, ...], *, root: Path) -> bool:
    """`True` iff any of `pathspecs` (`_full_ledger_pathspecs`'s output)
    has an uncommitted change in `root` -- `commit_full_ledger_change`'s
    own dirty check, split out only because it is needed at two call
    sites (the `no_commit=True` warn path and the real commit path)."""
    status = gitio.run_argv(
        ["git", "-C", str(root), "status", "--porcelain", "--", *pathspecs]
    )
    return status.is_ok and bool(status.danger_ok.stdout.strip())


# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.test_doable_in_second_worktree_hides_colliding_ticket kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.test_stale_lease_for_a_removed_worktree_is_skipped kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestOpportunisticUnlink.test_stale_path_lease_is_unlinked_from_disk kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestOpportunisticUnlink.test_live_lease_is_never_unlinked kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestAmbiguousLivenessGuard.test_ambiguous_stat_failure_does_not_unlink kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestAmbiguousLivenessGuard.test_ambiguous_failure_is_logged_once_per_process kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestAmbiguousLivenessGuard.test_genuine_enoent_still_unlinks kind="unit"  # noqa: E501
# frob:ticket T-0601
def read_all_leases(root: Path) -> tuple[_LeaseRecord, ...]:
    """Every currently-recorded cross-worktree lease visible from `root`'s
    repository (T-0473), id-ordered. Degrades to `()` if there is no shared
    git common dir, no leases directory yet (nothing has ever started a
    ticket), or a lease file is unreadable/malformed -- a corrupt or
    unreadable single lease file is logged and skipped rather than failing
    the whole read, since one bad file must never blind `doable` to every
    OTHER worktree's real leases. A record whose `branch`/`worktree` fails
    `_lease_shape_is_safe` (T-0780 -- an option-injection-shaped value like
    `branch="--output=/tmp/x"`, written by ANY co-located worktree agent
    into the shared, peer-writable leases directory) is likewise dropped
    and logged rather than admitted, since this function's output flows
    on into `frob.serve._daemon`'s `git merge-base`/`git merge-tree` argv.

    Split into a STAT-VALIDATED parse cache and a FRESH liveness check
    (T-0773, revised in round 2 for the daemon-blindness bug a reviewer
    caught): the directory's current file listing and every file's
    current `(mtime_ns, size)` are read on EVERY call -- this is what
    makes a lease written or removed by a SIBLING process (a different
    worktree's CLI invocation, invisible to `frob.serve`'s long-lived
    `poll_rebase_bot` daemon loop, which calls this function forever
    without ever calling this PROCESS's own `record_lease`/
    `release_lease`) show up on the very next call. Only the expensive
    part -- JSON-parsing a file whose stat is UNCHANGED since the last
    call -- is skipped, via `_lease_file_cache`. A file that no longer
    appears in the current listing is dropped from the cache too, so the
    cache can never grow unboundedly stale or leak removed tickets.

    Liveness (`_probe_worktree_liveness`) is re-checked on EVERY call and
    never itself cached, same reasoning extended one level further: a
    lease's worktree can vanish (`git worktree remove`, a crashed agent's
    checkout deleted by hand) with no write to the leases directory at
    all, so even a perfectly fresh file-content read could still serve a
    dead worktree's lease if liveness were cached. `_probe_worktree_
    liveness` is deliberately NOT a plain `Path.exists()` boolean (T-0782
    reviewer fix): `exists()` swallows every `OSError`, so a transient stat
    failure (permission, a stale NFS handle, a slow mount -- T-0584) would
    read identically to a genuine ENOENT and could delete a perfectly LIVE
    peer's lease (audit L2's TOCTOU note). Only a `FileNotFoundError` with
    a still-reachable PARENT directory counts as `"confirmed_absent"` and
    is opportunistically unlinked; anything else the probe cannot resolve
    (`"ambiguous"`) is skipped for this pass exactly like the old
    behavior, but NEVER unlinked. The stale-worktree INFO diagnostic (and
    the separate ambiguous-liveness WARNING) are still only logged ONCE
    per (leases directory, ticket id) per process (`_stale_lease_logged`/
    `_ambiguous_liveness_logged`), even though the liveness probe itself
    reruns every call. All of these
    caches are guarded by `_cache_lock` (T-0773 round 2), but the lock is
    held only around the dict reads/writes themselves -- NEVER across
    file IO or JSON parsing (T-0773 round 3, a second reviewer catch: an
    earlier version held the lock across `path.stat()`/`read_text()`/
    `json.loads()`/`model_validate()` for every file, which would stall
    every OTHER concurrent caller -- the daemon thread and a gate pool's
    workers -- for the whole scan). The sequence per call is: (1) glob +
    stat every file OUTSIDE the lock; (2) take the lock BRIEFLY to read
    each file's cached stat key and decide hit-or-miss; (3) for a miss,
    parse the file OUTSIDE the lock; (4) take the lock BRIEFLY again to
    write the parsed result back and prune removed paths. A benign race
    where two threads both miss the cache for the same file and both
    parse it is possible (last write to the dict wins) -- harmless and
    idempotent, the same reasoning `git_common_dir`'s double-spawn race
    already relies on."""
    resolved = leases_dir(root)
    if resolved.is_err:
        return ()
    leases_root = resolved.danger_ok
    if not leases_root.is_dir():
        with _cache_lock:
            _lease_file_cache.pop(leases_root, None)
        return ()

    current_paths = sorted(leases_root.glob("*.json"))
    parsed = _parse_lease_files_cached(leases_root, current_paths)
    return _live_leases_pruning_stale(leases_root, parsed)


# frob:ticket T-0976
def _parse_lease_files_cached(
    leases_root: Path, current_paths: list[Path]
) -> list["_LeaseRecord"]:
    """`read_all_leases`'s STAT-VALIDATED parse-cache half (T-0773): every
    currently-existing lease file, parsed (via `_lease_file_cache` when its
    stat is unchanged since the last call, freshly otherwise), in the
    original sorted (id-ordered) `current_paths` order -- split from
    `read_all_leases`'s own liveness-check half, which stays uncached.
    See `read_all_leases`'s docstring for the full lock-discipline
    rationale (short locks around cache reads/writes only, never around
    file IO/JSON parsing)."""
    stats = _stat_lease_files(current_paths)
    to_parse, hits = _decide_lease_cache_hits_misses(leases_root, current_paths, stats)
    freshly_parsed = _parse_missed_lease_files(leases_root, to_parse)
    return _recombine_lease_parse_results(current_paths, hits, freshly_parsed)


# frob:ticket T-0976
def _stat_lease_files(current_paths: list[Path]) -> dict[Path, tuple[int, int] | None]:
    """`path -> (mtime_ns, size)` for every lease file in `current_paths`,
    `None` for one that fails to stat (logged, not raised) --
    `_parse_lease_files_cached`'s stat half."""
    stats: dict[Path, tuple[int, int] | None] = {}
    for path in current_paths:
        try:
            st = path.stat()
        except OSError as exc:
            _log.warning("tickets: could not stat lease file %s: %s", path, exc)
            stats[path] = None
            continue
        stats[path] = (st.st_mtime_ns, st.st_size)
    return stats


# frob:ticket T-0976
def _decide_lease_cache_hits_misses(
    leases_root: Path,
    current_paths: list[Path],
    stats: dict[Path, tuple[int, int] | None],
) -> tuple[list[tuple[Path, tuple[int, int]]], dict[Path, "_LeaseRecord | None"]]:
    """Short lock #1: prune stale cache entries and read cached stat keys,
    deciding which files are cache HITS (reuse) vs. MISSES (`to_parse`,
    needs a fresh parse outside the lock) -- `_parse_lease_files_cached`'s
    hit/miss-decision half."""
    current_set = frozenset(current_paths)
    to_parse: list[tuple[Path, tuple[int, int]]] = []
    hits: dict[Path, _LeaseRecord | None] = {}
    with _cache_lock:
        file_cache = _lease_file_cache.setdefault(leases_root, {})
        for stale_path in [p for p in file_cache if p not in current_set]:
            del file_cache[stale_path]
        for path in current_paths:
            stat_key = stats[path]
            if stat_key is None:
                file_cache.pop(path, None)
                continue
            cached_entry = file_cache.get(path)
            if cached_entry is not None and cached_entry[0] == stat_key:
                hits[path] = cached_entry[1]
            else:
                to_parse.append((path, stat_key))
    return to_parse, hits


# frob:ticket T-0976
def _parse_missed_lease_files(
    leases_root: Path, to_parse: list[tuple[Path, tuple[int, int]]]
) -> dict[Path, tuple[tuple[int, int], "_LeaseRecord | None"]]:
    """Parse every cache-miss file in `to_parse` OUTSIDE `_cache_lock` (file
    IO/JSON parsing never holds it, so it never stalls a concurrent
    caller), then write the results back under short lock #2 --
    `_parse_lease_files_cached`'s parse-and-cache-write half."""
    freshly_parsed: dict[Path, tuple[tuple[int, int], _LeaseRecord | None]] = {}
    for path, stat_key in to_parse:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            record: _LeaseRecord | None = _LeaseRecord.model_validate(raw)
        except (OSError, ValueError) as exc:
            _log.warning("tickets: could not parse lease file %s: %s", path, exc)
            record = None
        if record is not None and not _lease_shape_is_safe(record):
            # frob:ticket T-0780
            _log_rejected_lease_once(path, record)
            record = None
        freshly_parsed[path] = (stat_key, record)

    if freshly_parsed:
        with _cache_lock:
            file_cache = _lease_file_cache.setdefault(leases_root, {})
            file_cache.update(freshly_parsed)
    return freshly_parsed


# frob:ticket T-0976
def _recombine_lease_parse_results(
    current_paths: list[Path],
    hits: dict[Path, "_LeaseRecord | None"],
    freshly_parsed: dict[Path, tuple[tuple[int, int], "_LeaseRecord | None"]],
) -> list["_LeaseRecord"]:
    """Recombine `hits`/`freshly_parsed` (separate dicts) in the original
    sorted (id-ordered) `current_paths` order -- naively concatenating
    them would reorder a file-set with a mix of hits and misses --
    `_parse_lease_files_cached`'s final recombination half."""
    parsed: list[_LeaseRecord] = []
    for path in current_paths:
        if path in hits:
            record = hits[path]
        elif path in freshly_parsed:
            record = freshly_parsed[path][1]
        else:
            continue  # unstattable file, already dropped above
        if record is not None:
            parsed.append(record)
    return parsed


# frob:ticket T-0976
def _live_leases_pruning_stale(
    leases_root: Path, parsed: list["_LeaseRecord"]
) -> tuple["_LeaseRecord", ...]:
    """`read_all_leases`'s liveness-check half, re-run on EVERY call and
    never cached (see its docstring for why): filters `parsed` down to
    leases whose worktree is confirmed present, opportunistically
    unlinking (and dropping from `parsed`'s own file cache) any whose
    worktree is confirmed gone, and skipping (never unlinking) any whose
    liveness is ambiguous."""
    live: list[_LeaseRecord] = []
    for record in parsed:
        liveness = _probe_worktree_liveness(record.worktree)
        if liveness == "present":
            live.append(record)
        elif liveness == "ambiguous":
            _log_ambiguous_lease_liveness_once(leases_root, record)
        else:
            _unlink_confirmed_stale_lease(leases_root, record)
    return tuple(live)


# frob:ticket T-0976
def _log_ambiguous_lease_liveness_once(
    leases_root: Path, record: "_LeaseRecord"
) -> None:
    """T-0782 reviewer fix (T-0584's slow-mount concern, audit L2's TOCTOU
    note): `_probe_worktree_liveness` could not confirm either way for
    `record` (a `PermissionError`, a transient stat failure, a stale NFS
    handle, or a mid-`git worktree move` race) -- the ONLY safe move is to
    skip this lease FOR THIS PASS (never treat it as live), but NEVER
    unlink it: an ambiguous read is not evidence of absence. Logs the
    warning at most once per (leases_root, ticket_id) per process."""
    log_key = (leases_root, record.ticket_id)
    with _cache_lock:
        already_logged = log_key in _ambiguous_liveness_logged
        if not already_logged:
            _ambiguous_liveness_logged.add(log_key)
    if not already_logged:
        _log.warning(
            "tickets: %s lease's worktree liveness could not be "
            "confirmed (%s) -- treating as unresolved this pass, "
            "NOT unlinking",
            record.ticket_id,
            record.worktree,
        )


# frob:ticket T-0976
def _unlink_confirmed_stale_lease(leases_root: Path, record: "_LeaseRecord") -> None:
    """T-0473/T-0476's full reconcile for a `record` whose liveness probe
    returned `"confirmed_absent"` -- `_probe_worktree_liveness` has
    confirmed via `FileNotFoundError` (the only trustworthy absence
    signal) plus a successful parent-directory stat that the worktree is
    genuinely gone, so it is safe to opportunistically unlink the lease
    file itself (and drop it from the file cache) -- otherwise `.git/
    frob-leases/` grows monotonically forever (audit M2), since the only
    prior removal path was a clean `IN_PROGRESS` exit (`release_lease`),
    which a crashed/removed worktree never gets to run. Logs the INFO
    diagnostic at most once per (leases_root, ticket_id) per process."""
    record_path = _lease_path(leases_root, record.ticket_id)
    try:
        record_path.unlink(missing_ok=True)
    except OSError as exc:
        _log.warning(
            "tickets: could not opportunistically unlink stale lease %s: %s",
            record_path,
            exc,
        )
    else:
        with _cache_lock:
            file_cache = _lease_file_cache.get(leases_root)
            if file_cache is not None:
                file_cache.pop(record_path, None)
    log_key = (leases_root, record.ticket_id)
    with _cache_lock:
        already_logged = log_key in _stale_lease_logged
        if not already_logged:
            _stale_lease_logged.add(log_key)
    if not already_logged:
        _log.info(
            "tickets: %s lease references a worktree that no "
            "longer exists (%s) -- treating as stale, unlinked",
            record.ticket_id,
            record.worktree,
        )


# frob:ticket T-0836
# frob:ticket T-0601
class _WorktreeSweepError(ErrorSet):
    """Fallible outcomes of `frob worktree sweep` (T-0836)."""

    NotARepo = "root is not inside a git repository"
    ListFailed = "git worktree list --porcelain failed"
    # frob:ticket T-1779
    NotARegisteredWorktree = (
        "path is not a git-registered .claude/worktrees/ agent worktree of root"
    )


# frob:ticket T-0836
# frob:ticket T-0601
# frob:ticket T-1739
class _WorktreeVerdict(BaseModel):
    """One decided outcome for a single dispatched-agent worktree during
    `frob worktree sweep` (T-0836): the worktree's resolved path, the
    verdict tag (`"removed"`, `"kept:live"` [T-1739, a live process is
    cwd'd into it], `"kept:lease"`, `"kept:dirty"`, or `"kept:age"`), and
    a human-readable `detail` string (e.g. the pinning pid for
    `"kept:live"`, the pinning ticket id and lease age for
    `"kept:lease"`; empty for the other verdicts unless a `git worktree
    remove` call itself failed)."""

    model_config = {}

    path: str
    verdict: str
    detail: str = ""


# frob:ticket T-0836
def _is_agent_worktree_path(path: Path) -> bool:
    """`True` iff `path` (already resolved) has a `.claude/worktrees`
    segment anywhere in it -- this repo's own dispatch convention for
    where a per-ticket agent worktree lives (see `docs/guides/agent-
    playbook.md`). `frob worktree sweep` only ever considers paths
    matching this convention as sweep candidates, so the repository's own
    primary checkout (and any worktree a human made by hand somewhere
    else on disk) is never a candidate for removal."""
    parts = path.parts
    return any(
        parts[i] == ".claude" and parts[i + 1] == "worktrees"
        for i in range(len(parts) - 1)
    )


# frob:ticket T-0836
# frob:tests tests/test_ticket_leases.py::TestListAgentWorktrees.test_lists_only_dot_claude_worktrees_paths kind="unit"  # noqa: E501
# frob:ticket T-0601
def _list_agent_worktrees(root: Path) -> Result[tuple[Path, ...], _WorktreeSweepError]:
    """Every git-registered worktree of `root`'s repository whose path
    matches the `.claude/worktrees/` dispatch convention (T-0836), parsed
    from `git worktree list --porcelain`'s stable machine-readable format
    (one blank-line-separated record per worktree, a leading `worktree
    <path>` line). Filtering to the convention means the repo's own
    primary checkout, and any worktree living elsewhere on disk, is never
    returned as a sweep candidate. `Err(ListFailed)` if the `git` call
    itself fails; never raises."""
    spawned = gitio.run_argv(
        ("git", "-C", str(root), "worktree", "list", "--porcelain")
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning(
            "tickets: worktree sweep: git worktree list --porcelain failed under %s",
            root,
        )
        return Err(_WorktreeSweepError.ListFailed)
    paths: list[Path] = []
    for block in spawned.danger_ok.stdout.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("worktree "):
                candidate = Path(line[len("worktree ") :]).resolve()
                if _is_agent_worktree_path(candidate):
                    paths.append(candidate)
                break
    return Ok(tuple(paths))


# frob:ticket T-0836
def _worktree_is_clean(path: Path) -> bool | None:
    """`True`/`False` iff `path`'s working tree has no modified or
    untracked files (`git status --porcelain` empty vs. non-empty),
    `None` if the `git` call itself failed. A caller MUST treat `None`
    the same as "dirty" -- an unresolvable clean check is never license
    to remove a worktree."""
    spawned = gitio.run_argv(("git", "-C", str(path), "status", "--porcelain"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    return spawned.danger_ok.stdout.strip() == ""


# frob:ticket T-0836
def _worktree_head_age_seconds(
    path: Path, *, now: datetime | None = None
) -> float | None:
    """Seconds since `path`'s HEAD commit (`git log -1 --format=%ct`), or
    `None` if unresolvable (a worktree with no commits yet, or a `git`
    failure) -- a caller MUST treat `None` conservatively here too, same
    as `_worktree_is_clean`'s `None`."""
    spawned = gitio.run_argv(("git", "-C", str(path), "log", "-1", "--format=%ct"))
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    try:
        committed = int(spawned.danger_ok.stdout.strip())
    except ValueError:
        return None
    except TypeError:
        # "`None` if unresolvable" (this function's own docstring) covers
        # a surprising subprocess-result shape too, not just `ValueError`
        # (EXHAUST001/EXHAUST002, T-1371).
        return None
    except Exception:
        return None
    current = now if now is not None else datetime.now(UTC)
    return current.timestamp() - committed


# frob:ticket T-0836
# frob:ticket T-1739
# frob:doc docs/guides/agent-playbook.md#12b-coordinator-worktree-cleanup-t-0836
# frob:tests \
# tests/test_ticket_leases.py::TestSweepWorktrees.test_clean_no_lease_removed \
# kind="unit"
# frob:tests \
# tests/test_ticket_leases.py::TestSweepWorktrees.test_clean_live_lease_kept kind="unit"
# frob:tests tests/test_ticket_leases.py::TestSweepWorktrees.test_dirty_kept kind="unit"
# frob:tests \
# tests/test_ticket_leases.py::TestSweepWorktrees.test_expired_lease_clean_removed \
# kind="unit"
# frob:tests \
# tests/test_ticket_leases.py::TestSweepWorktrees.test_dry_run_removes_nothing \
# kind="unit"
# frob:tests \
# tests/test_ticket_leases.py::TestSweepWorktrees.test_branches_survive_removal \
# kind="unit"
# frob:tests \
# tests/test_ticket_leases.py::TestSweepWorktrees.test_min_age_keeps_recent_worktree \
# kind="unit"
# frob:tests tests/test_worktree_guard.py::TestSweepWorktreesLiveProcess.test_clean_no_lease_recent_head_live_process_kept  # noqa: E501
# frob:tests tests/test_worktree_guard.py::TestSweepWorktreesLiveProcess.test_force_overrides_the_live_process_keep  # noqa: E501
# frob:ticket T-0601
def sweep_worktrees(
    root: Path,
    *,
    min_age_hours: float | None = None,
    dry_run: bool = False,
    now: datetime | None = None,
    force: bool = False,
) -> Result[tuple[_WorktreeVerdict, ...], _WorktreeSweepError]:
    """Decide, and (unless `dry_run`) act on, a removal verdict for every
    dispatched-agent worktree under `root`'s repository (T-0836) -- the
    lease-aware fix for the incident where a raw `git worktree remove`
    hand-sweep destroyed a live agent's CLEAN worktree: git's own dirty
    check cannot see a live agent between writes, only this repo's own
    lease machinery (`read_all_leases`/`is_lease_ttl_expired`) can.

    T-1739: BEFORE any of the below, a candidate is kept (`kept:live`) if
    `scan_for_live_worktree_process` finds a live process cwd'd into it --
    this is the fix for the exactly-inverted dry-run this ticket
    documents (a clean, unleased, recently-committed worktree with a
    live agent still in it used to read as `removed`). This gate is
    UNCONDITIONAL relative to the three below: dirty/lease/age are all
    proxies for liveness, and a well-behaved agent that COMMITS ITS OWN
    WORK-IN-PROGRESS (this repo's own stall-insurance guidance) defeats
    the dirty proxy specifically -- following the guidance must never
    make a worktree MORE likely to be swept. `force=True` is the only
    override.

    A worktree is removed only if ALL of these hold:
      (0) [T-1739] no live process is cwd'd into it (unless `force`);
      (a) its working tree is clean (`_worktree_is_clean` is `True` --
          `None`/unresolvable counts as dirty, never as clean);
      (b) no LIVE (unexpired) lease (`is_lease_ttl_expired`) among
          `read_all_leases(root)` is pinned to it -- an EXPIRED lease is
          treated as not live, exactly like a dead agent's abandoned
          worktree, and does not block removal.

    `min_age_hours`, if given, adds a fourth gate: a worktree whose HEAD
    commit (`_worktree_head_age_seconds`) is newer than `min_age_hours`
    (or whose age is unresolvable) is kept regardless of (a)/(b).

    `dry_run=True` computes and returns the same verdicts but never calls
    `git worktree remove` -- used by `--dry-run` to preview a sweep.
    Removal NEVER deletes a branch (`git worktree remove` alone never
    does); the branch this worktree points to survives every removal
    this function performs.

    Reuses `scan_for_live_worktree_process`/`read_all_leases`/
    `is_lease_ttl_expired`/`lease_age_seconds` directly rather than
    re-deriving liveness -- this ticket's own incident was caused by a
    sweep whose keep-criteria had no liveness check at all, not by a bug
    within the liveness machinery itself.

    `Err(ListFailed)` if `_list_agent_worktrees` itself fails; never
    raises."""
    candidates = _list_agent_worktrees(root)
    if candidates.is_err:
        return Err(candidates.danger_err)
    leases = read_all_leases(root)
    verdicts = [
        _sweep_verdict_for_worktree(
            root, candidate, leases, min_age_hours, dry_run, now, force=force
        )
        for candidate in candidates.danger_ok
    ]
    return Ok(tuple(verdicts))


# frob:ticket T-1779
# frob:doc docs/modules/tickets.md#root-checkout-write-guard-t-1779
# frob:tests \
# tests/test_ticket_leases.py::TestRemoveWorktree.test_removes_a_clean_unleased_worktree
# frob:tests \
# tests/test_ticket_leases.py::TestRemoveWorktree.test_keeps_a_live_process_worktree
# frob:tests tests/test_ticket_leases.py::TestRemoveWorktree.test_refuses_a_path_not_registered_as_a_worktree  # noqa: E501
def remove_worktree(
    root: Path,
    path: Path,
    *,
    dry_run: bool = False,
    force: bool = False,
    now: datetime | None = None,
) -> Result[_WorktreeVerdict, _WorktreeSweepError]:
    """`frob worktree remove PATH` (T-1779): the single-worktree twin of
    `sweep_worktrees`, for a coordinator who wants a SAFE alternative to
    raw `git worktree remove` for ONE specific worktree, not a bulk scan.

    T-1779's incident 4: `git worktree remove` deleted a LIVE agent's
    checkout outright -- there is no way to make the raw git command
    itself refuse (T-1739's liveness gate is this repo's own invention,
    not something `git worktree remove` knows about), so the fix is
    making the SAFE path (this function, and the `frob worktree remove`
    CLI verb it powers) easier to reach than the raw command, not
    guarding the raw command itself.

    Reuses `_sweep_verdict_for_worktree` (T-1739's per-candidate liveness/
    dirty/lease/age decision) directly rather than re-deriving any of its
    gates -- a single-worktree call is exactly `sweep_worktrees`'s own
    per-candidate loop body with one candidate instead of every
    `.claude/worktrees/` entry, so the same T-1739 liveness-first
    ordering, the same `force` escape hatch, and the same failure-closed
    posture on an unresolvable clean/lease/age check all apply unchanged.

    `Err(NotARegisteredWorktree)` if `path` (resolved) is not one of
    `root`'s own git-registered worktrees under the `.claude/worktrees/`
    dispatch convention (`_is_agent_worktree_path`) -- this function will
    never act on the repository's own primary checkout or a hand-made
    worktree living elsewhere on disk, the same restriction
    `_list_agent_worktrees` already enforces for the bulk sweep.
    `Err(ListFailed)` if `git worktree list --porcelain` itself fails."""
    resolved = path.resolve()
    if not _is_agent_worktree_path(resolved):
        return Err(_WorktreeSweepError.NotARegisteredWorktree)
    candidates = _list_agent_worktrees(root)
    if candidates.is_err:
        return Err(candidates.danger_err)
    if resolved not in candidates.danger_ok:
        return Err(_WorktreeSweepError.NotARegisteredWorktree)
    leases = read_all_leases(root)
    verdict = _sweep_verdict_for_worktree(
        root, resolved, leases, None, dry_run, now, force=force
    )
    return Ok(verdict)


# frob:ticket T-1739
def _kept_live_verdict_if_process_present(candidate: Path) -> "_WorktreeVerdict | None":
    """`_sweep_verdict_for_worktree`'s T-1739 liveness gate, split out to
    stay under ARCH001's per-function line budget: `kept:live` (naming the
    pid) if `scan_for_live_worktree_process` finds a live process cwd'd
    into `candidate`, else `None` (the caller falls through to the
    dirty/lease/age gates)."""
    found = scan_for_live_worktree_process(candidate)
    if found is None:
        return None
    pid, argv = found
    argv_str = " ".join(argv) if argv else "argv unknown"
    _log.warning(
        "tickets: worktree sweep: kept %s -- pid %s has it as its cwd (%s)",
        candidate,
        pid,
        argv_str,
    )
    return _WorktreeVerdict(
        path=str(candidate), verdict="kept:live", detail=f"pid {pid}"
    )


# frob:ticket T-1739
def _kept_lease_or_age_verdict(
    candidate: Path,
    leases: tuple["_LeaseRecord", ...],
    min_age_hours: float | None,
    now: datetime | None,
) -> "_WorktreeVerdict | None":
    """`_sweep_verdict_for_worktree`'s lease/age gates, split out to stay
    under ARCH001's per-function line budget: `kept:lease` if a live lease
    (`_live_lease_for_worktree`) is pinned to `candidate`, `kept:age` if
    `min_age_hours` is set and `candidate`'s HEAD commit is too recent (or
    unresolvable) to judge, else `None` (the caller proceeds to remove).
    Any surprise while judging either gate fails CLOSED to `kept:age`, the
    same removal-safety posture `sweep_worktrees`'s own docstring
    documents (EXHAUST001/EXHAUST002, T-1371)."""
    try:
        live_lease = _live_lease_for_worktree(candidate, leases, now=now)
        if live_lease is not None:
            age = lease_age_seconds(live_lease, now=now)
            age_str = f"{int(age)}s" if age is not None else "unknown-age"
            return _WorktreeVerdict(
                path=str(candidate),
                verdict="kept:lease",
                detail=f"{live_lease.ticket_id} {age_str}",
            )
        if min_age_hours is not None:
            head_age = _worktree_head_age_seconds(candidate, now=now)
            if head_age is None or head_age < min_age_hours * 3600:
                return _WorktreeVerdict(path=str(candidate), verdict="kept:age")
    except (TypeError, ValueError):
        return _WorktreeVerdict(path=str(candidate), verdict="kept:age")
    except Exception:
        return _WorktreeVerdict(path=str(candidate), verdict="kept:age")
    return None


# frob:ticket T-1739
def _sweep_verdict_for_worktree(
    root: Path,
    candidate: Path,
    leases: tuple["_LeaseRecord", ...],
    min_age_hours: float | None,
    dry_run: bool,
    now: datetime | None,
    *,
    force: bool = False,
) -> "_WorktreeVerdict":
    """One candidate worktree's removal verdict: `sweep_worktrees`'s per-
    candidate half, split from its own candidate-listing loop.

    T-1739: the LIVENESS check (a live process cwd'd into `candidate`,
    `scan_for_live_worktree_process`) runs FIRST, before the dirty/lease/
    age gates below, and unconditionally overrides them -- this is the
    exact fix for the inverted-verdict incident this ticket documents: a
    worktree that is clean, holds no lease, and has a recent HEAD commit
    (today's "remove" shape) still gets `kept:live` if a process is
    actually sitting in it, because a well-behaved agent committing its
    own work-in-progress (this repo's own stall-insurance guidance) makes
    it look identical to an abandoned one under the dirty/lease/age
    proxies alone. `force=True` (the CLI's `--force`) is the only way
    past this gate, for a worktree confirmed genuinely wedged.

    See `sweep_worktrees`'s own docstring for the dirty/lease/age gates
    below this one, in the same order as before."""
    if not force:
        live = _kept_live_verdict_if_process_present(candidate)
        if live is not None:
            return live

    clean = _worktree_is_clean(candidate)
    if clean is not True:
        return _WorktreeVerdict(path=str(candidate), verdict="kept:dirty")

    lease_or_age = _kept_lease_or_age_verdict(candidate, leases, min_age_hours, now)
    if lease_or_age is not None:
        return lease_or_age

    if dry_run:
        return _WorktreeVerdict(
            path=str(candidate), verdict="removed", detail="dry-run"
        )

    removed = gitio.run_argv(
        ("git", "-C", str(root), "worktree", "remove", str(candidate))
    )
    if removed.is_err or removed.danger_ok.returncode != 0:
        _log.warning(
            "tickets: worktree sweep: git worktree remove failed for %s", candidate
        )
        return _WorktreeVerdict(
            path=str(candidate), verdict="kept:dirty", detail="remove-failed"
        )
    _log.info("tickets: worktree sweep removed %s", candidate)
    return _WorktreeVerdict(path=str(candidate), verdict="removed")


# frob:ticket T-0601
def _read_one_lease(leases_root: Path, ticket_id: str) -> _LeaseRecord | None:
    """Read exactly `ticket_id`'s own lease file, by its known path
    (`_lease_path`) -- never by globbing/iterating the leases directory the
    way `read_all_leases` does. `None` if the file is missing or
    unreadable/malformed (logged, not raised)."""
    path = _lease_path(leases_root, ticket_id)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        record = _LeaseRecord.model_validate(raw)
    except (OSError, ValueError) as exc:
        _log.warning("tickets: could not parse lease file %s: %s", path, exc)
        return None
    if not _lease_shape_is_safe(record):
        # frob:ticket T-0780
        _log_rejected_lease_once(path, record)
        return None
    return record


# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests \
# tests/test_tickets_leases.py::TestResolveLease.test_resolves_own_ticket_own_worktree \
# kind="unit"
# frob:tests tests/test_tickets_leases.py::TestResolveLease.test_never_returns_a_sibling_tickets_lease kind="unit"  # noqa: E501
# frob:tests \
# tests/test_tickets_leases.py::TestResolveLease.test_no_lease_for_ticket_fails_loudly \
# kind="unit"
# frob:tests tests/test_tickets_leases.py::TestResolveLease.test_lease_recorded_for_a_different_worktree_fails_loudly kind="unit"  # noqa: E501
# frob:ticket T-0601
def resolve_lease(
    root: Path, ticket_id: str, invoking_worktree: Path
) -> Result[_LeaseRecord, LeaseError]:
    """`ticket_id`'s OWN cross-worktree lease, pinned to `invoking_worktree`
    (T-0766) -- the fix for the T-0695 incident where `frob check --ticket`
    resolved a completely different ticket's (and worktree's) stale lease
    state under concurrent multi-agent load.

    Reads `ticket_id`'s lease file directly by its known per-ticket path
    (`_read_one_lease`), never by scanning/ordering across every recorded
    lease the way a caller hand-rolling this on top of `read_all_leases`
    would have to -- there is no iteration order, mtime, or "first match"
    for a bug to hide in, structurally, because only ONE file is ever
    consulted for a given `ticket_id`.

    `Err(NoLeaseForTicket)` if `ticket_id` has no recorded lease at all --
    the loud, correct outcome when a ticket was never `start`ed (or its
    lease was released), never a silent borrow of some OTHER ticket's
    lease. `Err(LeaseWorktreeMismatch)` if `ticket_id` DOES have a recorded
    lease, but for a worktree other than `invoking_worktree` (paths compared
    resolved, so a relative vs. absolute or symlinked spelling of the same
    worktree still matches) -- this is the resolution NEVER borrowing a
    sibling ticket's lease, no matter how stale or recently-touched it is.
    Both error messages name `frob ticket start <ticket_id>` as the remedy
    (re-recording the lease for the CURRENT invoking worktree), matching
    the T-0695 incident's own observed fix."""
    resolved = leases_dir(root)
    if resolved.is_err:
        return Err(resolved.danger_err)
    record = _read_one_lease(resolved.danger_ok, ticket_id)
    if record is None:
        _log.error(
            "tickets: %s has no recorded lease for %s -- run: frob ticket start %s",
            ticket_id,
            invoking_worktree,
            ticket_id,
        )
        return Err(LeaseError.NoLeaseForTicket)
    invoking_resolved = invoking_worktree.resolve()
    if Path(record.worktree).resolve() != invoking_resolved:
        _log.error(
            "tickets: %s's recorded lease belongs to %s, not the invoking "
            "worktree %s -- refusing to borrow a sibling worktree's lease; "
            "run: frob ticket start %s",
            ticket_id,
            record.worktree,
            invoking_resolved,
            ticket_id,
        )
        return Err(LeaseError.LeaseWorktreeMismatch)
    return Ok(record)

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
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/tickets/_leases.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

import json
import os
import re
import threading
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob import gitio
from frob.logging import get_logger

_log = get_logger(__name__)

# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
LEASES_DIRNAME = "frob-leases"

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


# frob:ticket T-0773
def _clear_lease_caches() -> None:
    """Drop all T-0773 memoization state (`gitio`'s common-dir cache via
    `reset_common_dir_cache`, `_lease_file_cache`, `_stale_lease_logged`)
    -- available to tests that need to simulate a fresh CLI invocation (or
    a fresh daemon poll cycle) within one interpreter; not required for
    correctness on the read path any more (`read_all_leases` self-heals
    against sibling-process writes via per-file stat comparison), but
    still useful to force a clean-slate re-parse."""
    gitio.reset_common_dir_cache()
    with _cache_lock:
        _lease_file_cache.clear()
        _stale_lease_logged.clear()
        _ambiguous_liveness_logged.clear()


# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
class LeaseError(ErrorSet):
    """Fallible outcomes of the cross-worktree lease side-channel (T-0473)."""

    GitCommonDirUnavailable = "could not resolve the shared git common dir"
    WriteFailed = "writing the lease file failed"
    NoLeaseForTicket = "the ticket has no recorded lease at all"
    LeaseWorktreeMismatch = "the ticket's recorded lease belongs to another worktree"


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
# frob:tests tests/test_tickets_leases.py::TestLeaseTtl.test_age_seconds_computes_elapsed_time kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestLeaseTtl.test_age_seconds_none_for_unparseable_timestamp kind="unit"  # noqa: E501
# frob:ticket T-0601
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
    if recorded.tzinfo is None:
        recorded = recorded.replace(tzinfo=UTC)
    current = now if now is not None else datetime.now(UTC)
    return (current - recorded).total_seconds()


# frob:ticket T-0782
# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests tests/test_tickets_leases.py::TestLeaseTtl.test_expired_past_ttl kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestLeaseTtl.test_not_expired_within_ttl kind="unit"  # noqa: E501
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


# frob:waive COV005 reason="T-0601 rework: demoted git_common_dir -> _git_common_dir (frob-exports external-consumer test: only used intra-package by this module's own leases_dir, never imported outside frob.tickets); the frob:tests directive deliberately follows the same function to its new private name"  # noqa: E501
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
    else:
        return "present"
    try:
        os.stat(path.parent)
    except OSError:
        return "ambiguous"
    return "confirmed_absent"


# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.test_lease_written_in_one_worktree_seen_in_another kind="unit"  # noqa: E501
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


# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.test_doable_in_second_worktree_hides_colliding_ticket kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.test_stale_lease_for_a_removed_worktree_is_skipped kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestOpportunisticUnlink.test_stale_path_lease_is_unlinked_from_disk kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestOpportunisticUnlink.test_live_lease_is_never_unlinked kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestAmbiguousLivenessGuard.test_ambiguous_stat_failure_does_not_unlink kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestAmbiguousLivenessGuard.test_ambiguous_failure_is_logged_once_per_process kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestAmbiguousLivenessGuard.test_genuine_enoent_still_unlinks kind="unit"  # noqa: E501
# frob:ticket T-0601
# frob:waive AFFECT001 reason="T-0976 pure internal refactor: extraction of _parse_lease_files_cached/_live_leases_pruning_stale/etc from this already-documented function, no external contract/behavior change, doc anchor(s) remain accurate as-is"  # noqa: E501
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


# frob:ticket T-0836
# frob:ticket T-0601
class _WorktreeVerdict(BaseModel):
    """One decided outcome for a single dispatched-agent worktree during
    `frob worktree sweep` (T-0836): the worktree's resolved path, the
    verdict tag (`"removed"`, `"kept:lease"`, `"kept:dirty"`, or
    `"kept:age"`), and a human-readable `detail` string (e.g. the pinning
    ticket id and lease age for `"kept:lease"`; empty for the other
    verdicts unless a `git worktree remove` call itself failed)."""

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
# frob:waive COV005 reason="T-0601 rework: demoted list_agent_worktrees -> _list_agent_worktrees (frob-exports external-consumer test: only called intra-package by this module's own sweep_worktrees, never imported outside frob.tickets); the frob:tests directive deliberately follows the same function to its new private name"  # noqa: E501
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
    current = now if now is not None else datetime.now(UTC)
    return current.timestamp() - committed


# frob:ticket T-0836
# frob:doc docs/guides/agent-playbook.md#12b-coordinator-worktree-cleanup-t-0836
# frob:tests tests/test_ticket_leases.py::TestSweepWorktrees.test_clean_no_lease_removed kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestSweepWorktrees.test_clean_live_lease_kept kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestSweepWorktrees.test_dirty_kept kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestSweepWorktrees.test_expired_lease_clean_removed kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestSweepWorktrees.test_dry_run_removes_nothing kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestSweepWorktrees.test_branches_survive_removal kind="unit"  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestSweepWorktrees.test_min_age_keeps_recent_worktree kind="unit"  # noqa: E501
# frob:ticket T-0601
# frob:waive AFFECT001 reason="T-0976 pure internal refactor: extraction of _sweep_verdict_for_worktree from this already-documented function, no external contract/behavior change, doc anchor(s) remain accurate as-is"  # noqa: E501
def sweep_worktrees(
    root: Path,
    *,
    min_age_hours: float | None = None,
    dry_run: bool = False,
    now: datetime | None = None,
) -> Result[tuple[_WorktreeVerdict, ...], _WorktreeSweepError]:
    """Decide, and (unless `dry_run`) act on, a removal verdict for every
    dispatched-agent worktree under `root`'s repository (T-0836) -- the
    lease-aware fix for the incident where a raw `git worktree remove`
    hand-sweep destroyed a live agent's CLEAN worktree: git's own dirty
    check cannot see a live agent between writes, only this repo's own
    lease machinery (`read_all_leases`/`is_lease_ttl_expired`) can.

    A worktree is removed only if BOTH hold:
      (a) its working tree is clean (`_worktree_is_clean` is `True` --
          `None`/unresolvable counts as dirty, never as clean);
      (b) no LIVE (unexpired) lease (`is_lease_ttl_expired`) among
          `read_all_leases(root)` is pinned to it -- an EXPIRED lease is
          treated as not live, exactly like a dead agent's abandoned
          worktree, and does not block removal.

    `min_age_hours`, if given, adds a third gate: a worktree whose HEAD
    commit (`_worktree_head_age_seconds`) is newer than `min_age_hours`
    (or whose age is unresolvable) is kept regardless of (a)/(b).

    `dry_run=True` computes and returns the same verdicts but never calls
    `git worktree remove` -- used by `--dry-run` to preview a sweep.
    Removal NEVER deletes a branch (`git worktree remove` alone never
    does); the branch this worktree points to survives every removal
    this function performs.

    Reuses `read_all_leases`/`is_lease_ttl_expired`/`lease_age_seconds`
    directly rather than re-deriving liveness -- this ticket's own
    incident was caused by a sweep that bypassed the lease machinery
    entirely, not by a bug within it.

    `Err(ListFailed)` if `_list_agent_worktrees` itself fails; never
    raises."""
    candidates = _list_agent_worktrees(root)
    if candidates.is_err:
        return Err(candidates.danger_err)
    leases = read_all_leases(root)
    verdicts = [
        _sweep_verdict_for_worktree(
            root, candidate, leases, min_age_hours, dry_run, now
        )
        for candidate in candidates.danger_ok
    ]
    return Ok(tuple(verdicts))


# frob:ticket T-0976
def _sweep_verdict_for_worktree(
    root: Path,
    candidate: Path,
    leases: tuple["_LeaseRecord", ...],
    min_age_hours: float | None,
    dry_run: bool,
    now: datetime | None,
) -> "_WorktreeVerdict":
    """One candidate worktree's removal verdict: `sweep_worktrees`'s per-
    candidate half, split from its own candidate-listing loop. See
    `sweep_worktrees`'s own docstring for the dirty/lease/age gates this
    implements, in the same order."""
    clean = _worktree_is_clean(candidate)
    if clean is not True:
        return _WorktreeVerdict(path=str(candidate), verdict="kept:dirty")

    live_lease: _LeaseRecord | None = None
    for record in leases:
        try:
            record_path = Path(record.worktree).resolve()
        except OSError:
            continue
        if record_path != candidate:
            continue
        if not is_lease_ttl_expired(record, now=now):
            live_lease = record
            break
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
# frob:tests tests/test_tickets_leases.py::TestResolveLease.test_resolves_own_ticket_own_worktree kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestResolveLease.test_never_returns_a_sibling_tickets_lease kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_leases.py::TestResolveLease.test_no_lease_for_ticket_fails_loudly kind="unit"  # noqa: E501
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

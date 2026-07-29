"""Single-flight, foreground, blocking-until-fresh coverage contract (T-0322).

Observed failure mode this replaces: an implementer agent backgrounds `make
coverage` (it exceeds the harness's foreground timeout) and then ends its
turn "waiting" for a notification -- but as a dispatched sub-agent, no such
notification is ever routed to it (docs/guides/agent-playbook.md section
6b). Work sits done-but-uncommitted while the agent loops, and up to
several concurrent agents each separately re-run the full suite under
coverage at once, wasting the exact wall-clock time this is meant to save.

`run_coverage_wait` is the interim (pre-daemon) fix: a plain blocking call
an agent can run in the FOREGROUND and get a definitive fresh-or-failed
result from inline, backed by a single-flight file lock so concurrent
callers serialize onto one real coverage run instead of each starting
their own -- and a second caller that arrives after the first one just
finished the run gets a free "already fresh" answer rather than repeating
the whole suite.

Cross-worktree single-flight (T-1095): T-0322's original lock
(`_coverage_lock`/`coverage_lock_path`) is keyed by WORKTREE PATH
(`<root>/.frob/coverage.lock`), so it only serializes callers sharing one
worktree -- the common parallel-dispatch shape (N agents, N worktrees of
the identical commit, docs/guides/agent-playbook.md) still pays a full
coverage run per worktree even when every one of them has byte-for-byte
identical tracked source content. `run_coverage_wait` now arbitrates a
SECOND, outer layer first: a lock and a content-addressed result cache
keyed by `_tree_digest` (a hash of the snapshot's tracked source file
hashes, the same set `_is_stamp_fresh` already compares against), stored
under `_shared_state_dir` -- a location derived from `git rev-parse
--git-common-dir`, so every worktree of the SAME clone resolves to the
SAME shared directory regardless of which worktree path each one runs
from. Two worktrees whose source digests match contend on the identical
shared lock file and the second one to arrive finds the first one's
`SharedCoverageResult` already cached (`Ok`/`Err`, never re-run); two
worktrees with DIFFERING digests resolve to different lock/cache paths
and never contend with each other at all. This composes with (does not
replace) the original per-worktree lock: the shared layer decides "has
ANY worktree with this exact content already settled this?" before the
per-worktree layer's finer-grained "is MY OWN local stamp already
fresh?" check.
"""
# frob:waive INV006 reason="T-1095 INV006 calibration-batch disposition: this file's \
# exclusivity-vocabulary hits ('only', 'never re-run') are source-level design- \
# rationale prose describing already-implemented internal behavior (verifiable by \
# reading tree_digest/_shared_coverage_lock/run_coverage_wait themselves), not a \
# separate cross-module contract needing its own tracked invariant -- same disposition \
# this repo already applies to src/frob/serve/_socketd.py and \
# src/frob/app/_daemon_proxy.py (T-0585/T-1023/T-1093)"

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from pydantic import BaseModel
from typani import Err, Ok, Result
from typani.error_set import ErrorSet

# frob.gates.__init__ imports from frob.testing (public re-export of
# CollectedTests et al.); importing the *package* here would form a
# circular import that survives merely by accident of import order
# (T-0634). Import `load_stamp` from its actual home module instead --
# frob.gates._coverage does not import frob.testing -- so frob.testing
# can be imported standalone with no ordering dependency on frob.gates.
from frob.gates._coverage import load_stamp
from frob.gitio import git_common_dir
from frob.graph import GraphSnapshot, build_graph, load_graph
from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run

_log = get_logger(__name__)

_LOCK_REL = Path(".frob") / "coverage.lock"
_CACHE_REL = Path(".frob") / "cache.db"
# T-1126: the resource name every `run_coverage_wait` caller contends on
# via the daemon's `frob_lease_acquire`/`frob_lease_release` RPC
# (`ResourceLeaseManager`, T-1097) when a daemon is reachable for `root` --
# arbitrary but must be the same literal every caller uses, the same way
# `_LOCK_REL`'s path must be.
_DAEMON_LEASE_RESOURCE = "coverage"

# T-1095: extensions a tree digest is computed over -- identical to
# `_is_stamp_fresh`'s own filter, so "same digest" and "would already read
# as a fresh local stamp" agree on exactly the same file set.
_DIGESTED_SUFFIXES = (".py", ".rs", ".ts", ".tsx")
# The shared, worktree-path-independent state directory name, created
# under `git_common_dir(root)` -- every worktree of the SAME clone shares
# one `.git` common dir (T-0773/T-0784 precedent), so this resolves to the
# identical filesystem location no matter which worktree calls it from.
_SHARED_STATE_DIRNAME = "frob-coverage-shared"


# frob:doc docs/modules/testing.md#public-api
class CoverageWaitError(ErrorSet):
    """Failure values `run_coverage_wait` can return."""

    RunFailed = "the coverage subprocess exited non-zero"
    SnapshotUnavailable = "the obligation graph snapshot could not be built"


# frob:doc docs/modules/testing.md#public-api
class CoverageWaitOutcome(BaseModel):
    """The result of one `run_coverage_wait` call: whether it found an
    already-fresh stamp (`ran=False`) or had to actually run the coverage
    command (`ran=True`), and how long that took."""

    model_config = {}

    ran: bool
    duration_s: float


# frob:doc docs/modules/testing.md#public-api
# frob:tests tests/test_app.py::TestRunCoverageWait.test_coverage_lock_path_is_under_frob_dir  # noqa: E501
def coverage_lock_path(root: Path) -> Path:
    """The advisory single-flight lock path (`.frob/coverage.lock`) guarding
    concurrent `run_coverage_wait` callers under `root`."""
    return root / _LOCK_REL


@contextmanager
def _coverage_lock(root: Path) -> Iterator[None]:
    """Exclusive, blocking, cross-process lock serializing coverage runs
    under `root` (T-0322 single-flight), mirroring `frob.tickets._store
    .ledger_lock`'s `fcntl.flock`-on-a-dotfile pattern -- a second concurrent
    caller blocks here instead of independently re-running the full suite.
    Degrades to a documented no-op on a non-POSIX platform (same tradeoff
    `ledger_lock` accepts), logged at WARNING rather than silently pretended
    to be locked.
    """
    path = coverage_lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        _log.debug("coverage_wait: lock acquired (%s)", path)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        _log.debug("coverage_wait: lock released (%s)", path)


# frob:tests tests/test_coverage_wait_shared.py::TestWorktreeLock.test_uses_daemon_lease_when_daemon_up kind="unit"  # noqa: E501
# frob:tests tests/test_coverage_wait_shared.py::TestWorktreeLock.test_falls_back_to_file_lock_when_no_daemon kind="unit"  # noqa: E501
@contextmanager
def _worktree_lock(root: Path) -> Iterator[None]:
    """T-1126: this worktree's single-flight coverage-run arbitration --
    prefers the daemon-owned lease RPC (`frob_lease_acquire`/`frob_lease_
    release`, T-1097's `ResourceLeaseManager`, connection-liveness release
    on a crash) when a daemon is reachable for `root`, falling back to the
    original `_coverage_lock` `fcntl` file lock when it is not (no daemon
    running, `FROB_NO_DAEMON=1`, or the lease request itself failed --
    `try_daemon_lease`'s `Err` covers all three identically). Either path
    gives the same guarantee to every caller: only one proceeds past this
    context manager at a time for this worktree. This replaces `_coverage_
    lock` as `run_coverage_wait`'s own OUTER lock; T-1095's cross-worktree
    shared-state layer (`_shared_coverage_lock`, keyed by `tree_digest`
    under `shared_state_dir`) is untouched -- a genuinely different,
    cross-CLONE primitive the per-connection daemon lease does not cover
    (the daemon serves one worktree's own socket, not every worktree of
    the clone)."""
    from frob.app._daemon_proxy import release_daemon_lease, try_daemon_lease

    lease_result = try_daemon_lease(root, _DAEMON_LEASE_RESOURCE)
    if lease_result.is_ok:
        conn = lease_result.danger_ok
        _log.debug("coverage_wait: daemon lease acquired for %s", root)
        try:
            yield
        finally:
            release_daemon_lease(conn, _DAEMON_LEASE_RESOURCE)
            _log.debug("coverage_wait: daemon lease released for %s", root)
        return

    _log.debug(
        "coverage_wait: daemon lease unavailable (%s), falling back to file lock",
        lease_result.danger_err,
    )
    with _coverage_lock(root):
        yield


# frob:doc docs/modules/testing.md#public-api
# frob:tests tests/test_coverage_wait_shared.py::TestTreeDigest.test_identical_hashes_produce_identical_digest kind="unit"  # noqa: E501
# frob:tests tests/test_coverage_wait_shared.py::TestTreeDigest.test_differing_hashes_produce_differing_digest kind="unit"  # noqa: E501
def tree_digest(snapshot: GraphSnapshot) -> str:
    """A stable content digest (sha256 hex) over `snapshot`'s tracked
    source file hashes (`_DIGESTED_SUFFIXES` -- the same filter
    `_is_stamp_fresh` already applies), sorted by path so the digest
    depends only on WHAT content exists, never on dict iteration order.
    Two worktrees whose tracked source is byte-for-byte identical produce
    the identical digest regardless of worktree path (T-1095); two
    worktrees differing by even one tracked file's content produce
    different digests and so never share a lock or cached result."""
    relevant = sorted(
        (path, file_hash)
        for path, file_hash in snapshot.file_hashes.items()
        if path.endswith(_DIGESTED_SUFFIXES)
    )
    hasher = hashlib.sha256()
    for path, file_hash in relevant:
        hasher.update(path.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(file_hash.encode("utf-8"))
        hasher.update(b"\n")
    return hasher.hexdigest()


# frob:doc docs/modules/testing.md#public-api
# frob:tests tests/test_coverage_wait_shared.py::TestSharedStateDir.test_two_worktrees_of_same_clone_share_one_dir kind="unit"  # noqa: E501
# frob:tests tests/test_coverage_wait_shared.py::TestSharedStateDir.test_no_git_falls_back_to_worktree_local kind="unit"  # noqa: E501
def shared_state_dir(root: Path) -> Path:
    """The worktree-path-independent shared state directory (T-1095):
    `<git-common-dir>/frob-coverage-shared/`, one location per CLONE
    (not per worktree) -- resolved via `frob.gitio.git_common_dir`, the
    same primitive `frob.tickets._leases`/`frob.gates._exclude_hazard`
    already share for this exact "one shared dir across every linked
    worktree" need. Falls back to `<root>/.frob/frob-coverage-shared`
    (worktree-local, degrading to the pre-T-1095 single-worktree
    behavior) if `root` is not inside a git repository at all -- a bare
    checkout with no `.git` has no cross-worktree concept to share
    anything with in the first place."""
    common_dir = git_common_dir(root)
    if common_dir.is_err:
        _log.debug(
            "coverage_wait: git_common_dir unavailable (%s), falling back to "
            "worktree-local shared state dir",
            common_dir.danger_err,
        )
        return root / ".frob" / _SHARED_STATE_DIRNAME
    return common_dir.danger_ok / _SHARED_STATE_DIRNAME


def _shared_lock_path(root: Path, digest: str) -> Path:
    """The per-digest single-flight lock path: worktrees sharing a digest
    contend on this same path; worktrees with a different digest resolve
    to a different path and never contend with each other."""
    return shared_state_dir(root) / f"{digest}.lock"


def _shared_result_path(root: Path, digest: str) -> Path:
    """The per-digest cached-result path (T-1095's content-addressed
    result cache): the first worktree to settle a given digest writes its
    outcome here; every later caller with the SAME digest reads it
    instead of re-running."""
    return shared_state_dir(root) / f"{digest}.result.json"


@contextmanager
def _shared_coverage_lock(root: Path, digest: str) -> Iterator[None]:
    """Exclusive, blocking, cross-process, cross-WORKTREE lock serializing
    coverage runs that share `digest` (T-1095) -- the outer layer above
    `_coverage_lock`'s per-worktree lock. Same `flock`-on-a-dotfile shape,
    just keyed by content digest under `shared_state_dir` instead of by
    worktree path."""
    path = _shared_lock_path(root, digest)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        _log.debug("coverage_wait: shared lock acquired (%s)", path)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        _log.debug("coverage_wait: shared lock released (%s)", path)


# frob:doc docs/modules/testing.md#public-api
class SharedCoverageResult(BaseModel):
    """The cached, content-addressed outcome one worktree recorded for a
    given `tree_digest` (T-1095) -- read by every later caller sharing
    that same digest instead of independently re-running the suite."""

    model_config = {}

    ok: bool
    ran: bool
    duration_s: float
    file_hashes: dict[str, str]


def _read_shared_result(root: Path, digest: str) -> SharedCoverageResult | None:
    """The cached result for `digest`, or `None` if no worktree has
    settled it yet (missing/malformed cache file is treated as "nothing
    recorded", not an error -- the caller just proceeds to run it itself)."""
    path = _shared_result_path(root, digest)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return SharedCoverageResult.model_validate(payload)
    except Exception:
        return None


def _write_shared_result(root: Path, digest: str, result: SharedCoverageResult) -> None:
    """Record `result` as the settled outcome for `digest`, so every other
    worktree sharing this exact content hits `_read_shared_result` instead
    of running the suite itself. Best-effort: a write failure here just
    means the next caller pays for its own run, same as before T-1095."""
    path = _shared_result_path(root, digest)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(result.model_dump_json())
    except OSError as exc:
        _log.warning("coverage_wait: could not write shared result %s: %s", path, exc)


# Mirrors `frob.gates._coverage._STAMP_REL` (that module's own private
# constant, not imported here to avoid a second import path onto a
# private name -- both point at the identical `.frob/coverage-stamp`
# relative path by design, T-0545's one committed-stamp contract).
_STAMP_REL = Path(".frob") / "coverage-stamp"


def _adopt_shared_result(root: Path, cached: SharedCoverageResult) -> None:
    """Copy a cache hit's `file_hashes` into THIS worktree's own local
    `.frob/coverage-stamp` (T-1095), so `_is_stamp_fresh`'s local check
    (and every gate that reads the same stamp, e.g. TEST006) sees this
    worktree as fresh too -- without that copy, a cache hit would answer
    `run_coverage_wait` correctly but leave the local stamp stale, and the
    very next `frob check` in THIS worktree would re-flag it. `source_sha`
    is a synthetic marker (no local `coverage.xml` was ever produced here)
    rather than a real xml digest -- nothing reads `source_sha` for
    freshness, only `file_hashes` (`_is_stamp_fresh`/TEST006 both compare
    on `file_hashes` alone)."""
    stamp_path = root / _STAMP_REL
    stamp = {"source_sha": "shared:adopted", "file_hashes": cached.file_hashes}
    try:
        stamp_path.parent.mkdir(parents=True, exist_ok=True)
        stamp_path.write_text(json.dumps(stamp, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        _log.warning(
            "coverage_wait: could not adopt shared stamp into %s: %s", stamp_path, exc
        )


def _is_stamp_fresh(root: Path, snapshot: GraphSnapshot) -> bool:
    """Whether `.frob/coverage-stamp` already covers `snapshot`'s current
    source file hashes -- the SAME staleness contract `gate:TEST`'s TEST006
    enforces (`frob.gates._test006_stale`), reduced to a plain bool: no
    stamp, or any current source file's hash missing/changed since the
    stamp, is NOT fresh.
    """
    stamp = load_stamp(root)
    if stamp is None:
        return False
    stamped_hashes = stamp.get("file_hashes", {})
    for path, current_hash in snapshot.file_hashes.items():
        if not path.endswith((".py", ".rs", ".ts", ".tsx")):
            continue
        if stamped_hashes.get(path) != current_hash:
            return False
    return True


# frob:doc docs/modules/testing.md#public-api
# frob:tests tests/test_app.py::TestRunCoverageWait.test_no_stamp_runs_command_and_reports_ran  # noqa: E501
# frob:tests tests/test_app.py::TestRunCoverageWait.test_fresh_stamp_skips_the_run  # noqa: E501
# frob:tests tests/test_app.py::TestRunCoverageWait.test_failed_command_is_err  # noqa: E501
def run_coverage_wait(
    root: Path, *, command: tuple[str, ...] = ("make", "coverage-fast")
) -> Result[CoverageWaitOutcome, CoverageWaitError]:
    """Block until `root` has a coverage stamp fresh against its current
    source tree, running `command` (default `make coverage-fast`) under a
    single-flight lock if it does not already.

    This is the foreground, definitive-result counterpart to backgrounding
    `make coverage` (T-0322): a caller either gets `Ok(ran=False, ...)`
    immediately (another caller already made the stamp fresh, or this
    caller's own prior run did), or blocks in this call until `command`
    finishes and returns `Ok(ran=True, ...)` / `Err(RunFailed)` -- never a
    detached job an agent has to poll or "wait" on outside its own turn.

    T-1095: before falling through to the per-worktree lock/run below,
    this now checks the CROSS-worktree layer first -- `tree_digest`
    computed from the same snapshot, a shared cache keyed by that digest
    under `shared_state_dir`. A cache hit (another worktree with
    byte-for-byte identical tracked source already settled this digest)
    adopts that result (`_adopt_shared_result`) and returns immediately,
    with ZERO subprocess spawned in THIS worktree -- acceptance [0]. A
    cache miss acquires the shared per-digest lock (serializing every
    worktree sharing this digest onto one real run, re-checking the cache
    once more after acquiring it in case a racing worktree just finished),
    runs `command` exactly as before, and records the settled result for
    every other worktree sharing this digest to find. Two worktrees whose
    tracked source DIFFERS resolve to different digests -- different lock
    paths, different cache entries -- so they never contend or share a
    result with each other at all (acceptance [1]).

    T-1126: the OUTER lock is now `_worktree_lock` (daemon lease when
    reachable, else `_coverage_lock`); everything below is unchanged.
    """
    with _worktree_lock(root):
        cache = root / _CACHE_REL
        loaded = load_graph(cache)
        if loaded.is_err:
            loaded = build_graph(root, cache)
        if loaded.is_err:
            _log.error(
                "coverage_wait: could not build graph snapshot: %s",
                loaded.danger_err,
            )
            return Err(CoverageWaitError.SnapshotUnavailable)
        snapshot = loaded.danger_ok

        if _is_stamp_fresh(root, snapshot):
            _log.info("coverage_wait: stamp already fresh, nothing to run")
            return Ok(CoverageWaitOutcome(ran=False, duration_s=0.0))

        digest = tree_digest(snapshot)
        hit = _adopt_if_cached(root, digest, context="pre-lock")
        if hit is not None:
            return hit

        with _shared_coverage_lock(root, digest):
            # Re-check after acquiring the shared lock: a racing worktree
            # with the SAME digest may have finished its own run while
            # this caller was blocked waiting for the lock.
            hit = _adopt_if_cached(root, digest, context="post-lock")
            if hit is not None:
                return hit
            return _run_and_settle_shared(root, command, digest, snapshot)


def _adopt_if_cached(
    root: Path, digest: str, *, context: str
) -> Result[CoverageWaitOutcome, CoverageWaitError] | None:
    """If `digest` already has a settled `SharedCoverageResult`, adopt it
    (`_adopt_shared_result`) and return the equivalent `run_coverage_wait`
    result; `None` means "no cache hit, caller must proceed to run it" --
    `context` (`"pre-lock"`/`"post-lock"`) only shapes the log line, since
    `run_coverage_wait` checks this both before AND after acquiring the
    shared per-digest lock (T-1095)."""
    cached = _read_shared_result(root, digest)
    if cached is None:
        return None
    _log.info(
        "coverage_wait: shared result hit for digest=%s (ok=%s, %s), "
        "adopting -- no subprocess spawned",
        digest[:12],
        cached.ok,
        context,
    )
    _adopt_shared_result(root, cached)
    if cached.ok:
        return Ok(CoverageWaitOutcome(ran=False, duration_s=cached.duration_s))
    return Err(CoverageWaitError.RunFailed)


def _run_and_settle_shared(
    root: Path,
    command: tuple[str, ...],
    digest: str,
    snapshot: GraphSnapshot,
) -> Result[CoverageWaitOutcome, CoverageWaitError]:
    """The actual coverage-command spawn (T-1095's winner-of-the-lock
    path): run `command`, record the settled `SharedCoverageResult` for
    `digest` either way (success or failure -- acceptance [0] promises
    later callers the shared fresh-OR-FAILED result, not success only),
    and return the matching `run_coverage_wait` outcome. Called with the
    shared per-digest lock already held."""
    _log.info("coverage_wait: stamp stale/missing, running: %s", " ".join(command))
    start = time.monotonic()
    # T-0803: routed through `guarded_subprocess_run` (T-0778's guard) so
    # `FROB_DISABLE_EXEC=1` refuses this coverage-suite spawn too;
    # surfaced as the same `RunFailed` error this function already
    # returns for a nonzero exit, since a refused spawn is just another
    # "the coverage run did not happen" outcome from the caller's point
    # of view.
    guarded = guarded_subprocess_run(list(command), cwd=str(root), check=False)
    duration = time.monotonic() - start
    if guarded.is_err:
        _log.error(
            "coverage_wait: %s refused (exec disabled) after %.1fs",
            " ".join(command),
            duration,
        )
        ok = False
    else:
        result = guarded.danger_ok
        ok = result.returncode == 0
        if not ok:
            _log.error(
                "coverage_wait: %s exited %d after %.1fs",
                " ".join(command),
                result.returncode,
                duration,
            )
        else:
            _log.info(
                "coverage_wait: %s finished in %.1fs", " ".join(command), duration
            )
    _write_shared_result(
        root,
        digest,
        SharedCoverageResult(
            ok=ok,
            ran=True,
            duration_s=duration,
            file_hashes=dict(snapshot.file_hashes),
        ),
    )
    if not ok:
        return Err(CoverageWaitError.RunFailed)
    return Ok(CoverageWaitOutcome(ran=True, duration_s=duration))


__all__ = [
    "CoverageWaitError",
    "CoverageWaitOutcome",
    "SharedCoverageResult",
    "coverage_lock_path",
    "run_coverage_wait",
    "shared_state_dir",
    "tree_digest",
]

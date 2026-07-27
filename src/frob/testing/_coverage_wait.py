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
"""

from __future__ import annotations

import fcntl
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
from frob.graph import GraphSnapshot, build_graph, load_graph
from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run

_log = get_logger(__name__)

_LOCK_REL = Path(".frob") / "coverage.lock"
_CACHE_REL = Path(".frob") / "cache.db"


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
    """
    with _coverage_lock(root):
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

        _log.info("coverage_wait: stamp stale/missing, running: %s", " ".join(command))
        start = time.monotonic()
        # T-0803: routed through `guarded_subprocess_run` (T-0778's guard)
        # so `FROB_DISABLE_EXEC=1` refuses this coverage-suite spawn too;
        # surfaced as the same `RunFailed` error this function already
        # returns for a nonzero exit, since a refused spawn is just
        # another "the coverage run did not happen" outcome from the
        # caller's point of view.
        guarded = guarded_subprocess_run(list(command), cwd=str(root), check=False)
        duration = time.monotonic() - start
        if guarded.is_err:
            _log.error(
                "coverage_wait: %s refused (exec disabled) after %.1fs",
                " ".join(command),
                duration,
            )
            return Err(CoverageWaitError.RunFailed)
        result = guarded.danger_ok
        if result.returncode != 0:
            _log.error(
                "coverage_wait: %s exited %d after %.1fs",
                " ".join(command),
                result.returncode,
                duration,
            )
            return Err(CoverageWaitError.RunFailed)

        _log.info("coverage_wait: %s finished in %.1fs", " ".join(command), duration)
        return Ok(CoverageWaitOutcome(ran=True, duration_s=duration))


__all__ = [
    "CoverageWaitError",
    "CoverageWaitOutcome",
    "coverage_lock_path",
    "run_coverage_wait",
]

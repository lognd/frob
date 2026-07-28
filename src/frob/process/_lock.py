"""Cross-process shared/exclusive lock over a checkout's derived-state
directory (`.frob`), closing the TOCTOU window `frob.check`'s single
in-process integrity precheck (T-0603) left open (T-0859).

T-0603's `_derived_state_integrity_result` verifies `.frob`'s derived
artifacts (`cache.db`, `dup.db`, `baseline`, ...) exactly once, synchronously,
before a `run_check*` entry point dispatches its concurrent stages -- sound
against the in-process `ThreadPoolExecutor` race it was built for, but blind
to a SECOND `frob` process (a `frob serve` daemon, a parallel agent's own
`frob check` in the same checkout, a `frob mutate` run) rewriting or
corrupting the same files after the precheck passed and before a later stage
reads them. `derived_state_lock` closes that window for any two processes
that both go through it: a `frob check` run holds a SHARED lock for its
entire duration (precheck through the last stage's read), and any process
that mutates `.frob`'s derived artifacts is expected to hold the EXCLUSIVE
form while it writes -- the same shared/exclusive discipline `frob.tickets.
_store.ledger_lock` (T-0458) already uses for the ticket ledger, applied to
`.frob` itself.

Wiring the exclusive side into every current `.frob` writer (`frob mutate`,
`frob doctor`'s rebuild path, `frob.dup`/`frob.graph`'s cache rebuilders) is
tracked separately (see this ticket's Done report) -- this module only ships
the primitive and the `frob.check` shared-lock call site its own `scope`
covers; a writer that has not been wired onto the exclusive lock yet still
races the same way T-0603 disclosed, just with a narrower window (this
process's WHOLE run, not just its precheck) between fix and full coverage.
"""

from __future__ import annotations

import importlib
import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType

from frob.logging import get_logger

# frob:waive INV006 reason="T-0859: this module's several \\bonly\\b/\\bthe\\b \
# exclusivity-vocabulary hits are source-level design-rationale prose \
# (docstrings/comments describing already-implemented internal behavior, verifiable by \
# reading the code they annotate -- e.g. which platform fcntl requires, which \
# re-entrant mode a thread already holds) rather than a separate cross-module contract \
# needing its own tracked invariant, mirroring frob.check's INV006 T-0585 \
# calibration-batch waiver in src/frob/check/__init__.py"

# T-0859: `fcntl` is posix-only; `derived_state_lock` degrades to a
# documented no-op (see its docstring) on a platform without it, mirroring
# `frob.tickets._store.ledger_lock`'s T-0458 precedent.
fcntl: ModuleType | None
try:
    fcntl = importlib.import_module("fcntl")
except ImportError:  # pragma: no cover -- posix-only in this repo's CI
    fcntl = None

_log = get_logger(__name__)

#: The advisory lock file `derived_state_lock` holds, relative to a
#: checkout's `root` -- distinct from `frob.tickets._store._LOCK_REL`
#: (`.frob/tickets.lock`) so a ledger mutation and a derived-state check
#: never contend on the same file for an unrelated reason.
_LOCK_REL = Path(".frob") / "derived.lock"

# T-0859: thread-local re-entrancy bookkeeping, one entry per (path, mode)
# key, mirroring `frob.tickets._store._lock_local`'s reasoning: `flock` is
# scoped to an open file DESCRIPTION, not a process, so a naive
# "always os.open + flock" implementation would self-deadlock the moment a
# lock-holding caller in one thread invokes another lock-holding primitive
# nested inside it. A different thread or process still blocks on the real
# OS lock; only same-thread re-entry is short-circuited.
_lock_local = threading.local()

# frob:ticket T-0918
# T-0918: PROCESS-wide (not thread-local) reentrancy signal. `_lock_local`
# above only answers "does THIS thread already hold the lock" -- it says
# nothing about a SIBLING thread in the same process (e.g. `frob check`'s
# `ThreadPoolExecutor` gate workers) holding it concurrently. `flock(2)`
# itself gives no same-process reentrancy across distinct open file
# descriptions: a worker thread that naively requested EXCLUSIVE while the
# main thread already holds SHARED on the same lock file would genuinely
# block against its own process's other thread -- a real deadlock, not a
# logical contract violation (see T-0879's Done report and this module's
# own docstring for the flock(2) citation). `_process_held_counts` tracks,
# per lock-file path, how many distinct real OS-level acquisitions (across
# ALL threads, ANY mode) are currently outstanding in THIS process; it is
# incremented exactly once per first-time (non-reentrant) acquire and
# decremented exactly once when that acquisition's final release happens,
# guarded by `_process_registry_lock` since multiple threads race on it
# concurrently. `derived_state_write_lock` below is the only reader.
_process_registry_lock = threading.Lock()
_process_held_counts: dict[str, int] = {}


#: T-0982: env var name a `ProcessPoolExecutor` OWNER stamps, before pool
#: construction, with the canonical registry keys (`_canonical_registry_key`
#: form, `os.pathsep`-joined) it currently holds `derived_state_lock` for in
#: THIS process. Mirrors `frob.gates._WORKER_STDOUT_LOG_LEVEL_ENV`'s (T-0806)
#: established pattern: env vars set on the parent's `os.environ` right
#: before constructing a `ProcessPoolExecutor` are inherited by every worker
#: it spawns (forkserver helper or spawn), so a worker's own
#: `derived_state_write_lock` call can see this marker even though
#: `_process_held_counts` itself is process-local and therefore invisible
#: across the fork/spawn boundary (the cross-process sibling of T-0918's
#: same-process registry).
# frob:ticket T-0982
_INHERITED_LOCK_KEYS_ENV = "FROB_DERIVED_LOCK_HELD_KEYS"

#: Separator `_INHERITED_LOCK_KEYS_ENV` joins multiple held keys with
#: (T-0982). `os.pathsep` (`:` on POSIX) rather than a comma: registry keys
#: are resolved filesystem paths, which never contain `os.pathsep` on a
#: POSIX host, whereas a path COULD legitimately contain a comma.
_INHERITED_LOCK_KEYS_SEP = os.pathsep


# frob:doc docs/modules/process.md#derived-state-lock-t-0859
# frob:tests \
# tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance.test_real_pool_worke\
# r_under_parent_shared_holder_completes  # noqa: E501
# frob:ticket T-0982
def held_registry_keys() -> tuple[str, ...]:
    """Snapshot of every canonical registry key (`_canonical_registry_key`
    form) THIS process currently holds `derived_state_lock` for, in any
    mode (T-0982).

    A `ProcessPoolExecutor` OWNER (`frob.gates._open_process_pool`) calls
    this right before constructing its pool to build the
    `_INHERITED_LOCK_KEYS_ENV` marker a worker consults via
    `_worker_inherits_hold` -- see that constant's and that function's
    docstrings. Read-only; does not itself acquire or release anything."""
    with _process_registry_lock:
        return tuple(_process_held_counts)


# frob:tests \
# tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance.test_real_pool_worke\
# r_under_parent_shared_holder_completes  # noqa: E501
# frob:tests \
# tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance.test_independent_pro\
# cess_without_marker_still_blocks  # noqa: E501
# frob:ticket T-0982
def _worker_inherits_hold(root: Path) -> bool:
    """Whether THIS process was told (via `_INHERITED_LOCK_KEYS_ENV`) that
    the process which SPAWNED it already holds `derived_state_lock` for
    `root` (T-0982) -- the cross-process sibling of `_process_already_holds`.

    A `ProcessPoolExecutor` worker forked/spawned from a parent that holds
    `derived_state_lock(root, exclusive=False)` (e.g. `frob check`'s own
    SHARED hold for its whole run) starts with an EMPTY
    `_process_held_counts` of its own -- T-0918's registry is process-local,
    rebuilt fresh by each worker interpreter -- even though the PARENT's
    hold already fully serializes this whole process tree against every
    OTHER process for `root`. A naive worker-side `flock(LOCK_EX)` in that
    situation genuinely blocks against the parent's `LOCK_SH` on a
    *different* open file description, forever (T-0982, lslocks-confirmed:
    READ held by the parent pid, WRITE* blocked on the worker pid, same
    `.frob/derived.lock`). The pool OWNER closes this by stamping
    `_INHERITED_LOCK_KEYS_ENV` with its own `held_registry_keys()` right
    before constructing the pool (`frob.gates._open_process_pool`); this
    reads that marker back and treats a match for `root`'s canonical key
    exactly like `_process_already_holds` treats a same-process hold: the
    worker trusts the parent's guarantee and takes no real OS lock of its
    own here, rather than inventing a second bypass rule.

    Says nothing about an INDEPENDENT process's pool worker -- one whose
    parent does NOT hold `derived_state_lock` for `root` never sees its key
    in this marker (the env var is either absent or names a different
    root), so it falls through to a real, fully cross-process-exclusive
    `flock(LOCK_EX)` exactly as before this ticket.
    """
    # frob:waive SEC110 reason="lock-registry-key marker (resolved filesystem paths \
    # this same process's pool owner stamped), carries no confidential data"
    raw = os.environ.get(_INHERITED_LOCK_KEYS_ENV, "")
    if not raw:
        return False
    held_keys = raw.split(_INHERITED_LOCK_KEYS_SEP)
    return _canonical_registry_key(root) in held_keys


def _process_already_holds(root: Path) -> bool:
    """Whether ANY thread in THIS process currently holds `derived_state_lock`
    for `root`, in any mode (shared or exclusive).

    This is the process-wide reentrancy signal `derived_state_write_lock`
    consults before taking a real OS-level exclusive lock: a `True` here
    means some other thread in this same process (or this thread itself)
    already has skin in the game, so a naive same-process EXCLUSIVE
    request here would deadlock against it (flock has no same-process
    reentrancy across distinct fds). Says nothing about OTHER processes --
    those are still fully serialized through the real `flock(2)` call.
    """
    key = _canonical_registry_key(root)
    with _process_registry_lock:
        return _process_held_counts.get(key, 0) > 0


def _derived_lock_path(root: Path) -> Path:
    """The advisory lock file path (`.frob/derived.lock`) `derived_state_lock`
    holds under checkout `root`."""
    return root / _LOCK_REL


# frob:ticket T-0933
def _canonical_registry_key(root: Path) -> str:
    """CANONICAL string key for `root` in `_process_held_counts` (T-0933).

    `_process_already_holds`/`derived_state_write_lock` need to answer "does
    THIS process already hold `derived_state_lock` for this checkout" using
    a key that is stable across however many different (but equivalent)
    `Path` spellings of the same root different call sites happen to pass
    in -- e.g. `frob.check`'s outer `derived_state_lock(root, ...)` call
    historically received `root` UNRESOLVED (whatever the CLI/caller passed,
    often relative or symlink-bearing), while `frob.graph.build_graph`
    calls `root.resolve()` on its own copy before reaching
    `derived_state_write_lock`. Both name the SAME on-disk checkout, but
    `str(_derived_lock_path(root))` on the unresolved and resolved forms
    produced two DIFFERENT dict keys -- so the resolved-root caller's
    `_process_already_holds` read `False` even though the unresolved-root
    caller already held the lock in this same process, and it went on to
    attempt a real second `flock(LOCK_EX)` against its own process's
    outstanding `LOCK_SH`, deadlocking (T-0933, a T-0918 regression).
    Resolving here -- and ONLY here, for the registry key, not for the
    actual `os.open` path passed to `flock` -- fixes that without changing
    which physical file gets locked (flock is inode-scoped, so the two
    spellings already serialized correctly at the OS level; only this
    in-process dict lookup was spelling-sensitive).
    """
    return str(_derived_lock_path(root).resolve())


# frob:doc docs/modules/process.md#derived-state-lock-t-0859
# frob:tests \
# tests/unit/test_process_lock.py::TestDerivedStateLock.test_two_threads_serialize_excl\
# usive  # noqa: E501
# frob:tests \
# tests/unit/test_process_lock.py::TestDerivedStateLock.test_shared_locks_do_not_block_\
# each_other  # noqa: E501
# frob:tests \
# tests/unit/test_process_lock.py::TestDerivedStateLock.test_reentrant_same_mode_in_sam\
# e_thread  # noqa: E501
# frob:tests \
# tests/unit/test_process_lock.py::TestDerivedStateLock.test_reentrant_opposite_mode_ra\
# ises  # noqa: E501
# frob:ticket T-0859
@contextmanager
def derived_state_lock(root: Path, *, exclusive: bool) -> Iterator[None]:
    """Cross-process `flock` over checkout `root`'s derived-state directory.

    `exclusive=False` (the reader/checker form) takes a SHARED lock: any
    number of readers -- including concurrent `frob check` runs -- can hold
    it at once, but it blocks against, and is blocked by, an exclusive
    holder. `exclusive=True` (the writer form, for any process about to
    rebuild or rewrite a derived artifact under `.frob`) takes an
    EXCLUSIVE lock: it waits for every reader and every other writer to
    release first, and no reader can acquire while it is held. This is the
    same shared/exclusive discipline as a `flock(2)` reader-writer lock,
    applied to `.frob` the way `frob.tickets._store.ledger_lock` (T-0458)
    already applies a single-writer `LOCK_EX` to the ticket ledger.

    Uses `fcntl.flock` on `.frob/derived.lock` (POSIX). On a platform
    without `fcntl` this degrades to a documented no-op (logged at
    WARNING, not silently pretended to be locked) -- mirroring
    `ledger_lock`'s same fallback. Re-entrant per thread and per exact
    `exclusive` value (see `_lock_local`): a second `with
    derived_state_lock(root, exclusive=X)` in the SAME thread, requesting
    the SAME mode, is a no-op re-entry; requesting the OPPOSITE mode while
    already holding one from the same thread is refused up front (a
    same-thread exclusive-under-shared or shared-under-exclusive upgrade/
    downgrade is not supported and would either deadlock against the
    thread's own held lock or silently violate the mode it already holds).
    """
    if fcntl is None:  # pragma: no cover -- posix-only in this repo's CI
        _log.warning(
            "process: derived_state_lock: fcntl unavailable on this "
            "platform, lock is a NO-OP (mirrors ledger_lock's T-0458 "
            "fallback) -- concurrent frob processes are NOT serialized here"
        )
        yield
        return

    path = _derived_lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    key = str(path)
    # frob:ticket T-0933
    # T-0933: `_process_held_counts` is keyed CANONICALLY (see
    # `_canonical_registry_key`), independent of `key` above -- `key` is
    # deliberately spelling-sensitive (per-thread reentrancy bookkeeping
    # only needs to match a caller against ITSELF), but the cross-thread
    # process-wide registry must agree with `_process_already_holds` no
    # matter which `Path` spelling of the same root a given call site used.
    registry_key = _canonical_registry_key(root)
    maybe_held: dict[str, tuple[int, bool, int]] | None = getattr(
        _lock_local, "held", None
    )
    held: dict[str, tuple[int, bool, int]] = (
        maybe_held if maybe_held is not None else {}
    )
    if maybe_held is None:
        _lock_local.held = held

    entry = held.get(key)
    if entry is not None:
        fd, held_exclusive, depth = entry
        if held_exclusive != exclusive:
            raise RuntimeError(
                f"derived_state_lock: {path} already held in "
                f"{'exclusive' if held_exclusive else 'shared'} mode by "
                f"this thread; cannot re-enter as "
                f"{'exclusive' if exclusive else 'shared'} (upgrade/"
                "downgrade is not supported)"
            )
        held[key] = (fd, held_exclusive, depth + 1)
        try:
            yield
        finally:
            fd, held_exclusive, depth = held[key]
            if depth <= 1:
                del held[key]
            else:
                held[key] = (fd, held_exclusive, depth - 1)
        return

    fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
    held[key] = (fd, exclusive, 1)
    with _process_registry_lock:
        _process_held_counts[registry_key] = (
            _process_held_counts.get(registry_key, 0) + 1
        )
    _log.debug(
        "process: derived_state_lock acquired (%s, exclusive=%s)",
        path,
        exclusive,
    )
    try:
        yield
    finally:
        del held[key]
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        with _process_registry_lock:
            remaining = _process_held_counts.get(registry_key, 0) - 1
            if remaining <= 0:
                _process_held_counts.pop(registry_key, None)
            else:
                _process_held_counts[registry_key] = remaining
        _log.debug(
            "process: derived_state_lock released (%s, exclusive=%s)",
            path,
            exclusive,
        )


# frob:doc docs/modules/process.md#derived-state-lock-t-0859
# frob:tests \
# tests/unit/test_process_lock.py::TestDerivedStateWriteLock.test_standalone_rebuild_ta\
# kes_exclusive  # noqa: E501
# frob:tests \
# tests/unit/test_process_lock.py::TestDerivedStateWriteLock.test_nested_inside_shared_\
# holder_does_not_deadlock  # noqa: E501
# frob:tests \
# tests/unit/test_process_lock.py::TestDerivedStateWriteLock.test_concurrent_separate_p\
# rocess_writer_still_blocked  # noqa: E501
# frob:tests \
# tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance.test_real_pool_worke\
# r_under_parent_shared_holder_completes  # noqa: E501
# frob:tests \
# tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance.test_independent_pro\
# cess_without_marker_still_blocks  # noqa: E501
# frob:ticket T-0918
# frob:ticket T-0982
@contextmanager
def derived_state_write_lock(root: Path) -> Iterator[None]:
    """Writer lock for a cache rebuilder that may run standalone OR nested
    inside an existing `derived_state_lock` holder in this SAME process
    (T-0918).

    `frob.dup.find_clones` and `frob.graph.build_graph` both rebuild
    derived state under `.frob`, but unlike `frob.mutate.run_mutations`/
    `frob.doctor.run_diagnosis` (which unconditionally wrap themselves in
    `derived_state_lock(root, exclusive=True)`, T-0879) they are NOT always
    invoked standalone: `frob check` also calls them from a
    `ThreadPoolExecutor` gate-worker thread while ITS OWN main thread holds
    `derived_state_lock(root, exclusive=False)` (SHARED) for the run's
    whole duration. Wrapping them in a naive unconditional
    `derived_state_lock(root, exclusive=True)` would deadlock every such
    run: the worker thread's EXCLUSIVE request blocks on `flock(2)` against
    the main thread's SHARED hold on a DIFFERENT open file description, and
    that SHARED hold cannot release until the worker returns (see this
    module's docstring and T-0879's Done report for the citation).

    Chosen semantics: before taking a real lock, this consults
    `_process_already_holds(root)` -- the T-0918 process-wide (not just
    thread-local) reentrancy signal:

    - If NO thread in this process currently holds `derived_state_lock`
      for `root`, this behaves exactly like `derived_state_lock(root,
      exclusive=True)`: a normal cross-process EXCLUSIVE acquire, blocking
      out every other reader/writer process. This is the standalone-
      rebuild path (e.g. a direct `frob.dup.find_clones` call outside
      `frob check`).
    - If SOME thread in this process already holds the lock (in EITHER
      mode -- this thread itself via reentry, or a different thread, e.g.
      `frob check`'s main thread holding SHARED), this is a SAME-PROCESS
      NO-OP: no new OS-level lock is taken at all. The caller trusts that
      the outer holder already serializes this whole process against every
      OTHER process for the derived-state directory; this rebuild is
      running inside that window, not opening a new one.

    This is a deliberate SOUNDNESS TRADE-OFF, not a free lunch: two
    `frob check` runs in two DIFFERENT processes each hold their own
    SHARED lock concurrently (by design -- readers don't exclude
    readers), and if both reach a dup/graph rebuild at the same moment,
    each one's `derived_state_write_lock` sees its OWN process already
    holding the lock and no-ops, so the two rebuilds are NOT mutually
    exclusive against each other. That gap is accepted here because it is
    no worse than the pre-T-0859 baseline (no lock at all) for this exact
    nested case, and closing it fully needs `frob check` itself to
    upgrade its run-wide hold to EXCLUSIVE around a rebuild stage --
    tracked separately, out of this ticket's scope
    (`src/frob/process/_lock.py`, `src/frob/dup/_pipeline.py`,
    `src/frob/graph/__init__.py` only). What this DOES fully close: a
    standalone rebuild (no other in-process holder) is still fully
    cross-process exclusive, and a rebuild nested inside a check-style
    SHARED holder no longer deadlocks.

    The same gap applies, by construction, to two SIBLING calls racing
    within one process with no legitimate outer holder at all: the
    process-wide signal cannot distinguish "a real outer holder that
    already serializes this process against others" from "some other
    thread mid-way through its OWN standalone `derived_state_write_lock`
    call" -- whichever caller wins the race to acquire first makes the
    second one see `_process_already_holds(root) is True` and no-op
    without waiting. There is no current production call site that
    invokes `find_clones`/`build_graph` this way (both call sites are
    either fully standalone or run under `frob check`'s single main-
    thread SHARED hold), so this is a documented latent gap, not an
    observed regression; a future caller that fans out concurrent
    standalone rebuilds in one process would need a different primitive.
    """
    if _process_already_holds(root):
        _log.debug(
            "process: derived_state_write_lock: %s already held by this "
            "process (some thread), same-process no-op (T-0918)",
            root,
        )
        yield
        return
    if _worker_inherits_hold(root):
        _log.debug(
            "process: derived_state_write_lock: %s held by the process "
            "that spawned this one (%s), inherited no-op (T-0982)",
            root,
            _INHERITED_LOCK_KEYS_ENV,
        )
        yield
        return
    with derived_state_lock(root, exclusive=True):
        yield


__all__ = [
    "derived_state_lock",
    "derived_state_write_lock",
    "held_registry_keys",
]

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


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
    docstrings. Read-only; does not itself acquire or release anything.

    Imports `_process_held_counts`/`_process_registry_lock` LOCALLY
    (T-3628/T-3653): `_lock.py`'s own re-export shim for the symbols this
    module owns creates a genuine module-init-time circular import against
    any module-level `from frob.process._lock import ...` here -- deferred
    to call time, by which point both modules have finished initializing."""
    from frob.process._lock import _process_held_counts, _process_registry_lock

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

    Imports `_INHERITED_LOCK_KEYS_ENV`/`_INHERITED_LOCK_KEYS_SEP` LOCALLY
    -- see `held_registry_keys`'s docstring for why."""
    from frob.process._lock import _INHERITED_LOCK_KEYS_ENV, _INHERITED_LOCK_KEYS_SEP

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

    Imports `_process_held_counts`/`_process_registry_lock` LOCALLY -- see
    `held_registry_keys`'s docstring for why.
    """
    from frob.process._lock import _process_held_counts, _process_registry_lock

    key = _canonical_registry_key(root)
    with _process_registry_lock:
        return _process_held_counts.get(key, 0) > 0


def _derived_lock_path(root: Path) -> Path:
    """The advisory lock file path (`.frob/derived.lock`) `derived_state_lock`
    holds under checkout `root`.

    Imports `_LOCK_REL` LOCALLY -- see `held_registry_keys`'s docstring for
    why."""
    from frob.process._lock import _LOCK_REL

    return root / _LOCK_REL


# frob:doc docs/modules/process.md#public-api
# frob:tests tests/unit/test_process_lock.py::TestDerivedStateLockPlatformBackends.test_no_lock_primitive_refuses_loudly  # noqa: E501
class DerivedStateLockUnavailable(RuntimeError):
    """T-2934: raised by `derived_state_lock` when neither `fcntl`
    (POSIX) nor `msvcrt` (Windows) is importable -- there is no known
    advisory-lock primitive on this platform at all. A loud refusal,
    never a silent no-op: `.frob`'s derived artifacts (`cache.db`,
    `dup.db`, `baseline`, ...) are shared, concurrently-mutated state
    across every `frob` process in a checkout; proceeding unlocked would
    reopen exactly the TOCTOU race this module's own docstring says it
    exists to close, for as long as this process runs, not just under
    brief contention."""


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

    Uses `fcntl.flock` on `.frob/derived.lock` (POSIX) or, on Windows,
    `msvcrt.locking` (T-2934) -- always EXCLUSIVE on the Windows backend
    regardless of the requested `exclusive` mode, since `msvcrt` has no
    shared/read-lock primitive at all (a documented, deliberate
    conservative-concurrency tradeoff: readers block each other too on
    Windows). If NEITHER primitive exists, raises
    `DerivedStateLockUnavailable` (T-2934) rather than the pre-T-2934
    silent unconditional no-op. Re-entrant per thread and per exact
    `exclusive` value (see `_lock_local`): a second `with
    derived_state_lock(root, exclusive=X)` in the SAME thread, requesting
    the SAME mode, is a no-op re-entry; requesting the OPPOSITE mode while
    already holding one from the same thread is refused up front (a
    same-thread exclusive-under-shared or shared-under-exclusive upgrade/
    downgrade is not supported and would either deadlock against the
    thread's own held lock or silently violate the mode it already holds).
    """
    from frob.process._lock import (  # T-3628: local import breaks the
        _lock_local,
        _log,
        _process_held_counts,
        _process_registry_lock,
        # module-init-time circular dependency between this cluster-3
        # module and _lock.py's own re-export shim for these symbols --
        # see held_registry_keys's docstring for the same pattern.
        fcntl,
        msvcrt,
        portable_flock_acquire,
        portable_flock_release,
    )

    if fcntl is None and msvcrt is None:
        raise DerivedStateLockUnavailable(
            f"process: derived_state_lock: neither fcntl (POSIX) nor "
            f"msvcrt (Windows) is available on this platform -- refusing "
            f"to proceed unlocked against {root} (T-2934)"
        )

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

    # frob:ticket T-3506
    # byte-seeding for msvcrt's byte-range lock (when that backend is the
    # one in use) now happens inside portable_flock_acquire itself, not
    # here.
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR | getattr(os, "O_BINARY", 0), 0o644)
    portable_flock_acquire(fd, exclusive=exclusive)
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
        # frob:ticket T-3506
        portable_flock_release(fd)
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
    # T-3628: see derived_state_lock's own local-import comment
    from frob.process._lock import _INHERITED_LOCK_KEYS_ENV, _log

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

"""T-0602: per-obligation dependency-tracked partial re-evaluation.

`run_gates` (this package's `__init__.py`) evaluates every selected gate in
full on every call -- `docs/modules/serve.md`'s "Staleness/correctness
contract" section disclosed this gap explicitly when T-0177 shipped the
warm graph/baseline/test-collection cache: "there is no per-obligation
dependency-tracked partial re-evaluation inside `run_gates` today." This
module is that missing piece, for the subset of gates it can serve
SOUNDLY -- everything else stays fully re-evaluated every call, loudly
disclosed rather than silently guessed at.

Design (recorded here, not just in the ticket's Done report, since this is
the one place a future reader will actually look):

- **Dependency key, not per-obligation ID.** A gate is cacheable only if
  its result is a pure function of (a) `GraphSnapshot`-derived state
  reachable through `symbols`/`edges`/`file_hashes`/`malformed`/
  `parse_failures`, and (b) a short tuple of already-hashable scalars (a
  ticket id, `date.today()`, ...). `_CACHEABLE_GATES` in `gates/__init__.py`
  is the closed, hand-audited allowlist: every OTHER gate either reads
  `st.root`/`st.repo_root` directly (an unbounded filesystem walk this
  module cannot observe) or combines several gates behind one dispatch
  name in a way that would make partial caching silently wrong for the
  root-scanning half. A gate not on the allowlist is not opted out by
  omission -- `docs/modules/serve.md`'s "What it does NOT cover" section
  names the excluded classes and why, so the gap is disclosed, not implied.

- **Touched-file tracking, not static analysis.** `TrackedSnapshot` wraps
  the real `GraphSnapshot` and records, at RUN time, every file path a
  cacheable gate actually dereferenced through `.symbols`/`.edges`/
  `.file_hashes`/`.malformed`/`.parse_failures`. This is exact by
  construction (it observes real reads, not a guessed dependency set) and
  needs no per-gate hand-written file-selector to keep in sync as gate
  logic evolves.

- **The added/removed-file soundness hole, closed by a membership guard.**
  A touched-file list recorded on a PAST run cannot, by itself, notice a
  file that did not exist at record time but that the SAME gate would now
  also touch (a new `.md` file a doc-drift gate would now scan, say).
  `_membership_key` folds the full sorted `file_hashes.keys()` set into
  every cache entry; ANY file add/remove anywhere in the tracked tree
  invalidates every cacheable gate's cached entry, not just the gate that
  would have touched the new file. This is conservative (a repo-wide
  add/remove pays for a full re-run of every cacheable gate, not just the
  affected one) but closes the hole completely rather than leaving a
  documented latent gap -- see this module's own property test
  (`tests/test_gate_cache.py::TestColdDiffOracle`) for the add/remove case
  the design note above is protecting against.

- **One row per gate, not per dependency-key.** Unlike a content-addressed
  build cache, this only ever needs to answer "is THIS gate's cached
  result still valid right now" -- it never needs to look up an arbitrary
  past state. Storing exactly one row per gate (`INSERT OR REPLACE`) keeps
  `.frob/gate-cache.db` bounded regardless of how many times a tree
  churns, at the cost of losing reuse across a revert-then-reapply of the
  same tree state (acceptable: this is a same-session dispatch cache, not
  a build artifact store).

- **Storage extends `.frob`, no parallel cache.** `.frob/gate-cache.db` is
  a new table living in the SAME derived-state directory `frob.graph.
  cache`'s `cache.db` and `frob.gates._baseline`'s `.frob/baseline` already
  own -- guarded by the SAME `frob.process._lock.derived_state_lock`/
  `derived_state_write_lock` primitive every other `.frob` writer uses
  (T-0918's process-wide reentrancy registry), not a second lock or a
  second cache mechanism. `derived_state_write_lock` is specifically the
  T-0918 primitive built for "a worker thread wants EXCLUSIVE while the
  main `frob check` thread holds SHARED for the run's whole duration" --
  exactly this module's call shape (gate jobs run inside `run_gates`'s
  `ThreadPoolExecutor`, nested under `frob.check`'s outer SHARED hold) --
  so writing a cache entry from a gate-worker thread cannot deadlock
  against that outer hold; see `derived_state_write_lock`'s own docstring
  for the full reasoning.

- **Correctness beats speedup.** `evaluate_cacheable_gate` always returns
  the gate's true result: a cache HIT skips real work, a cache MISS (or no
  entry at all) runs the gate for real and updates the cache -- there is
  no code path that can return a stale answer silently. The cold-diff
  oracle property test
  (`tests/test_gate_cache.py::TestColdDiffOracle::test_cache_agrees_with_cold_across_random_edits`)
  asserts exactly this: for a sequence of random snapshot mutations
  (content edits, file adds, file removes, scalar-extra changes), a gate
  run through `evaluate_cacheable_gate` against whatever cache state
  happens to exist always agrees with a fresh, cache-bypassing cold call.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from frob.gates._models import Violation
from frob.graph._models import GraphSnapshot
from frob.logging import get_logger
from frob.process._lock import derived_state_write_lock

_log = get_logger(__name__)

# frob:ticket T-0602
#: the gate-result cache, a new table in a new file under the SAME
#: `.frob/` derived-state directory `cache.db`/`baseline` already live in --
#: not merged into `cache.db` itself since that schema (`frob.graph.cache`)
#: is owned by `frob.graph`, outside this ticket's `src/frob/gates/**` scope.
_CACHE_REL = Path(".frob") / "gate-cache.db"

# frob:ticket T-0602
_SCHEMA = """
CREATE TABLE IF NOT EXISTS gate_results (
    gate TEXT PRIMARY KEY,
    membership_key TEXT NOT NULL,
    touched_key TEXT NOT NULL,
    extra_key TEXT NOT NULL,
    touched_files TEXT NOT NULL,
    violations_json TEXT NOT NULL,
    recorded_at REAL NOT NULL
);
"""


# frob:ticket T-0602
def _db_path(root: Path) -> Path:
    """The `.frob/gate-cache.db` path for a checkout rooted at `root`."""
    return root / _CACHE_REL


# frob:ticket T-0602
def _connect(root: Path) -> sqlite3.Connection:
    """Open (creating/migrating as needed) the gate-result cache db, with
    the same busy-timeout posture `frob.graph.cache._open` uses for
    concurrent-writer tolerance."""
    path = _db_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.executescript(_SCHEMA)
    return conn


# --- Touched-file tracking -------------------------------------------------


# frob:ticket T-0602
class _TrackedMapping(Mapping):
    """Read-only `Mapping` proxy that records every key it is asked to
    resolve -- iteration, `__getitem__`, and `.values()`/`.items()` (both
    inherited from `Mapping`'s default implementations, which route through
    `__iter__`/`__getitem__`) all funnel through here, so no access pattern
    a gate might use can silently escape tracking."""

    # frob:ticket T-0602
    def __init__(
        self, data: Mapping, touched: set[str], key_of: Callable[[object], str]
    ) -> None:
        """Wrap `data`, recording `key_of(key)` into `touched` on every access."""
        self._data = data
        self._touched = touched
        self._key_of = key_of

    # frob:ticket T-0602
    def __getitem__(self, key: object) -> object:
        """Record `key`'s file, then return the real value."""
        self._touched.add(self._key_of(key))
        return self._data[key]

    # frob:ticket T-0602
    def __iter__(self) -> Iterator[object]:
        """Record every key's file as it is yielded (a full scan records
        every currently-live key -- see this module's docstring on why that
        is what makes the membership guard sound)."""
        for key in self._data:
            self._touched.add(self._key_of(key))
            yield key

    # frob:ticket T-0602
    def __len__(self) -> int:
        """Delegate to the wrapped mapping; length checks alone are cheap
        and do not themselves need tracking (`__iter__`/`__getitem__` already
        cover every path that reads a VALUE)."""
        return len(self._data)


# frob:ticket T-0602
class _TrackedSequence:
    """Read-only iterable proxy over a tuple of graph records (edges,
    malformed directives, parse failures), recording each item's file(s) as
    it is yielded."""

    # frob:ticket T-0602
    def __init__(
        self,
        data: tuple[Any, ...],
        touched: set[str],
        files_of: Callable[[Any], Iterable[str]],
    ) -> None:
        """Wrap `data`, recording every file `files_of(item)` names as `data`
        is iterated or indexed."""
        self._data = data
        self._touched = touched
        self._files_of = files_of

    # frob:ticket T-0602
    def _record(self, item: Any) -> Any:
        for f in self._files_of(item):
            self._touched.add(f)
        return item

    # frob:ticket T-0602
    def __iter__(self) -> Iterator[Any]:
        """Record and yield every item in order."""
        for item in self._data:
            yield self._record(item)

    # frob:ticket T-0602
    def __len__(self) -> int:
        """Delegate to the wrapped tuple."""
        return len(self._data)

    # frob:ticket T-0602
    def __getitem__(self, idx):  # noqa: ANN001, ANN204
        """Record and return the item(s) at `idx` (single index or slice)."""
        item = self._data[idx]
        if isinstance(idx, slice):
            return [self._record(i) for i in item]
        return self._record(item)


# frob:ticket T-0602
def _symref_file(ref: object) -> str:
    """The `path` half of a `path::qualname` symref key."""
    return str(ref).split("::", 1)[0]


# frob:ticket T-0602
def _edge_files(edge: object) -> tuple[str, ...]:
    """Both endpoints' files for an `Edge` -- an edge can name a doc anchor
    (`path#anchor`) as either side, so both `src`/`target` are stripped of a
    trailing `::qualname` or `#anchor` the same way `frob.graph.affects`
    already does."""
    files = []
    for ref in (getattr(edge, "src", None), getattr(edge, "target", None)):
        if ref is None:
            continue
        files.append(str(ref).split("::", 1)[0].split("#", 1)[0])
    return tuple(files)


# frob:doc \
# docs/modules/serve.md#per-gate-dependency-tracked-partial-re-evaluation-t-0602
# frob:ticket T-0602
# frob:tests tests/test_gate_cache.py::TestTrackedSnapshot.test_symbol_iteration_records_file  # noqa: E501
# frob:tests tests/test_gate_cache.py::TestTrackedSnapshot.test_getitem_records_only_accessed_key  # noqa: E501
class TrackedSnapshot:
    """Read-only proxy over a `GraphSnapshot` recording every file path a
    cacheable gate actually dereferences through `.symbols`/`.edges`/
    `.file_hashes`/`.malformed`/`.parse_failures` this call -- the exact,
    observed (not guessed) dependency set `evaluate_cacheable_gate` keys
    its cache entry on. `.root`/`.stats` pass straight through (no gate on
    the cacheable allowlist reads them for anything file-dependent)."""

    # frob:ticket T-0602
    def __init__(self, snapshot: GraphSnapshot, touched: set[str]) -> None:
        """Wrap `snapshot`, accumulating every touched file path into
        `touched` (owned by the caller, so it can inspect the final set
        after the gate function returns)."""
        self._snapshot = snapshot
        self._touched = touched

    # frob:doc \
    # docs/modules/serve.md#per-gate-dependency-tracked-partial-re-evaluation-t-0602
    # frob:ticket T-0602
    @property
    def root(self) -> str:
        """Pass-through: `GraphSnapshot.root` is a fixed string, not itself
        file-dependent."""
        return self._snapshot.root

    # frob:doc \
    # docs/modules/serve.md#per-gate-dependency-tracked-partial-re-evaluation-t-0602
    # frob:ticket T-0602
    @property
    def stats(self):  # noqa: ANN201
        """Pass-through: build stats are diagnostic, not gate input."""
        return self._snapshot.stats

    # frob:doc \
    # docs/modules/serve.md#per-gate-dependency-tracked-partial-re-evaluation-t-0602
    # frob:ticket T-0602
    @property
    def symbols(self) -> _TrackedMapping:
        """Every symref resolved records its own file."""
        return _TrackedMapping(self._snapshot.symbols, self._touched, _symref_file)

    # frob:doc \
    # docs/modules/serve.md#per-gate-dependency-tracked-partial-re-evaluation-t-0602
    # frob:ticket T-0602
    @property
    def edges(self) -> _TrackedSequence:
        """Every edge yielded records both its src and target file."""
        return _TrackedSequence(self._snapshot.edges, self._touched, _edge_files)

    # frob:doc \
    # docs/modules/serve.md#per-gate-dependency-tracked-partial-re-evaluation-t-0602
    # frob:ticket T-0602
    @property
    def file_hashes(self) -> _TrackedMapping:
        """Every path looked up (or iterated) records itself directly."""
        return _TrackedMapping(self._snapshot.file_hashes, self._touched, str)

    # frob:doc \
    # docs/modules/serve.md#per-gate-dependency-tracked-partial-re-evaluation-t-0602
    # frob:ticket T-0602
    @property
    def malformed(self) -> _TrackedSequence:
        """Every malformed-directive record yielded records its `.file`."""
        return _TrackedSequence(
            self._snapshot.malformed, self._touched, lambda m: (m.file,)
        )

    # frob:doc \
    # docs/modules/serve.md#per-gate-dependency-tracked-partial-re-evaluation-t-0602
    # frob:ticket T-0602
    @property
    def parse_failures(self) -> _TrackedSequence:
        """Every parse-failure record yielded records its `.file`."""
        return _TrackedSequence(
            self._snapshot.parse_failures, self._touched, lambda p: (p.file,)
        )


# --- Dependency keys ---------------------------------------------------


# frob:ticket T-0602
def _hash_parts(parts: Iterable[str]) -> str:
    """sha256 over `parts`, each terminated by a NUL so no ambiguous
    concatenation (`["ab", "c"]` vs `["a", "bc"]`) can collide."""
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8", "surrogateescape"))
        h.update(b"\0")
    return h.hexdigest()


# frob:ticket T-0602
def _membership_key(file_hashes: Mapping[str, str]) -> str:
    """The full tracked-file PATH SET's fingerprint (T-0602's
    "membership guard"): changes on ANY file add/remove anywhere in the
    tree, regardless of whether a given cacheable gate would have touched
    the new/removed file -- closing the "gate never saw this file because
    it did not exist yet" soundness hole a pure touched-hash comparison
    would otherwise leave open. See this module's docstring."""
    return _hash_parts(sorted(file_hashes))


# frob:ticket T-0602
def _touched_key(file_hashes: Mapping[str, str], touched: Iterable[str]) -> str:
    """The content-hash fingerprint of exactly the files `touched` names:
    unaffected by an edit to any file NOT in `touched`, which is the actual
    partial-re-evaluation win this ticket is for -- an edit to a file a
    given gate never reads never invalidates that gate's cache entry."""
    return _hash_parts(
        f"{path}={file_hashes.get(path, '<absent>')}" for path in sorted(set(touched))
    )


# frob:doc \
# docs/modules/serve.md#per-gate-dependency-tracked-partial-re-evaluation-t-0602
# frob:ticket T-0602
def extra_key(values: Iterable[str]) -> str:
    """Fold a gate's non-file scalar inputs (a ticket id, `date.today()`,
    ...) into the same key space as the file-based halves above -- a
    cacheable gate that also depends on one of these must never reuse a
    cached result recorded under a different scalar value."""
    return _hash_parts(values)


# --- Cache storage -------------------------------------------------------


@dataclass(frozen=True)
# frob:ticket T-0602
class _CacheEntry:
    """One stored `gate_results` row, deserialized."""

    membership_key: str
    touched_key: str
    extra_key: str
    touched_files: tuple[str, ...]
    violations: tuple[Violation, ...]


# frob:ticket T-0602
def _load_entry(root: Path, gate: str) -> _CacheEntry | None:
    """Read `gate`'s single cached row, or `None` on a cold cache/miss.

    A read-only query: no `derived_state_lock` needed beyond sqlite's own
    busy-timeout -- a concurrent writer's `INSERT OR REPLACE` is atomic per
    row, so a reader either sees the old row or the new one, never a torn
    one."""
    conn = _connect(root)
    try:
        row = conn.execute(
            "SELECT membership_key, touched_key, extra_key, touched_files, "
            "violations_json FROM gate_results WHERE gate = ?",
            (gate,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    membership_key, touched_key, extra, touched_files_json, violations_json = row
    touched_files = tuple(json.loads(touched_files_json))
    violations = tuple(Violation.model_validate(v) for v in json.loads(violations_json))
    return _CacheEntry(
        membership_key=membership_key,
        touched_key=touched_key,
        extra_key=extra,
        touched_files=touched_files,
        violations=violations,
    )


# frob:ticket T-0602
def _store_entry(
    root: Path,
    gate: str,
    *,
    membership_key: str,
    touched_key: str,
    extra: str,
    touched_files: tuple[str, ...],
    violations: tuple[Violation, ...],
) -> None:
    """Persist `gate`'s fresh result, single-flight-safe via
    `derived_state_write_lock` (T-0918): this call happens from a gate
    worker thread nested under `frob.check`'s outer SHARED
    `derived_state_lock` hold, and `derived_state_write_lock` is the
    primitive built specifically for that nesting (a naive
    unconditional-EXCLUSIVE lock here would deadlock against that outer
    hold, per its own docstring). Two concurrent writers racing for the
    SAME (gate, key) is harmless either way: the write is a pure function
    of already-observed state, so whichever writer's `INSERT OR REPLACE`
    lands last is equally correct."""
    payload = json.dumps([v.model_dump(mode="json") for v in violations])
    files_payload = json.dumps(sorted(touched_files))
    with derived_state_write_lock(root):
        conn = _connect(root)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO gate_results "
                "(gate, membership_key, touched_key, extra_key, touched_files, "
                "violations_json, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    gate,
                    membership_key,
                    touched_key,
                    extra,
                    files_payload,
                    payload,
                    time.time(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
    _log.info(
        "gate-cache: stored gate=%s touched=%d violation(s)=%d",
        gate,
        len(touched_files),
        len(violations),
    )


# frob:doc \
# docs/modules/serve.md#per-gate-dependency-tracked-partial-re-evaluation-t-0602
# frob:ticket T-0602
# frob:tests tests/test_gate_cache.py::TestEvaluateCacheableGate.test_invalidate_forces_next_call_to_miss  # noqa: E501
def invalidate(root: Path) -> None:
    """Drop the whole gate-result cache (used by the cold-diff oracle test
    and by any caller that wants a guaranteed-fresh next evaluation) -- a
    correctness reset, not a performance knob: rebuilt lazily, one gate at
    a time, on next access."""
    path = _db_path(root)
    with derived_state_write_lock(root):
        if path.exists():
            path.unlink()
    _log.info("gate-cache: invalidated (%s removed)", path)


# --- Public entry point ----------------------------------------------------


# frob:doc \
# docs/modules/serve.md#per-gate-dependency-tracked-partial-re-evaluation-t-0602
# frob:ticket T-0602
# frob:tests tests/test_gate_cache.py::TestEvaluateCacheableGate.test_miss_then_hit_skips_second_call  # noqa: E501
# frob:tests tests/test_gate_cache.py::TestEvaluateCacheableGate.test_edit_to_untouched_file_stays_a_hit  # noqa: E501
# frob:tests tests/test_gate_cache.py::TestEvaluateCacheableGate.test_edit_to_touched_file_forces_miss  # noqa: E501
# frob:tests tests/test_gate_cache.py::TestEvaluateCacheableGate.test_new_untouched_file_forces_miss_membership_guard  # noqa: E501
# frob:tests tests/test_gate_cache.py::TestEvaluateCacheableGate.test_extra_change_forces_miss  # noqa: E501
# frob:tests tests/test_gate_cache.py::TestColdDiffOracle.test_cache_agrees_with_cold_across_random_edits  # noqa: E501
def evaluate_cacheable_gate(
    root: Path,
    gate: str,
    snapshot: GraphSnapshot,
    run: Callable[[GraphSnapshot], tuple[Violation, ...]],
    extra: tuple[str, ...] = (),
) -> tuple[Violation, ...]:
    """Serve `gate`'s cached result if -- and only if -- every file it
    touched last time still hashes the same AND the tree's overall file
    membership is unchanged AND `extra` (the gate's non-file scalar inputs)
    is unchanged; otherwise run `run` for real (against a `TrackedSnapshot`
    that records exactly what it reads this time) and store the fresh
    result. Always returns the gate's true current result -- see this
    module's docstring, "Correctness beats speedup"."""
    membership = _membership_key(snapshot.file_hashes)
    extra_k = extra_key(extra)
    cached = _load_entry(root, gate)
    if (
        cached is not None
        and cached.membership_key == membership
        and cached.extra_key == extra_k
    ):
        touched_now = _touched_key(snapshot.file_hashes, cached.touched_files)
        if touched_now == cached.touched_key:
            _log.info(
                "gate-cache: HIT gate=%s (%d tracked file(s), re-evaluation skipped)",
                gate,
                len(cached.touched_files),
            )
            return cached.violations
    _log.info("gate-cache: MISS gate=%s (evaluating)", gate)
    touched: set[str] = set()
    tracked = TrackedSnapshot(snapshot, touched)
    # `run` is typed for the real `GraphSnapshot` (matching every existing
    # gate function's own signature, e.g. `drift_gate(snapshot: GraphSnapshot,
    # ...)`) -- `TrackedSnapshot` is a deliberate, verified-safe duck-typed
    # stand-in exposing the exact same `.symbols`/`.edges`/`.file_hashes`/
    # `.malformed`/`.parse_failures`/`.root`/`.stats` surface those functions
    # actually read, so every gate on `_CACHEABLE_GATES` runs unmodified
    # against it; `tests/test_gate_cache.py::TestColdDiffOracle` is the
    # runtime proof this substitution is behavior-preserving.
    violations = run(cast(GraphSnapshot, tracked))
    _store_entry(
        root,
        gate,
        membership_key=membership,
        touched_key=_touched_key(snapshot.file_hashes, touched),
        extra=extra_k,
        touched_files=tuple(sorted(touched)),
        violations=violations,
    )
    return violations


__all__ = [
    "TrackedSnapshot",
    "evaluate_cacheable_gate",
    "extra_key",
    "invalidate",
]

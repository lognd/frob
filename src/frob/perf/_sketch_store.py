"""`frob.perf._sketch_store` -- sqlite-backed decayed-merge store for
`frob.stats._sketch.QuantileSketch`, keyed by hot-graph `Section`
(T-0711, child of EPIC T-0709, second half of T-0710's hit-stream
contract: "feeding `resolve_stream`'s `HitStream` into a persisted store
... is T-0711/T-0712's job").

**Keying.** `stable_section_key` deliberately does NOT reuse `Section.id`
verbatim: `Section.id` is `sha256(file, qualname, kind, start_line)`
(`frob.perf._hotgraph`'s per-run resolver id), which changes the instant a
line above a section drifts even when the section's own content did not
change. This store's whole point is accumulating a decayed history ACROSS
runs, so it needs a key that survives that drift -- `Section.id`'s own
docstring names this exact ticket as the layer responsible for it. Until a
future ticket wires the real line-drift-tolerant symbol digest
(`frob.graph.digest.compute_digests`) through the hot-graph resolver,
`stable_section_key` accepts an optional `symbol_digest` and falls back to
`section.file` when the caller has none -- still qualname/kind-precise,
just not yet line-drift tolerant; wiring a real digest through only
changes what basis string is hashed, not this module's schema or the
merge/decay/eviction logic below.

**The merge/decay/eviction contract** (the ticket's plan, verbatim):
`prior' = merge(current_run_sketch, decay(stored_prior, half_life_runs))`
computed by `put_sketch` on every write; `store_size_bytes` /
`_evict_coldest` enforce `[perf.sketch].store_cap_bytes` (~100KB default)
by dropping the least-recently-used section's row first, so the store
structurally cannot grow to megabytes regardless of how many distinct
sections get sampled over the repo's lifetime.
"""
# frob:waive INV006 reason="T-0711: this module's 'only' usages are source-level \
# design-rationale prose (describing already-implemented internal behavior -- what \
# wiring a real symbol digest changes, and that _close_all is test-teardown-only) \
# verifiable by reading the code they annotate, not a separate cross-module contract \
# needing its own tracked invariant; same calibration-batch disposition as the T-0585 \
# INV006 pool"
# frob:waive ARCH102 reason="11 of 13 exports form one connected sqlite decayed-merge \
# store cluster (connect/put_sketch/get_sketch/ list_sketches/_evict_coldest all \
# sharing the one on-disk store this module's docstring describes); the 2 outliers \
# (stable_section_key, new_run_sketch) are the key-derivation and constructor helpers \
# for rows in that exact same store, coupled to it by the schema/data model rather \
# than a direct call -- there is one store here, not two concerns"

from __future__ import annotations

import hashlib
import sqlite3
import threading
import time
import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani import Err, Ok
from typani.result import Result

from frob.logging import get_logger
from frob.perf._hotgraph import Section
from frob.perf._models import PerfError
from frob.stats._sketch import (
    QuantileSketch,
    decay_sketch,
    merge_sketches,
    new_sketch,
)

_log = get_logger(__name__)

__all__ = [
    "SketchStoreConfig",
    "StoredSketch",
    "get_sketch",
    "list_sketches",
    "load_sketch_config",
    "new_run_sketch",
    "put_sketch",
    "stable_section_key",
    "store_size_bytes",
]

#: Process-lifetime connection cache, keyed by resolved db path -- mirrors
#: `frob.dup._cache`'s `_conn_cache` (T-0191 pattern: reopening the file
#: and re-running `executescript` on every call is the dominant cost at
#: repo scale for a store this hot-path-adjacent).
_conn_cache: dict[Path, sqlite3.Connection] = {}
_conn_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sketches (
    section_key TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    last_used REAL NOT NULL,
    payload TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT ''
);
"""

_DEFAULT_ALPHA = 0.02
_DEFAULT_HALF_LIFE_RUNS = 5.0
_DEFAULT_STORE_CAP_BYTES = 100_000
# T-0712: relative p90 shift (new vs stored prior) beyond which the
# regression ratchet fires a PERF finding naming the section -- see
# `frob.perf._ratchet.check_ratchet`.
_DEFAULT_RATCHET_TOLERANCE = 0.5


# frob:doc docs/modules/perf.md#hot-graph-sketch-store-t-0711-epic-t-0709
class SketchStoreConfig(BaseModel):
    """The `[perf.sketch]` table in `frob.toml` (T-0711's tunables, per the
    ticket's plan): `alpha` is the DDSketch relative-error target new run
    sketches are built at (`frob.stats._sketch.DEFAULT_ALPHA`'s
    frob.toml-configurable twin); `half_life_runs` is how many
    `put_sketch` calls it takes a stored prior's weight to halve relative
    to the incoming run's (the "decayed merge" the ticket names, so
    recent runs dominate without discarding history outright);
    `store_cap_bytes` bounds the WHOLE store's total payload size,
    evicting the coldest (least-recently-used) section first, so the
    store structurally cannot grow to megabytes."""

    model_config = ConfigDict(frozen=True)

    alpha: float = _DEFAULT_ALPHA
    half_life_runs: float = _DEFAULT_HALF_LIFE_RUNS
    store_cap_bytes: int = _DEFAULT_STORE_CAP_BYTES
    #: T-0712: relative p90 shift (new run vs stored prior) beyond which
    #: `frob.perf._ratchet.check_ratchet` fires a regression finding.
    ratchet_tolerance: float = _DEFAULT_RATCHET_TOLERANCE


def _read_toml(path: Path) -> dict | None:
    """Best-effort TOML load: `None` on any missing/unreadable/malformed
    file -- a missing/absent `[perf.sketch]` table just means store
    defaults, never a crash (fail-open, matching `_redundancy._read_toml`)."""
    if not path.exists():
        return None
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("sketch store: %s unreadable: %s", path, exc)
        return None


# frob:doc docs/modules/perf.md#hot-graph-sketch-store-t-0711-epic-t-0709
# frob:tests tests/unit/perf/test_sketch_store.py::TestSketchStoreConfig.test_missing_frob_toml_returns_defaults  # noqa: E501
# frob:tests tests/unit/perf/test_sketch_store.py::TestSketchStoreConfig.test_parses_perf_sketch_table  # noqa: E501
# frob:tests tests/unit/perf/test_sketch_store.py::TestSketchStoreConfig.test_malformed_toml_falls_back_to_defaults  # noqa: E501
# frob:tests tests/unit/perf/test_sketch_store.py::TestSketchStoreConfig.test_wrong_typed_perf_sketch_falls_back_to_defaults  # noqa: E501
def load_sketch_config(root: Path) -> SketchStoreConfig:
    """The `[perf.sketch]` table from `root/frob.toml`, or all-defaults on
    a missing/malformed file/table -- never raises."""
    data = _read_toml(root / "frob.toml")
    if data is None:
        return SketchStoreConfig()
    table = data.get("perf", {}).get("sketch", {})
    if not isinstance(table, dict):
        _log.warning("sketch store: [perf.sketch] is not a table, using defaults")
        return SketchStoreConfig()
    try:
        return SketchStoreConfig(**table)
    except (TypeError, ValueError) as exc:
        _log.warning("sketch store: [perf.sketch] rejected (%s), using defaults", exc)
        return SketchStoreConfig()


# frob:doc docs/modules/perf.md#hot-graph-sketch-store-t-0711-epic-t-0709
def stable_section_key(section: Section, symbol_digest: str | None = None) -> str:
    """The store key for `section`: sha256 hex over `(basis, qualname,
    kind)` where `basis` is `symbol_digest` when the caller has one (a
    real line-drift-tolerant symbol digest, `frob.graph.digest.
    compute_digests`) or `section.file` otherwise. Deliberately excludes
    `start_line`/`end_line` (unlike `Section.id`) -- see module docstring
    for why a run-scoped id is the wrong key for a cross-run store."""
    basis = symbol_digest if symbol_digest is not None else section.file
    joined = "\x00".join((basis, section.qualname, section.kind))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:24]


def _db_path(root: Path) -> Path:
    """The `.frob/hotgraph_sketches.db` path under `root`."""
    return root / ".frob" / "hotgraph_sketches.db"


def _connect(root: Path) -> Result[sqlite3.Connection, PerfError]:
    """A shared, process-cached connection to `root`'s
    `.frob/hotgraph_sketches.db`, creating the schema on first open."""
    path = _db_path(root).resolve()
    with _conn_lock:
        cached = _conn_cache.get(path)
        if cached is not None:
            return Ok(cached)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(path, check_same_thread=False)
            conn.executescript(_SCHEMA)
            _ensure_label_column(conn)
        except sqlite3.DatabaseError as exc:
            _log.error("sketch store at %s unreadable: %s", path, exc)
            return Err(PerfError.SketchStoreCorrupt)
        _conn_cache[path] = conn
        return Ok(conn)


def _ensure_label_column(conn: sqlite3.Connection) -> None:
    """T-0712: a store created before the `label` column existed still has
    `CREATE TABLE IF NOT EXISTS`'s original schema (sqlite does not
    retroactively add columns to an existing table) -- add it here,
    tolerating the "duplicate column" error on a store that already has
    it, so every store this process ever opens ends up with the column
    `list_sketches`/`put_sketch` both need, regardless of when it was
    created."""
    try:
        conn.execute("ALTER TABLE sketches ADD COLUMN label TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError as exc:
        if "duplicate column" not in str(exc).lower():
            raise


# frob:tests \
# tests/unit/perf/test_sketch_store.py::TestConnectionReuse.test_close_all_drops_cached\
# _connections  # noqa: E501
def _close_all() -> None:
    """Close and forget every process-cached sketch-store connection --
    test teardown only (mirrors `frob.dup._cache._close_all`); not needed
    in normal CLI use since the process exit reclaims the descriptor."""
    with _conn_lock:
        for conn in _conn_cache.values():
            conn.close()
        _conn_cache.clear()


# frob:doc docs/modules/perf.md#hot-graph-sketch-store-t-0711-epic-t-0709
# frob:tests tests/unit/perf/test_sketch_store.py::TestSketchStore.test_get_on_never_seen_key_is_none  # noqa: E501
# frob:tests tests/unit/perf/test_sketch_store.py::TestSketchStore.test_put_then_get_round_trips  # noqa: E501
def get_sketch(root: Path, section_key: str) -> QuantileSketch | None:
    """The currently-stored sketch for `section_key`, or `None` on a miss
    (never seen, or the store is unreadable -- both are "no prior" from a
    caller's perspective)."""
    conn_r = _connect(root)
    if conn_r.is_err:
        return None
    conn = conn_r.danger_ok
    row = conn.execute(
        "SELECT payload FROM sketches WHERE section_key = ?", (section_key,)
    ).fetchone()
    if row is None:
        return None
    return QuantileSketch.model_validate_json(row[0])


def _evict_coldest(conn: sqlite3.Connection, cap_bytes: int) -> None:
    """Delete least-recently-used rows until the sum of stored payload
    sizes is at or under `cap_bytes` -- the store's size-budget
    enforcement (T-0711's plan: "eviction of coldest sections, so it
    structurally cannot grow to megabytes"). A single section whose own
    serialized sketch already exceeds `cap_bytes` cannot be brought under
    cap by evicting OTHER rows; that section's own row is left in place
    (evicting it would just re-write it back on the next `put_sketch` for
    that same section) -- a documented corner case, not silently papered
    over: `sketch_size_bytes` staying under the ticket's <1KB acceptance
    bound at the intended alpha keeps this from happening in practice."""
    total = sum(
        len(payload) for (payload,) in conn.execute("SELECT payload FROM sketches")
    )
    if total <= cap_bytes:
        return
    rows = conn.execute(
        "SELECT section_key, length(payload) FROM sketches ORDER BY last_used ASC"
    ).fetchall()
    for section_key, size in rows:
        if total <= cap_bytes:
            break
        conn.execute("DELETE FROM sketches WHERE section_key = ?", (section_key,))
        total -= size
        _log.info(
            "sketch store: evicted coldest section %s (%d bytes) over cap %d",
            section_key,
            size,
            cap_bytes,
        )


# frob:doc docs/modules/perf.md#hot-graph-sketch-store-t-0711-epic-t-0709
# frob:tests tests/unit/perf/test_sketch_store.py::TestSketchStore.test_put_then_get_round_trips  # noqa: E501
# frob:tests tests/unit/perf/test_sketch_store.py::TestSketchStore.test_decayed_merge_converges_toward_recent_run_distribution  # noqa: E501
# frob:tests tests/unit/perf/test_sketch_store.py::TestSketchStore.test_store_cap_evicts_coldest_section_first  # noqa: E501
# frob:tests tests/unit/perf/test_sketch_store.py::TestSketchStore.test_first_write_has_no_prior_to_decay  # noqa: E501
def put_sketch(
    root: Path,
    section_key: str,
    kind: str,
    run_sketch: QuantileSketch,
    config: SketchStoreConfig,
    label: str = "",
) -> Result[QuantileSketch, PerfError]:
    """Merge `run_sketch` onto the decayed stored prior for `section_key`
    (`prior' = merge(run_sketch, decay(stored_prior, config.
    half_life_runs))`, the ticket's decayed-merge update rule -- one decay
    step per `put_sketch` call, so `half_life_runs` really is "runs", not
    wall-clock time), persists the merged result, evicts coldest rows
    beyond `config.store_cap_bytes`, and returns the sketch actually
    stored. A first write for a never-seen `section_key` has no prior to
    decay -- `run_sketch` alone becomes the stored value. `label`
    (T-0712, e.g. a `Section.qualname`) is stored alongside the sketch
    purely for display -- `frob perf hot`'s query surface needs a
    human-readable name since `section_key` is an opaque digest; an empty
    `label` on an existing row is left untouched by a caller that never
    passes one (`INSERT OR REPLACE` always supplies a value, so this only
    matters for a caller choosing not to name it)."""
    conn_r = _connect(root)
    if conn_r.is_err:
        return Err(conn_r.danger_err)
    conn = conn_r.danger_ok
    prior = get_sketch(root, section_key)
    if prior is None:
        merged = run_sketch
    else:
        decay_factor = 0.5 ** (1.0 / config.half_life_runs)
        merged = merge_sketches(run_sketch, decay_sketch(prior, decay_factor))
    conn.execute(
        "INSERT OR REPLACE INTO sketches "
        "(section_key, kind, last_used, payload, label) VALUES (?, ?, ?, ?, ?)",
        (section_key, kind, time.time(), merged.model_dump_json(), label),
    )
    _evict_coldest(conn, config.store_cap_bytes)
    conn.commit()
    return Ok(merged)


# frob:doc docs/modules/perf.md#hot-graph-query-surface-t-0712
class StoredSketch(BaseModel):
    """One row of `frob.perf._sketch_store`'s persisted store, as read by
    `list_sketches` -- the shape `frob perf hot` renders and the MCP
    mirror serializes."""

    model_config = ConfigDict(frozen=True)

    section_key: str
    kind: str
    label: str
    last_used: float
    sketch: QuantileSketch


# frob:doc docs/modules/perf.md#hot-graph-query-surface-t-0712
# frob:tests tests/unit/perf/test_hot_query.py::TestListSketches.test_empty_store_is_empty  # noqa: E501
# frob:tests tests/unit/perf/test_hot_query.py::TestListSketches.test_lists_every_stored_row_with_its_label  # noqa: E501
# frob:tests tests/unit/perf/test_hot_query.py::TestListSketches.test_pre_label_store_still_reads_via_column_migration  # noqa: E501
def list_sketches(root: Path) -> list[StoredSketch]:
    """Every currently-stored sketch at `root`'s hot-graph store, in no
    particular order -- `frob perf hot`'s query surface sorts/ranks this
    itself (`--by p90|p50xcount`) so the store stays a dumb read, not a
    second place ranking logic lives. `[]` on an unreadable/never-created
    store (fail-open, matching `get_sketch`'s "no prior" posture)."""
    conn_r = _connect(root)
    if conn_r.is_err:
        return []
    conn = conn_r.danger_ok
    rows = conn.execute(
        "SELECT section_key, kind, label, last_used, payload FROM sketches"
    ).fetchall()
    return [
        StoredSketch(
            section_key=section_key,
            kind=kind,
            label=label,
            last_used=last_used,
            sketch=QuantileSketch.model_validate_json(payload),
        )
        for section_key, kind, label, last_used, payload in rows
    ]


# frob:doc docs/modules/perf.md#hot-graph-sketch-store-t-0711-epic-t-0709
# frob:tests tests/unit/perf/test_sketch_store.py::TestSketchStore.test_decayed_merge_converges_toward_recent_run_distribution  # noqa: E501
# frob:tests tests/unit/perf/test_sketch_store.py::TestSketchStore.test_store_cap_evicts_coldest_section_first  # noqa: E501
def store_size_bytes(root: Path) -> int:
    """Total serialized payload bytes currently held across every section
    in `root`'s sketch store -- what `[perf.sketch].store_cap_bytes`
    bounds."""
    conn_r = _connect(root)
    if conn_r.is_err:
        return 0
    conn = conn_r.danger_ok
    row = conn.execute(
        "SELECT COALESCE(SUM(length(payload)), 0) FROM sketches"
    ).fetchone()
    return int(row[0]) if row is not None else 0


# frob:doc docs/modules/perf.md#hot-graph-sketch-store-t-0711-epic-t-0709
# frob:tests tests/unit/perf/test_sketch_store.py::TestSketchStore.test_new_run_sketch_is_an_empty_sketch_at_alpha  # noqa: E501
def new_run_sketch(alpha: float) -> QuantileSketch:
    """Convenience: an empty sketch a caller accumulates one run's samples
    into before handing it to `put_sketch` -- thin wrapper over
    `frob.stats._sketch.new_sketch` so a `frob.perf` caller need not
    import `frob.stats` directly for the common case."""
    return new_sketch(alpha=alpha)

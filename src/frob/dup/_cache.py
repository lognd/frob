"""Content-addressed + LRU cache for the dup pipeline (docs/modules/dup.md's Caching).

Two tables, one rule each:

- `fingerprints` is keyed by body digest -- content addressing means a body
  edit changes the key, which IS the invalidation; there is no staleness
  flag to get wrong.
- `verdicts` is keyed by `(min(d1,d2), max(d1,d2), method, corpus_epoch)`
  and carries `last_used` so it can be evicted LRU beyond
  `[dup].cache_entries` -- pairwise verdicts grow quadratically in the
  worst case, fingerprints do not.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: src/frob/dup/_cache.py's \
# exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable by \
# reading the code it annotates) rather than a separate cross-module contract needing \
# its own tracked invariant; disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from pathlib import Path

from typani import Err, Ok
from typani.result import Result
from typani.unit import Unit

from frob.dup._models import DupError
from frob.graph.cache import _compute_fingerprint
from frob.logging import get_logger

_log = get_logger(__name__)

#: The `frob.dup` package directory, used to source-hash the rule/
#: normalization code below (T-0798).
_DUP_PKG_DIR = Path(__file__).resolve().parent

#: Process-lifetime connection cache, keyed by resolved `.frob/dup.db` path.
#: T-0191: `find_clones` issues thousands of get/put calls on a repo this
#: size (one fingerprint lookup per rung per symbol, plus a verdict lookup
#: per candidate pair); reopening the file and re-running `executescript`
#: on every single call was the dominant cost of the clones gate (measured
#: ~76s wall time on this repo before this fix). Reusing one open
#: connection per db path for the process's lifetime turns that into a
#: single open + one CREATE TABLE IF NOT EXISTS. Guarded by `_conn_lock`
#: since the gate executor can, in principle, run gates from more than one
#: thread; `check_same_thread=False` plus the lock makes that safe.
_conn_cache: dict[Path, sqlite3.Connection] = {}
_conn_lock = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS fingerprints (
    digest TEXT NOT NULL,
    rung TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (digest, rung)
);
CREATE TABLE IF NOT EXISTS verdicts (
    d1 TEXT NOT NULL,
    d2 TEXT NOT NULL,
    method TEXT NOT NULL,
    corpus_epoch INTEGER NOT NULL,
    payload TEXT NOT NULL,
    last_used REAL NOT NULL,
    PRIMARY KEY (d1, d2, method, corpus_epoch)
);
"""


# frob:ticket T-0798
def _dup_code_fingerprint() -> str:
    """Sha256 hex digest over every `frob.dup/*.py` file's own source bytes.

    `_compute_fingerprint` (below) only changes on an installed-package
    VERSION bump; a rule/normalization edit landed in the same dev version
    (e.g. T-0785's rule change) does not touch it, so `_check_fingerprint`
    saw no change and kept serving verdicts computed under the old rules
    (T-0798: a gate-integrity hole -- the dup gate reported stale results
    as current until `.frob/dup.db` was hand-deleted). Hashing this
    package's own `.py` files directly makes ANY edit to the rule/
    normalization/pipeline code -- version bump or not -- change the
    stored fingerprint and trip the existing wholesale-invalidate path,
    with no second cache-key scheme to keep in sync.
    """
    digest = hashlib.sha256()
    for path in sorted(_DUP_PKG_DIR.glob("*.py")):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(path.read_bytes())
    return digest.hexdigest()


# frob:ticket T-0517
# frob:ticket T-0798
def _check_fingerprint(conn: sqlite3.Connection) -> None:
    """Invalidate cached fingerprint/verdict rows if the stored fingerprint
    does not match the running process's (version + dup source digest).

    Reuses `frob.graph.cache`'s `_compute_fingerprint` (T-0243 pattern)
    rather than a second implementation: `dup.db` rows are payloads
    derived from the same frob + tree-sitter grammar versions the graph
    cache keys on, so an algorithm change there (e.g. `_KEYWORDS`, r3
    canonicalization) can silently change what a digest *should* map to
    while the digest string itself stays the same -- content addressing
    alone cannot catch that, only a version fingerprint can (T-0517: an
    untracked, wrong-version `dup.db` served stale rows -- 6 cache hits,
    0 pairs verified -- against a landed algorithm change). Combined with
    `_dup_code_fingerprint` (T-0798) so an in-tree dup rule/normalization
    edit invalidates too, not only a package version bump.
    """
    current = f"{_compute_fingerprint()}|dup={_dup_code_fingerprint()}"
    row = conn.execute("SELECT value FROM meta WHERE key = 'fingerprint'").fetchone()
    stored = row[0] if row is not None else None
    if stored == current:
        return
    _log.info(
        "dup cache: fingerprint %r -> %r, invalidating cached rows",
        stored,
        current,
    )
    conn.execute("DELETE FROM fingerprints")
    conn.execute("DELETE FROM verdicts")
    conn.execute(
        "INSERT INTO meta (key, value) VALUES ('fingerprint', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (current,),
    )
    conn.commit()


def _db_path(root: Path) -> Path:
    """The `.frob/dup.db` path under `root`."""
    return root / ".frob" / "dup.db"


def _connect(root: Path) -> Result[sqlite3.Connection, DupError]:
    """A shared, process-cached connection to `root`'s `.frob/dup.db`.

    Returns the same open `sqlite3.Connection` for repeated calls against
    the same resolved path rather than reopening the file each time (see
    `_conn_cache`'s docstring for why this matters at repo scale).
    """
    path = _db_path(root).resolve()
    with _conn_lock:
        cached = _conn_cache.get(path)
        if cached is not None:
            return Ok(cached)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(path, check_same_thread=False)
            conn.executescript(_SCHEMA)
            _check_fingerprint(conn)
        except sqlite3.DatabaseError as exc:
            _log.error("dup cache at %s unreadable: %s", path, exc)
            return Err(DupError.CacheCorrupt)
        _conn_cache[path] = conn
        return Ok(conn)


# frob:ticket T-0565
# frob:tests tests/unit/test_dup_cache.py::TestConnectionReuse.test_close_all_drops_cached_connections  # noqa: E501
def _close_all() -> None:
    """Close and forget every process-cached dup-cache connection.

    Not needed in normal CLI use (the process exits and the OS reclaims
    the file descriptor), but test suites that create many `tmp_path`
    dup caches in one process should call this in teardown to avoid an
    unbounded number of open connections accumulating across tests.
    """
    with _conn_lock:
        for conn in _conn_cache.values():
            conn.close()
        _conn_cache.clear()


# frob:doc docs/modules/dup.md#caching
# frob:tests tests/unit/test_dup_cache.py::TestFingerprintRoundTrip.test_put_then_get_returns_same_payload  # noqa: E501
# frob:tests tests/unit/test_dup_cache.py::TestFingerprintRoundTrip.test_get_fingerprint_connect_error_returns_none  # noqa: E501
def get_fingerprint(root: Path, digest: str, rung: str) -> tuple[object, ...] | None:
    """The cached fingerprint payload for `digest`/`rung`, or None on a miss."""
    conn_r = _connect(root)
    if conn_r.is_err:
        return None
    conn = conn_r.danger_ok
    row = conn.execute(
        "SELECT payload FROM fingerprints WHERE digest = ? AND rung = ?",
        (digest, rung),
    ).fetchone()
    return json.loads(row[0]) if row else None


# frob:doc docs/modules/dup.md#caching
def put_fingerprint(
    root: Path, digest: str, rung: str, payload: tuple[object, ...]
) -> Result[Unit, DupError]:
    """Store `payload` for `digest`/`rung`, content-addressed (no staleness logic)."""
    conn_r = _connect(root)
    if conn_r.is_err:
        return conn_r.map(lambda _: Unit())
    conn = conn_r.danger_ok
    conn.execute(
        "INSERT OR REPLACE INTO fingerprints (digest, rung, payload) VALUES (?, ?, ?)",
        (digest, rung, json.dumps(payload)),
    )
    conn.commit()
    return Ok(Unit())


# frob:doc docs/modules/dup.md#caching
def get_verdict(
    root: Path, d1: str, d2: str, method: str, corpus_epoch: int
) -> tuple[object, ...] | None:
    """The cached pairwise verdict, touching `last_used` for the LRU on a hit."""
    lo, hi = (d1, d2) if d1 <= d2 else (d2, d1)
    conn_r = _connect(root)
    if conn_r.is_err:
        return None
    conn = conn_r.danger_ok
    row = conn.execute(
        "SELECT payload FROM verdicts "
        "WHERE d1=? AND d2=? AND method=? AND corpus_epoch=?",
        (lo, hi, method, corpus_epoch),
    ).fetchone()
    if row is None:
        return None
    conn.execute(
        "UPDATE verdicts SET last_used=? "
        "WHERE d1=? AND d2=? AND method=? AND corpus_epoch=?",
        (time.time(), lo, hi, method, corpus_epoch),
    )
    conn.commit()
    return json.loads(row[0])


# frob:doc docs/modules/dup.md#caching
# frob:tests tests/unit/test_dup_cache.py::TestVerdictRoundTrip.test_put_then_get_returns_same_payload  # noqa: E501
# frob:tests tests/unit/test_dup_cache.py::TestVerdictRoundTrip.test_put_verdict_evicts_lru_rows_beyond_cache_entries  # noqa: E501
# frob:tests tests/unit/test_dup_cache.py::TestVerdictRoundTrip.test_put_verdict_connect_error_is_propagated  # noqa: E501
def put_verdict(
    root: Path,
    d1: str,
    d2: str,
    method: str,
    corpus_epoch: int,
    payload: tuple[object, ...],
    cache_entries: int,
) -> Result[Unit, DupError]:
    """Store a pairwise verdict, then evict LRU rows beyond `cache_entries`."""
    lo, hi = (d1, d2) if d1 <= d2 else (d2, d1)
    conn_r = _connect(root)
    if conn_r.is_err:
        return conn_r.map(lambda _: Unit())
    conn = conn_r.danger_ok
    conn.execute(
        "INSERT OR REPLACE INTO verdicts "
        "(d1, d2, method, corpus_epoch, payload, last_used) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (lo, hi, method, corpus_epoch, json.dumps(payload), time.time()),
    )
    (count,) = conn.execute("SELECT COUNT(*) FROM verdicts").fetchone()
    if count > cache_entries:
        overflow = count - cache_entries
        conn.execute(
            "DELETE FROM verdicts WHERE rowid IN "
            "(SELECT rowid FROM verdicts ORDER BY last_used ASC LIMIT ?)",
            (overflow,),
        )
        _log.debug("dup cache: evicted %d LRU verdict row(s)", overflow)
    conn.commit()
    return Ok(Unit())


__all__ = [
    "_close_all",
    "get_fingerprint",
    "get_verdict",
    "put_fingerprint",
    "put_verdict",
]

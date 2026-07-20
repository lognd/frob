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

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

from typani import Err, Ok
from typani.result import Result
from typani.unit import Unit

from frob.dup._models import DupError
from frob.logging import get_logger

_log = get_logger(__name__)

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
        except sqlite3.DatabaseError as exc:
            _log.error("dup cache at %s unreadable: %s", path, exc)
            return Err(DupError.CacheCorrupt)
        _conn_cache[path] = conn
        return Ok(conn)


# frob:doc docs/modules/dup.md#caching
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
# frob:waive TEST005 reason="get_fingerprint 85.7% branch cover, debt T-0160"
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
# frob:waive TEST005 reason="put_verdict 71.4% branch cover, debt T-0160"
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

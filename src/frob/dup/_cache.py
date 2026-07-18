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
import time
from pathlib import Path

from typani import Err, Ok
from typani.result import Result
from typani.unit import Unit

from frob.dup._models import DupError
from frob.logging import get_logger

_log = get_logger(__name__)

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
    path = _db_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.executescript(_SCHEMA)
        return Ok(conn)
    except sqlite3.DatabaseError as exc:
        _log.error("dup cache at %s unreadable: %s", path, exc)
        return Err(DupError.CacheCorrupt)


# frob:doc docs/modules/dup.md#caching
# frob:waive TEST005 reason="get_fingerprint 85.7% branch cover, debt T-0160"
def get_fingerprint(root: Path, digest: str, rung: str) -> tuple[object, ...] | None:
    """The cached fingerprint payload for `digest`/`rung`, or None on a miss."""
    conn_r = _connect(root)
    if conn_r.is_err:
        return None
    conn = conn_r.danger_ok
    try:
        row = conn.execute(
            "SELECT payload FROM fingerprints WHERE digest = ? AND rung = ?",
            (digest, rung),
        ).fetchone()
    finally:
        conn.close()
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
    try:
        conn.execute(
            "INSERT OR REPLACE INTO fingerprints (digest, rung, payload) "
            "VALUES (?, ?, ?)",
            (digest, rung, json.dumps(payload)),
        )
        conn.commit()
    finally:
        conn.close()
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
    try:
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
    finally:
        conn.close()
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
    try:
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
    finally:
        conn.close()
    return Ok(Unit())


__all__ = ["get_fingerprint", "get_verdict", "put_fingerprint", "put_verdict"]

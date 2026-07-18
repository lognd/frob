"""SQLite-backed snapshot cache at `.frob/cache.db` (docs/modules/graph.md, "Cache").

Everything stored here is derived and rebuildable from the tracked source
tree -- safe to delete at any time. Rows are keyed per source/doc file so
`build_graph` can incrementally replace only the files whose content hash
changed, and `load_graph` can read the whole snapshot back without
re-parsing anything.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from frob.graph._models import (
    BuildStats,
    Digests,
    Edge,
    EdgeKind,
    GraphSnapshot,
    MalformedDirective,
    SymbolId,
    SymbolRecord,
)
from frob.lang import SymbolKind
from frob.logging import get_logger

_log = get_logger(__name__)

_SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, content_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS symbols (
    symref TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    qualname TEXT NOT NULL,
    kind TEXT NOT NULL,
    public INTEGER NOT NULL,
    span_start INTEGER NOT NULL,
    span_end INTEGER NOT NULL,
    digest_sig TEXT NOT NULL,
    digest_body TEXT NOT NULL,
    digest_doc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file TEXT NOT NULL,
    src TEXT NOT NULL,
    kind TEXT NOT NULL,
    target TEXT NOT NULL,
    origin TEXT NOT NULL,
    attrs TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS malformed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file TEXT NOT NULL,
    line INTEGER NOT NULL,
    reason TEXT NOT NULL
);
"""


# frob:ticket T-0029
def _open(path: Path) -> sqlite3.Connection:
    """A cache connection with a busy timeout so concurrent builds wait
    rather than raising `disk I/O error` (T-0029: two agents building the
    same worktree cache collided; sqlite's default is no wait at all)."""
    conn = sqlite3.connect(str(path), timeout=30.0)
    # These pragmas can touch page structure, so on a non-sqlite file they
    # raise here -- swallow it and let connect()'s schema SELECT be the one
    # place that detects corruption and triggers recreate (T-0019/T-0029).
    # WAL lets concurrent builds queue on a single writer instead of
    # deadlocking on a shared->exclusive lock upgrade; rollback-journal mode
    # timed out even at 30s under 4 parallel builders.
    try:
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.DatabaseError as exc:
        _log.debug("cache: pragma setup deferred (%s)", exc)
    conn.execute("PRAGMA foreign_keys = OFF")
    return conn


# frob:ticket T-0141
def _read_schema_version(
    conn: sqlite3.Connection, path: Path
) -> tuple[sqlite3.Connection, int | None]:
    """Read the stored schema version, recreating the file if it is not sqlite."""
    try:
        cur = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'")
        row = cur.fetchone()
        return conn, (int(row[0]) if row is not None else None)
    except sqlite3.DatabaseError as exc:
        _log.warning("cache.connect: unreadable db at %s, rebuilding: %s", path, exc)
    try:
        conn.execute("SELECT 1")
    except sqlite3.DatabaseError:
        _log.warning("cache.connect: %s is not a sqlite file; recreating", path)
        conn = _recreate(conn, path)
    return conn, None


def _apply_schema(conn: sqlite3.Connection, existing: int | None, path: Path) -> None:
    """Ensure the schema is current; wipe and rebuild on a version mismatch."""
    if existing == _SCHEMA_VERSION:
        conn.executescript(_SCHEMA)
        return
    _log.info(
        "cache.connect: schema %s -> %s at %s, rebuilding",
        existing,
        _SCHEMA_VERSION,
        path,
    )
    for table in ("meta", "files", "symbols", "edges", "malformed"):
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.executescript(_SCHEMA)
    conn.execute(
        "INSERT INTO meta (key, value) VALUES ('schema_version', ?)",
        (str(_SCHEMA_VERSION),),
    )
    conn.commit()


# frob:ticket T-0141
def _recreate(conn: sqlite3.Connection, path: Path) -> sqlite3.Connection:
    """Close `conn`, delete `path` and its WAL/SHM sidecars, reopen fresh.

    Shared by both corruption-detection points in `connect` (T-0141): a
    cache.db whose bytes cannot be trusted is derived state, so the only
    honest recovery is delete-and-recreate, never DDL over the bad handle.
    The `-wal`/`-shm` sidecars from T-0029's WAL mode are not themselves a
    corruption vector here (a fresh db's WAL salt won't match a stale
    sidecar, so sqlite discards it on open) -- but leaving them behind on
    every recovery orphans them permanently since nothing else ever cleans
    them up, so they are unlinked alongside the main file.
    """
    conn.close()
    path.unlink(missing_ok=True)
    path.with_name(path.name + "-wal").unlink(missing_ok=True)
    path.with_name(path.name + "-shm").unlink(missing_ok=True)
    return _open(path)


# frob:ticket T-0141
def _apply_schema_with_recovery(
    conn: sqlite3.Connection, existing: int | None, path: Path
) -> sqlite3.Connection:
    """Apply the schema; on a DatabaseError escaping the DDL, recreate once.

    `_read_schema_version`'s own "is this even sqlite" probe (`SELECT 1`)
    can pass on a file that is sqlite-shaped but has a corrupted table page
    (T-0141: this is what py3.12's libsqlite exposes that 3.11 did not) --
    `SELECT 1` never touches a btree page, so it can't see that damage. The
    DDL here is what actually reads the meta/files/symbols pages, so it is
    the second and final place corruption can surface. A failure right
    after recreation is a real error, not something to loop on, so the
    retry's own DatabaseError propagates uncaught.
    """
    try:
        _apply_schema(conn, existing, path)
    except sqlite3.DatabaseError as exc:
        _log.warning(
            "cache.connect: %s failed schema application, recreating: %s",
            path,
            exc,
        )
        conn = _recreate(conn, path)
        _apply_schema(conn, None, path)
    return conn


# frob:invariant INV-003
# frob:ticket T-0029
# frob:ticket T-0141
# frob:doc docs/modules/graph.md#cache
def connect(path: Path) -> sqlite3.Connection:
    """Open (creating parent dirs) the cache db; wipe and rebuild on schema mismatch.

    A cache.db whose bytes are not sqlite at all (truncation, disk garbage)
    cannot be repaired through its own connection -- DROP TABLE raises the
    same DatabaseError. The cache is derived state, so the honest recovery
    is delete-and-recreate the file (T-0019 / INV-003), applied at both the
    connect-probe stage and, per T-0141, the later DDL stage too.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = _open(path)
    conn, existing = _read_schema_version(conn, path)
    return _apply_schema_with_recovery(conn, existing, path)


# frob:doc docs/modules/graph.md#cache
def set_root(conn: sqlite3.Connection, root: str) -> None:
    """Record the snapshot's repo root (used by `load_graph`)."""
    conn.execute(
        "INSERT INTO meta (key, value) VALUES ('root', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (root,),
    )


# frob:doc docs/modules/graph.md#cache
def get_root(conn: sqlite3.Connection) -> str | None:
    """The stored repo root, if any snapshot has ever been saved."""
    cur = conn.execute("SELECT value FROM meta WHERE key = 'root'")
    row = cur.fetchone()
    return row[0] if row is not None else None


# frob:doc docs/modules/graph.md#cache
def get_file_hash(conn: sqlite3.Connection, file_path: str) -> str | None:
    """The cached content hash for `file_path`, or `None` if never stored."""
    cur = conn.execute("SELECT content_hash FROM files WHERE path = ?", (file_path,))
    row = cur.fetchone()
    return row[0] if row is not None else None


def _store_symbols(
    conn: sqlite3.Connection, file_path: str, symbols: tuple[SymbolRecord, ...]
) -> None:
    """Replace the `symbols` rows derived from `file_path`."""
    conn.execute("DELETE FROM symbols WHERE path = ?", (file_path,))
    for record in symbols:
        conn.execute(
            "INSERT INTO symbols VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                record.symref,
                record.id.path,
                record.id.qualname,
                record.kind.value,
                int(record.public),
                record.span[0],
                record.span[1],
                record.digests.sig,
                record.digests.body,
                record.digests.doc,
            ),
        )


def _store_edges(
    conn: sqlite3.Connection, file_path: str, edges: tuple[Edge, ...]
) -> None:
    """Replace the `edges` rows derived from `file_path`."""
    conn.execute("DELETE FROM edges WHERE file = ?", (file_path,))
    for edge in edges:
        conn.execute(
            "INSERT INTO edges (file, src, kind, target, origin, attrs) "
            "VALUES (?,?,?,?,?,?)",
            (
                file_path,
                edge.src,
                edge.kind.value,
                edge.target,
                edge.origin,
                json.dumps(dict(edge.attrs)),
            ),
        )


def _store_malformed(
    conn: sqlite3.Connection,
    file_path: str,
    malformed: tuple[MalformedDirective, ...],
) -> None:
    """Replace the `malformed` rows derived from `file_path`."""
    conn.execute("DELETE FROM malformed WHERE file = ?", (file_path,))
    for item in malformed:
        conn.execute(
            "INSERT INTO malformed (file, line, reason) VALUES (?,?,?)",
            (file_path, item.line, item.reason),
        )


# frob:doc docs/modules/graph.md#cache
def store_file_data(
    conn: sqlite3.Connection,
    *,
    file_path: str,
    content_hash: str,
    symbols: tuple[SymbolRecord, ...],
    edges: tuple[Edge, ...],
    malformed: tuple[MalformedDirective, ...],
) -> None:
    """Replace all rows derived from `file_path` (delete-then-insert, one commit)."""
    conn.execute(
        "INSERT INTO files (path, content_hash) VALUES (?, ?) "
        "ON CONFLICT(path) DO UPDATE SET content_hash = excluded.content_hash",
        (file_path, content_hash),
    )
    _store_symbols(conn, file_path, symbols)
    _store_edges(conn, file_path, edges)
    _store_malformed(conn, file_path, malformed)


def _row_to_symbol(row: tuple) -> SymbolRecord:
    """Reassemble one `symbols` table row into a `SymbolRecord`."""
    _symref, path, qualname, kind, public, span_start, span_end, sig, body, doc = row
    return SymbolRecord(
        id=SymbolId(path=path, qualname=qualname),
        kind=SymbolKind(kind),
        public=bool(public),
        digests=Digests(sig=sig, body=body, doc=doc),
        span=(span_start, span_end),
    )


# frob:doc docs/modules/graph.md#cache
def load_file_data(
    conn: sqlite3.Connection, file_path: str
) -> tuple[tuple[SymbolRecord, ...], tuple[Edge, ...], tuple[MalformedDirective, ...]]:
    """Read back everything previously stored for `file_path` (a cache hit)."""
    rows = conn.execute(
        "SELECT symref, path, qualname, kind, public, span_start, span_end, "
        "digest_sig, digest_body, digest_doc FROM symbols WHERE path = ?",
        (file_path,),
    )
    symbols = tuple(_row_to_symbol(row) for row in rows)
    edges = tuple(
        Edge(
            src=src,
            kind=EdgeKind(kind),
            target=target,
            origin=origin,
            attrs=json.loads(attrs),
        )
        for src, kind, target, origin, attrs in conn.execute(
            "SELECT src, kind, target, origin, attrs FROM edges WHERE file = ?",
            (file_path,),
        )
    )
    malformed = tuple(
        MalformedDirective(file=file_path, line=line, reason=reason)
        for line, reason in conn.execute(
            "SELECT line, reason FROM malformed WHERE file = ?", (file_path,)
        )
    )
    return symbols, edges, malformed


# frob:doc docs/modules/graph.md#cache
def load_all(
    conn: sqlite3.Connection, *, stats: BuildStats | None = None
) -> GraphSnapshot:
    """Reassemble the full `GraphSnapshot` from every row currently in the db."""
    root = get_root(conn) or ""
    file_hashes = {
        path: content_hash
        for path, content_hash in conn.execute("SELECT path, content_hash FROM files")
    }
    symbols: dict[str, SymbolRecord] = {}
    edges: list[Edge] = []
    malformed: list[MalformedDirective] = []
    for path in file_hashes:
        recs, e, m = load_file_data(conn, path)
        for rec in recs:
            symbols[rec.symref] = rec
        edges.extend(e)
        malformed.extend(m)
    return GraphSnapshot(
        root=root,
        symbols=symbols,
        edges=tuple(edges),
        malformed=tuple(malformed),
        file_hashes=file_hashes,
        stats=stats
        if stats is not None
        else BuildStats(parsed=0, cache_hits=len(file_hashes)),
    )


__all__ = [
    "connect",
    "get_file_hash",
    "get_root",
    "load_all",
    "load_file_data",
    "set_root",
    "store_file_data",
]

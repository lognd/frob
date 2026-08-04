"""SQLite-backed snapshot cache at `.frob/cache.db` (docs/modules/graph.md, "Cache").

Everything stored here is derived and rebuildable from the tracked source
tree -- safe to delete at any time. Rows are keyed per source/doc file so
`build_graph` can incrementally replace only the files whose content hash
changed, and `load_graph` can read the whole snapshot back without
re-parsing anything.
"""
# frob:waive ARCH102 reason="19 of 21 exports form one connected sqlite cache-store \
# cluster around connect/_apply_schema/load_all/store_file_data; the 2 outliers \
# (set_root, touch_file_stat) are small accessors over the exact same on-disk \
# cache/connection this module owns, not a second concern -- there is only one cache \
# seam here, and these two functions have nowhere else to live"

from __future__ import annotations

import json
import sqlite3
import time
from importlib.metadata import version
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
from frob.lang import GRAMMAR_FINGERPRINT_PACKAGES, SymbolKind
from frob.logging import get_logger

_log = get_logger(__name__)

# frob:ticket T-0279
# Bumped 1 -> 2: a cache.db written before the T-0336 gates.py fix (which
# taught `frob.gates` to treat a `frob:tests` edge's src/target endpoints
# per the either-direction convention, T-0137) can carry rows whose shape
# was never re-validated against that convention -- `_check_fingerprint`
# only catches a PACKAGE VERSION change, not a same-version code fix inside
# a dev/editable install (`_FINGERPRINT_PACKAGES` reads `importlib.metadata`
# versions, which do not move between commits absent an explicit version
# bump). `dsl.py`'s fresh-parse construction (`src`=attached symbol,
# `target`=directive argument, always) and `cache.py`'s store/load
# (identity passthrough, no field swap) already agree with each other --
# this bump exists purely to force every existing `.frob/cache.db` in the
# wild to discard whatever it holds and reparse once under the current,
# canonical dsl.py+gates.py pairing, rather than trusting rows written
# under an unknown historical version of that pairing forever.
# frob:ticket T-0245
# Bumped 2 -> 3: the `files` table gains `mtime_ns`/`size` columns (T-0245):
# a mount-filesystem stat is one syscall vs. the open+read+close of a full
# content hash, so build_graph and load_graph can trust an unchanged
# (mtime_ns, size) pair and skip reading file bytes entirely for the common
# "nothing changed" case -- the per-file stat storm this ticket exists to
# cut. A cache.db written under schema 2 has no such columns, so this must
# invalidate it same as any other shape change.
# frob:ticket T-1464
# Bumped 3 -> 4: new `parsed_artifacts` table (T-1464) persists whole
# per-file `ParsedFile` payloads (symbols/comments/content_hash), keyed by
# `(content_hash, fingerprint)`, so `ProcessPoolExecutor` gate workers
# (perf/dup/dead_symbols/arch, see `frob.gates._run_process_gate`) can read
# an already-derived artifact instead of independently re-parsing +
# re-extracting the same file in every worker process. Lives in this same
# `connect()`/schema machinery but under its OWN db file
# (`.frob/parse-artifacts.db`, `frob.gates._PARSE_ARTIFACT_CACHE_REL`) --
# NOT `.frob/cache.db` -- so this table's write volume never contends
# with `store_file_data`'s own T-1423 lock budget on the graph-snapshot
# cache; this schema bump still applies to BOTH files (any db this
# module's `connect()` ever opens gets the new table). A db written
# before this table existed has no such rows -- same "shape changed, must
# invalidate" rule as every prior bump, even though this bump is additive
# (no existing table's columns changed) rather than corrective.
_SCHEMA_VERSION = 4

# frob:ticket T-0243
# Packages whose behavior changes the shape of the parsed graph: the frob
# distribution itself (extraction/digest logic) plus every tree-sitter
# grammar/runtime package it parses source with. Bumping any of these can
# silently change symbol/edge output for identical source bytes -- see the
# T-0243 malmberg pilot incident (2830 vs 3007 symbols from a stale cache
# after a frob upgrade).
# frob:ticket T-0402
# G6: "strata-core" was missing here -- a strata-core native-extension
# upgrade that changed `.strata` parse output would NOT invalidate the
# cache, exactly the T-0243 incident this mechanism exists to prevent,
# reintroduced for `.strata`.
# frob:ticket T-0433
# G6 (full fix): the tree-sitter grammar packages are now DERIVED from
# `frob.lang.GRAMMAR_FINGERPRINT_PACKAGES` -- the module that actually owns
# grammar loading -- instead of hand-copied here. "frob" (this
# distribution's own extraction/digest logic) and "strata-core" (the one
# non-tree-sitter grammar) are not `frob.lang` grammar packages, so they
# stay listed here explicitly; every tree-sitter-loaded language's
# fingerprint surface now updates automatically if `frob.lang` ever adds or
# drops a package to that set, with no second hand-copied tuple to forget.
_NON_LANGUAGE_FINGERPRINT_PACKAGES = ("frob", "strata-core")
_FINGERPRINT_PACKAGES = (
    *_NON_LANGUAGE_FINGERPRINT_PACKAGES,
    *sorted(GRAMMAR_FINGERPRINT_PACKAGES),
)


# frob:ticket T-0243
# frob:tests tests/test_graph.py::TestBuildIncremental.test_fingerprint_bump_rebuilds
def _compute_fingerprint() -> str:
    """Version string of frob + every tree-sitter grammar package it uses.

    Used as a cache-invalidation key (`meta.fingerprint`, T-0243): any
    version change here means the same source bytes can parse to a
    different symbol/edge set, so a cache written under an old fingerprint
    must never be served under a new one.
    """
    parts = []
    for pkg in _FINGERPRINT_PACKAGES:
        try:
            parts.append(f"{pkg}=={version(pkg)}")
        except Exception:
            parts.append(f"{pkg}==unknown")
    return "|".join(parts)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS files (
    path TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    mtime_ns INTEGER NOT NULL DEFAULT 0,
    size INTEGER NOT NULL DEFAULT 0
);
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
CREATE TABLE IF NOT EXISTS parsed_artifacts (
    content_hash TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (content_hash, fingerprint)
);
"""


# frob:ticket T-0029
# frob:ticket T-0245
_LOCK_POLL_SECONDS = 2.0
_LOCK_TOTAL_TIMEOUT_SECONDS = 30.0


# frob:ticket T-1423
# frob:doc docs/modules/graph.md#lock-contention-t-1423
# frob:tests tests/test_graph_lock.py::TestCacheLockRetry.test_raises_cache_locked_once_budget_exhausted  # noqa: E501
# frob:tests tests/test_graph_lock.py::TestCacheLockRetry.test_build_graph_reports_err_instead_of_crashing_on_cache_locked  # noqa: E501
class CacheLocked(sqlite3.OperationalError):
    """A cache operation could not acquire the sqlite lock within the retry
    budget (T-1423). Distinct from a bare `sqlite3.OperationalError` so a
    caller (`frob.graph.build_graph`/`load_graph`) can catch exactly this
    recoverable-contention case and turn it into a typani `Result` instead
    of letting it escape as an unhandled exception -- never raised for a
    non-lock `DatabaseError`, which still propagates unchanged."""


# frob:ticket T-1423
# frob:tests tests/test_graph_lock.py::TestCacheLockRetry.test_retries_then_succeeds_past_a_transient_lock  # noqa: E501
# frob:tests tests/test_graph_lock.py::TestCacheLockRetry.test_non_locked_operational_error_is_not_retried  # noqa: E501
# frob:tests tests/test_graph_lock.py::TestCacheLockRetry.test_store_file_data_retries_past_a_held_exclusive_lock  # noqa: E501
# frob:raises CacheLocked
def _with_lock_retry(op, *, what: str):  # noqa: ANN001, ANN202
    """Run `op()`, retrying while sqlite reports the db as locked, up to
    `_LOCK_TOTAL_TIMEOUT_SECONDS`; raises `CacheLocked` once the budget is
    exhausted instead of letting the raw `sqlite3.OperationalError` escape.

    T-1239 and T-1416 already retry a locked/racing `OperationalError`
    during schema application (`_apply_schema_with_recovery`); this is the
    same retry shape generalized to every OTHER cache read/write path
    (`store_file_data`, `set_root`, `touch_file_stat`, `connect_readonly`)
    so a lock encountered outside schema application is retried too,
    instead of crashing `frob check` outright (T-1423). `op` must be safe
    to call more than once -- every current use is a delete-then-insert
    (or a read), both idempotent under retry.
    """
    deadline = time.monotonic() + _LOCK_TOTAL_TIMEOUT_SECONDS
    warned = False
    while True:
        try:
            return op()
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower():
                raise
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _log.error(
                    "cache: %s still locked after %.0fs, giving up",
                    what,
                    _LOCK_TOTAL_TIMEOUT_SECONDS,
                )
                raise CacheLocked(str(exc)) from exc
            if not warned:
                _log.warning(
                    "cache: %s locked, retrying (up to %.0fs remaining)",
                    what,
                    remaining,
                )
                warned = True
            else:
                _log.debug(
                    "cache: %s still locked, retrying (%.0fs remaining)",
                    what,
                    remaining,
                )
            time.sleep(_LOCK_POLL_SECONDS)


def _open(path: Path) -> sqlite3.Connection:
    """A cache connection with a busy timeout so concurrent builds wait
    rather than raising `disk I/O error` (T-0029: two agents building the
    same worktree cache collided; sqlite's default is no wait at all).

    T-0245: the malmberg pilot reported concurrent frob processes on /mnt/c
    stalling in D-state with no lock feedback -- a silent 30s blind wait is
    indistinguishable from a hang. Connecting in short polls instead of one
    flat `timeout=30.0` call lets us log a visible "waiting on cache lock"
    line the first time a poll actually blocks, while keeping the same
    30s overall budget.
    """
    deadline = time.monotonic() + _LOCK_TOTAL_TIMEOUT_SECONDS
    warned = False
    while True:
        try:
            conn = sqlite3.connect(str(path), timeout=_LOCK_POLL_SECONDS)
            break
        except sqlite3.OperationalError as exc:
            remaining = deadline - time.monotonic()
            if "locked" not in str(exc).lower() or remaining <= 0:
                raise
            if not warned:
                _log.warning(
                    "cache: waiting on lock at %s (another frob process is "
                    "writing the cache; up to %.0fs)",
                    path,
                    _LOCK_TOTAL_TIMEOUT_SECONDS,
                )
                warned = True
            else:
                _log.debug("cache: still waiting on lock at %s", path)
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
    """Ensure the schema is current; wipe and rebuild on a version mismatch.

    A no-op when `existing` already matches `_SCHEMA_VERSION` (T-0232): the
    common case, hit on every `connect()` call, has no schema work to do at
    all, so skip re-running `CREATE TABLE IF NOT EXISTS` for it rather than
    re-executing statements whose only possible effect on an up-to-date db
    is wasted work. See `connect_readonly` (T-0232) for the actual .frob
    db contention fix -- callers that only ever read (e.g. `load_graph`)
    now use a connection that cannot request sqlite's write lock at all,
    instead of relying on this DDL being a no-op to stay out of a
    concurrent writer's way.
    """
    if existing == _SCHEMA_VERSION:
        return
    _log.info(
        "cache.connect: schema %s -> %s at %s, rebuilding",
        existing,
        _SCHEMA_VERSION,
        path,
    )
    for table in ("meta", "files", "symbols", "edges", "malformed", "parsed_artifacts"):
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.executescript(_SCHEMA)
    conn.execute(
        "INSERT INTO meta (key, value) VALUES ('schema_version', ?)",
        (str(_SCHEMA_VERSION),),
    )
    conn.commit()


# frob:ticket T-0243
def _check_fingerprint(conn: sqlite3.Connection, path: Path) -> None:
    """Invalidate all derived rows (keep schema) if the stored fingerprint
    (frob version + grammar/parser package versions) does not match the
    running process's fingerprint (T-0243).

    A cache built under an older frob/tree-sitter version can parse the
    same source bytes to a different symbol/edge set; the schema-version
    check alone does not catch this because the table shape hasn't
    changed, only the parsed content would be wrong. This treats every
    cached file as a miss (deletes `files`/`symbols`/`edges`/`malformed`
    rows) so `build_graph` reparses everything on the next incremental
    build, exactly as if the cache were empty.
    """
    current = _compute_fingerprint()
    cur = conn.execute("SELECT value FROM meta WHERE key = 'fingerprint'")
    row = cur.fetchone()
    stored = row[0] if row is not None else None
    if stored == current:
        return
    _log.info(
        "cache.connect: fingerprint %r -> %r at %s, invalidating cached rows",
        stored,
        current,
        path,
    )
    for table in ("files", "symbols", "edges", "malformed", "parsed_artifacts"):
        conn.execute(f"DELETE FROM {table}")
    # Also drop 'root', mirroring the schema-version mismatch path: this
    # makes `load_graph` see "never been built" (CacheCorrupt) rather than
    # silently returning an empty-but-Ok snapshot for a cache whose rows
    # were just invalidated out from under it.
    conn.execute("DELETE FROM meta WHERE key = 'root'")
    conn.execute(
        "INSERT INTO meta (key, value) VALUES ('fingerprint', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (current,),
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


def _is_concurrent_meta_key_race(exc: sqlite3.IntegrityError) -> bool:
    """True iff `exc` is the T-1416 "two processes migrated at once" signature.

    A UNIQUE-constraint violation specifically on `meta.key` during schema
    application means a concurrent process's own migration INSERT won the
    race, not that the file is corrupt -- narrow enough that any OTHER
    IntegrityError (a real constraint violation, or a UNIQUE hit on some
    other column) still falls through to the recreate path.
    """
    msg = str(exc).lower()
    return "unique constraint" in msg and "meta.key" in msg


def _recreate_and_reapply(
    conn: sqlite3.Connection, path: Path, exc: Exception
) -> sqlite3.Connection:
    """Delete-and-recreate `path`, then apply a fresh schema (T-0141 recovery)."""
    _log.warning(
        "cache.connect: %s failed schema application, recreating: %s", path, exc
    )
    conn = _recreate(conn, path)
    _apply_schema(conn, None, path)
    return conn


def _poll_and_reread(
    conn: sqlite3.Connection,
    path: Path,
    existing: int | None,
    deadline: float,
    why: str,
) -> tuple[sqlite3.Connection, int | None]:
    """Sleep one poll interval, then re-read the schema version (T-1239/T-1416).

    Raises the caller's original exception (via bare `raise`) if `deadline`
    has already passed -- a contending process that never finishes is a
    real timeout, not something to poll on forever.
    """
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise
    _log.warning(
        "cache.connect: %s %s, retrying (up to %.0fs remaining)",
        path,
        why,
        remaining,
    )
    time.sleep(_LOCK_POLL_SECONDS)
    return _read_schema_version(conn, path)


# frob:ticket T-0141
# frob:ticket T-1239
# frob:ticket T-1416
def _apply_schema_with_recovery(
    conn: sqlite3.Connection, existing: int | None, path: Path
) -> sqlite3.Connection:
    """Apply the schema; retry through concurrency races, recreate on real corruption.

    `_read_schema_version`'s own "is this even sqlite" probe can pass on a
    file that has a corrupted table page (T-0141); the DDL here is what
    actually reads those pages, so it is the final place corruption
    surfaces. Two known concurrency symptoms masquerade as `DatabaseError`
    (both OperationalError and IntegrityError subclass it) and must NOT
    recreate a cache another process is mid-write on: a lock-timeout
    `OperationalError` (T-1239, a concurrent process's own migration DDL
    still in flight) and a `meta.key` UNIQUE-constraint `IntegrityError`
    (T-1416, two processes' migration INSERTs racing). Both poll and
    re-read the stored schema version instead -- a no-op if the contender
    already finished, a retry of the DDL otherwise. Every other
    `DatabaseError` still recreates once, and that retry's own failure
    still propagates uncaught.
    """
    deadline = time.monotonic() + _LOCK_TOTAL_TIMEOUT_SECONDS
    while True:
        try:
            _apply_schema(conn, existing, path)
            return conn
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower():
                raise
            conn, existing = _poll_and_reread(
                conn, path, existing, deadline, "locked during schema application"
            )
        except sqlite3.IntegrityError as exc:
            if not _is_concurrent_meta_key_race(exc):
                return _recreate_and_reapply(conn, path, exc)
            conn, existing = _poll_and_reread(
                conn,
                path,
                existing,
                deadline,
                "hit a concurrent schema-migration race (UNIQUE on meta.key)",
            )
        except sqlite3.DatabaseError as exc:
            return _recreate_and_reapply(conn, path, exc)


# frob:invariant INV-003
# invariant spec: [INV-003](invariants/INV-003.md)
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
    conn = _apply_schema_with_recovery(conn, existing, path)
    _check_fingerprint(conn, path)
    return conn


# frob:ticket T-0232
# frob:doc docs/modules/graph.md#cache
# frob:tests tests/test_graph.py::TestCacheModule.test_connect_readonly_rejects_writes_no_lock_contention  # noqa: E501
def connect_readonly(path: Path) -> sqlite3.Connection:
    """A connection that can never take sqlite's write lock -- for callers
    (`load_graph`, and any gate that only reads the snapshot) that must
    never contend with a concurrent writer's build (T-0232: multiple frob
    processes racing over the same `.frob/cache.db`, the multi-agent-loop
    scenario).

    `connect()` self-heals a missing/stale/corrupt cache by writing to it,
    which is right for a builder but wrong for a reader: a reader has no
    business taking the single writer slot just to `SELECT`, and doing so
    is exactly what serializes unrelated `frob` invocations behind each
    other's cache writes. Opened via sqlite's `mode=ro` URI so any stray
    write attempt raises immediately (`OperationalError: attempt to write
    a readonly database`) instead of silently blocking on `busy_timeout`
    -- a bug that would otherwise reintroduce this contention.

    Raises `sqlite3.OperationalError` if `path` does not exist; callers
    must check existence first (`load_graph` already does).
    """
    uri = f"file:{path}?mode=ro"
    conn = _with_lock_retry(
        lambda: sqlite3.connect(uri, uri=True, timeout=30.0),
        what=f"connect_readonly({path})",
    )
    conn.execute("PRAGMA query_only = ON")
    return conn


# frob:doc docs/modules/graph.md#cache
# frob:ticket T-1423
def set_root(conn: sqlite3.Connection, root: str) -> None:
    """Record the snapshot's repo root (used by `load_graph`).

    Retries through a contended lock (T-1423, `_with_lock_retry`) rather
    than raising a bare `sqlite3.OperationalError`; the upsert is
    idempotent under retry.
    """
    _with_lock_retry(
        lambda: conn.execute(
            "INSERT INTO meta (key, value) VALUES ('root', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (root,),
        ),
        what="set_root",
    )


# frob:doc docs/modules/graph.md#cache
def get_root(conn: sqlite3.Connection) -> str | None:
    """The stored repo root, if any snapshot has ever been saved."""
    cur = conn.execute("SELECT value FROM meta WHERE key = 'root'")
    row = cur.fetchone()
    return row[0] if row is not None else None


# frob:ticket T-0600
# frob:tests tests/test_graph.py::TestCacheModule.test_store_and_load_file_data_roundtrip  # noqa: E501
def _get_file_hash(conn: sqlite3.Connection, file_path: str) -> str | None:
    """The cached content hash for `file_path`, or `None` if never stored.

    Private (T-0600): a low-level cache accessor with no consumer outside
    this module's own test coverage -- `frob.graph.__init__`'s incremental
    rebuild path reads staleness via `get_file_meta`, never this directly."""
    cur = conn.execute("SELECT content_hash FROM files WHERE path = ?", (file_path,))
    row = cur.fetchone()
    return row[0] if row is not None else None


# frob:ticket T-0245
# frob:doc docs/modules/graph.md#cache
def get_file_meta(
    conn: sqlite3.Connection, file_path: str
) -> tuple[str, int, int] | None:
    """`(content_hash, mtime_ns, size)` for `file_path`, or `None` if never stored.

    The stat pair lets callers skip a full content read when the file's
    on-disk (mtime_ns, size) has not moved since the last build (T-0245) --
    a single `os.stat` syscall instead of open+read+close per file.
    """
    cur = conn.execute(
        "SELECT content_hash, mtime_ns, size FROM files WHERE path = ?", (file_path,)
    )
    row = cur.fetchone()
    return (row[0], row[1], row[2]) if row is not None else None


# frob:ticket T-0245
# frob:ticket T-1423
# frob:doc docs/modules/graph.md#cache
def touch_file_stat(
    conn: sqlite3.Connection, file_path: str, *, mtime_ns: int, size: int
) -> None:
    """Update only the stored (mtime_ns, size) for `file_path` (content unchanged).

    Used when a file's mtime moved (e.g. a re-checkout or `touch`) but its
    content hash did not: cheaper than a full `store_file_data` re-insert of
    symbols/edges/malformed, which are already correct (T-0245). Retries
    through a contended lock (T-1423, `_with_lock_retry`) instead of
    raising; the update is idempotent under retry.
    """
    _with_lock_retry(
        lambda: conn.execute(
            "UPDATE files SET mtime_ns = ?, size = ? WHERE path = ?",
            (mtime_ns, size, file_path),
        ),
        what=f"touch_file_stat({file_path})",
    )


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
# frob:ticket T-1423
def store_file_data(
    conn: sqlite3.Connection,
    *,
    file_path: str,
    content_hash: str,
    mtime_ns: int = 0,
    size: int = 0,
    symbols: tuple[SymbolRecord, ...],
    edges: tuple[Edge, ...],
    malformed: tuple[MalformedDirective, ...],
) -> None:
    """Replace all rows derived from `file_path` (delete-then-insert, one
    transaction step -- caller commits; see T-0402 G12: this never calls
    `conn.commit()` itself, only `_finalize_build` does, once, for the
    whole build).

    `mtime_ns`/`size` (T-0245) are the stat pair a later build can trust
    instead of re-reading the file's bytes; default to 0 for callers (tests,
    mainly) that only care about content-hash behavior.

    Retries through a contended lock (T-1423, `_with_lock_retry`) instead
    of raising a bare `sqlite3.OperationalError`: the whole delete-then-
    insert body is idempotent under retry (a partial attempt just gets
    redone identically), so retrying the entire function on a mid-write
    lock is safe.
    """

    def _op() -> None:
        conn.execute(
            "INSERT INTO files (path, content_hash, mtime_ns, size) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(path) DO UPDATE SET "
            "content_hash = excluded.content_hash, "
            "mtime_ns = excluded.mtime_ns, "
            "size = excluded.size",
            (file_path, content_hash, mtime_ns, size),
        )
        _store_symbols(conn, file_path, symbols)
        _store_edges(conn, file_path, edges)
        _store_malformed(conn, file_path, malformed)

    _with_lock_retry(_op, what=f"store_file_data({file_path})")


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
# frob:ticket T-1464
# frob:tests tests/unit/test_graph_cache.py::TestParsedArtifacts.test_store_then_load_round_trips  # noqa: E501
def store_parsed_artifact(
    conn: sqlite3.Connection, *, content_hash: str, fingerprint: str, payload: str
) -> None:
    """Persist one `frob.lang.ParsedFile`'s serialized `payload` (its own
    `model_dump_json()`), keyed by `(content_hash, fingerprint)` (T-1464).

    Content-addressed like `frob.dup._cache`'s `fingerprints` table: the
    same `(content_hash, fingerprint)` pair always derives to the same
    `ParsedFile` (parsing is a pure function of source bytes + frob/grammar
    version), so there is no staleness flag to get wrong, only a key to
    look up. `fingerprint` is `_compute_fingerprint()`'s own string (frob +
    tree-sitter grammar package versions) folded into the primary key
    rather than relying solely on `_check_fingerprint`'s wholesale-delete
    sweep -- a row written under an old fingerprint simply never matches a
    new lookup, so a race between a worker's read and a concurrent
    fingerprint-bump delete can never serve a wrong-version payload.
    Retries through a contended lock (T-1423) exactly like
    `store_file_data`: the insert is idempotent under retry.
    """

    def _op() -> None:
        conn.execute(
            "INSERT INTO parsed_artifacts (content_hash, fingerprint, payload) "
            "VALUES (?, ?, ?) "
            "ON CONFLICT(content_hash, fingerprint) DO UPDATE SET "
            "payload = excluded.payload",
            (content_hash, fingerprint, payload),
        )
        conn.commit()

    _with_lock_retry(_op, what=f"store_parsed_artifact({content_hash[:12]})")


# frob:doc docs/modules/graph.md#cache
# frob:ticket T-1464
# frob:tests tests/unit/test_graph_cache.py::TestParsedArtifacts.test_load_miss_returns_none  # noqa: E501
def load_parsed_artifact(
    conn: sqlite3.Connection, *, content_hash: str, fingerprint: str
) -> str | None:
    """The serialized `ParsedFile` payload for `(content_hash, fingerprint)`,
    or `None` on a cache miss (T-1464) -- the read side of
    `store_parsed_artifact`, letting `frob.lang` skip a full tree-sitter
    parse + `extract()` walk when a `ProcessPoolExecutor` sibling worker
    (or an earlier run) already derived the same file's artifacts."""
    row = conn.execute(
        "SELECT payload FROM parsed_artifacts "
        "WHERE content_hash = ? AND fingerprint = ?",
        (content_hash, fingerprint),
    ).fetchone()
    return row[0] if row is not None else None


# frob:doc docs/modules/graph.md#cache
# frob:ticket T-1214
# frob:waive AFFECT001 reason="T-1214 only batches load_all's internal query \
# shape (3 whole-table SELECTs instead of 3-per-file); its documented contract \
# in docs/modules/graph.md#cache -- reassembles the full GraphSnapshot from \
# every row currently in the db -- is unchanged, so the doc anchor needs no \
# prose update. Touching docs/modules/graph.md itself would pull the whole \
# graph module's scope-closure obligations into this ticket's narrow scope, \
# which is out of proportion to a query-shape-only perf change."  # noqa: E501
def load_all(
    conn: sqlite3.Connection, *, stats: BuildStats | None = None
) -> GraphSnapshot:
    """Reassemble the full `GraphSnapshot` from every row currently in the db.

    T-1214: does 3 whole-table `SELECT`s total (symbols, edges, malformed),
    each ordered by `path`, instead of `load_file_data`'s 3-queries-PER-FILE
    shape (5595 `execute` calls for ~1865 files, measured pre-fix) --
    `attrs == '{}'` (the common no-attrs case) also skips `json.loads`
    entirely rather than parsing an empty object every time. `load_file_data`
    itself is unchanged and still used by the incremental single-file cache-
    hit path (`frob.graph.__init__`); this rewrite only touches the
    whole-snapshot path, which never needs a per-file round trip."""
    root = get_root(conn) or ""
    file_hashes = {
        path: content_hash
        for path, content_hash in conn.execute("SELECT path, content_hash FROM files")
    }
    symbols: dict[str, SymbolRecord] = {}
    for row in conn.execute(
        "SELECT symref, path, qualname, kind, public, span_start, span_end, "
        "digest_sig, digest_body, digest_doc FROM symbols ORDER BY path"
    ):
        rec = _row_to_symbol(row)
        symbols[rec.symref] = rec
    edges: list[Edge] = [
        Edge(
            src=src,
            kind=EdgeKind(kind),
            target=target,
            origin=origin,
            attrs={} if attrs == "{}" else json.loads(attrs),
        )
        for src, kind, target, origin, attrs in conn.execute(
            "SELECT src, kind, target, origin, attrs FROM edges ORDER BY file"
        )
    ]
    malformed: list[MalformedDirective] = [
        MalformedDirective(file=file_path, line=line, reason=reason)
        for file_path, line, reason in conn.execute(
            "SELECT file, line, reason FROM malformed ORDER BY file"
        )
    ]
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
    "CacheLocked",
    "connect",
    "get_file_meta",
    "get_root",
    "load_all",
    "load_file_data",
    "set_root",
    "store_file_data",
    "touch_file_stat",
]

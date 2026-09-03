"""SQLite-backed snapshot cache at `.frob/cache.db` (docs/modules/graph.md, "Cache").

Everything stored here is derived and rebuildable from the tracked source
tree -- safe to delete at any time. Rows are keyed per source/doc file so
`build_graph` can incrementally replace only the files whose content hash
changed, and `load_graph` can read the whole snapshot back without
re-parsing anything.
"""

# frob:waive LARGE001 reason="T-1651-grade: one SQLite-backed persistence concern for \
# GraphSnapshot (module docstring: 'everything stored here is derived and rebuildable \
# from the tracked source tree'), covering schema, incremental per-file hash-keyed \
# writes, and the full-snapshot read-back load_graph depends on. Splitting schema/ \
# migration from the read/write paths that depend on the exact same row shape would \
# cut a single atomic-write discipline in half, the same 'cut a real edge' outcome \
# T-1651 already ruled out for this repo's other persistence-layer files (frob.tickets \
# ._store's own LARGE001 waiver draws the identical distinction)."

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
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
from frob.lang._models import GRAMMAR_FINGERPRINT_PACKAGES, SymbolKind
from frob.logging import get_logger
from frob.process._lock import (
    lock_backend_available,
    portable_flock_acquire,
    portable_flock_release,
)

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
# frob:ticket T-3433
# PORT001-IDENT reviewed and DECIDED as a legitimate self-reference, not a
# portability bug: this cache belongs to frob's OWN analyzer, not to
# whatever repo it happens to be scanning. The fingerprint's job is "would
# a version bump of a package that determines parse OUTPUT silently make
# this cache stale" -- and the packages that determine THIS cache's parse
# output are always frob's own extraction/digest code and strata-core's
# native `.strata` grammar, regardless of which repo is under analysis. A
# consumer repo's own dependencies play no part in how frob.graph parses
# that repo's source, so there is nothing to "resolve from the scanned
# repo's own declared dependencies" here -- unlike PORT001-PATH's silent-
# pass/false-fire class, retargeting this to be config-driven would not
# fix a real cross-repo bug, only replace two names that are correct for
# every host repo with a lookup that could return the wrong ones.
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

# frob:ticket T-3654
_LOCK_BACKOFF_BASE_SECONDS = 0.05
_LOCK_BACKOFF_CAP_SECONDS = _LOCK_POLL_SECONDS


# frob:ticket T-3654
# frob:tests tests/unit/test_graph_cache.py::TestLockBackoff.test_backoff_doubles_up_to_the_cap  # noqa: E501
# frob:tests tests/unit/test_graph_cache.py::TestLockBackoff.test_backoff_never_exceeds_remaining_budget  # noqa: E501
def _lock_backoff_seconds(attempt: int, *, remaining: float) -> float:
    """The delay (seconds) before lock-retry attempt number `attempt`
    (0-indexed) -- exponential backoff starting at
    `_LOCK_BACKOFF_BASE_SECONDS`, doubling each attempt, capped at the
    former fixed poll interval (`_LOCK_BACKOFF_CAP_SECONDS`), and never
    longer than `remaining` time left on the caller's deadline (T-3654).

    Round 5 of the cache lock-contention saga: T-3644 retired WAL and
    widened lock-error matching to cover sqlite's `readonly database`
    shape, but run 33513484322's darwin sibling still exhausted the
    retry budget and surfaced `CacheLocked`. The prior retry loops slept
    a FIXED `_LOCK_POLL_SECONDS` (2.0s) between polls against the 30s
    deadline -- effectively ~15 evenly-spaced attempts, a small FIXED
    COUNT in practice, not backoff. Under darwin's slower filesystem
    contention a narrow lock window can fall between two of those widely
    spaced polls. Starting with a much shorter delay and doubling up to
    the same 2.0s cap keeps the total attempts made within the SAME
    30s budget far higher early on (when contention is most likely to be
    brief), while never sleeping past the caller's own remaining
    deadline (so the final hard error still fires promptly once the
    budget is truly exhausted)."""
    delay = _LOCK_BACKOFF_BASE_SECONDS * (2**attempt)
    return max(0.0, min(delay, _LOCK_BACKOFF_CAP_SECONDS, remaining))


# frob:ticket T-3644
# frob:tests tests/unit/test_graph_build_lock.py::TestBuildGraphLockScope.test_two_processes_never_commit_to_the_same_cache_concurrently  # noqa: E501
# frob:tests tests/test_graph_lock.py::TestCacheLockRetry.test_non_locked_operational_error_is_not_retried  # noqa: E501
def _is_transient_lock_error(exc: sqlite3.OperationalError) -> bool:
    """True iff `exc` is contention this module's lock-retry loops should
    poll past rather than let escape (T-3644).

    Under WAL (rounds 1-3 of this cache's atomicity work), the same-file
    contention this file's retry loops exist to absorb (T-1423) always
    surfaced as sqlite's ordinary `database is locked` (SQLITE_BUSY).
    Retiring WAL for TRUNCATE journal mode (T-3644, to structurally
    eliminate the WAL `-shm`-mmap SIGBUS class) means that SAME
    contention can instead surface as `attempt to write a readonly
    database` (SQLITE_READONLY) -- a documented SQLite/POSIX caveat: a
    rollback-journal connection's locking uses `fcntl` advisory locks,
    which are scoped per (process, inode) rather than per file
    descriptor, so two `sqlite3.Connection` objects on the same file
    within one process (exactly `test_two_processes_never_commit_to_
    the_same_cache_concurrently`'s same-process two-thread shape) can
    observe each other's locks as this shape instead of `locked`. Both
    strings name the identical transient condition this module already
    retries -- an op retried here is already required to be idempotent
    under retry (`_with_lock_retry`'s own docstring), so treating the two
    shapes alike is safe."""
    msg = str(exc).lower()
    return "locked" in msg or "readonly database" in msg


# frob:ticket T-3669
# frob:tests \
# tests/unit/test_graph_cache.py::TestHandleIdentity.test_readonly_database_is_classifi\
# ed_as_a_handle_fault
def _is_readonly_handle_error(exc: sqlite3.Error) -> bool:
    """True iff `exc` is sqlite's `attempt to write a readonly database`
    (T-3669) -- the shape a WRITE through a handle bound to a replaced-away
    inode takes on darwin.

    `_is_transient_lock_error` also matches this string, deliberately
    (T-3644: the same-process fcntl-aliasing contention it describes is
    genuinely transient and genuinely retryable). But when the caller has a
    canonical path to reopen at, this shape must be treated as a HANDLE
    fault first: retrying it on the same connection is what made five
    rounds of retry budget useless on darwin (run 33529632605 ended with
    `CacheLocked('attempt to write a readonly database')` after the full
    deadline). Callers that can reopen check this predicate before falling
    back to the transient-lock reading."""
    return "readonly database" in str(exc).lower()


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
# frob:ticket T-3669
def _with_lock_retry(op, *, what: str, retry_readonly: bool = True):  # noqa: ANN001, ANN202
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
    attempt = 0
    while True:
        try:
            return op()
        except sqlite3.OperationalError as exc:
            if not _is_transient_lock_error(exc):
                raise
            # T-3669: a caller that owns an outer reopen layer passes
            # retry_readonly=False so the readonly-database shape escapes
            # IMMEDIATELY to that layer, which closes the handle and
            # reopens at the canonical path. Absorbing it here instead is
            # what burned the entire 30s budget on a connection bound to a
            # replaced-away inode, five rounds running.
            if not retry_readonly and _is_readonly_handle_error(exc):
                raise
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _log.error(
                    "cache: %s still locked after %.0fs, giving up",
                    what,
                    _LOCK_TOTAL_TIMEOUT_SECONDS,
                )
                raise CacheLocked(str(exc)) from exc
            # T-3654: WARNING every retry (not just the first) -- keeping
            # the whole retry sequence loud, per this ticket's acceptance
            # criterion; a WARN-level line per attempt is cheap next to a
            # genuine lock exhaustion going silently unnoticed.
            _log.warning(
                "cache: %s locked, retrying (up to %.0fs remaining)",
                what,
                remaining,
            )
            time.sleep(_lock_backoff_seconds(attempt, remaining=remaining))
            attempt += 1


# frob:ticket T-3654
# frob:tests tests/unit/test_graph_cache.py::TestLockBackoff.test_backoff_doubles_up_to_the_cap  # noqa: E501
def _connect_with_backoff(path: Path) -> sqlite3.Connection:
    """`sqlite3.connect(path)`, retrying a transient lock with exponential
    backoff against `_LOCK_TOTAL_TIMEOUT_SECONDS` (T-3654, split out of
    `_open` to keep it under ARCH001's size threshold).

    `sqlite3.connect`'s own `timeout=` argument IS this loop's poll
    interval (it busy-waits internally on SQLITE_BUSY), so backoff here
    means shrinking/growing that per-attempt timeout across retries
    rather than adding an extra explicit sleep between calls -- see
    `_lock_backoff_seconds`'s own docstring for why (darwin's slower fs
    contention, run 33513484322, exhausted the prior fixed-interval
    budget)."""
    deadline = time.monotonic() + _LOCK_TOTAL_TIMEOUT_SECONDS
    attempt = 0
    while True:
        remaining = deadline - time.monotonic()
        per_attempt_timeout = _lock_backoff_seconds(
            attempt, remaining=max(remaining, 0.0)
        )
        try:
            return sqlite3.connect(str(path), timeout=per_attempt_timeout)
        except sqlite3.OperationalError as exc:
            remaining = deadline - time.monotonic()
            if not _is_transient_lock_error(exc) or remaining <= 0:
                raise
            _log.warning(
                "cache: waiting on lock at %s (another frob process is "
                "writing the cache; up to %.0fs remaining)",
                path,
                remaining,
            )
            attempt += 1


# frob:ticket T-3669
# Round 6 of the cache-atomicity saga. Every prior round (T-3607 quarantine
# -rename, T-3623 schema-complete-before-visible, T-3632 atomic temp-build
# + double-checked locking, T-3634 disk-I/O reconnect, T-3644 WAL
# retirement, T-3654 deadline backoff) treated the symptom on the SAME
# connection object. The defect they all missed is a HANDLE LIFECYCLE one:
# `os.replace` publishes a NEW inode at the canonical path, and a
# `sqlite3.Connection` opened before that replace stays bound to the OLD,
# now-unlinked (or quarantined) inode forever. On darwin such a handle
# reads the pre-replace state indefinitely -- so a sibling keeps seeing
# `fingerprint None`, re-invalidates, republishes, and the two processes
# thrash rebuilds over each other (~20 cycles, run 33529632605) -- and a
# WRITE through it surfaces as `attempt to write a readonly database`,
# which every retry loop then retried ON THE SAME DOOMED HANDLE. The fix
# is to make "is my handle still bound to the file at the canonical path?"
# a cheap, explicit check taken BEFORE every fingerprint read and before
# every retried operation, and to make the readonly shape reopen rather
# than retry. `id(conn)` keys this map because `sqlite3.Connection`
# supports neither weak references nor attribute assignment; entries are
# dropped in `_close_conn`, and an id collision is harmless either way (a
# stale entry that differs from the live inode only causes one extra
# correct reopen; one that matches it describes the same file anyway).
_CONN_FILE_IDENTITY: dict[int, tuple[int, int]] = {}
_OPEN_IDENTITY_ATTEMPTS = 3
_CONN_IDENTITY_MAX_ENTRIES = 512


# frob:ticket T-3669
# frob:tests \
# tests/unit/test_graph_cache.py::TestHandleIdentity.test_identity_changes_after_os_rep\
# lace
def _file_identity(path: Path) -> tuple[int, int] | None:
    """The `(st_dev, st_ino)` pair naming the file currently at `path`, or
    `None` if it does not exist (T-3669) -- the value a cache connection's
    recorded identity is compared against to detect that a sibling's
    `os.replace` published a new inode under a live handle."""
    try:
        st = path.stat()
    except OSError:
        return None
    return (st.st_dev, st.st_ino)


# frob:ticket T-3669
def _close_conn(conn: sqlite3.Connection) -> None:
    """Close `conn`, swallowing an already-broken handle's close error, and
    forget its recorded file identity (T-3669) so the `id()`-keyed
    `_CONN_FILE_IDENTITY` map cannot grow without bound or be misread by a
    later connection that happens to reuse the same `id()`."""
    _CONN_FILE_IDENTITY.pop(id(conn), None)
    try:
        conn.close()
    except sqlite3.Error:
        pass


# frob:ticket T-3669
# frob:tests \
# tests/unit/test_graph_cache.py::TestHandleIdentity.test_store_file_data_after_a_repla\
# ce_lands_on_the_live_file
def _reopen_without_closing(
    conn: sqlite3.Connection, path: Path
) -> sqlite3.Connection | None:
    """A FRESH connection at `path` if `conn` is bound to a file that has
    since been replaced there, else `None` (T-3669).

    The non-destructive half of `_reopen_if_replaced`, for the one caller
    that does not own the connection it was handed
    (`_run_with_stale_reconnect`, reached from `store_file_data` and the
    other module-level read/write helpers): closing a caller's connection
    out from under it turns the caller's next ordinary use into a
    `ProgrammingError`, so a stranded handle is worked AROUND here rather
    than invalidated."""
    recorded = _CONN_FILE_IDENTITY.get(id(conn))
    if recorded is None:
        return None
    current = _file_identity(path)
    if current is None or current == recorded:
        return None
    _log.warning(
        "cache: operating through a fresh connection at %s -- the caller's "
        "handle is bound to a replaced-away file (inode %s, now %s)",
        path,
        recorded,
        current,
    )
    return _open(path)


# frob:ticket T-3669
# frob:tests \
# tests/unit/test_graph_cache.py::TestHandleIdentity.test_replaced_away_handle_is_reope\
# ned_before_the_next_read
# frob:tests \
# tests/unit/test_graph_cache.py::TestHandleIdentity.test_live_handle_is_not_reopened
def _reopen_if_replaced(conn: sqlite3.Connection, path: Path) -> sqlite3.Connection:
    """Return `conn` if it is still bound to the file now at `path`;
    otherwise close it and return a FRESH connection opened at `path`
    (T-3669).

    This is round 6's whole thesis in one function: a handle whose backing
    inode was replaced out from under it is not "temporarily busy", it is
    permanently looking at dead state, and no amount of retrying the
    operation on it can ever succeed. Called before each fingerprint read
    and before each retried cache operation, it converts the previously
    unbounded rebuild-thrash and readonly-database loops into a single
    reopen at the canonical path -- which, by construction of
    `_build_schema_complete_db` + `os.replace`, always holds the winner's
    schema-complete db. Returns `conn` unchanged when either identity is
    unknown (an unstattable path, or a connection this module did not open
    through `_open`): reopening on no evidence would defeat T-0232's
    pinned "a second connection must not queue behind a held write"
    invariant for the ordinary, non-racing case.
    """
    recorded = _CONN_FILE_IDENTITY.get(id(conn))
    if recorded is None:
        return conn
    current = _file_identity(path)
    if current is None or current == recorded:
        return conn
    _log.warning(
        "cache: connection at %s is bound to a replaced-away file "
        "(inode %s, now %s) -- closing and reopening at the canonical path",
        path,
        recorded,
        current,
    )
    _close_conn(conn)
    return _open(path)


# frob:ticket T-3669
def _connect_recording_identity(
    path: Path,
) -> tuple[sqlite3.Connection, tuple[int, int] | None]:
    """`_connect_with_backoff(path)` plus the `(st_dev, st_ino)` the opened
    handle is actually bound to (T-3669).

    Stats `path` on both sides of the connect and retries when the two
    disagree: a sibling's `os.replace` landing in exactly that window would
    otherwise make us record the NEW inode for a handle holding the OLD
    one -- an identity that lies in the one direction that matters, since
    `_reopen_if_replaced` would then never reopen it. After
    `_OPEN_IDENTITY_ATTEMPTS` losses the connection is returned with an
    unknown (`None`) identity, which degrades to exactly the pre-T-3669
    behavior rather than looping against a pathologically busy path."""
    for _attempt in range(_OPEN_IDENTITY_ATTEMPTS):
        before = _file_identity(path)
        conn = _connect_with_backoff(path)
        after = _file_identity(path)
        if before is not None and before == after:
            return conn, after
        _close_conn(conn)
    return _connect_with_backoff(path), None


# frob:ticket T-3669
def _open(path: Path) -> sqlite3.Connection:
    """A cache connection with a busy timeout so concurrent builds wait
    rather than raising `disk I/O error` (T-0029: two agents building the
    same worktree cache collided; sqlite's default is no wait at all).

    T-3644 (SIGBUS round 4): journal mode is TRUNCATE, not WAL -- WAL mmaps
    a per-connection `-shm` wal-index, and any cross-process db replace or
    recover racing a live mapping (SQLite's own WAL recovery included) can
    SIGBUS the sibling at the OS level, unreachable by python `except` (a
    fatal signal, not an exception); three prior atomicity-hardening
    rounds (T-3607/T-3623/T-3632/T-3634) still left a worker dying this
    way (run 33491468339). TRUNCATE has no `-shm`, structurally eliminating
    the class, while truncating the journal file in place each transaction
    rather than DELETE mode's create/delete (cheaper, against the "timed
    out under 4 parallel builders" regression rollback-journal mode hit
    before WAL was adopted -- see `_inprocess_write_lock`'s docstring for
    the other half of this fix, the intra-process locking gap TRUNCATE
    reopens). Rounds 1-3's atomic-rebuild machinery is unchanged.

    T-0245: the malmberg pilot reported concurrent frob processes on /mnt/c
    stalling in D-state with no lock feedback -- a silent 30s blind wait is
    indistinguishable from a hang. Connecting in short polls instead of one
    flat `timeout=30.0` call lets us log a visible "waiting on cache lock"
    line the first time a poll actually blocks, while keeping the same
    30s overall budget.
    """
    conn, identity = _connect_recording_identity(path)
    if identity is not None:
        # T-3669: callers close their own connections without going
        # through `_close_conn`, so entries accumulate; this map is a
        # best-effort cache, not a registry, and dropping it wholesale
        # only costs one skipped reopen check per surviving connection.
        if len(_CONN_FILE_IDENTITY) >= _CONN_IDENTITY_MAX_ENTRIES:
            _CONN_FILE_IDENTITY.clear()
        _CONN_FILE_IDENTITY[id(conn)] = identity
    # These pragmas can touch page structure, so on a non-sqlite file they
    # raise here -- swallow it and let connect()'s schema SELECT be the one
    # place that detects corruption and triggers recreate (T-0019/T-0029).
    #
    # T-3644: TRUNCATE, not WAL -- WAL's `-shm` mmap is a structural SIGBUS
    # source under cross-process db replace/recover (unreachable by python
    # `except`); see this function's own T-3644 docstring paragraph and
    # `_inprocess_write_lock`'s docstring for the full rationale.
    try:
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.execute("PRAGMA journal_mode = TRUNCATE")
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


def _apply_schema(
    conn: sqlite3.Connection, existing: int | None, path: Path
) -> sqlite3.Connection:
    """Ensure the schema is current; rebuild atomically on a version mismatch.

    A no-op (returns `conn` unchanged) when `existing` already matches
    `_SCHEMA_VERSION` (T-0232): the common case, hit on every `connect()`
    call, has no schema work to do at all, so skip re-running `CREATE
    TABLE IF NOT EXISTS` for it rather than re-executing statements whose
    only possible effect on an up-to-date db is wasted work. See
    `connect_readonly` (T-0232) for the actual .frob db contention fix --
    callers that only ever read (e.g. `load_graph`) now use a connection
    that cannot request sqlite's write lock at all, instead of relying on
    this DDL being a no-op to stay out of a concurrent writer's way.

    T-3632 (round 2 of T-3623): a real rebuild used to `DROP TABLE` /
    `CREATE TABLE` one statement at a time IN PLACE on `conn`, live at the
    canonical `path` -- each of those statements auto-commits on its own
    (`executescript`/individual DDL statements are not one transaction in
    sqlite3), so a concurrent connector querying `path` mid-sequence could
    observe a window with `meta` dropped but `files` not yet recreated
    (measured as `OperationalError: no such table: files` from a sibling
    process's tight `connect()` loop, run 33472403980). Now this always
    goes through the same build-at-a-temp-path-then-`os.replace` primitive
    `_recreate` uses (`_build_schema_complete_db` / `_quarantine_sidecars`)
    so no connector ever sees a schema mid-rebuild, whether the mismatch
    was found here (first DDL touch) or via `_recreate`'s own corruption
    path.

    Double-checked locking (T-3632 direction 2): the rebuild is
    serialized on `path`'s dedicated rebuild lock, and the FIRST thing
    done under that lock is a fresh re-read of the stored schema version
    -- if a sibling already won the race and published a current-version
    db while this caller was waiting on the lock, this is a no-op (just
    reopen) instead of thrashing a second full rebuild over the winner's
    fresh db.
    """
    if existing == _SCHEMA_VERSION:
        return conn
    return _rebuild_schema_atomically(conn, existing, path)


def _rebuild_schema_atomically(
    conn: sqlite3.Connection, existing: int | None, path: Path
) -> sqlite3.Connection:
    """Do `_apply_schema`'s actual rebuild: serialize on `path`'s rebuild
    lock, double-check under it (a sibling may have already published a
    current-version db while this caller waited), and otherwise publish a
    fresh schema-complete db via the same atomic temp-build-then-`os.
    replace` primitive `_recreate` uses (T-3632, split out of
    `_apply_schema` to keep that function under ARCH001's line
    threshold)."""
    lock_fd = _rebuild_lock_fd(path)
    if lock_fd is not None:
        portable_flock_acquire(lock_fd, exclusive=True, blocking=True)
    try:
        # Double-checked locking (T-3632 direction 2): re-read under the
        # lock before doing any rebuild work -- if a sibling already won
        # the race, this is a no-op reopen instead of a second thrash-
        # inducing rebuild over the winner's fresh db.
        if lock_fd is not None:
            recheck_conn = _open(path)
            try:
                _, recheck_existing = _read_schema_version(recheck_conn, path)
            finally:
                _close_conn(recheck_conn)
            if recheck_existing == _SCHEMA_VERSION:
                _log.debug(
                    "cache.connect: schema already rebuilt to %s at %s by a "
                    "sibling, skipping redundant rebuild",
                    _SCHEMA_VERSION,
                    path,
                )
                _close_conn(conn)
                return _open(path)
        _log.info(
            "cache.connect: schema %s -> %s at %s, rebuilding",
            existing,
            _SCHEMA_VERSION,
            path,
        )
        _close_conn(conn)
        tmp_path = _build_schema_complete_db(path)
        _quarantine_sidecars(path)
        os.replace(tmp_path, path)
        return _open(path)
    finally:
        if lock_fd is not None:
            portable_flock_release(lock_fd)
            os.close(lock_fd)


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
# frob:ticket T-3607
_REBUILD_LOCK_SUFFIX = ".rebuild.lock"
_STALE_SUFFIX_PREFIX = ".stale-"
# T-3607: a quarantined sidecar older than this is assumed to have no live
# reader left mapping it (any sibling holding it open at rebuild time has
# long since finished or crashed) -- swept opportunistically on the next
# rebuild so quarantined files never accumulate forever, without needing a
# separate cleanup job.
_STALE_SWEEP_AGE_SECONDS = 60 * 60


def _rebuild_lock_fd(path: Path) -> int | None:
    """Open (creating if needed) `path`'s dedicated rebuild-serialization
    lock file (T-3607), or `None` if no advisory-lock backend exists on
    this platform -- callers degrade to running the quarantine-swap
    unlocked rather than failing outright (the swap is still far safer
    than the old in-place unlink even without the lock, see `_recreate`'s
    docstring)."""
    if not lock_backend_available():
        return None
    lock_path = path.with_name(path.name + _REBUILD_LOCK_SUFFIX)
    try:
        return os.open(
            str(lock_path), os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0)
        )
    except OSError:
        return None


def _sweep_stale_quarantined_sidecars(path: Path) -> None:
    """Best-effort delete of `path`'s own previously-quarantined `_recreate`
    sidecars (T-3607) older than `_STALE_SWEEP_AGE_SECONDS` -- opportunistic
    hygiene run at the START of every rebuild so quarantined files (never
    unlinked at swap time, precisely because a sibling might still have
    them mapped) do not accumulate forever. Any failure (permission,
    already gone, a concurrent sweeper) is swallowed: this is cleanup, not
    correctness, and must never block or fail the rebuild it runs inside."""
    try:
        candidates = tuple(path.parent.glob(path.name + _STALE_SUFFIX_PREFIX + "*"))
    except OSError:
        return
    now = time.time()
    for candidate in candidates:
        try:
            if now - candidate.stat().st_mtime < _STALE_SWEEP_AGE_SECONDS:
                continue
            candidate.unlink()
        except OSError:
            continue


def _build_schema_complete_db(path: Path) -> Path:
    """Create a brand-new sqlite db with the full schema already applied,
    at a throwaway temp path sitting next to `path` -- publish it into
    place with `os.replace` (T-3623). Returns the temp path.

    Split out from the old single `_create_schema_complete_db` (T-3623
    round 1) so `_recreate` can build this BEFORE quarantining the old
    file: building the schema takes real time, and doing that work while
    `path` still points at the (about to be replaced) old file keeps
    `path` continuously present on disk right up until one atomic rename
    -- rather than absent for the whole build duration, which regressed
    `connect_readonly` callers racing `_recreate` (T-3607's own
    concurrent-reader test) straight into `unable to open database file`.
    """
    tmp_path = path.with_name(f"{path.name}.new-{os.getpid()}-{uuid.uuid4().hex[:8]}")
    conn = sqlite3.connect(str(tmp_path))
    try:
        conn.executescript(_SCHEMA)
        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('schema_version', ?)",
            (str(_SCHEMA_VERSION),),
        )
        conn.commit()
    finally:
        conn.close()
    return tmp_path


def _create_schema_complete_db(path: Path) -> None:
    """Build a brand-new cache db with the full schema already applied at
    a temp path, then atomically `os.replace` it into place at `path`
    (T-3623).

    Used where no old file needs quarantining first (the very first
    `connect()` at a brand-new path, `connect()`'s own doc comment) --
    `_recreate` instead calls `_build_schema_complete_db` directly so it
    can build BEFORE renaming the old file aside (see that function's
    docstring for why the ordering matters).

    Old behavior (pre-T-3623) was to `_open(path)` a fresh, EMPTY sqlite
    file directly at the real path, then apply the schema over that same
    connection in a later step back in `connect()` -- between those two
    moments, `path` was visible on disk as a valid-but-tableless sqlite
    file. A concurrent connection (another process's own `connect()`, or
    `connect_readonly`, which has no rebuild-on-miss handling of its own)
    that opened `path` inside that window saw a file with no `meta` table
    and raised `OperationalError: no such table: meta` straight out of
    whatever query it ran first (`_check_fingerprint`'s SELECT at line
    ~377 was the one this surfaced through in run 33466891764). Doing all
    schema-creation work at a throwaway temp path first and only exposing
    it at the real path via one atomic rename closes that window: any
    connection that can see `path` at all sees a schema-complete db, by
    construction, never a half-built one.
    """
    tmp_path = _build_schema_complete_db(path)
    os.replace(tmp_path, path)


def _recreate(conn: sqlite3.Connection, path: Path) -> sqlite3.Connection:
    """Close `conn`, quarantine `path` and its WAL/SHM sidecars aside by
    RENAME, then reopen a fresh db at `path`.

    Shared by both corruption-detection points in `connect` (T-0141): a
    cache.db whose bytes cannot be trusted is derived state, so the only
    honest recovery is delete-and-recreate, never DDL over the bad handle.

    T-3607: this used to `unlink()` `path` and its `-wal`/`-shm` sidecars
    in place, then reopen at the same path -- a SIGBUS-in-production
    incident (a sibling `ProcessPoolExecutor` worker's already-open,
    process-lifetime `_artifact_cache_connection` crashed on an ordinary
    `SELECT` in `load_parsed_artifact` while this function's unlink+
    recreate ran concurrently in another worker) traced the fault to that
    sibling's WAL-index `-shm` mapping being invalidated out from under
    it by the in-place delete-and-recreate-at-the-same-path sequence.

    The fix: never delete-then-recreate AT THE SAME PATH while another
    process might have `path`'s sidecars memory-mapped. Instead, RENAME
    the (possibly bad) db and its sidecars aside to a quarantined sibling
    name -- a rename does not invalidate any process's already-open fd or
    active mmap (those stay bound to the renamed file's inode exactly as
    before) -- and only THEN open a brand-new db at the original `path`
    (a fresh `open(..., O_CREAT)` there always allocates a new inode, so
    it can never collide with what a sibling still has mapped). The
    quarantined files are deliberately NOT unlinked immediately -- a
    sibling might still be attached to them -- `_sweep_stale_quarantined_
    sidecars` reclaims them later, once they are old enough that no
    reader from this rebuild's moment could plausibly still be using
    them.

    The whole quarantine-and-reopen sequence is serialized by an advisory
    exclusive flock on a dedicated `<path>.rebuild.lock` file (falling
    back to running unlocked if no lock backend exists on this platform,
    T-3607/`_rebuild_lock_fd`) so two processes racing to recover the
    same corrupt db never quarantine each other's freshly-created
    replacement.
    """
    _close_conn(conn)
    lock_fd = _rebuild_lock_fd(path)
    if lock_fd is not None:
        portable_flock_acquire(lock_fd, exclusive=True, blocking=True)
    try:
        _sweep_stale_quarantined_sidecars(path)
        # T-3623: build the replacement's schema at a temp path FIRST,
        # while the OLD file still sits at `path` -- see
        # _build_schema_complete_db's docstring for why the ordering
        # matters (T-3607's own concurrent-reader test caught the
        # regression when this was tried the other way around).
        tmp_path = _build_schema_complete_db(path)
        _quarantine_sidecars(path)
        os.replace(tmp_path, path)
        return _open(path)
    finally:
        if lock_fd is not None:
            portable_flock_release(lock_fd)
            os.close(lock_fd)


def _quarantine_sidecars(path: Path) -> None:
    """Rename `path`'s db/`-wal`/`-shm` files aside to a quarantined
    sibling name (T-3607), best-effort -- shared by `_recreate` so the
    rename-not-unlink step has one home distinct from the schema-build
    step it now runs alongside (T-3623 split this out of `_recreate`
    itself to keep that function under ARCH001's complexity threshold)."""
    suffix = f"{_STALE_SUFFIX_PREFIX}{os.getpid()}-{uuid.uuid4().hex[:8]}"
    for name in (path.name, path.name + "-wal", path.name + "-shm"):
        src = path.with_name(name)
        try:
            if src.exists():
                src.rename(src.with_name(name + suffix))
        except OSError:
            # T-3607: best-effort -- a losing racer under the same
            # lock, or a sidecar that never existed, is not fatal;
            # the reopen below still produces a valid fresh db.
            _log.debug("cache.connect: quarantine rename of %s failed", src)


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
    """Delete-and-recreate `path` (T-0141 recovery).

    T-3632: `_recreate` already builds and atomically publishes a
    schema-complete db at the current `_SCHEMA_VERSION` (same primitive
    `_apply_schema`'s rebuild path now uses), so a second, separate
    `_apply_schema(conn, None, path)` call here used to be both redundant
    AND the actual root cause of the measured mutual-rebuild thrash: it
    ran its own in-place DROP/CREATE sequence directly on the connection
    `_recreate` had just atomically published, reopening the exact
    schema-incomplete-window T-3623 closed. `_recreate`'s output is
    already schema-complete, so there is nothing left to reapply.
    """
    _log.warning(
        "cache.connect: %s failed schema application, recreating: %s", path, exc
    )
    return _recreate(conn, path)


def _is_missing_meta_table(exc: sqlite3.Error) -> bool:
    """True iff `exc` is sqlite's "no such table: meta" shape."""
    return "no such table" in str(exc).lower() and "meta" in str(exc).lower()


# frob:ticket T-3634
_STALE_CONNECTION_ERROR_SHAPES = (
    "no such table",
    "disk i/o error",
    "database is corrupted",
    "database disk image is malformed",
    "unable to open database file",
    "file is not a database",
)


def _is_stale_or_corrupt_connection(exc: sqlite3.Error) -> bool:
    """True iff `exc` is one of the sqlite error shapes a sibling's
    concurrent rebuild can produce against a connection whose backing
    file was atomically replaced or quarantined out from under it
    (T-3634, round 3 of the T-3623/T-3632 cache-atomicity series).

    Round 1 (T-3623) and round 2 (T-3632) closed the windows where a
    connection could observe a schema-incomplete db mid-rebuild; this
    round's new symptom is different in kind -- on darwin, `os.replace`-
    ing the db file out from under a LIVE WAL connection makes that
    connection's *next* query raise `sqlite3.OperationalError('disk I/O
    error')` (its WAL sidecars/file handle no longer match the inode it
    has open), not the "no such table" shape the earlier rounds handled.
    Ubuntu tolerated this; darwin's mmap/WAL semantics do not. Matched by
    substring against `str(exc)` like `_is_missing_meta_table`, just over
    a wider set of known "this connection is looking at dead state, not
    a real corruption" shapes -- anything else still propagates as a
    genuine error.

    T-3733 (round 9, macOS CI run 33729699769): `exc` is typed as the
    sqlite3 base `Error`, not `DatabaseError` -- a stale/closed handle
    can raise `sqlite3.InterfaceError('bad parameter or other API
    misuse')`, which is a SIBLING of `DatabaseError` under `Error`, not
    a subclass of it, so it never matched the T-3706 catch clauses at
    all. `InterfaceError`'s message is generic ("bad parameter or other
    API misuse") and never appears in `_STALE_CONNECTION_ERROR_SHAPES`,
    so unlike the other shapes here it is matched by TYPE, not message
    substring: any `InterfaceError` reaching this point is, by
    construction, sqlite3 itself reporting operation-on-a-dead-handle,
    which is exactly the stale-connection condition this function
    exists to detect.
    """
    if isinstance(exc, sqlite3.InterfaceError):
        return True
    msg = str(exc).lower()
    return any(shape in msg for shape in _STALE_CONNECTION_ERROR_SHAPES)


def _conn_path(conn: sqlite3.Connection) -> Path | None:
    """Best-effort recover the on-disk path `conn` was opened against, via
    sqlite's own `PRAGMA database_list` (T-3634).

    Lets stale-connection recovery reopen at the connection's own path
    without every cache read/write function needing its own `path`
    parameter threaded in just for this. Returns `None` if the pragma
    itself fails (a connection broken badly enough that even metadata
    queries fail) or reports no file -- callers must fall back to
    whatever `path` they already have in scope.
    """
    try:
        rows = conn.execute("PRAGMA database_list").fetchall()
    except sqlite3.Error:
        # T-3733: a stale/closed handle can raise InterfaceError here
        # too, a sibling of DatabaseError -- widened so this best-effort
        # probe stays best-effort instead of propagating that shape.
        return None
    for _seq, name, file in rows:
        if name == "main" and file:
            return Path(file)
    return None


_STALE_CONN_MAX_RETRIES = 3


# frob:ticket T-3669
# frob:ticket T-3706
# frob:ticket T-3733
# frob:raises sqlite3.Error
def _reconnect_delay_for(
    exc: sqlite3.Error,
    *,
    what: str,
    path: Path | None,
    deadline: float,
    attempt: int,
    readonly_attempt: int,
) -> tuple[Path, float, bool]:
    """Decide whether `exc` earns another attempt through a REOPENED
    connection, returning `(delay before that attempt, was it the readonly
    shape)` -- or re-raising `exc` when it does not (T-3669, split out of
    `_run_with_stale_reconnect` to keep that function under ARCH001's line
    threshold).

    Two budgets, because the two shapes mean different things. `attempt to
    write a readonly database` is a handle fault whose underlying cause (a
    sibling's `os.replace` mid-rebuild) clears on its own, so it retries
    against the whole `_LOCK_TOTAL_TIMEOUT_SECONDS` budget with backoff;
    a stale/corrupt-connection shape means the reopen itself should have
    already fixed things, so a small fixed `_STALE_CONN_MAX_RETRIES` is
    the honest ceiling. Anything else, or an unknown path to reopen at,
    propagates unchanged.

    T-3706 (round 8): `exc` is typed `DatabaseError`, not the narrower
    `OperationalError` -- sqlite raises the "file is not a database" shape
    (already listed in `_STALE_CONNECTION_ERROR_SHAPES`) as a bare
    `DatabaseError`, sqlite3's PARENT exception class, not a subclass of
    `OperationalError`. The matcher already handled the shape by message;
    only the catch type at the call site was too narrow to ever reach it.

    T-3733 (round 9, macOS CI run 33729699769): `exc` is typed `Error`,
    not `DatabaseError` -- a stale/closed connection can raise
    `sqlite3.InterfaceError`, which is a SIBLING of `DatabaseError`
    under `Error`, not a subclass of it, so it still escaped even after
    the T-3706 widening. `_is_stale_or_corrupt_connection` now matches
    `InterfaceError` by type; only the parameter type here (and the
    catch clause at the call site) needed widening to actually reach
    it."""
    readonly = _is_readonly_handle_error(exc)
    if not readonly and not _is_stale_or_corrupt_connection(exc):
        raise exc
    if path is None:
        raise exc
    if readonly:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise exc
        _log.warning(
            "cache: %s hit a readonly-database write fault, reopening at "
            "%s and retrying (up to %.0fs remaining): %s",
            what,
            path,
            remaining,
            exc,
        )
        return path, _lock_backoff_seconds(readonly_attempt, remaining=remaining), True
    if attempt >= _STALE_CONN_MAX_RETRIES:
        raise exc
    _log.warning(
        "cache: %s hit a stale/corrupt connection, reopening at %s and "
        "retrying (attempt %d/%d): %s",
        what,
        path,
        attempt + 1,
        _STALE_CONN_MAX_RETRIES,
        exc,
    )
    return path, 0.0, False


# frob:ticket T-3634
# frob:ticket T-3669
# frob:ticket T-3706
# frob:ticket T-3733
def _run_with_stale_reconnect(conn: sqlite3.Connection, op, *, what: str):  # noqa: ANN001, ANN202
    """Call `op(conn)` through a connection guaranteed to be bound to the
    file currently at the cache path, reopening and retrying rather than
    reusing a handle that a sibling's `os.replace` stranded on the old
    inode (T-3634; T-3669 handle-lifecycle rewrite; T-3706 widened the
    catch to `DatabaseError`, sqlite's "file is not a database" PARENT
    class; T-3733 widens once more to the base `Error`, since sibling
    `InterfaceError` escaped the same way).

    `op` receives the (possibly reopened) connection on each attempt and
    must be safe to call more than once; every current use (a read, or a
    `_with_lock_retry`-wrapped delete-then-insert) already is. `conn`
    itself is never closed when it is merely stranded -- it belongs to the
    caller, whose own later calls route back through here -- so a write
    made through a connection of this function's own is committed here,
    since the caller cannot commit a handle it was never given (T-3669).
    """
    deadline = time.monotonic() + _LOCK_TOTAL_TIMEOUT_SECONDS
    canonical = _conn_path(conn)
    attempt = 0
    readonly_attempt = 0
    active = conn
    owned = False
    try:
        while True:
            if canonical is not None and not owned:
                fresh = _reopen_without_closing(conn, canonical)
                if fresh is not None:
                    active, owned = fresh, True
            try:
                result = op(active)
            except sqlite3.Error as exc:
                path = _conn_path(active) or canonical
                path, delay, readonly = _reconnect_delay_for(
                    exc,
                    what=what,
                    path=path,
                    deadline=deadline,
                    attempt=attempt,
                    readonly_attempt=readonly_attempt,
                )
                if readonly:
                    readonly_attempt += 1
                else:
                    attempt += 1
                if owned:
                    _close_conn(active)
                active, owned = _open(path), True
                canonical = path
                if delay:
                    time.sleep(delay)
                continue
            if owned:
                # The caller holds no reference to `active`, so nobody
                # else can ever commit it -- do it here or lose the write.
                active.commit()
            return result
    finally:
        if owned:
            _close_conn(active)


# frob:ticket T-3623
# frob:ticket T-3634
# frob:raises Error
# frob:ticket T-3669
# frob:ticket T-3700
# frob:tests \
# tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_two_\
# processes_connecting_concurrently_never_see_no_such_table_meta
def _check_fingerprint_with_recovery(
    conn: sqlite3.Connection, path: Path
) -> sqlite3.Connection:
    """Run `_check_fingerprint`, reopening-and-retrying (bounded) whenever it
    hits "no such table: meta" or a T-3634 stale/corrupt-connection shape,
    instead of letting that `OperationalError` escape `connect()` uncaught
    (T-3623 direction 2; T-3634 round 3 widens the match; T-3700 makes the
    recovery a bounded loop rather than one-shot).

    `_check_fingerprint` is the last of `connect()`'s three DB touches
    (`_read_schema_version`, `_apply_schema_with_recovery`, this) -- both
    of the earlier two already route a missing/corrupt schema through a
    rebuild, but this one had no such handling of its own, so it was the
    step where a genuinely still-possible connection-level race (this
    connection's own SELECT lazily resolving against a `path` inode that
    changed under it between statements, distinct from the visibility
    window T-3623's `_create_schema_complete_db`/`_build_schema_complete_
    db` change closes) surfaced as a raw crash instead of the ordinary
    "schema missing, rebuild" path every OTHER miss shape here already
    gets. T-3634: the same race can now also surface as `disk I/O error`
    on darwin (a sibling's `os.replace` publishing a fresh db while this
    connection still has the old inode's WAL mapped) rather than "no such
    table" -- recovered the same way, by reopening at the canonical path,
    which by construction already holds the winner's fresh complete db.

    T-3700 (round 7): the pre-T-3700 code recovered exactly ONCE and then
    ran a FINAL, UNGUARDED `_check_fingerprint`. Under heavy parallel CI
    load (run 33633092156, ubuntu) a sibling's `os.replace` racing that
    final unguarded read re-raised `disk I/O error` / `no such table:
    meta` straight out of `connect()` -- and the `_with_lock_retry`
    wrapping this step never catches those shapes (they are not the
    transient-lock shape it matches). Making recovery a bounded reopen+
    retry loop (each pass reopens at the canonical inode first, exactly
    where a sibling's atomic `os.replace` publishes its schema-complete
    winner, then re-reads) closes that window: only after
    `_STALE_CONN_MAX_RETRIES` consecutive losses -- a real, persistent
    problem, not a load-timing race -- does the last exception propagate,
    still declared via `frob:raises`.

    T-3706 (round 8, macOS run 33680767948): the catch here was
    `sqlite3.OperationalError` only, but sqlite raises the "file is not a
    database" torn-read shape as a bare `sqlite3.DatabaseError` (sqlite3's
    PARENT exception class, not a subclass of `OperationalError`) -- so it
    escaped this recovery loop uncaught even though
    `_is_stale_or_corrupt_connection` has matched that exact message since
    T-3634. Widened to `DatabaseError` so the existing matcher is actually
    reachable.

    T-3733 (round 9, macOS CI run 33729699769): the catch here was
    `sqlite3.DatabaseError`, but `sqlite3.InterfaceError` -- the shape a
    stale/closed connection raises as "bad parameter or other API
    misuse" -- is a SIBLING of `DatabaseError` under `sqlite3.Error`, not
    a subclass of it, so it still escaped uncaught after T-3706. Widened
    to `sqlite3.Error`, the documented base for every sqlite3 exception,
    so no future sibling shape can repeat this pattern.
    """
    # T-3669: the fingerprint read is the exact statement the darwin
    # thrash loop kept answering from a replaced-away inode (`fingerprint
    # None` ~20 times running, run 33529632605). Reopen the handle at the
    # canonical path FIRST, so the value read -- and the invalidation
    # write that follows a mismatch -- both land on the live file.
    attempt = 0
    while True:
        conn = _reopen_if_replaced(conn, path)
        try:
            _check_fingerprint(conn, path)
            return conn
        except sqlite3.Error as exc:
            conn = _recover_fingerprint_connection(conn, path, exc, attempt)
            attempt += 1


# frob:ticket T-3700
# frob:ticket T-3706
# frob:ticket T-3733
def _recover_fingerprint_connection(
    conn: sqlite3.Connection, path: Path, exc: sqlite3.Error, attempt: int
) -> sqlite3.Connection:
    """Recover one `_check_fingerprint` failure into a fresh connection
    ready for another read, or re-raise `exc` (T-3700, split out of
    `_check_fingerprint_with_recovery` to keep that function under ARCH001's
    line threshold; T-3706 widens the accepted exception type; T-3733
    widens it again to the sqlite3 base `Error`).

    Re-raises on the last allowed `attempt` (the honest ceiling -- a
    genuine, non-racing fault), on a "no such table: meta" this rebuilds
    via `_recreate_and_reapply`, and on a stale/corrupt or readonly-handle
    shape reopens at the canonical inode (where a sibling's atomic
    `os.replace` publishes its schema-complete winner); anything else
    propagates unchanged. `exc` is typed as the sqlite3 base `Error`,
    not `DatabaseError`, because `sqlite3.InterfaceError` -- the shape a
    stale/closed connection raises -- is a SIBLING of `DatabaseError`,
    not a subclass of it, and `_is_stale_or_corrupt_connection` matches
    it by type."""
    if attempt >= _STALE_CONN_MAX_RETRIES:
        raise exc
    if _is_missing_meta_table(exc):
        return _recreate_and_reapply(conn, path, exc)
    if _is_stale_or_corrupt_connection(exc) or _is_readonly_handle_error(exc):
        reopen_path = _conn_path(conn) or path
        _log.warning(
            "cache.connect: %s hit a stale connection (%s), reopening "
            "at %s (attempt %d/%d)",
            path,
            exc,
            reopen_path,
            attempt + 1,
            _STALE_CONN_MAX_RETRIES,
        )
        _close_conn(conn)
        return _open(reopen_path)
    raise exc


def _poll_and_reread(
    conn: sqlite3.Connection,
    path: Path,
    existing: int | None,
    deadline: float,
    why: str,
    *,
    attempt: int = 0,
) -> tuple[sqlite3.Connection, int | None]:
    """Sleep one (exponentially backed-off, T-3654) poll interval, then
    re-read the schema version (T-1239/T-1416).

    Raises the caller's original exception (via bare `raise`) if `deadline`
    has already passed -- a contending process that never finishes is a
    real timeout, not something to poll on forever. `attempt` (0-indexed,
    incremented by the caller each time this is called for the SAME
    contention loop) drives `_lock_backoff_seconds` so repeated schema-
    application races poll faster early on, same rationale as
    `_with_lock_retry`'s own T-3654 backoff.
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
    time.sleep(_lock_backoff_seconds(attempt, remaining=remaining))
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
    attempt = 0
    while True:
        try:
            return _apply_schema(conn, existing, path)
        except sqlite3.OperationalError as exc:
            if not _is_transient_lock_error(exc):
                raise
            conn, existing = _poll_and_reread(
                conn,
                path,
                existing,
                deadline,
                "locked during schema application",
                attempt=attempt,
            )
            attempt += 1
        except sqlite3.IntegrityError as exc:
            if not _is_concurrent_meta_key_race(exc):
                return _recreate_and_reapply(conn, path, exc)
            conn, existing = _poll_and_reread(
                conn,
                path,
                existing,
                deadline,
                "hit a concurrent schema-migration race (UNIQUE on meta.key)",
                attempt=attempt,
            )
            attempt += 1
        except sqlite3.DatabaseError as exc:
            return _recreate_and_reapply(conn, path, exc)


# frob:ticket T-3644
_INPROCESS_WRITE_LOCKS: dict[str, threading.RLock] = {}
_INPROCESS_WRITE_LOCKS_GUARD = threading.Lock()


# frob:ticket T-3644
# frob:tests tests/unit/test_graph_build_lock.py::TestBuildGraphLockScope.test_two_processes_never_commit_to_the_same_cache_concurrently  # noqa: E501
# frob:tests tests/unit/test_graph_cache.py::TestConnectNeverReturnsAStaleConnection.test_connect_after_forced_schema_rebuild_returns_a_fresh_live_connection  # noqa: E501
def _inprocess_write_lock(path: Path) -> threading.RLock:
    """The per-resolved-path lock serializing `connect()` calls WITHIN this
    process (T-3644).

    Retiring WAL (see `_open`'s T-3644 comment) moves this cache's writer
    locking onto sqlite's rollback-journal `fcntl` advisory locks, which
    are documented (SQLite's own "File Locking Notes") to be scoped per
    `(process, inode)` rather than per file descriptor: two
    `sqlite3.Connection` objects opened by the SAME process against the
    SAME db file do not correctly exclude each other at the OS level
    (`test_two_processes_never_commit_to_the_same_cache_concurrently`'s
    same-process two-thread shape hit exactly this -- both connections
    proceeding as if unlocked, then one losing an internal sqlite state
    race and surfacing `attempt to write a readonly database` instead of
    a plain retryable `database is locked`). A per-path Python lock closes
    that gap the OS cannot: it only ever serializes THIS process's own
    `connect()` callers against each other, leaving genuine cross-process
    concurrency (real separate `frob` invocations, WAL's actual
    audience) exactly as it was -- real OS processes still contend
    correctly on the same fcntl locks."""
    with _INPROCESS_WRITE_LOCKS_GUARD:
        key = str(path.resolve())
        lock = _INPROCESS_WRITE_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _INPROCESS_WRITE_LOCKS[key] = lock
        return lock


# frob:invariant INV-003
# invariant spec: [INV-003](invariants/INV-003.md)
# frob:invariant INV-050
# invariant spec: [INV-050](invariants/INV-050.md)
# frob:ticket T-0029
# frob:ticket T-0141
# frob:ticket T-1519
# frob:ticket T-3644
# frob:doc docs/modules/graph.md#cache
# frob:tests tests/unit/test_graph_build_lock.py::TestBuildGraphLockScope.test_two_processes_never_commit_to_the_same_cache_concurrently  # noqa: E501
# frob:tests tests/test_graph.py::TestConcurrentCache.test_connect_on_current_schema_does_not_block_on_a_held_write_lock  # noqa: E501
def connect(path: Path) -> sqlite3.Connection:
    """Open (creating parent dirs) the cache db; wipe and rebuild on schema mismatch.

    A cache.db whose bytes are not sqlite at all (truncation, disk garbage)
    cannot be repaired through its own connection -- DROP TABLE raises the
    same DatabaseError. The cache is derived state, so the honest recovery
    is delete-and-recreate the file (T-0019 / INV-003), applied at both the
    connect-probe stage and, per T-0141, the later DDL stage too.

    T-3130: `_check_fingerprint`'s own writes (DELETE + upsert on a
    fingerprint mismatch) were the one write step here NOT routed through
    `_with_lock_retry` -- every other cache write path already retries a
    transient `sqlite3.OperationalError: database is locked` (T-1423), but
    a lock hit during `_check_fingerprint` propagated straight out of
    `connect` as an unhandled exception instead, measured under ordinary
    concurrent `frob check` load (fleet_status regularly shows several
    concurrent checks on one host -- not a rare spike). `_check_fingerprint`
    is idempotent under retry: its first statement is a plain `SELECT`, and
    a lock error on any later write means the transaction has not
    committed, so re-running the whole function from scratch is safe.

    T-3632: the final `_check_fingerprint_with_recovery` step used to be
    wrapped as `lambda: _check_fingerprint_with_recovery(conn, path)` and
    handed to `_with_lock_retry`, which can call that lambda more than
    once (T-1423 lock retry). A retry re-reads the closed-over `conn` --
    but if the FIRST attempt hit a "database is locked" error partway
    through its own internal `_recreate_and_reapply` recovery (a distinct,
    real possibility: `_recreate` takes a rebuild lock and reopens),
    `_check_fingerprint_with_recovery`'s internal reassignment of its
    local `conn` name is discarded when the exception propagates, and the
    retry would reuse the OUTER `conn` -- by then already `.close()`d by
    `_recreate` -- producing exactly the stale-connection misuse
    (`sqlite3.InterfaceError` / `ProgrammingError`) measured at this
    file's old line ~1083 (run 33472403980, `test_waive002_end_to_end_via_
    run_gates`). Using `nonlocal` so every retry attempt reads and writes
    the SAME variable this function ultimately returns closes that gap:
    a caller of `connect()` can never receive, and no retry can ever
    reuse, a connection object that a recreate has since closed out from
    under it.

    T-3644: holds this process's per-path write lock (`_inprocess_write_
    lock`) for the DURATION OF THIS CALL ONLY -- acquired before opening
    anything, released before returning (or on any exception) -- not for
    the returned connection's whole lifetime. Serializing only this
    function's own body is enough to close the intra-process fcntl-
    aliasing gap `_inprocess_write_lock`'s docstring describes (the
    schema/fingerprint DDL this function itself runs is exactly where
    that race was measured, run 33491468339); holding it any longer would
    make an already-open connection's mere existence block a SIBLING
    THREAD's unrelated `connect()` at this same path even when neither is
    actually racing -- which regressed T-0232's own pinned invariant
    (`test_connect_on_current_schema_does_not_block_on_a_held_write_
    lock`: a second connection to an already-current-schema db must
    return promptly beside another connection's held-open write, not
    queue behind it) when this was first tried holding the lock through
    `close()`.
    """
    with _inprocess_write_lock(path):
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            # T-3623: the very first ever connect() at this path has the same
            # schema-incomplete-but-visible window _recreate used to have --
            # sqlite3.connect() creates a 0-byte file immediately, before any
            # CREATE TABLE runs. Pre-building the schema at a temp path and
            # atomically renaming it into place (same helper _recreate uses)
            # means a racing sibling's connect_readonly (or its own connect())
            # never observes a tableless file at all. A second racer that also
            # sees `not path.exists()` just repeats this and loses the rename
            # race harmlessly -- os.replace is atomic either way.
            _create_schema_complete_db(path)
        conn = _open(path)
        conn, existing = _read_schema_version(conn, path)
        conn = _apply_schema_with_recovery(conn, existing, path)

        def _check_fingerprint_step() -> None:
            nonlocal conn
            conn = _check_fingerprint_with_recovery(conn, path)

        _with_lock_retry(_check_fingerprint_step, what="fingerprint check")
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


# frob:ticket T-3700
def _read_root(conn: sqlite3.Connection) -> str | None:
    """The stored repo root via one raw `meta` SELECT, no reconnect wrapper
    -- for `load_all`, which already runs its whole body inside a single
    `_run_with_stale_reconnect` (T-3700, so `get_root`'s own wrapper does
    not nest a second reconnect layer per snapshot load)."""
    cur = conn.execute("SELECT value FROM meta WHERE key = 'root'")
    row = cur.fetchone()
    return row[0] if row is not None else None


# frob:doc docs/modules/graph.md#cache
# frob:ticket T-3700
# frob:waive WIRE001 reason="wired via _cache.get_root(conn) at graph/__init__.py:754 (frob explore xref confirms); WIRE FUNCTION call_pattern's negative lookbehind excludes module-alias dotted calls -- new-in-diff only because T-3700 rewrapped the body" follow_up="T-3703"  # noqa: E501
# frob:tests \
# tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb.test_two_\
# processes_connecting_concurrently_never_see_no_such_table_meta
def get_root(conn: sqlite3.Connection) -> str | None:
    """The stored repo root, if any snapshot has ever been saved.

    T-3700: routed through `_run_with_stale_reconnect` like every other
    read here -- this `meta` read is one of the queries a caller issues
    right after `connect()`, and on a connection a sibling's concurrent
    `os.replace` stranded on the pre-rebuild inode a bare read surfaces
    `disk I/O error` / `no such table: meta` (a hot rollback journal
    resolved by path against the replaced-in inode) straight to the
    caller. Reopening at the canonical inode before the read, exactly as
    the other read paths do, absorbs that race; the read is idempotent
    under retry."""
    return _run_with_stale_reconnect(conn, _read_root, what="get_root")


# frob:ticket T-0600
# frob:ticket T-3700
# frob:tests tests/test_graph.py::TestCacheModule.test_store_and_load_file_data_roundtrip  # noqa: E501
def _get_file_hash(conn: sqlite3.Connection, file_path: str) -> str | None:
    """The cached content hash for `file_path`, or `None` if never stored.

    Private (T-0600): a low-level cache accessor with no consumer outside
    this module's own test coverage -- `frob.graph.__init__`'s incremental
    rebuild path reads staleness via `get_file_meta`, never this directly.

    T-3700: routed through `_run_with_stale_reconnect` like the other post-
    connect reads, so a sibling's concurrent rebuild stranding the handle
    mid-read reopens at the canonical inode rather than surfacing a raw
    `disk I/O error` / `no such table`."""

    def _op(c: sqlite3.Connection) -> str | None:
        cur = c.execute("SELECT content_hash FROM files WHERE path = ?", (file_path,))
        row = cur.fetchone()
        return row[0] if row is not None else None

    return _run_with_stale_reconnect(conn, _op, what=f"_get_file_hash({file_path})")


# frob:ticket T-0245
# frob:ticket T-3700
# frob:doc docs/modules/graph.md#cache
def get_file_meta(
    conn: sqlite3.Connection, file_path: str
) -> tuple[str, int, int] | None:
    """`(content_hash, mtime_ns, size)` for `file_path`, or `None` if never stored.

    The stat pair lets callers skip a full content read when the file's
    on-disk (mtime_ns, size) has not moved since the last build (T-0245) --
    a single `os.stat` syscall instead of open+read+close per file.

    T-3700: routed through `_run_with_stale_reconnect` -- this is one of
    the per-file reads `frob.graph.__init__`'s incremental rebuild issues
    right after `connect()`, so a sibling's concurrent rebuild stranding
    the handle reopens at the canonical inode instead of surfacing a raw
    `disk I/O error` / `no such table`; the read is idempotent under retry.
    """

    def _op(c: sqlite3.Connection) -> tuple[str, int, int] | None:
        cur = c.execute(
            "SELECT content_hash, mtime_ns, size FROM files WHERE path = ?",
            (file_path,),
        )
        row = cur.fetchone()
        return (row[0], row[1], row[2]) if row is not None else None

    return _run_with_stale_reconnect(conn, _op, what=f"get_file_meta({file_path})")


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
# frob:ticket T-3669
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
    lock is safe. T-3634: also survives a sibling's concurrent rebuild
    publishing a fresh db mid-call (`_run_with_stale_reconnect`) -- same
    idempotency argument, over a reopened connection instead of the same
    one.
    """

    def _op(c: sqlite3.Connection) -> None:
        def _write() -> None:
            c.execute(
                "INSERT INTO files (path, content_hash, mtime_ns, size) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(path) DO UPDATE SET "
                "content_hash = excluded.content_hash, "
                "mtime_ns = excluded.mtime_ns, "
                "size = excluded.size",
                (file_path, content_hash, mtime_ns, size),
            )
            _store_symbols(c, file_path, symbols)
            _store_edges(c, file_path, edges)
            _store_malformed(c, file_path, malformed)

        # T-3669: retry_readonly=False -- `_run_with_stale_reconnect`
        # (this call's own wrapper, below) owns the reopen, so a readonly
        # write fault must reach it rather than being retried here on the
        # replaced-away handle that caused it.
        _with_lock_retry(
            _write, what=f"store_file_data({file_path})", retry_readonly=False
        )

    _run_with_stale_reconnect(conn, _op, what=f"store_file_data({file_path})")


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
    """Read back everything previously stored for `file_path` (a cache hit).

    T-3634: retried via `_run_with_stale_reconnect` if a sibling's
    concurrent rebuild lands mid-read -- the whole read is idempotent
    under retry (it takes no locks and mutates nothing), so re-running it
    against a freshly reopened connection is safe.
    """

    def _op(c: sqlite3.Connection):  # noqa: ANN202
        rows = c.execute(
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
            for src, kind, target, origin, attrs in c.execute(
                "SELECT src, kind, target, origin, attrs FROM edges WHERE file = ?",
                (file_path,),
            )
        )
        malformed = tuple(
            MalformedDirective(file=file_path, line=line, reason=reason)
            for line, reason in c.execute(
                "SELECT line, reason FROM malformed WHERE file = ?", (file_path,)
            )
        )
        return symbols, edges, malformed

    return _run_with_stale_reconnect(conn, _op, what=f"load_file_data({file_path})")


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
    `store_file_data`: the insert is idempotent under retry. T-3634:
    also survives a sibling's concurrent rebuild mid-call, via
    `_run_with_stale_reconnect`.
    """

    def _op(c: sqlite3.Connection) -> None:
        def _write() -> None:
            c.execute(
                "INSERT INTO parsed_artifacts (content_hash, fingerprint, payload) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(content_hash, fingerprint) DO UPDATE SET "
                "payload = excluded.payload",
                (content_hash, fingerprint, payload),
            )
            c.commit()

        _with_lock_retry(_write, what=f"store_parsed_artifact({content_hash[:12]})")

    _run_with_stale_reconnect(
        conn, _op, what=f"store_parsed_artifact({content_hash[:12]})"
    )


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
    (or an earlier run) already derived the same file's artifacts.

    T-3634: retried via `_run_with_stale_reconnect` if a sibling's
    concurrent rebuild lands mid-read -- the read is idempotent under
    retry.
    """

    def _op(c: sqlite3.Connection) -> str | None:
        row = c.execute(
            "SELECT payload FROM parsed_artifacts "
            "WHERE content_hash = ? AND fingerprint = ?",
            (content_hash, fingerprint),
        ).fetchone()
        return row[0] if row is not None else None

    return _run_with_stale_reconnect(
        conn, _op, what=f"load_parsed_artifact({content_hash[:12]})"
    )


# frob:doc docs/modules/graph.md#cache
# frob:ticket T-1214
# frob:ticket T-3700
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
    whole-snapshot path, which never needs a per-file round trip.

    T-3634: the whole read is retried via `_run_with_stale_reconnect` if
    a sibling's concurrent rebuild lands mid-read -- idempotent under
    retry since it only reads."""

    def _op(c: sqlite3.Connection) -> GraphSnapshot:
        # T-3700: `_read_root`, not `get_root` -- this whole body already
        # runs inside `_run_with_stale_reconnect`, so calling the wrapped
        # `get_root` here would nest a second reconnect layer needlessly.
        root = _read_root(c) or ""
        file_hashes = {
            path: content_hash
            for path, content_hash in c.execute("SELECT path, content_hash FROM files")
        }
        symbols: dict[str, SymbolRecord] = {}
        for row in c.execute(
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
            for src, kind, target, origin, attrs in c.execute(
                "SELECT src, kind, target, origin, attrs FROM edges ORDER BY file"
            )
        ]
        malformed: list[MalformedDirective] = [
            MalformedDirective(file=file_path, line=line, reason=reason)
            for file_path, line, reason in c.execute(
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

    return _run_with_stale_reconnect(conn, _op, what="load_all")


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

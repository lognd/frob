"""The obligation graph: symbols, comment-DSL edges, and doc anchors
(docs/modules/graph.md).

`frob.graph` is a persistent registry of every symbol's identity and
digests, plus typed edges declared in `frob:` comments and markdown
`frob:describes` anchors, so any change to code, docs, or contracts is
detectable statically -- a type checker for obligations. Built entirely on
`frob.lang`'s uniform `ParsedFile` contract; this package never inspects a
tree-sitter node directly.

`build_graph` is incremental: a per-file sha256 content hash is stored in
the sqlite cache (`frob.graph.cache`), and a file whose hash is unchanged
loads its symbols/edges back from the cache instead of being re-parsed.

Source-file discovery filters through `frob.lang.supported_extensions()`
(T-0129) -- the canonical extension registry -- rather than a hand-copied
local table, so every grammar `frob.lang` gains (including `.strata`)
reaches the graph automatically.
"""
# frob:waive ARCH102 reason="19 of 22 exports form one connected build-graph pipeline \
# cluster (load_graph's own ingest/parse/cache-prune chain); the remaining 2 \
# (edges_from, edges_to) are small read-only query accessors over the exact \
# GraphSnapshot the pipeline produces, coupled to it by the shared data model rather \
# than by direct calls -- splitting query accessors away from the builder of the \
# structure they query would separate one cohesive graph API into pieces with no \
# independent reason to exist apart. `resolve` moved to the frob.graph._resolve leaf \
# module (T-3411, to collapse the frob.graph<->frob.graph.lock import cycle) and is \
# re-exported here for its public surface, so it no longer counts against this \
# waiver's boundary."
# frob:waive LARGE001 reason="T-1651-grade: same cohesion the ARCH102 waiver above \
# already establishes -- one build-graph pipeline (ingest/parse/cache-prune) plus its \
# two query accessors, coupled by the shared GraphSnapshot model. Splitting the \
# pipeline stages apart would sever load_graph's own incremental-cache-vs-reparse \
# decision from the parse/ingest steps it decides between."

from __future__ import annotations

import hashlib
import os
import sqlite3
import time
from collections.abc import Sequence
from pathlib import Path

from typani import Err, Ok
from typani.result import Result

import frob.excludes as _excludes
from frob.check._memo import memoize_per_run
from frob.graph import cache as _cache
from frob.graph._generated import is_generated_source
from frob.graph._models import (
    BuildStats,
    DanglingEdge,
    Digests,
    DriftReport,
    Edge,
    EdgeKind,
    GraphError,
    GraphSnapshot,
    LockEntry,
    LockFile,
    MalformedDirective,
    ParseFailure,
    StaleItem,
    SymbolId,
    SymbolRecord,
)
from frob.graph._resolve import resolve
from frob.graph.affects import (
    AffectedSet,
    ScopeClosureGap,
    affects,
    scope_doc_code_gaps,
    scope_test_gaps,
)
from frob.graph.callgraph import (
    CallGraph,
    OrderedCallGraph,
    PrivateHelperGap,
    build_call_graph,
    build_ordered_call_graph,
    build_reference_graph,
    closure,
    scope_private_helper_gaps,
)
from frob.graph.digest import compute_digests
from frob.graph.dsl import (
    dedupe_slug,
    fold_comment_runs,
    markdown_anchors,
    parse_directives,
    slugify,
)
from frob.graph.lock import LockError, acknowledge, load_lock, write_lock
from frob.graph.summary import (
    FunctionSummary,
    SCCTimeout,
    SummaryResult,
    compute_protocol_summaries,
)
from frob.lang import LangError, ParsedFile, parse_file, supported_extensions
from frob.logging import get_logger
from frob.process._lock import derived_state_write_lock

_log = get_logger(__name__)


BuildError = GraphError | LangError


def _content_hash(path: Path) -> str | None:
    """Sha256 hex of `path`'s bytes, or `None` if it cannot be read."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        _log.warning("could not read %s for hashing: %s", path, exc)
        return None


# frob:ticket T-0245
def _stat_key(path: Path) -> tuple[int, int] | None:
    """`(mtime_ns, size)` for `path` via a single `os.stat`, or `None` unreadable.

    One syscall vs. the open+read+close a content hash needs (T-0245); on a
    latency-heavy mount (WSL9p `/mnt/c`, network shares) this is the
    difference between a per-file stat and a per-file full read, and it is
    the cheap check `build_graph`/`load_graph` try first.
    """
    try:
        st = path.stat()
        return st.st_mtime_ns, st.st_size
    except OSError as exc:
        _log.warning("could not stat %s: %s", path, exc)
        return None


# frob:ticket T-4257
#: T-4257: `(mtime_ns, size)` collisions across GENUINELY different content
#: are not just a theoretical race -- MEASURED directly (both on this
#: repo's Linux dev boxes and on real Windows via the `winrun` mirror): a
#: tight loop of write-then-stat with no other work between the two calls
#: produces IDENTICAL `(mtime_ns, size)` pairs for a meaningful fraction of
#: edits (Windows: 8/20 in one measured run; this repo's own WSL/ext4 dev
#: mount: 5/20) even though every edit's content differs. `_process_source_
#: file`/`_process_doc_file` below never re-verify a stat match against
#: content -- a collision there is a silent STALE cache HIT, exactly the
#: shape T-0602/gate-cache's own module docstring calls out as the failure
#: this whole cache design must never produce. In practice, `build_graph`'s
#: real pipeline (parse + digest + sqlite write, not a bare write()) puts
#: enough wall-clock distance between two builds of the SAME file that a
#: genuine collision was never reproduced end-to-end (measured: 0/200
#: across a build_graph-based edit loop, both platforms) -- but "usually
#: enough real work happens in between" is exactly the kind of incidental,
#: unmeasured assumption this project exists to replace with an enforced
#: one. A stat entry younger than this margin is treated as untrustworthy
#: on its own and always falls through to the existing content-hash
#: comparison (still far cheaper than a full reparse) instead of being
#: trusted blindly -- closing the gap categorically rather than leaving it
#: to how much other work happens to separate two edits.
#:
#: T-4279: the margin used to be this one FIXED constant (250ms),
#: correct only while the filesystem's mtime granularity is much finer
#: than it -- verified true for this repo's own WSL/ext4 mount (measured
#: granularity under 5ms, so 250ms is a ~50x safety margin over it) but
#: NOT a property every mount has. A filesystem with 1-2 SECOND mtime
#: granularity (older removable formats, some network mounts where the
#: time is server-supplied or truncated on write) can alias two writes
#: comfortably OUTSIDE a 250ms margin onto the same stat pair; the fast
#: path would then trust the match and return a stale verdict silently
#: -- the exact failure shape this whole mechanism exists to close, just
#: moved to a mount nobody measured it against. `_stat_trust_margin_ns`
#: below replaces the fixed constant with one derived from `_mtime_
#: granularity_ns`'s own measurement of the ACTUAL mount, so the ~50x
#: safety factor this constant encoded empirically is now applied to
#: whatever granularity is really observed, not assumed.
_STAT_TRUST_SAFETY_MULTIPLIER = 50


#: T-4279: candidate filesystem mtime-observation granularities,
#: coarsest bucket a measured value gets rounded UP to, finest first,
#: covering every real one this module's docstring above discusses: exact
#: nanosecond timestamps, NTFS's 100ns ticks, common coarser steps a
#: network filesystem or a kernel's own coarse-clock timestamp update
#: policy might exhibit, and the two historical worst cases (1s FAT/
#: HFS+, 2s old FAT). Rounding UP to the nearest candidate (rather than
#: using the raw measured gap directly) keeps the derived margin a
#: stable, round value instead of one that wobbles with per-run
#: scheduling noise.
_MTIME_GRANULARITY_CANDIDATES_NS: tuple[int, ...] = (
    1,  # exact ns
    100,  # NTFS
    1_000,  # 1us
    1_000_000,  # 1ms
    10_000_000,  # 10ms
    1_000_000_000,  # 1s (FAT/HFS+)
    2_000_000_000,  # 2s (old FAT)
)

#: T-4279: number of real back-to-back writes `_probe_mtime_granularity_
#: ns` performs to observe the mount's actual mtime-update behavior --
#: matches T-4257's own original measurement methodology's sample size
#: (that ticket's docstring: "a tight loop of write-then-stat ... 5/20"
#: on this repo's own mount), so the probe reproduces the same shape of
#: measurement this margin has always been justified by, just performed
#: live against whatever mount is actually running rather than assumed
#: from one prior measurement.
_GRANULARITY_PROBE_WRITES = 20

#: T-4279: per-root in-process cache for `_mtime_granularity_ns`'s
#: measurement -- a mount's observed timestamp-update granularity does
#: not change for the life of a process, so re-probing per file (or per
#: build) would pay a real write-loop cost for a value that can only
#: ever come out the same. Keyed by `root.resolve()` since a bare `root`
#: can be given in more than one spelling across calls within one run.
_mtime_granularity_cache: dict[Path, int | None] = {}

#: T-4279: on-disk sidecar filename for `_mtime_granularity_ns`'s
#: measurement, written under `<root>/.frob/` -- makes the "measure once"
#: half of the ticket's own remedy survive PAST one process's lifetime
#: too, since `frob check`'s real usage pattern is many short-lived CLI
#: invocations against the same root, each of which would otherwise
#: re-probe from a cold in-process cache. Deliberately a plain text file
#: read/written directly here rather than a new `frob.graph.cache`
#: sqlite meta row: this ticket's own declared scope is `src/frob/graph/
#: __init__.py` only.
_MTIME_GRANULARITY_CACHE_FILENAME = "mtime-granularity-ns"


# frob:ticket T-4279
# frob:tests \
# tests/unit/test_graph_stat_trust_margin.py::TestProbeMtimeGranularityNs.test_real_pro\
# be_returns_a_plausible_small_value
# frob:tests \
# tests/unit/test_graph_stat_trust_margin.py::TestProbeMtimeGranularityNs.test_all_samp\
# les_colliding_falls_back_to_loop_span
# frob:tests \
# tests/unit/test_graph_stat_trust_margin.py::TestProbeMtimeGranularityNs.test_unwritab\
# le_root_returns_none
def _probe_mtime_granularity_ns(root: Path) -> int | None:
    """Measure `root`'s filesystem's OBSERVED mtime-update granularity in
    nanoseconds (T-4279), via `_GRANULARITY_PROBE_WRITES` real back-to-
    back writes to a throwaway probe file under `root/.frob/`, recording
    `stat().st_mtime_ns` after each.

    Deliberately does NOT measure storage precision via `os.utime` (an
    earlier draft of this function did, and was wrong): a filesystem can
    happily STORE an arbitrary nanosecond value written directly via
    `os.utime` while the kernel's own timestamp-update path for a real
    write still advances mtime in much coarser ticks -- exactly the gap
    T-4257's own docstring measured empirically on this repo's ext4 mount
    (nominally full ns storage precision, yet 5/20 real back-to-back
    writes still collided onto an identical stat pair). Only a real
    write loop observes that actual behavior; a synthetic timestamp
    round-trip does not.

    Returns the smallest OBSERVED positive gap between consecutive
    distinct timestamps, rounded up to the nearest
    `_MTIME_GRANULARITY_CANDIDATES_NS` bucket. If every sample in the
    loop collides onto the identical timestamp, the mount is at least as
    coarse as the whole loop's wall-clock span; that span is used as the
    measured gap instead so the result is still a real, conservative
    lower bound rather than a guess. `None` if the probe file cannot be
    created or stat'd (`.frob/` unwritable, an unreadable/vanished root)
    or if even the whole-loop span is coarser than every candidate here
    -- callers must treat that as "cannot establish safety", never as
    license to guess a value.
    """
    probe_dir = root / ".frob"
    try:
        probe_dir.mkdir(parents=True, exist_ok=True)
        probe_path = probe_dir / f".mtime-granularity-probe-{os.getpid()}"
    except OSError as exc:
        _log.warning(
            "could not create mtime-granularity probe dir %s: %s", probe_dir, exc
        )
        return None
    try:
        samples = _collect_mtime_probe_samples(probe_path)
        if samples is None:
            return None
        timestamps, loop_elapsed_ns = samples
        return _granularity_bucket_for_samples(root, timestamps, loop_elapsed_ns)
    finally:
        try:
            probe_path.unlink()
        except OSError:
            pass


# frob:ticket T-4279
# frob:tests \
# tests/unit/test_graph_stat_trust_margin.py::TestProbeMtimeGranularityNs.test_real_pro\
# be_returns_a_plausible_small_value
def _collect_mtime_probe_samples(
    probe_path: Path,
) -> tuple[list[int], int] | None:
    """Write to `probe_path` `_GRANULARITY_PROBE_WRITES` times back to
    back, recording `stat().st_mtime_ns` after each (T-4279, split out of
    `_probe_mtime_granularity_ns` to keep it under ARCH001's length
    threshold). Returns `(timestamps, loop_elapsed_ns)`, or `None` if a
    write/stat call fails partway through."""
    loop_start_ns = time.monotonic_ns()
    timestamps: list[int] = []
    try:
        for i in range(_GRANULARITY_PROBE_WRITES):
            probe_path.write_bytes(bytes([i % 256]))
            timestamps.append(probe_path.stat().st_mtime_ns)
    except OSError as exc:
        _log.warning("could not probe mtime granularity at %s: %s", probe_path, exc)
        return None
    return timestamps, time.monotonic_ns() - loop_start_ns


# frob:ticket T-4279
# frob:tests \
# tests/unit/test_graph_stat_trust_margin.py::TestProbeMtimeGranularityNs.test_all_samp\
# les_colliding_falls_back_to_loop_span
def _granularity_bucket_for_samples(
    root: Path, timestamps: list[int], loop_elapsed_ns: int
) -> int | None:
    """Derive a `_MTIME_GRANULARITY_CANDIDATES_NS` bucket from
    `_collect_mtime_probe_samples`'s output (T-4279, split out of
    `_probe_mtime_granularity_ns` to keep it under ARCH001's length
    threshold) -- see that function's own docstring for the measurement
    rationale. `None` if even the whole loop's span is coarser than
    every candidate."""
    positive_gaps = [
        later - earlier
        for earlier, later in zip(timestamps, timestamps[1:])
        if later > earlier
    ]
    measured_gap_ns = min(positive_gaps) if positive_gaps else loop_elapsed_ns

    for candidate_ns in _MTIME_GRANULARITY_CANDIDATES_NS:
        if candidate_ns >= measured_gap_ns:
            return candidate_ns
    _log.warning(
        "mtime granularity at %s is coarser than every candidate up to "
        "%.0fs (observed gap %.0fns) -- cannot establish a safe "
        "stat-trust margin",
        root,
        _MTIME_GRANULARITY_CANDIDATES_NS[-1] / 1_000_000_000,
        measured_gap_ns,
    )
    return None


# frob:ticket T-4279
# frob:tests \
# tests/unit/test_graph_stat_trust_margin.py::TestMtimeGranularityCaching.test_second_c\
# all_does_not_reprobe
# frob:tests \
# tests/unit/test_graph_stat_trust_margin.py::TestMtimeGranularityCaching.test_on_disk_\
# cache_survives_a_fresh_in_process_cache
# frob:tests \
# tests/unit/test_graph_stat_trust_margin.py::TestMtimeGranularityCaching.test_unmeasur\
# able_result_is_not_persisted_to_disk
def _mtime_granularity_ns(root: Path) -> int | None:
    """`root`'s filesystem mtime granularity in nanoseconds, measured once
    and cached both in-process (`_mtime_granularity_cache`) and on disk
    (`_MTIME_GRANULARITY_CACHE_FILENAME`, T-4279) -- see
    `_probe_mtime_granularity_ns`'s own docstring for the measurement
    itself. `None` (unmeasurable) is cached in-process too, so a genuinely
    coarse or unwritable mount is not re-probed every call within one run,
    but is deliberately NOT written to the on-disk sidecar: a transient
    probe failure (root momentarily unwritable) should not permanently
    pin every future invocation to "never trust the fast path" once the
    underlying cause clears.
    """
    resolved = root.resolve()
    if resolved in _mtime_granularity_cache:
        return _mtime_granularity_cache[resolved]
    cache_file = resolved / ".frob" / _MTIME_GRANULARITY_CACHE_FILENAME
    try:
        cached_value = int(cache_file.read_text().strip())
        if cached_value > 0:
            _mtime_granularity_cache[resolved] = cached_value
            return cached_value
    except (OSError, ValueError):
        pass
    measured = _probe_mtime_granularity_ns(resolved)
    _mtime_granularity_cache[resolved] = measured
    if measured is not None:
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(str(measured))
        except OSError as exc:
            _log.warning(
                "could not persist mtime-granularity cache at %s: %s",
                cache_file,
                exc,
            )
    return measured


# frob:ticket T-4279
# frob:tests \
# tests/unit/test_graph_stat_trust_margin.py::TestStatTrustMarginAndTrustworthy.test_ma\
# rgin_is_granularity_times_safety_multiplier
# frob:tests \
# tests/unit/test_graph_stat_trust_margin.py::TestStatTrustMarginAndTrustworthy.test_ma\
# rgin_is_none_when_granularity_unmeasurable
def _stat_trust_margin_ns(root: Path) -> int | None:
    """The stat-trust margin (ns) for `root`'s filesystem (T-4279):
    `_STAT_TRUST_SAFETY_MULTIPLIER` times the measured mtime granularity
    (`_mtime_granularity_ns`), or `None` if granularity could not be
    established -- `_stat_trustworthy` treats `None` as "never trust a
    stat match", the safe default when the property the margin depends
    on has no measurement to rest on."""
    granularity_ns = _mtime_granularity_ns(root)
    if granularity_ns is None:
        return None
    return granularity_ns * _STAT_TRUST_SAFETY_MULTIPLIER


# frob:ticket T-4257
# frob:ticket T-4279
# frob:tests \
# tests/test_gate_cache.py::TestStatKeyCoarseClockSafety.test_recent_stat_match_falls_t\
# hrough_to_content_hash
# frob:tests \
# tests/test_gate_cache.py::TestStatKeyCoarseClockSafety.test_old_stat_match_is_trusted\
# _and_skips_reparse
# frob:tests \
# tests/unit/test_graph_stat_trust_margin.py::TestStatTrustMarginAndTrustworthy.test_no\
# ne_margin_never_trusts_regardless_of_age
# frob:tests \
# tests/unit/test_graph_stat_trust_margin.py::TestStatTrustMarginAndTrustworthy.test_st\
# at_within_margin_is_not_trusted
# frob:tests \
# tests/unit/test_graph_stat_trust_margin.py::TestStatTrustMarginAndTrustworthy.test_st\
# at_past_margin_is_trusted
# frob:tests \
# tests/unit/test_graph_stat_trust_margin.py::TestStatTrustMarginAndTrustworthy.test_co\
# arse_granularity_widens_the_untrusted_window
def _stat_trustworthy(mtime_ns: int, margin_ns: int | None) -> bool:
    """`True` iff `mtime_ns` is old enough (past `margin_ns`) for a
    matching cached `(mtime_ns, size)` to be trusted WITHOUT a
    content-hash fallback (T-4257/T-4279) -- a file whose on-disk mtime
    is still within the margin of "now" gets the safe, slightly more
    expensive verification path instead, since that is exactly the
    window a coarse or contended filesystem clock can alias two
    different writes onto the same stat pair. `margin_ns` is the
    caller's own `_stat_trust_margin_ns(root)` result for the file's
    filesystem (T-4279: derived from measured granularity, not a fixed
    constant) -- `None` (granularity unmeasurable) always returns
    `False`, forcing the content-hash path rather than guessing a value
    with no measurement behind it."""
    if margin_ns is None:
        return False
    return time.time_ns() - mtime_ns > margin_ns


def _display_path(path: Path, root: Path) -> str:
    """Repo-root-relative POSIX path for `path`."""
    return path.relative_to(root).as_posix()


# The [graph] exclude reader and matcher live in frob.excludes (the one
# copy shared with the dup/arch/cycle scanners -- T-0026); these are thin
# aliases so the graph's internal call sites keep their names.
_load_exclude_globs = _excludes.load_exclude_globs
_is_excluded = _excludes.is_excluded
# T-0239: directory-pruning helper is intentionally private in frob.excludes
# (leading underscore keeps it off the REL001 public-API surface -- it is an
# internal walker detail, not something outside consumers should call).
_should_prune_dir = _excludes._should_prune_dir  # noqa: SLF001


# frob:ticket T-0239
# frob:ticket T-0245
# frob:ticket T-0544
# frob:tests \
# tests/test_graph.py::TestExclude.test_nested_git_worktree_pruned_without_config
# frob:tests \
# tests/test_graph.py::TestExclude.test_walk_source_files_prunes_before_descent
# frob:tests tests/test_graph.py::TestExclude.test_walk_repo_files_classifies_top_level_readme_as_doc  # noqa: E501
def _walk_repo_files(
    root: Path, exclude_globs: tuple[str, ...] = ()
) -> tuple[list[Path], list[Path]]:
    """`(source_files, doc_files)` in one `os.walk` pass over `root`.

    Two things folded into one walk: excluded directories -- the builtin
    skip set, `[graph] exclude` globs, and nested git worktree checkouts --
    are pruned from `dirnames` BEFORE `os.walk` descends into them (T-0239:
    filtering files after the walk still pays the full traversal/stat cost
    of every excluded subtree). And source files and `docs/**/*.md` files
    are classified from the SAME walk (T-0245) instead of a full
    `os.walk(root)` for source files plus a separate walk of `docs/` for
    doc files -- on a mount filesystem each `os.scandir` per directory is a
    syscall, and `docs/` was being walked twice.
    """
    docs_dir = root / "docs"
    source_files: list[Path] = []
    doc_files: list[Path] = []
    exts = supported_extensions()
    # frob:waive WALK001 reason="already prunes via frob.excludes._should_prune_dir before descending (T-0239); this IS the underlying primitive walk_pruned wraps, folded with dual source/doc classification in one pass for perf, not a naive raw walk"  # noqa: E501
    for dirpath, dirnames, filenames in os.walk(root):
        dir_path = Path(dirpath)
        dirnames[:] = [
            d
            for d in dirnames
            if not _should_prune_dir(dir_path / d, root, exclude_globs)
        ]
        under_docs = dir_path == docs_dir or docs_dir in dir_path.parents
        # T-0544: a `frob:describes` anchor placed in README.md (or any other
        # top-level *.md note) used to be invisible to the design graph --
        # this walker only ever classified files under docs/ as doc files,
        # so its DESCRIBES edge (and the facet it selects for DRIFT001)
        # never existed even though gates.doclink's own root set
        # (docs/index.md, README.md) already treats README.md as a doc
        # entry point. Top-level *.md files are cheap to fold in here (one
        # directory, no recursive cost) rather than duplicating gates'
        # frob.toml-driven include/exclude glob resolution into this leaf
        # walker.
        at_repo_root = dir_path == root
        for name in filenames:
            path = dir_path / name
            suffix = Path(name).suffix.lower()
            is_source = suffix in exts
            # The ticket ledgers are top-level *.md but HISTORY, not docs:
            # archived Done reports quote frob:describes lines verbatim, and
            # classifying the ledgers as docs resurrects those historical
            # edges as live DRIFT obligations (incident: a dangling
            # describes edge under the archive's 381st done-report heading
            # appeared the moment T-0544 landed).
            is_ledger = at_repo_root and name in (
                "tickets.md",
                "tickets-archive.md",
            )
            is_doc = (under_docs or at_repo_root) and suffix == ".md" and not is_ledger
            if not is_source and not is_doc:
                continue
            if exclude_globs and _is_excluded(_display_path(path, root), exclude_globs):
                continue
            if is_source:
                source_files.append(path)
            if is_doc:
                doc_files.append(path)
    return source_files, sorted(doc_files)


def _symbol_record(rel_path: str, symbol) -> SymbolRecord:  # noqa: ANN001
    """A `SymbolRecord` for one `RawSymbol`, digests computed fresh."""
    return SymbolRecord(
        id=SymbolId(path=rel_path, qualname=symbol.qualname),
        kind=symbol.kind,
        public=symbol.public,
        digests=compute_digests(symbol),
        span=symbol.span,
    )


def _dedupe_symbols(rel_path: str, parsed: ParsedFile) -> tuple[SymbolRecord, ...]:
    """Symbol records for `parsed`, last-def-wins on duplicate symrefs.

    @typing.overload stubs and conditional redefinitions legally repeat a
    qualname in one file, and Python's own semantics are that the final def
    is the live one (T-0024; the cache's symref PRIMARY KEY made duplicates
    a hard crash before).
    """
    by_ref: dict[str, SymbolRecord] = {}
    for sym in parsed.symbols:
        record = _symbol_record(rel_path, sym)
        if record.symref in by_ref:
            _log.debug(
                "duplicate symref %s (overload/redef): last def wins", record.symref
            )
        by_ref[record.symref] = record
    return tuple(by_ref.values())


# frob:ticket T-0433
# frob:ticket T-0558
# frob:ticket T-0561
# frob:tests tests/test_graph.py::TestBuildIncremental.test_stored_hash_matches_bytes_actually_parsed  # noqa: E501
# frob:tests \
# tests/test_graph.py::TestParseFailures.test_parse_error_is_recorded_as_parse_failure
def _parse_source_file_fresh(
    conn, rel_path: str, path: Path, stat_key: tuple[int, int]
) -> tuple[
    bool,
    tuple[SymbolRecord, ...],
    tuple[Edge, ...],
    tuple[MalformedDirective, ...],
    ParseFailure | None,
]:
    """Parse one uncached source file and store the result:
    `(True, symbols, edges, malformed, parse_failure)`.

    T-0433 (G7 fix): the stored `content_hash` is `parsed.content_hash` --
    the hash `frob.lang` computed from the EXACT bytes it read and parsed
    -- never a hash read separately by the caller beforehand. `_content_hash`
    and `parse_file`/`_parse_strata_file` used to each do their own
    `read_bytes()`, so a write landing between the two reads stored the
    SECOND read's symbols under the FIRST read's hash: a cached row whose
    hash no longer described its own symbols. Hashing only the bytes that
    were actually parsed closes that window -- there is exactly one read
    per store, not two.

    T-0558: a parse/IO failure (any `LangError` other than the expected
    `NativeParserUnavailable` degrade) used to come back as
    `(True, (), (), ())` indistinguishable from a genuinely empty file --
    every public symbol and every `frob:doc`/`frob:invariant`/`frob:tests`
    edge in the file silently vanished, and COV001/DRIFT/INV all passed
    vacuously for it. Now that case also returns a non-`None`
    `ParseFailure`, which `gates._parse_failures.parse_failure_gate`
    (PARSE001) surfaces as an ERROR-severity violation instead of a
    swallowed warning.
    """
    parsed_result = parse_file(path)
    if parsed_result.is_err:
        err = parsed_result.danger_err
        if err == LangError.NativeParserUnavailable:
            # Expected degrade path (T-0133): a standalone tool install has
            # no strata-core native extension, so every .strata file skips
            # here every build -- debug, not warning, or a repo with any
            # .strata files would spam a warning line per file per run.
            # Not a ParseFailure: this is a known, environment-level
            # degrade, not a file frob.lang genuinely could not parse.
            _log.debug("skipping %s: %s", rel_path, err)
            return True, (), (), (), None
        _log.warning("skipping %s: %s", rel_path, err)
        return True, (), (), (), ParseFailure(file=rel_path, reason=str(err))
    parsed: ParsedFile = parsed_result.danger_ok
    if parsed.path != rel_path:
        # frob.lang renders paths cwd-relative (or absolute outside cwd); graph's
        # contract is always repo-root-relative, so the path is corrected here.
        parsed = parsed.model_copy(update={"path": rel_path})
    symbols = _dedupe_symbols(rel_path, parsed)
    edges, malformed = parse_directives(parsed)
    _cache.store_file_data(
        conn,
        file_path=rel_path,
        content_hash=parsed.content_hash,
        mtime_ns=stat_key[0],
        size=stat_key[1],
        symbols=symbols,
        edges=edges,
        malformed=malformed,
    )
    return True, symbols, edges, malformed, None


# frob:ticket T-0133
# frob:ticket T-0245
# frob:ticket T-0558
# frob:ticket T-0561
def _process_source_file(
    conn, root: Path, path: Path, stat_key: tuple[int, int]
) -> tuple[
    bool,
    tuple[SymbolRecord, ...],
    tuple[Edge, ...],
    tuple[MalformedDirective, ...],
    ParseFailure | None,
]:
    """Parse (or load) one source file:
    `(was_parsed, symbols, edges, malformed, parse_failure)`.

    Stat-first (T-0245): if `stat_key` (mtime_ns, size) matches what was
    stored last build, trust it and load straight from cache -- no file read
    at all. Only when the stat pair has moved does this fall back to a full
    content hash, and even then a hash match (a `touch` with no edit) still
    skips the reparse, just refreshing the stored stat.

    T-0433 (G7): the `_content_hash` computed here only decides WHETHER to
    reparse (a cheap early-out); it is never what gets stored for an
    actually-reparsed file -- `_parse_source_file_fresh` stores the hash
    `frob.lang` computed from the bytes it itself read and parsed, closing
    the old TOCTOU window where a write between this decision-read and
    `parse_file`'s own read could store fresh symbols under a stale hash.

    T-0558: an unreadable file (`_content_hash` returns `None`) is also a
    parse/IO failure whose entire obligation set silently vanished before
    this fix -- it now returns a `ParseFailure` too, same as a genuine
    `frob.lang.parse_file` error.
    """
    rel_path = _display_path(path, root)
    meta = _cache.get_file_meta(conn, rel_path)
    if meta is not None:
        cached_hash, cached_mtime_ns, cached_size = meta
        if (cached_mtime_ns, cached_size) == stat_key and _stat_trustworthy(
            stat_key[0], _stat_trust_margin_ns(root)
        ):
            _log.debug("stat cache hit: %s", rel_path)
            symbols, edges, malformed = _cache.load_file_data(conn, rel_path)
            return False, symbols, edges, malformed, None
    else:
        cached_hash = None
    on_disk_hash = _content_hash(path)
    if on_disk_hash is None:
        return (
            True,
            (),
            (),
            (),
            ParseFailure(file=rel_path, reason="could not read file for hashing"),
        )
    if on_disk_hash == cached_hash:
        # mtime moved but content did not (e.g. a checkout/touch): refresh
        # the stat so the next build takes the fast path again, but skip
        # the reparse -- the stored symbols/edges/malformed are still correct.
        _log.debug("content unchanged despite stat move: %s", rel_path)
        _cache.touch_file_stat(conn, rel_path, mtime_ns=stat_key[0], size=stat_key[1])
        symbols, edges, malformed = _cache.load_file_data(conn, rel_path)
        return False, symbols, edges, malformed, None
    return _parse_source_file_fresh(conn, rel_path, path, stat_key)


# frob:ticket T-0245
def _process_doc_file(conn, root: Path, path: Path, stat_key: tuple[int, int]) -> bool:
    """Parse (or cache-skip) one markdown file for `frob:describes` anchors.

    Same stat-first fast path as `_process_source_file` (T-0245).
    """
    rel_path = _display_path(path, root)
    meta = _cache.get_file_meta(conn, rel_path)
    if meta is not None:
        cached_hash, cached_mtime_ns, cached_size = meta
        if (cached_mtime_ns, cached_size) == stat_key and _stat_trustworthy(
            stat_key[0], _stat_trust_margin_ns(root)
        ):
            _log.debug("stat cache hit: %s", rel_path)
            return False
    else:
        cached_hash = None
    on_disk_hash = _content_hash(path)
    if on_disk_hash is None:
        return True
    if on_disk_hash == cached_hash:
        _log.debug("content unchanged despite stat move: %s", rel_path)
        _cache.touch_file_stat(conn, rel_path, mtime_ns=stat_key[0], size=stat_key[1])
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        # frob:ticket T-0402
        # G2: UnicodeDecodeError subclasses ValueError, not OSError, so it
        # was never caught here -- one non-UTF-8 .md crashed the whole
        # build (and every command layered on `Result`, hard). Degrade the
        # same way an unreadable file already does: log loudly, skip the
        # file, keep the build alive.
        _log.warning("skipping %s: %s", rel_path, exc)
        return True
    # T-1968: markdown_anchors now also returns MalformedDirectives (an
    # unhandled frob:<verb> HTML-comment directive DSL001 must see the
    # same way it already sees a code-comment malformed directive) --
    # previously hardcoded empty here, silently dropping every one.
    edges, malformed = markdown_anchors(rel_path, text)
    _cache.store_file_data(
        conn,
        file_path=rel_path,
        content_hash=on_disk_hash,
        mtime_ns=stat_key[0],
        size=stat_key[1],
        symbols=(),
        edges=edges,
        malformed=malformed,
    )
    return True


# frob:ticket T-4282
_INGEST_COMMIT_BATCH_SIZE = 200
"""Files processed between intermediate `conn.commit()` calls during
ingestion (T-4282, obligation [1]). Bounds how long `build_graph`'s single
write connection can go without committing: sqlite's rollback-journal
writer escalates to an EXCLUSIVE lock once its dirty-page cache spills to
disk, and does not release it again until the transaction actually
commits -- so one giant uncommitted transaction spanning an entire large
repo's ingest (the pre-T-4282 shape: everything committed once, in
`_finalize_build`, at the very end) holds that EXCLUSIVE lock for the
build's whole remaining duration once the first spill happens, which is
exactly what starves every concurrent reader/builder (`_cache.
connect_readonly`/`_cache.connect`) for a build's duration -- the residual
half of the T-4258 lock-starvation incident this ticket was split from.
Committing every `_INGEST_COMMIT_BATCH_SIZE` files instead lets the writer
drop back to no lock at all between batches, so readers interleave through
the gaps rather than queuing for the whole build. Safe because each
committed batch is internally consistent on its own: `_cache.
store_file_data` already replaces one file's rows (content hash, symbols,
edges, malformed) atomically per call, keyed by path, so a reader mid-
build sees some paths already updated and others still at their prior
value -- exactly the ordinary "cache lags disk until the next build"
state a reader already has to tolerate before any build even starts, not
a new inconsistency. A crash between batches similarly just leaves a
valid partial cache that the next build's own cache-hit/miss bookkeeping
picks up from, never a half-written row. `_prune_stale_cache` and the
final `set_root` (`_finalize_build`) are UNCHANGED -- still committed once
under `derived_state_write_lock`, after every batch above has landed --
because those DO touch cross-file derived state (which cached files still
exist) that must not be applied piecemeal against an in-flight walk. A
smaller batch spends more wall-clock on `commit()` overhead per build; 200
was chosen as a value that keeps individual transactions well under
sqlite's default page-cache spill threshold (~2000 pages) for the
symbol/edge/malformed row volumes this ingest typically writes per file,
without measurably slowing a full-repo build -- not derived from a
per-mount measurement, since (unlike T-4279's stat-trust margin) nothing
here depends on filesystem granularity, only on sqlite's own page-cache
size, which is not filesystem-dependent."""


# frob:ticket T-0558
# frob:ticket T-0561
# frob:ticket T-4282
def _ingest_source_files(
    conn, root: Path, source_files: Sequence[Path]
) -> tuple[set[str], int, int, tuple[ParseFailure, ...]]:
    """Process every source file; return
    `(seen_paths, parsed_count, cache_hits, parse_failures)`.

    T-0558: `parse_failures` collects every file this build could not
    parse/read at all (never cached -- see `_parse_source_file_fresh` and
    `_process_source_file` -- so a fixed file drops out on its next
    successful build).

    T-4282: commits every `_INGEST_COMMIT_BATCH_SIZE` files (see that
    constant's own docstring) instead of leaving every write in this
    build's single transaction until `_finalize_build`'s final commit --
    bounds how long a concurrent reader can be starved by this build's
    writer lock."""
    seen_paths: set[str] = set()
    parsed_count = 0
    cache_hits = 0
    parse_failures: list[ParseFailure] = []
    for index, path in enumerate(source_files, start=1):
        stat_key = _stat_key(path)
        if stat_key is None:
            continue
        seen_paths.add(_display_path(path, root))
        was_parsed, _symbols, _edges, _malformed, failure = _process_source_file(
            conn, root, path, stat_key
        )
        if was_parsed:
            parsed_count += 1
        else:
            cache_hits += 1
        if failure is not None:
            parse_failures.append(failure)
        if index % _INGEST_COMMIT_BATCH_SIZE == 0:
            conn.commit()
    return seen_paths, parsed_count, cache_hits, tuple(parse_failures)


# frob:ticket T-4282
def _ingest_doc_files(
    conn, root: Path, doc_files: Sequence[Path]
) -> tuple[set[str], int, int]:
    """Process every markdown file; return `(seen_paths, parsed_count, cache_hits)`.

    T-4282: same periodic-commit batching as `_ingest_source_files`, and
    for the identical reason -- see `_INGEST_COMMIT_BATCH_SIZE`'s
    docstring."""
    seen_paths: set[str] = set()
    parsed_count = 0
    cache_hits = 0
    for index, path in enumerate(doc_files, start=1):
        stat_key = _stat_key(path)
        if stat_key is None:
            continue
        seen_paths.add(_display_path(path, root))
        if _process_doc_file(conn, root, path, stat_key):
            parsed_count += 1
        else:
            cache_hits += 1
        if index % _INGEST_COMMIT_BATCH_SIZE == 0:
            conn.commit()
    return seen_paths, parsed_count, cache_hits


def _prune_stale_cache(conn, seen_paths: set[str]) -> None:
    """Delete cache rows for files that no longer exist on disk."""
    stale_cached = {row[0] for row in conn.execute("SELECT path FROM files")}
    for stale_path in stale_cached - seen_paths:
        _log.debug("removing deleted file from cache: %s", stale_path)
        conn.execute("DELETE FROM files WHERE path = ?", (stale_path,))
        conn.execute("DELETE FROM symbols WHERE path = ?", (stale_path,))
        conn.execute("DELETE FROM edges WHERE file = ?", (stale_path,))
        conn.execute("DELETE FROM malformed WHERE file = ?", (stale_path,))


# frob:doc docs/modules/graph.md#public-api
# frob:doc docs/commands/check.md#run-scoped-memoization
# frob:doc docs/modules/graph.md#exclusive-lock-scope-narrowed-to-the-commit-tail-t-3478  # noqa: E501
# frob:tests \
# tests/test_graph.py::TestLoadGraph.test_non_utf8_doc_file_is_skipped_not_crashed
# frob:tests tests/unit/test_memo.py::test_build_graph_second_call_is_memo_hit
# frob:tests tests/test_graph.py::TestBuildIncremental.test_stats_sum_source_and_doc_counts_not_difference  # noqa: E501
# frob:tests tests/unit/test_graph_build_lock.py
# frob:waive AFFECT002 reason="T-3478 only narrows build_graph's internal derived_state_write_lock scope (perf, no signature/behavior change observable to callers); src/frob/gates/_waive.py::_severity_overrides is out of this ticket's scope and has nothing to update"  # noqa: E501
# frob:waive AFFECT001 reason="T-4282 updated \
# docs/modules/graph.md#exclusive-lock-scope-narrowed-to-the-commit-tail-t-3478 in \
# place with the periodic-commit ingest behavior. The other two cited anchors are \
# unaffected in content: docs/modules/graph.md#public-api is a plain API listing \
# (signature/return type unchanged), and \
# docs/commands/check.md#run-scoped-memoization's own prose already states memoization \
# is orthogonal to the lock and short-circuits before reaching it -- true whether the \
# ingest commits once or in batches, so nothing there is now inaccurate"  # noqa: E501
# frob:ticket T-0423
# frob:ticket T-0918
# frob:ticket T-3478
# frob:ticket T-4282
@memoize_per_run
def build_graph(root: Path, cache: Path) -> Result[GraphSnapshot, BuildError]:
    """Incrementally (re)build the obligation graph for `root` into `cache`.

    Memoized per `frob check` run (T-0423, `frob.check._memo.memoize_
    per_run`): a second call with the same `(root, cache)` in the same run
    is a cache hit, not a re-walk -- closes the "same heavy analysis reruns
    across stages" class the T-0418 arch double-run was one instance of.

    T-0918/T-3478: only the CACHE-MUTATING tail -- `_prune_stale_cache`
    plus `_finalize_build`'s `conn.commit()` -- is wrapped in
    `frob.process._lock.derived_state_write_lock`, which takes a real
    cross-process EXCLUSIVE `derived_state_lock` when called standalone
    but no-ops when this process already holds the lock in another thread
    (e.g. nested inside `frob check`'s SHARED hold) -- see that function's
    docstring for the full reentrancy contract. T-0918 originally held
    this lock around the ENTIRE rebuild (walk + parse of every file, not
    just the commit), which serializes concurrent `build_graph` calls
    (e.g. xdist test workers) behind each other for the full parse
    duration instead of just the cheap final commit -- measured as a
    ~19-minute CI tail stall (T-3478). Narrowing is sound because:
    `_cache.connect` and every per-file write inside `_ingest_source_
    files`/`_ingest_doc_files` (`_cache.store_file_data`) already retry
    past sqlite-level lock contention on their own (T-1423,
    `_cache._with_lock_retry`); the lock this docstring is about is
    `frob.process._lock.derived_state_write_lock` (an in-repo cross-
    process mutex frob owns), not sqlite's own lock -- what it guards is
    cross-file DERIVED state (which cached files still exist, per
    `_prune_stale_cache`), which must not be applied against an
    in-flight walk from a sibling. Per-file writes need no such guard:
    each is independently keyed by path and already safe to observe
    mid-build (T-4282: `_ingest_source_files`/`_ingest_doc_files` now
    commit them in batches rather than leaving all of them in one
    transaction open until this function's own final `conn.commit()`,
    specifically so a concurrent reader is not starved for this build's
    entire duration -- see `_INGEST_COMMIT_BATCH_SIZE`'s docstring). The
    exclusive hold only needs to cover the point from which the PRUNE
    decision (and the final commit landing it) is made, which is exactly
    what stays locked below.

    T-1423: `_cache.CacheLocked` (raised once `_cache._with_lock_retry`'s
    own retry budget is exhausted under sustained contention) is caught
    here and reported as `Err(GraphError.CacheLocked)`, never an unhandled
    exception reaching `main()`'s top-level handler -- both around the
    unlocked `connect`/parse phase and around the locked commit phase.
    """
    root = root.resolve()
    _log.info("build_graph: root=%s cache=%s", root, cache)
    try:
        conn = _cache.connect(cache)
    except _cache.CacheLocked as exc:
        _log.error("build_graph: cache lock never released: %s", exc)
        return Err(GraphError.CacheLocked)
    try:
        exclude_globs = _load_exclude_globs(root)
        source_files, doc_files = _walk_repo_files(root, exclude_globs)

        src_seen, src_parsed, src_hits, parse_failures = _ingest_source_files(
            conn, root, source_files
        )
        doc_seen, doc_parsed, doc_hits = _ingest_doc_files(conn, root, doc_files)
        seen_paths = src_seen | doc_seen
        parsed_count = src_parsed + doc_parsed
        cache_hits = src_hits + doc_hits

        with derived_state_write_lock(root):
            _prune_stale_cache(conn, seen_paths)
            snapshot = _finalize_build(
                conn, root, parsed_count, cache_hits, parse_failures
            )
        return Ok(snapshot)
    except _cache.CacheLocked as exc:
        _log.error("build_graph: cache lock never released: %s", exc)
        return Err(GraphError.CacheLocked)
    finally:
        conn.close()


# frob:ticket T-0216
def _log_malformed_files(malformed: tuple[MalformedDirective, ...]) -> None:
    """WARN-log every malformed directive's file:line + parse error (T-0216):
    the aggregate `malformed=N` build-summary count alone gives no way to
    find which file to fix. Runs on every build, including all-cache-hit
    rebuilds, where the per-file warning in `dsl.parse_directives` never
    fires because cached malformed rows are loaded, not re-parsed."""
    for item in malformed:
        _log.warning(
            "malformed directive: %s:%d: %s", item.file, item.line, item.reason
        )


# frob:ticket T-0558
# frob:ticket T-0561
def _log_parse_failures(parse_failures: tuple[ParseFailure, ...]) -> None:
    """WARN-log every parse/IO failure's file + reason, same shape as
    `_log_malformed_files` (T-0216) -- the aggregate count alone gives no
    way to find which file to fix."""
    for item in parse_failures:
        _log.warning("parse failure: %s: %s", item.file, item.reason)


def _finalize_build(
    conn,
    root: Path,
    parsed_count: int,
    cache_hits: int,
    parse_failures: tuple[ParseFailure, ...] = (),
) -> GraphSnapshot:
    """Persist the root, commit, and load the final snapshot with build stats.

    T-0558: `parse_failures` is never persisted to the cache (a failed
    file is never `store_file_data`-d, so the next build simply retries
    it) -- it is folded into the returned snapshot here, live, for this
    build only.
    """
    _cache.set_root(conn, root.as_posix())
    conn.commit()
    stats = BuildStats(parsed=parsed_count, cache_hits=cache_hits)
    snapshot = _cache.load_all(conn, stats=stats)
    if parse_failures:
        snapshot = snapshot.model_copy(update={"parse_failures": parse_failures})
    _log_malformed_files(snapshot.malformed)
    _log_parse_failures(snapshot.parse_failures)
    _log.info(
        "build_graph: done, parsed=%d hits=%d symbols=%d edges=%d malformed=%d "
        "parse_failures=%d",
        parsed_count,
        cache_hits,
        len(snapshot.symbols),
        len(snapshot.edges),
        len(snapshot.malformed),
        len(snapshot.parse_failures),
    )
    return snapshot


# frob:ticket T-0361
# frob:ticket T-0245
def _first_stale_cached_file(conn: sqlite3.Connection, root: Path) -> str | None:
    """The first cached file path whose on-disk state no longer matches the
    cache, or `None` if every cached file still matches; split out of
    `load_graph`'s staleness-check loop (T-0361).

    Stat-first (T-0245): a matching `(mtime_ns, size)` trusts the cache with
    one `os.stat` per file; only a stat mismatch pays for a full content
    read to confirm the bytes actually moved (a `touch` alone should not
    force `CacheStale`). This is the hot path every gate invocation runs
    through, so it is where the mount-filesystem per-file cost (T-0245:
    0.5ms/stat under load) matters most.
    """
    for path, stored_hash, stored_mtime_ns, stored_size in conn.execute(
        "SELECT path, content_hash, mtime_ns, size FROM files"
    ):
        stat_key = _stat_key(root / path)
        if stat_key is not None and stat_key == (stored_mtime_ns, stored_size):
            continue
        current = _content_hash(root / path)
        if current != stored_hash:
            return path
    return None


# frob:ticket T-0402
def _first_added_file(
    conn: sqlite3.Connection, root: Path, exclude_globs: tuple[str, ...]
) -> str | None:
    """The first on-disk source/doc path with no `files` cache row, or
    `None` if every on-disk path is already cached (T-0402, G1).

    `_first_stale_cached_file` only iterates rows already IN the cache, so
    it can never see a file that has never been ingested at all -- a
    brand-new source or doc file made `load_graph` return `Ok` on a
    snapshot silently missing that file's symbols, edges, malformed
    directives, and doc obligations. This pays one extra `os.walk` (the
    same walk `build_graph` already pays) to catch additions, the one
    staleness shape `_first_stale_cached_file`'s hash-only loop cannot see.
    """
    cached = {row[0] for row in conn.execute("SELECT path FROM files")}
    source_files, doc_files = _walk_repo_files(root, exclude_globs)
    for path in source_files + doc_files:
        rel_path = _display_path(path, root)
        if rel_path not in cached:
            return rel_path
    return None


# frob:doc docs/modules/graph.md#public-api
# frob:ticket T-0232
# frob:tests tests/test_graph.py::TestLoadGraph.test_cache_stale_after_new_file_added
# frob:tests tests/test_graph.py::TestLoadGraph.test_cache_stale_after_new_doc_added
def load_graph(cache: Path) -> Result[GraphSnapshot, GraphError]:
    """Cache-only read: `Err(CacheStale)` if any on-disk hash moved, `Err(CacheCorrupt)`
    if the cache is unreadable, schema-mismatched, or has never been built.

    Opens `cache` via `connect_readonly` (T-0232), not `connect`: a pure
    read has no business taking sqlite's single writer slot, and doing so
    is what serialized concurrent `frob` invocations (agent loop, CI, a
    background `frob vet`) behind each other's cache writes even when
    neither side had anything to write. A cache this can't open read-only
    (missing, corrupt, or mid-rebuild) is exactly `CacheCorrupt` territory
    -- self-healing it is `build_graph`'s job, not a reader's.

    frob:ticket T-0799
    A read-only connection can never DDL its way out of schema drift the
    way `connect()`'s `_apply_schema_with_recovery` does -- a pre-migration
    cache.db (missing a table T-0245/T-0279 added, or missing a column like
    `mtime_ns`) surfaces as `sqlite3.OperationalError` ("no such table:
    symbols", "no such column: mtime_ns") from whatever query happens to
    touch the drifted shape first: `get_root`, the staleness probes, or
    `load_all`. Two such crashes escaped this function mid-land on
    2026-07-23 (one leaving a partial squash staged on main) because only
    `get_root`'s own query was guarded -- every query after it was not. The
    whole read body is wrapped in one `OperationalError` handler now: ANY
    schema-shape error anywhere in this function is `CacheCorrupt`, never a
    propagating exception -- `build_graph` (via `connect()`'s schema-version
    check) is what actually rebuilds it on the next write.
    """
    if not cache.exists():
        _log.warning("load_graph: no cache at %s", cache)
        return Err(GraphError.CacheCorrupt)
    try:
        conn = _cache.connect_readonly(cache)
    except _cache.CacheLocked as exc:
        # T-1423: contended, not corrupt -- do not conflate the two, or a
        # transient lock triggers a needless cache rebuild downstream.
        _log.error("load_graph: cache lock never released at %s: %s", cache, exc)
        return Err(GraphError.CacheLocked)
    except Exception as exc:  # sqlite3.DatabaseError and friends
        _log.error("load_graph: cache unreadable at %s: %s", cache, exc)
        return Err(GraphError.CacheCorrupt)
    try:
        return _load_graph_from_connection(conn, cache)
    finally:
        conn.close()


# frob:ticket T-0976
def _load_graph_from_connection(conn, cache: Path) -> Result[GraphSnapshot, GraphError]:  # noqa: ANN001
    """`load_graph`'s read body once a read-only connection is open: root/
    staleness/added-file checks, then `_cache.load_all` -- split out so
    `load_graph` itself only owns opening and closing `conn`. Any schema-
    shape `OperationalError`/`DatabaseError` here (T-0799) is `CacheCorrupt`,
    never a propagating exception."""
    try:
        root_str = _cache.get_root(conn)
        if root_str is None:
            _log.warning("load_graph: cache at %s has never been built", cache)
            return Err(GraphError.CacheCorrupt)
        root = Path(root_str)
        stale_path = _first_stale_cached_file(conn, root)
        if stale_path is not None:
            _log.warning("load_graph: %s drifted from cache", stale_path)
            return Err(GraphError.CacheStale)
        # T-0402: G1, a hash-only staleness loop is blind to files added
        # since the last build (they simply have no cache row to compare
        # against). Catch that shape too, or a load-only reader silently
        # operates on an incomplete graph forever, never re-triggering a
        # rebuild.
        exclude_globs = _load_exclude_globs(root)
        added_path = _first_added_file(conn, root, exclude_globs)
        if added_path is not None:
            _log.warning("load_graph: %s added since cache built", added_path)
            return Err(GraphError.CacheStale)
        snapshot = _cache.load_all(conn)
    except _cache.CacheLocked as exc:
        # T-1423: contended, not corrupt -- distinct from the OperationalError
        # branch below, which is genuine schema drift.
        _log.error("load_graph: cache lock never released at %s: %s", cache, exc)
        return Err(GraphError.CacheLocked)
    except sqlite3.OperationalError as exc:
        # T-0799: schema drift (missing table/column from a pre-migration
        # cache.db) surfaces here as a query-time OperationalError, not at
        # connect time -- a read-only connection cannot self-heal it, so
        # treat it exactly like the corrupt-bytes case: give up and let
        # the writer path rebuild.
        _log.error("load_graph: schema mismatch/unreadable cache at %s: %s", cache, exc)
        return Err(GraphError.CacheCorrupt)
    except sqlite3.DatabaseError as exc:
        # A read-only connection cannot self-heal a garbage/corrupt file
        # the way `connect()` does (T-0232) -- that would require a write.
        # Corrupt bytes surface as a query-time error here rather than at
        # connect time; still `CacheCorrupt`, same as the old self-healing
        # path's outcome once it found no root ever recorded.
        _log.error("load_graph: cache unreadable at %s: %s", cache, exc)
        return Err(GraphError.CacheCorrupt)
    _log.info(
        "load_graph: loaded %d symbols, %d edges",
        len(snapshot.symbols),
        len(snapshot.edges),
    )
    return Ok(snapshot)


# frob:doc docs/modules/graph.md#public-api
def edges_from(snapshot: GraphSnapshot, ref: str) -> tuple[Edge, ...]:
    """All edges whose `src` is exactly `ref`."""
    return tuple(edge for edge in snapshot.edges if edge.src == ref)


# frob:doc docs/modules/graph.md#public-api
def edges_to(snapshot: GraphSnapshot, target: str) -> tuple[Edge, ...]:
    """All edges whose `target` is exactly `target`."""
    return tuple(edge for edge in snapshot.edges if edge.target == target)


__all__ = [
    "AffectedSet",
    "BuildError",
    "BuildStats",
    "CallGraph",
    "Digests",
    "DanglingEdge",
    "DriftReport",
    "Edge",
    "EdgeKind",
    "FunctionSummary",
    "GraphError",
    "GraphSnapshot",
    "LockEntry",
    "LockError",
    "LockFile",
    "MalformedDirective",
    "OrderedCallGraph",
    "ParseFailure",
    "PrivateHelperGap",
    "SCCTimeout",
    "ScopeClosureGap",
    "StaleItem",
    "SummaryResult",
    "SymbolId",
    "SymbolRecord",
    "acknowledge",
    "affects",
    "build_call_graph",
    "build_graph",
    "build_ordered_call_graph",
    "build_reference_graph",
    "closure",
    "compute_protocol_summaries",
    "dedupe_slug",
    "edges_from",
    "edges_to",
    "fold_comment_runs",
    "is_generated_source",
    "load_graph",
    "load_lock",
    "resolve",
    "scope_doc_code_gaps",
    "scope_private_helper_gaps",
    "scope_test_gaps",
    "slugify",
    "write_lock",
]

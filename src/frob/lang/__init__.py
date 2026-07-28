"""Uniform parsing across six grammars (docs/modules/graph.md, Phase 1; T-0077).

`frob.graph` needs one shape -- symbols plus comments plus a content hash --
regardless of whether the source file is Python, TypeScript, Rust, C, C++,
or a `.strata` design file. Hand-rolling bespoke parsers (the fate of the
retired, Python-only predecessor module) means one place to fix every bug
per language and just as many places graph-level assumptions can silently
drift apart. `tree-sitter-language-pack` gives one grammar-loading
mechanism for the five code languages; this package gives one extraction
contract on top of it. `.strata` has no tree-sitter grammar, so it routes
through strata-core's own parser instead (`frob.lang._walk_strata`) but
produces the identical `ParsedFile` contract -- see `parse_file`.
Everything language-specific (node-type tables, publicness rules, doc-
comment conventions) lives in `_extract.py`'s per-language walkers or
`_walk_strata.py`; everything else (models, dispatch, hashing, the Result
boundary) lives here.
"""
# frob:waive ARCH102 reason="post-T-0989 split, the remaining cluster count is a real \
# blind spot in the naming/usage heuristic, not real fragmentation: this module's \
# exports fall into two groups, each cohesive around a shared resource the clustering \
# pass cannot see because it only tracks name prefixes and direct calls. (1) \
# supported_languages/supported_extensions/language_for_extension/ \
# tree_sitter_extensions all read the same module-level \
# _EXTENSION_TABLE/_SUPPORTED_LANGUAGES constants by subscript, never by calling each \
# other. (2) reset_parse_cache/parse_cache_stats/ \
# partial_parse_files/parse_file/_parse all read or mutate the same module-level \
# _parse_cache dict and _parse_cache_hits/ _parse_cache_misses counters directly, \
# again by shared state rather than calls -- this is the exact same call-graph blind \
# spot T-0977 fixed for data-only classes, generalized to shared-mutable-state \
# modules; splitting the cache-memo functions away from the cache dict they close over \
# would force the cache into its own tiny module with no callers but this one. The \
# third group named in the prior waiver reason \
# (cpp_function_nodes/child_by_field/node_text/ resolve_local_import) has been \
# extracted to `frob.lang._nodes` and re-exported here (T-0989); re-measure after this \
# change decided whether this waiver remains needed at the new, lower cluster count"

from __future__ import annotations

import hashlib
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import TypeVar

from tree_sitter import Tree
from tree_sitter_language_pack import get_parser
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.lang._common import export_tree as _export_tree
from frob.lang._common import flatten_tree
from frob.lang._extract import COMMENT_TYPES, extract
from frob.lang._extract import extract_imports as _extract_imports
from frob.lang._extract import iter_identifiers as _iter_identifiers
from frob.lang._models import ParsedFile, RawComment, RawSymbol, SymbolKind, TreeNode
from frob.lang._nodes import (
    child_by_field,
    cpp_function_nodes,
    node_text,
    resolve_local_import,
)
from frob.lang._support import (
    FACETS,
    FacetState,
    FacetStatus,
    LanguageSupport,
    conformance_violations,
    derive_language_registry,
)
from frob.lang._walk_strata import NATIVE_UNAVAILABLE_MESSAGE as _NATIVE_UNAVAIL_MSG
from frob.lang._walk_strata import walk_strata as _walk_strata
from frob.logging import get_logger

_log = get_logger(__name__)

_T = TypeVar("_T")


# frob:doc docs/modules/lang.md#error-types
class LangError(ErrorSet):
    """Failure values `parse_file` can return -- never a bare exception."""

    UnsupportedLanguage = "File extension has no registered grammar"
    ParseFailed = "tree-sitter could not produce a usable tree"
    IoFailed = "File could not be read"
    NativeParserUnavailable = (
        "strata-core native extension unavailable in this install (T-0133)"
    )
    FileTooLarge = "File exceeds the max parseable size (T-0893)"
    ParseTimedOut = "Parse did not finish inside the wall-clock budget (T-0893)"


# extension -> (tree-sitter-language-pack grammar name, ParsedFile.language label)
_EXTENSION_TABLE: dict[str, tuple[str, str]] = {
    ".py": ("python", "python"),
    ".ts": ("typescript", "typescript"),
    ".tsx": ("tsx", "typescript"),
    ".rs": ("rust", "rust"),
    ".c": ("c", "c"),
    ".h": ("c", "c"),
    ".cpp": ("cpp", "cpp"),
    ".hpp": ("cpp", "cpp"),
    ".cc": ("cpp", "cpp"),
    ".hh": ("cpp", "cpp"),
    ".cxx": ("cpp", "cpp"),
    # frob:ticket T-0723
    # T-0613's `parse_kotlin`/`raw_kotlin_tree` already load kotlin's
    # grammar through this SAME `get_parser` chokepoint standalone; this
    # entry is what actually makes `.kt`/`.kts` reach `parse_file`'s
    # general `extract()` dispatch (`_extract.py`'s `_WALKERS`/
    # `COMMENT_TYPES`, both now carrying a "kotlin" entry too -- see
    # `frob.lang._walk_kotlin._walk_kotlin`).
    ".kt": ("kotlin", "kotlin"),
    ".kts": ("kotlin", "kotlin"),
}

# `.strata` has no tree-sitter grammar (`_parse`/`_EXTENSION_TABLE` below
# is tree-sitter-only) -- `parse_file` special-cases it through
# `frob.lang._walk_strata` instead (docs/modules/lang.md#strata, T-0077).
# It is still a first-class `frob.lang` language for every purpose
# `supported_languages()` signals: `parse_file` succeeds, symbols/comments
# come back, and `frob.graph`/`frob.check` can bind `frob:doc`/`frob:tests`
# to strata qualnames like any other grammar's. `extract_imports`,
# `iter_identifiers`, `raw_tree`, and `symbol_tree` are tree-sitter escape
# hatches with no strata analogue yet and return `Err(UnsupportedLanguage)`
# for `.strata` paths -- see each function's docstring.
_STRATA_EXTENSION = ".strata"
_STRATA_LANGUAGE = "strata"

_SUPPORTED_LANGUAGES = frozenset(
    label for _grammar, label in _EXTENSION_TABLE.values()
) | {_STRATA_LANGUAGE}

_SUPPORTED_EXTENSIONS = frozenset(_EXTENSION_TABLE) | {_STRATA_EXTENSION}

# Extensions `parse_file` can turn into symbols/comments via tree-sitter's
# `raw_tree`/`symbol_tree` escape hatches (T-0129) -- `.strata` is excluded
# because it has no tree-sitter grammar; see `_STRATA_EXTENSION` above and
# each escape hatch's own `.strata` handling for the precise boundary.
_TREE_SITTER_EXTENSIONS = frozenset(_EXTENSION_TABLE)

# frob:ticket T-0433
# frob:doc docs/modules/lang.md#dependencies
# frob:tests tests/test_graph.py::TestBuildIncremental.test_fingerprint_packages_derived_from_lang_registry  # noqa: E501
# T-0433 (G6): the installed-distribution names whose VERSION changing can
# change what every non-`.strata` grammar in `_EXTENSION_TABLE` parses to.
# `tree_sitter_language_pack.get_parser` is the ONE loading mechanism every
# tree-sitter language in this module goes through (see the module
# docstring) -- so it, plus the `tree-sitter` core library it is built on,
# are the entire fingerprint surface for ALL six grammars today, not a
# per-language package. `frob.graph.cache._compute_fingerprint` derives its
# cache-invalidation fingerprint from this set (plus its own non-language
# packages, `frob` and `strata-core`) instead of hand-copying a tuple here
# -- adding a new `_EXTENSION_TABLE` grammar via `tree_sitter_language_pack`
# needs no fingerprint update at all; a language added through some OTHER
# package (a standalone `tree-sitter-<lang>` binding imported directly,
# bypassing the language pack) must be added here too, or a cache row for
# it can go stale exactly like the T-0243 incident this mechanism exists
# to prevent.
GRAMMAR_FINGERPRINT_PACKAGES = frozenset({"tree-sitter", "tree-sitter-language-pack"})


# frob:doc docs/modules/graph.md#public-api
def supported_languages() -> frozenset[str]:
    """The set of `ParsedFile.language` labels `parse_file` can ever produce."""
    return _SUPPORTED_LANGUAGES


# frob:doc docs/modules/graph.md#public-api
# frob:ticket T-0129
def supported_extensions() -> frozenset[str]:
    """The canonical set of file extensions `parse_file` accepts (T-0129).

    The single source of truth every `frob.lang` consumer (`frob.graph`,
    `frob.outline`, `frob.xref`, `frob.testing`, `frob.policy`,
    `frob.app.cycle_runner`, `frob.arch`) should filter files through
    instead of hand-maintaining its own duplicate extension table -- see
    docs/modules/lang.md#supported-extensions.
    """
    return _SUPPORTED_EXTENSIONS


# frob:doc docs/modules/graph.md#public-api
# frob:ticket T-0129
def language_for_extension(ext: str) -> str | None:
    """The `ParsedFile.language` label `parse_file` would produce for `ext`, or `None`.

    The canonical extension-to-language mapping (T-0129) -- callers that
    need to know a file's language label without parsing it (e.g.
    `frob.testing._select`'s touched-set-to-test-suite mapping) should use
    this instead of hand-copying `_EXTENSION_TABLE`'s entries.
    """
    ext = ext.lower()
    if ext == _STRATA_EXTENSION:
        return _STRATA_LANGUAGE
    entry = _EXTENSION_TABLE.get(ext)
    return entry[1] if entry is not None else None


# frob:doc docs/modules/graph.md#public-api
# frob:ticket T-0129
def tree_sitter_extensions() -> frozenset[str]:
    """Extensions `parse_file` routes through tree-sitter (excludes `.strata`, T-0129).

    For consumers that specifically need the tree-sitter-only escape hatches
    (`raw_tree`, `symbol_tree`, `extract_imports`, `iter_identifiers`), which
    return `Err(UnsupportedLanguage)` for `.strata` -- see each function's
    docstring and docs/modules/lang.md#supported-extensions.
    """
    return _TREE_SITTER_EXTENSIONS


def _display_path(path: Path) -> str:
    """Repo-relative POSIX path when possible, else the path as given."""
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


# frob:ticket T-0893
#: Maximum source-file size `_parse`/`_parse_strata_file` will attempt to
#: parse, in bytes. Both entry points visit files from a caller-supplied
#: (potentially untrusted, adopter-repo) tree with no upper bound of their
#: own before this -- an oversized file could exhaust memory just being
#: read into `bytes`, well before it ever reaches tree-sitter/strata-core.
#: Checked against `Path.stat().st_size` BEFORE `read_bytes()` so a file
#: over the cap is never even fully read. 8 MiB comfortably covers every
#: legitimate source file this repo's own graph walk has ever visited
#: (docs/audits/perf.md's largest-file measurements are sub-1MiB) while
#: staying small enough that a full read+parse attempt at the cap stays
#: bounded in both memory and (combined with `_PARSE_TIMEOUT_SECONDS`
#: below) wall-clock time.
_MAX_PARSE_FILE_BYTES = 8 * 1024 * 1024  # 8 MiB

# frob:ticket T-0893
#: Wall-clock budget, in seconds, for a single tree-sitter/strata-core
#: parse call (`_run_parse_with_timeout`). tree-sitter's error-recovery is
#: generally fast but not immune to pathological input (deeply nested
#: brackets/parens can drive quadratic-ish recovery); with no cap at all a
#: single adversarial or merely enormous file could hang an entire `frob
#: check` run. 10s is generous relative to the largest legitimate parse
#: observed in this repo's own perf audits (sub-second per file, even for
#: the largest source files) while still failing well within a single
#: foreground command's patience (docs/guides/agent-playbook.md section
#: 3b's ~120s auto-background cap).
_PARSE_TIMEOUT_SECONDS = 10.0


# frob:doc docs/modules/lang.md#size-cap-and-parse-timeout-t-0893
# frob:tests tests/test_lang.py::TestSizeCapAndTimeout.test_oversized_file_is_skipped_loudly  # noqa: E501
# frob:waive COV007 reason="docs/modules/lang.md's Size cap and parse timeout section \
# (T-0893) is a deliberate, per-function architecture doc of this module's internal \
# DoS guards, same convention as the Primitives section's private tree-sitter helpers"
def _check_size_cap(path: Path, size: int) -> LangError | None:
    """LOUD PARSE-family skip for a file over `_MAX_PARSE_FILE_BYTES` (T-0893).

    Returns `LangError.FileTooLarge` to short-circuit the caller with, or
    `None` if `size` is within the cap. Always logs at WARNING -- naming
    both the file and the exact limit hit -- so a skip is visible in plain
    `frob check` output, not just via `frob.graph.GraphSnapshot.
    parse_failures` (PARSE001) for a caller that reads it; this is the
    loud-skip discipline T-0897's silent-drop incident (a skip with no
    diagnostic at all) exists to prevent from recurring here.
    """
    if size <= _MAX_PARSE_FILE_BYTES:
        return None
    _log.warning(
        "PARSE: skipping %s -- %d bytes exceeds the %d byte max-parse-size "
        "cap (T-0893); file too large to safely parse",
        path,
        size,
        _MAX_PARSE_FILE_BYTES,
    )
    return LangError.FileTooLarge


# frob:doc docs/modules/lang.md#size-cap-and-parse-timeout-t-0893
# frob:tests tests/test_lang.py::TestSizeCapAndTimeout.test_parse_timeout_returns_err_not_hang  # noqa: E501
# frob:waive COV007 reason="docs/modules/lang.md's Size cap and parse timeout section \
# (T-0893) is a deliberate, per-function architecture doc of this module's internal \
# DoS guards, same convention as the Primitives section's private tree-sitter helpers"
def _run_parse_with_timeout(
    fn: Callable[[], _T], path: Path, budget: float = _PARSE_TIMEOUT_SECONDS
) -> Result[_T, LangError]:
    """Run zero-arg `fn` (a tree-sitter/strata-core parse call) under a
    `budget`-second wall-clock cap (T-0893).

    Neither tree-sitter nor strata-core expose a cancellation hook, so a
    call that blows the budget is left running on its own single-use
    daemon-pool thread (abandoned, never joined or killed -- the same
    bounded-wait shape `frob.vet._scan._run_with_timeout` already uses for
    subprocess calls, minus the ability to actually terminate the worker)
    while this returns `Err(LangError.ParseTimedOut)` immediately so the
    caller is never blocked past `budget`. Always logs at WARNING naming
    the file and the exact limit hit -- see `_check_size_cap`'s docstring
    for why a skip must never be silent.
    """
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn)
    try:
        return Ok(future.result(timeout=budget))
    except FutureTimeoutError:
        _log.warning(
            "PARSE: %s did not finish parsing within the %.1fs budget "
            "(T-0893); skipping -- the worker thread is abandoned, not "
            "killed (tree-sitter/strata-core expose no cancellation hook)",
            path,
            budget,
        )
        return Err(LangError.ParseTimedOut)
    finally:
        executor.shutdown(wait=False)


# T-0414: process-lifetime, content-hash-keyed memo for `_parse` -- the
# single read+tree-sitter-parse chokepoint every `frob.lang` entry point
# funnels through (see docs/audits/perf.md H4). Before this cache, a 213-
# file source tree was independently re-read and re-parsed by every stage
# that touches source (arch 2x, vet 3x, selfconform 6x via vet) -- ~2000-
# 2500 tree-sitter parses per `frob check` where ~213 would suffice. Keyed
# on `(path, sha256(content))`, NEVER on mtime/size alone (T-0414's
# correctness mandate: a stale or wrong cached tree would silently corrupt
# every gate that reads it) -- a content change always misses the cache and
# reparses, even if the path is unchanged; a path revisited with byte-
# identical content always hits, even across two different calling stages.
# Guarded by a lock since `frob check`'s gate stages run concurrently in a
# `ThreadPoolExecutor` (`frob.check._run_tasks_concurrently`).
_parse_cache_lock = threading.Lock()
_parse_cache: dict[str, Result[tuple[Tree, bytes, str], LangError]] = {}
_parse_cache_hits = 0
_parse_cache_misses = 0

# frob:ticket T-0555
#: Repo-relative-ish display paths (`_display_path`) of every file whose
#: tree-sitter parse was salvaged around a syntax error since the last
#: `reset_parse_cache` -- T-0404 finding 9's visibility instrument.
#: `_parse` treats such a tree as usable (a hard `Err` would blank out
#: doc/coverage checking for the whole file over one typo), but every
#: symbol after the error region is silently absent from it; this set lets
#: a caller (a future gate, `frob check -v`, or a test) see exactly which
#: files lost symbols this way, not just a scattered WARNING log line
#: (`_warn_if_partial_tree`, T-0434) that only appears above the default
#: log level.
_partial_parse_files: set[str] = set()


# frob:doc docs/modules/lang.md#parse-cache
# frob:ticket T-0555
# frob:ticket T-0905
# frob:tests tests/test_lang.py::TestParseCache.test_reset_clears_counters  # noqa: E501
def partial_parse_files() -> tuple[str, ...]:
    """Display paths of every partially-parsed file since the last
    `reset_parse_cache` (T-0404 finding 9), sorted for determinism.

    A file appears here whenever tree-sitter salvaged a tree with
    `has_error=True` for it -- meaning symbols inside the broken region
    were silently dropped from extraction. Ruff/ty independently catch a
    Python syntax error via their own diagnostics; Rust/C++/TS have no such
    independent signal (T-0404 finding 1: no gates stage runs there at
    all), so this is the only visibility mechanism for those languages
    today. Consumed by `frob.gates._parse_failures.parse_failure_gate` as
    PARSE002 (T-0905) -- no longer just an unconsumed accessor.
    """
    with _parse_cache_lock:
        return tuple(sorted(_partial_parse_files))


# frob:doc docs/modules/lang.md#parse-cache
# frob:ticket T-0414
def reset_parse_cache() -> None:
    """Clear the process-lifetime `_parse` memo and its hit/miss counters.

    Called once per `frob check` invocation (`frob.check._run_check_with_
    skips`) so the anti-regression instrument (`parse_cache_stats`) reports
    counts for a single run rather than accumulated state across an entire
    process (e.g. a long-lived test session or MCP server). Never required
    for correctness -- the cache is content-hash-keyed, not invocation-
    scoped, so stale entries are simply never returned for changed content;
    this only resets instrumentation and frees memory held by old trees.
    """
    global _parse_cache_hits, _parse_cache_misses
    with _parse_cache_lock:
        _parse_cache.clear()
        _parse_cache_hits = 0
        _parse_cache_misses = 0
        _partial_parse_files.clear()


# frob:doc docs/modules/lang.md#parse-cache
# frob:ticket T-0414
def parse_cache_stats() -> tuple[int, int]:
    """(hits, misses) against the `_parse` memo since the last `reset_parse_cache`.

    The T-0414 anti-regression instrument: a test asserts each distinct
    `(path, content)` is parsed (a miss) at most once per invocation, no
    matter how many stages (`graph`, `arch`, `vet`, `dup`) call through
    `frob.lang`'s public entry points for it.
    """
    with _parse_cache_lock:
        return _parse_cache_hits, _parse_cache_misses


# frob:ticket T-0434
# frob:ticket T-0555
# frob:ticket T-0905
def _warn_if_partial_tree(tree: Tree, path: Path) -> None:
    """WARN when `tree` was salvaged around a syntax error (T-0402 finding G9).

    tree-sitter can return a tree with `has_error` set but children still
    present -- `_parse` treats that as usable (a hard `Err` would blank out
    doc/coverage checking for the whole file over one typo), but every
    symbol after the error region is silently absent from the salvaged
    tree, and with it every `frob:` directive obligation attached to those
    symbols (docs/audits/graph.md). This log line is the loud signal for
    that otherwise-invisible loss.

    T-0404 finding 9: also records `path` into `_partial_parse_files` so
    `partial_parse_files()` gives a structured, queryable answer (not just
    a log line only visible above the default log level) -- the same
    "log line existed but nothing consumed it" gap noted for Rust/C++/TS,
    which have no gates stage at all (finding 1) to notice a WARNING here.
    T-0905 closed that gap: `frob.gates._parse_failures.parse_failure_gate`
    now turns every entry into a PARSE002 ERROR violation instead of a
    silently-unconsumed accessor.
    """
    if tree.root_node.has_error:
        _log.warning(
            "tree-sitter produced a PARTIAL tree for %s "
            "(syntax error present, some top-level symbols may be "
            "silently dropped from the salvaged tree)",
            path,
        )
        with _parse_cache_lock:
            _partial_parse_files.add(_display_path(path))


# frob:doc docs/modules/lang.md#size-cap-and-parse-timeout-t-0893
# frob:tests tests/test_lang.py::TestSizeCapAndTimeout.test_oversized_file_is_skipped_loudly  # noqa: E501
# frob:waive COV007 reason="docs/modules/lang.md's Size cap and parse timeout section \
# (T-0893) is a deliberate, per-function architecture doc of this module's internal \
# DoS guards, same convention as the Primitives section's private tree-sitter helpers"
def _read_source_under_cap(path: Path) -> Result[bytes, LangError]:
    """`stat` then `read_bytes` `path`, refusing anything over
    `_MAX_PARSE_FILE_BYTES` (T-0893) before the read happens.

    Split out of `_parse` purely to keep `_parse` under ARCH001's line
    threshold once the size-cap/timeout guard was added -- the stat-check-
    read sequence is one cohesive "safely obtain source bytes" step with no
    internal branch either caller needs to see.
    """
    try:
        file_size = path.stat().st_size
    except OSError as exc:
        _log.error("failed to stat %s: %s", path, exc)
        return Err(LangError.IoFailed)
    size_error = _check_size_cap(path, file_size)
    if size_error is not None:
        return Err(size_error)
    try:
        return Ok(path.read_bytes())
    except OSError as exc:
        _log.error("failed to read %s: %s", path, exc)
        return Err(LangError.IoFailed)


def _parse(path: Path) -> Result[tuple[Tree, bytes, str], LangError]:
    """Read and parse `path`, returning (tree, source, language_label).

    Shared by every public entry point below (`parse_file`, `extract_imports`,
    `iter_identifiers`) so the extension dispatch / read / tree-sitter-parse
    steps live in exactly one place. Memoized content-hash-keyed (T-0414,
    see `_parse_cache` above): the read+hash always happens (cheap relative
    to a tree-sitter parse), but the actual grammar parse is skipped on a
    cache hit.
    """
    global _parse_cache_hits, _parse_cache_misses

    ext = path.suffix.lower()
    entry = _EXTENSION_TABLE.get(ext)
    if entry is None:
        _log.warning("no grammar registered for extension %r (path=%s)", ext, path)
        return Err(LangError.UnsupportedLanguage)
    grammar_name, language_label = entry
    _log.debug("dispatching path=%s to grammar=%s", path, grammar_name)

    source_result = _read_source_under_cap(path)
    if source_result.is_err:
        return Err(source_result.danger_err)
    source = source_result.danger_ok

    cache_key = f"{path}:{hashlib.sha256(source).hexdigest()}"
    with _parse_cache_lock:
        cached = _parse_cache.get(cache_key)
        if cached is not None:
            _parse_cache_hits += 1
            result = cached
        else:
            _parse_cache_misses += 1
            result = None

    if result is not None:
        _log.debug("parse cache hit path=%s", path)
        return result

    parser = get_parser(grammar_name)  # type: ignore[arg-type]
    tree_result = _run_parse_with_timeout(lambda: parser.parse(source), path)
    if tree_result.is_err:
        result = Err(tree_result.danger_err)
        with _parse_cache_lock:
            _parse_cache[cache_key] = result
        return result
    tree = tree_result.danger_ok
    unusable = tree.root_node is None or (
        tree.root_node.has_error and tree.root_node.child_count == 0
    )
    if unusable:
        _log.error("tree-sitter produced no usable tree for %s", path)
        result = Err(LangError.ParseFailed)
    else:
        _warn_if_partial_tree(tree, path)
        result = Ok((tree, source, language_label))

    with _parse_cache_lock:
        _parse_cache[cache_key] = result
    return result


def _build_parsed_file(
    path: Path,
    language_label: str,
    symbols: tuple[RawSymbol, ...],
    comments: tuple[RawComment, ...],
    content_bytes: bytes,
) -> ParsedFile:
    """Assemble and log a `ParsedFile` -- the tail both `parse_file` branches share."""
    parsed = ParsedFile(
        path=_display_path(path),
        language=language_label,
        symbols=symbols,
        comments=comments,
        content_hash=hashlib.sha256(content_bytes).hexdigest(),
    )
    _log.info(
        "parsed %s: language=%s symbols=%d comments=%d",
        parsed.path,
        language_label,
        len(symbols),
        len(comments),
    )
    return parsed


def _parse_strata_file(path: Path) -> Result[ParsedFile, LangError]:
    """`parse_file`'s `.strata` branch -- strata-core validation, no tree-sitter.

    Mirrors `parse_file`'s tree-sitter branch shape (read -> extract ->
    hash -> log -> `ParsedFile`, via the shared `_build_parsed_file` tail)
    so both branches produce an identical contract for `frob.graph`, just
    with `frob.lang._walk_strata.walk_strata` standing in for `extract`.
    """
    source_result = _read_source_under_cap(path)
    if source_result.is_err:
        return Err(source_result.danger_err)
    source_bytes = source_result.danger_ok

    walk_result = _run_parse_with_timeout(
        lambda: _walk_strata(source_bytes.decode("utf-8", errors="replace")), path
    )
    if walk_result.is_err:
        return Err(walk_result.danger_err)
    walked = walk_result.danger_ok
    if walked.is_err:
        message = walked.danger_err
        if message == _NATIVE_UNAVAIL_MSG:
            # Expected degrade path (T-0133), not a real parse failure --
            # every .strata file in a standalone (native-less) install hits
            # this once per graph build; logging it at error/warning level
            # for each file would be pure spam. One debug line is enough.
            _log.debug("strata parser unavailable for %s: %s", path, message)
            return Err(LangError.NativeParserUnavailable)
        _log.error("strata parse failed for %s: %s", path, message)
        return Err(LangError.ParseFailed)
    symbols, comments = walked.danger_ok
    parsed = _build_parsed_file(path, _STRATA_LANGUAGE, symbols, comments, source_bytes)
    return Ok(parsed)


# frob:ticket T-0410
def _parse_file_uncached(path: Path) -> Result[ParsedFile, LangError]:
    """`parse_file`'s real body, unwrapped -- see `parse_file` (below) for
    the public contract and the T-0410 memoization rationale. Split out
    purely so `parse_file` can wrap it in `@memoize_per_run` lazily (the
    module-level `frob.check`/`frob.lang` circular-import trap `parse_file`
    documents) without a second copy of the parse/extract logic itself.

    `.strata` files route through `_parse_strata_file` (strata-core's own
    parser, no tree-sitter grammar exists for the language); every other
    extension routes through the tree-sitter `_parse`/`extract` pair below.
    """
    if path.suffix.lower() == _STRATA_EXTENSION:
        return _parse_strata_file(path)

    parsed_result = _parse(path)
    if parsed_result.is_err:
        return Err(parsed_result.danger_err)
    tree, source, language_label = parsed_result.danger_ok

    symbols, comments = extract(tree, source, language_label)
    return Ok(_build_parsed_file(path, language_label, symbols, comments, source))


_parse_file_memoized: Callable[[Path], Result[ParsedFile, LangError]] | None = None


# frob:doc docs/modules/graph.md#public-api
# frob:invariant INV-015
# frob:ticket T-0410
# frob:tests tests/unit/test_memo.py::test_parse_file_second_call_is_memo_hit
# invariant spec: [INV-015](invariants/INV-015.md)
# frob:tests tests/test_lang.py::TestErrors.test_syntax_error_yields_partial_symbols
def parse_file(path: Path) -> Result[ParsedFile, LangError]:
    """Read, parse, and extract `path` into a `ParsedFile` (dispatch by extension).

    `_parse_file_uncached`, wrapped in `@memoize_per_run` on first call
    (T-0410) -- the wrap itself is deferred past import time (see
    `_parse_file_uncached`'s docstring) rather than a module-level
    decorator, purely to dodge the `frob.lang`/`frob.check` circular-import
    trap; behavior is identical to a plain `@memoize_per_run def
    parse_file` once the module has finished loading.

    T-0410 perf audit: `@memoize_per_run` closes the gap `_parse`'s own
    content-hash cache leaves open -- `_parse` caches the raw tree-sitter
    `Tree`, but `extract()` (the symbol/comment walk over that tree) was
    NOT cached, so repeat `parse_file` calls on the same path within one
    `frob check` invocation (measured: COV006's rescue helpers call it
    ~2000+ times, many on the same test/target files across different
    candidate edges) re-ran the full extraction walk every time even on a
    `_parse` cache hit. Profiled cost: `extract()` accounted for ~151s of a
    ~156s `coverage_gate` run, almost entirely inside `_walk_python`/
    `_common.walk`'s AST traversal -- measured after the fix, the same
    `coverage_gate` call drops to ~16s. Safe under the same run-scope
    invariant `build_graph`/`analyze_project` already rely on (T-0423):
    only active during `run_memo_scope()`, a transparent passthrough
    otherwise."""
    global _parse_file_memoized
    if _parse_file_memoized is None:
        from frob.check._memo import memoize_per_run

        _parse_file_memoized = memoize_per_run(_parse_file_uncached)
    return _parse_file_memoized(path)


# frob:doc docs/modules/graph.md#public-api
def extract_imports(path: Path) -> Result[tuple[str, ...], LangError]:
    """Raw, unresolved import/include specifiers declared in `path`.

    `frob.cycle` uses this to build its dependency graph -- specifiers come
    back exactly as written in source (a dotted python module name, a quoted
    C/C++ include path); resolving one to a real file under a scan root is
    the caller's job (see `resolve_local_import`), not this parser's.
    """
    parsed_result = _parse(path)
    if parsed_result.is_err:
        return Err(parsed_result.danger_err)
    tree, _source, language_label = parsed_result.danger_ok
    specifiers = _extract_imports(tree, language_label)
    _log.debug("extracted %d import specifiers from %s", len(specifiers), path)
    return Ok(specifiers)


# frob:doc docs/modules/graph.md#public-api
def iter_identifiers(path: Path) -> Result[tuple[tuple[str, int], ...], LangError]:
    """(name, 1-based line) for every identifier-like leaf token in `path`.

    `frob.xref` uses this to find usages of a symbol -- a broader, flatter
    shape than `RawSymbol` (which only covers declarations), so it is kept
    as its own extraction rather than folded into `parse_file`.
    """
    parsed_result = _parse(path)
    if parsed_result.is_err:
        return Err(parsed_result.danger_err)
    tree, _source, language_label = parsed_result.danger_ok
    return Ok(_iter_identifiers(tree, language_label))


# frob:doc docs/modules/graph.md#public-api
def raw_tree(path: Path) -> Result[tuple[Tree, bytes, str], LangError]:
    """The raw tree-sitter `(Tree, source_bytes, language_label)` for `path`.

    An escape hatch for callers that need node-level tree-sitter access
    (`frob.arch`'s structural metric walks, `frob.dup._legacy`'s Type-1/2
    scanner) without standing up a second `get_parser`/`Parser.parse` call
    site of their own -- every grammar load in the process still goes
    through this module's single `_parse` dispatch table. Prefer
    `parse_file`/`extract_imports`/`iter_identifiers` when the normalized
    shape is enough; reach for `raw_tree` only when a caller genuinely needs
    tree-sitter's `Node` API (field lookups, byte spans) directly.
    """
    return _parse(path)


# frob:doc docs/modules/dup.md#public-api
def symbol_tree(path: Path, span: tuple[int, int]) -> Result[TreeNode, LangError]:
    """The `TreeNode` subtree covering `span` (1-based, inclusive lines) in `path`.

    `frob.dup`'s R4 rung calls this with a `RawSymbol.span` (from an earlier
    `parse_file`) to get real node structure for `frob-core`'s Zhang-Shasha
    tree-edit-distance kernel, instead of the flat `body_tokens` sequence.
    Re-parses `path` (a second `_parse` call for the same file `parse_file`
    already visited) -- acceptable here since `frob.dup._pipeline` calls
    this only for R4 candidate pairs already surfaced by cheaper rungs, not
    for every symbol in a scan.
    """
    parsed_result = _parse(path)
    if parsed_result.is_err:
        return Err(parsed_result.danger_err)
    tree, _source, language_label = parsed_result.danger_ok
    start_line, end_line = span
    start_point = (max(start_line - 1, 0), 0)
    # A too-large end column makes some tree-sitter bindings fall back to
    # the whole-tree root instead of the smallest enclosing node -- probe a
    # single point first, then climb parents until the span is covered.
    node = tree.root_node.descendant_for_point_range(start_point, start_point)
    if node is None:
        node = tree.root_node
    while node.parent is not None and node.end_point[0] < end_line - 1:
        node = node.parent
    comment_types = COMMENT_TYPES.get(language_label, frozenset())
    return Ok(_export_tree(node, comment_types))


__all__ = [
    "COMMENT_TYPES",
    "FACETS",
    "FacetState",
    "FacetStatus",
    "LangError",
    "LanguageSupport",
    "ParsedFile",
    "RawComment",
    "RawSymbol",
    "SymbolKind",
    "child_by_field",
    "conformance_violations",
    "cpp_function_nodes",
    "derive_language_registry",
    "extract_imports",
    "flatten_tree",
    "iter_identifiers",
    "node_text",
    "parse_cache_stats",
    "partial_parse_files",
    "parse_file",
    "raw_tree",
    "reset_parse_cache",
    "resolve_local_import",
    "supported_languages",
    "symbol_tree",
    "TreeNode",
]

"""Pure touched-set test selection (docs/modules/testing.md's Selection algorithm).

`select_tests` never touches the filesystem or spawns a process -- it is a
function of a `GraphSnapshot` and a `Diff`, so it is trivially unit-tested
and safe to call speculatively (e.g. `--dry-run`).
"""

from __future__ import annotations

from pathlib import PurePosixPath

from frob.excludes import is_test_file
from frob.gitio import Diff, Hunk
from frob.graph import EdgeKind, GraphSnapshot, SymbolRecord
from frob.lang import language_for_extension
from frob.logging import get_logger
from frob.testing._models import SelectConfig, SelectionReport

_log = get_logger(__name__)

# The all-suite sentinel `run_selected` recognizes in a language's selected tuple:
# render `all_command` instead of the placeholder-rendered `command`.
# frob:doc docs/modules/testing.md#public-api
ALL_SENTINEL = "*"


# frob:doc docs/modules/testing.md#public-api
def extension_language(path: str) -> str | None:
    """The `frob.lang` language label for `path`'s extension, or `None` if unknown.

    Routes through `frob.lang.language_for_extension` (T-0129) -- the
    canonical extension registry -- rather than a locally hand-copied table.
    """
    suffix = PurePosixPath(path).suffix.lower()
    return language_for_extension(suffix)


def _overlaps(hunk_span: tuple[int, int], sym_span: tuple[int, int]) -> bool:
    """True if two inclusive 1-indexed line ranges intersect."""
    return hunk_span[0] <= sym_span[1] and sym_span[0] <= hunk_span[1]


def _enclosing_class_symref(symbol: SymbolRecord) -> str | None:
    """`path::Parent` for a dotted qualname, else `None` (no enclosing symbol)."""
    qualname = symbol.id.qualname
    if "." not in qualname:
        return None
    parent, _, _ = qualname.rpartition(".")
    return f"{symbol.id.path}::{parent}"


def _touched_symbols(
    snapshot: GraphSnapshot, hunks_by_file: dict[str, list[Hunk]]
) -> set[str]:
    """Symrefs whose span overlaps a changed hunk in the same file."""
    touched: set[str] = set()
    for symbol in snapshot.symbols.values():
        for hunk in hunks_by_file.get(symbol.id.path, ()):
            if _overlaps(hunk.span, symbol.span):
                touched.add(symbol.symref)
                break
    return touched


# D-07: a single-hop ripple horizon missed a caller two-or-more hops
# removed from a touched leaf (A tests-covered, A calls B, B calls changed
# C: neither C's own test nor A's covering test used to be selected).
# Bounded so a dense graph cannot make selection blow up to "everything".
_RIPPLE_MAX_HOPS = 4


def _ripple_symbols(snapshot: GraphSnapshot, touched_symbols: set[str]) -> set[str]:
    """Symbols that transitively depend (via `uses-contract`) on a touched
    symbol, up to `_RIPPLE_MAX_HOPS` hops (D-07, widened from a single
    hop): a bounded breadth-first walk of the `USES_CONTRACT` edges,
    frontier by frontier, so a dependent two or more hops away still gets
    its own covering test selected."""
    edges_into: dict[str, list[str]] = {}
    for edge in snapshot.edges:
        if edge.kind == EdgeKind.USES_CONTRACT:
            edges_into.setdefault(edge.target, []).append(edge.src)

    ripple: set[str] = set()
    frontier = set(touched_symbols)
    for _ in range(_RIPPLE_MAX_HOPS):
        next_frontier: set[str] = set()
        for target in frontier:
            for src in edges_into.get(target, ()):
                if src not in ripple and src not in touched_symbols:
                    ripple.add(src)
                    next_frontier.add(src)
        if not next_frontier:
            break
        frontier = next_frontier
    return ripple


def _add_selected(selected: dict[str, set[str]], edge_src: str) -> None:
    """Group `edge_src` (a test's own symref/file) under its own language."""
    file_part = edge_src.split("::", 1)[0]
    language = extension_language(file_part)
    if language is None:
        _log.warning("select_tests: no language for test src %r", edge_src)
        return
    selected.setdefault(language, set()).add(edge_src)


def _matches_enclosing(
    all_touched: set[str], enclosing_by_symref: dict[str, str | None], target: str
) -> bool:
    """Whether `target` is the enclosing class of any touched symbol."""
    return any(enclosing_by_symref.get(symref) == target for symref in all_touched)


def _edge_symref_path(symref: str) -> str:
    """The file-path half of a `path::qualname` (or bare-path) symref."""
    return symref.split("::", 1)[0]


def _looks_like_test_symbol(symref: str) -> bool:
    """Whether `symref` is itself a test: a conventional test *file*
    (`is_test_file`), or a Rust inline `mod tests { ... }` symbol whose
    qualname's leading component is `tests` (e.g.
    `strata-core/src/parse.rs::tests.some_case`) -- those live in the same
    source file as the code they cover, so the file-path check alone
    would call neither endpoint a test."""
    path, sep, qualname = symref.partition("::")
    if is_test_file(path):
        return True
    return sep == "::" and qualname.split(".", 1)[0] == "tests"


def _edge_test_and_source(edge) -> tuple[str, str] | None:
    """Which endpoint of a `TESTS` edge is the test and which is the tested
    source symbol, or `None` if that can't be determined.

    T-0137: the `frob:tests` directive is written on either side in
    practice -- above the source symbol naming the covering test (`src` is
    the source, `target` is the test), or above the test naming what it
    covers (`src` is the test, `target` is the source, matching
    `frob.gates`' `_test_edges` convention). Both are real in this
    codebase (compare `src/frob/strata/_sysdoc.py`'s directives above
    `merge_models` with `tests/unit/strata/test_sysdoc.py`'s directives
    above each test method, or `strata-core/src/parse.rs`'s `mod tests`
    directives above its own source functions), so selection must not
    assume a fixed side -- only whichever endpoint looks like a test
    (`_looks_like_test_symbol`) can be "the test to run"; the other
    endpoint is what must be touched to trigger it.
    """
    src_is_test = _looks_like_test_symbol(edge.src)
    target_is_test = _looks_like_test_symbol(edge.target)
    if src_is_test and not target_is_test:
        return edge.src, edge.target
    if target_is_test and not src_is_test:
        return edge.target, edge.src
    return None


def _source_matches_touched(
    source: str,
    all_touched: set[str],
    enclosing_by_symref: dict[str, str | None],
    files_of_touched: set[str],
    touched_files: set[str],
) -> bool:
    """Whether `source` (a `TESTS` edge's tested-side symref) is implicated
    by the touched set: itself, its enclosing class, its file, or its
    package."""
    if source in all_touched or _matches_enclosing(
        all_touched, enclosing_by_symref, source
    ):
        return True
    if "::" in source:
        return False
    if source in files_of_touched or source in touched_files:
        return True
    prefix = source.rstrip("/") + "/"
    return any(f.startswith(prefix) for f in files_of_touched | touched_files)


def _select_from_edges(
    snapshot: GraphSnapshot,
    all_touched: set[str],
    enclosing_by_symref: dict[str, str | None],
    files_of_touched: set[str],
    touched_files: set[str],
) -> tuple[dict[str, set[str]], set[str]]:
    """Selection and bound-file set from TESTS edges plus touched test files."""
    selected: dict[str, set[str]] = {}
    bound_files: set[str] = set()
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TESTS:
            continue
        sides = _edge_test_and_source(edge)
        if sides is None:
            _log.warning(
                "select_tests: TESTS edge %s -> %s has no test-file endpoint "
                "(or both sides look like test files); skipping",
                edge.src,
                edge.target,
            )
            continue
        test_ref, source_ref = sides
        if _source_matches_touched(
            source_ref,
            all_touched,
            enclosing_by_symref,
            files_of_touched,
            touched_files,
        ):
            _add_selected(selected, test_ref)
            bound_files.update(files_of_touched)
    for file in touched_files:
        if is_test_file(file):
            _add_selected(selected, file)
            bound_files.add(file)
    return selected, bound_files


def _file_has_selected_test(
    snapshot: GraphSnapshot, file: str, all_touched: set[str]
) -> bool:
    """Whether any TESTS edge already selects `file` directly or by prefix.

    T-0137: reads the edge's tested-source side via `_edge_test_and_source`
    (direction-agnostic, see its docstring) rather than assuming `target`
    is always the source -- an edge written the other way round must still
    count here, or `_collect_unbound` would wrongly apply the fallback for
    a file that already has a bound test."""
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.TESTS:
            continue
        sides = _edge_test_and_source(edge)
        if sides is None:
            continue
        _, source = sides
        if (
            source in all_touched
            or source == file
            or file.startswith(source.rstrip("/") + "/")
        ):
            return True
    return False


def _apply_fallback(
    cfg: SelectConfig,
    file: str,
    language: str,
    selected: dict[str, set[str]],
    *,
    force_package: bool = False,
) -> None:
    """Add the configured fallback selection for an unbound `file`.

    `force_package` (D-06) overrides `fallback="warn"` to `"package"` for a
    file that IS a member of the graph (has at least one symbol recorded)
    but whose particular touched hunk overlapped none of them -- a
    module-level edit (an import, a module constant, a decorator argument,
    a top-level side-effecting call). `warn` mode's accepted-risk posture
    is for files with NO test infrastructure at all; a module-level edit
    to a file the graph already knows about is a different, narrower risk
    class that must not be silently skipped even under `warn`."""
    mode = "package" if force_package and cfg.fallback == "warn" else cfg.fallback
    if mode == "package":
        package = str(PurePosixPath(file).parent)
        selected.setdefault(language, set()).add(package)
        _log.info(
            "select_tests: fallback=%s for %s -> %s",
            "package (forced, module-level edit)" if force_package else "package",
            file,
            package,
        )
    elif mode == "suite":
        selected.setdefault(language, set()).add(ALL_SENTINEL)
        _log.info("select_tests: fallback=suite for %s -> all_command", file)
    elif cfg.fallback == "warn":
        _log.warning("select_tests: unbound file %s, fallback=warn (skipped)", file)
    else:
        _log.warning("select_tests: unknown fallback mode %r", cfg.fallback)


def _apply_unknown_language_fallback(
    cfg: SelectConfig,
    file: str,
    known_languages: set[str],
    selected: dict[str, set[str]],
) -> None:
    """Fallback for a touched file whose extension maps to no known
    language at all (D-04: config/data -- `.toml`/`.json`/`.yaml`/`.md`/
    etc). `select_tests` cannot name a language-specific "package" for such
    a file (there is no source-language directory to point at), so both
    `package` and `suite` degrade to a suite-wide (`ALL_SENTINEL`) run of
    EVERY language this repo's graph has any symbols for -- conservative
    (never silently selects nothing), matching the audit's repro (editing
    `frob.toml` or a data fixture under the default `package` fallback
    must still select something). `warn` still only logs, preserving that
    mode's documented accepted-risk posture unchanged."""
    if cfg.fallback in ("package", "suite"):
        if not known_languages:
            _log.warning(
                "select_tests: unbound file %s has unknown language and no "
                "known languages to fall back to -- selecting nothing",
                file,
            )
            return
        for language in known_languages:
            selected.setdefault(language, set()).add(ALL_SENTINEL)
        # frob:waive PERF004 reason="lazy log-format arg, evaluated once per \
        # fallback at INFO only, not a hot loop; indentation-blind FP (T-0367)"
        _log.info(
            "select_tests: fallback=%s for unknown-language file %s -> "
            "suite-wide across %s",
            cfg.fallback,
            file,
            sorted(known_languages),
        )
    elif cfg.fallback == "warn":
        _log.warning(
            "select_tests: unbound file %s has unknown language, "
            "fallback=warn (skipped)",
            file,
        )
    else:
        _log.warning("select_tests: unknown fallback mode %r", cfg.fallback)


def _collect_unbound(
    snapshot: GraphSnapshot,
    cfg: SelectConfig,
    touched_files: set[str],
    bound_files: set[str],
    all_touched: set[str],
    files_of_touched: set[str],
    selected: dict[str, set[str]],
) -> list[str]:
    """Unbound touched files, applying the fallback policy for each."""
    known_languages = {
        lang
        for lang in (extension_language(s.id.path) for s in snapshot.symbols.values())
        if lang is not None
    }
    files_with_symbols = {s.id.path for s in snapshot.symbols.values()}

    ordered_files = sorted(touched_files)
    unbound: list[str] = []
    for file in ordered_files:
        if file in bound_files or is_test_file(file):
            continue
        if _file_has_selected_test(snapshot, file, all_touched):
            continue
        unbound.append(file)
        language = extension_language(file)
        if language is None:
            _apply_unknown_language_fallback(cfg, file, known_languages, selected)
            continue
        # D-06: the file IS a member of the graph (it has symbols
        # somewhere) but NONE of them were touched -- the changed hunk(s)
        # landed strictly between symbols (an import, a module constant, a
        # top-level side-effecting call). Force selection even under
        # fallback="warn"; a file with NO symbols at all, or whose touched
        # hunk DID overlap a symbol (just one with no bound test), keeps
        # warn's ordinary accepted-risk skip.
        force_package = file in files_with_symbols and file not in files_of_touched
        _apply_fallback(cfg, file, language, selected, force_package=force_package)
    return unbound


def _build_report(
    all_touched: set[str],
    touched_files: set[str],
    selected: dict[str, set[str]],
    ripple: set[str],
    unbound: list[str],
    fallback: str,
) -> SelectionReport:
    """Assemble the final `SelectionReport` with deterministic ordering."""
    touched = tuple(sorted(all_touched | touched_files))
    ripple_sorted = tuple(sorted(ripple))
    selected_sorted = {lang: tuple(sorted(ids)) for lang, ids in selected.items()}
    _log.info(
        "select_tests: touched=%d ripple=%d selected_langs=%d unbound=%d",
        len(touched),
        len(ripple),
        len(selected),
        len(unbound),
    )
    return SelectionReport(
        touched=touched,
        selected=selected_sorted,
        ripple=ripple_sorted,
        unbound=tuple(unbound),
        fallback=fallback,
    )


# frob:doc docs/modules/testing.md#public-api
def select_tests(
    snapshot: GraphSnapshot, diff: Diff, cfg: SelectConfig
) -> SelectionReport:
    """Resolve `diff`'s hunks against `snapshot` into a `SelectionReport` (pure)."""
    hunks_by_file: dict[str, list[Hunk]] = {}
    for hunk in diff.hunks:
        hunks_by_file.setdefault(hunk.file, []).append(hunk)
    touched_files = set(hunks_by_file)

    touched_symbols = _touched_symbols(snapshot, hunks_by_file)
    ripple = _ripple_symbols(snapshot, touched_symbols)
    all_touched = touched_symbols | ripple

    enclosing_by_symref = {
        symref: _enclosing_class_symref(snapshot.symbols[symref])
        for symref in all_touched
        if symref in snapshot.symbols
    }
    files_of_touched = {
        snapshot.symbols[symref].id.path
        for symref in all_touched
        if symref in snapshot.symbols
    }

    selected, bound_files = _select_from_edges(
        snapshot, all_touched, enclosing_by_symref, files_of_touched, touched_files
    )
    unbound = _collect_unbound(
        snapshot,
        cfg,
        touched_files,
        bound_files,
        all_touched,
        files_of_touched,
        selected,
    )
    return _build_report(
        all_touched, touched_files, selected, ripple, unbound, cfg.fallback
    )


__all__ = ["ALL_SENTINEL", "extension_language", "select_tests"]

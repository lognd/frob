"""frob.arch -- lightweight architectural analysis (docs/modules/arch.md).

`analyze_project` walks a repo and flags long functions, god classes, deep
nesting, high coupling, large files, shared-signature abstraction
opportunities, and (T-0332) advisory design-pattern recommendations /
anti-pattern escapes. The per-language rule sets live in cohesive
submodules (`_python`, `_cpp`, `_patterns`); this package module owns file
collection, the language-agnostic large-file check, and the orchestration
that fans each parsed file out to its language's checks.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/arch/__init__.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

# frob:waive TEST005 reason="module line coverage 83.1%, debt T-0160"

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from frob.arch import _cpp, _patterns, _python
from frob.arch._models import (
    ArchCategory,
    ArchResult,
    ArchSeverity,
    ArchSuggestion,
)
from frob.check._memo import memoize_per_run
from frob.excludes import (
    is_excluded,
    is_test_file,
    iter_files,
    load_exclude_globs,
)
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = [
    "ArchCategory",
    "ArchResult",
    "ArchSeverity",
    "ArchSuggestion",
    "analyze_project",
]

# T-0359: test functions sharing a fixture-driven signature and long
# arrange-act-assert bodies are the nature of tests, not production-
# architecture debt -- `analyze_project`'s advisory categories
# (long-function, god-class, abstraction-opportunity) skip test files (via
# the shared `frob.excludes.is_test_file`) so they only flag production code.


# frob:ticket T-0471
# frob:tests tests/unit/test_arch.py::TestGodClass.test_big_class_triggers_god_class
def _collect_files(root: Path) -> list[Path]:
    """Every file under `root` worth handing to a language's arch checks
    (T-0026's original built-in-skip-dir/exclude-glob filtering, now routed
    through the shared `frob.excludes.iter_files` prune-aware walk (T-0471)
    instead of a raw `root.rglob("*")` that paid the full traversal cost of
    `.git`/`.venv`/`.claude/worktrees` before any filter ran)."""
    exclude_globs = load_exclude_globs(root)
    result: list[Path] = []
    for p in iter_files(root):
        try:
            rel = p.relative_to(root)
        except ValueError:
            continue
        if exclude_globs and is_excluded(rel.as_posix(), exclude_globs):
            continue
        result.append(p)
    return result


# frob:ticket T-0368
# frob:tests tests/unit/test_arch.py::TestLargeFile.test_fixtures_json_not_flagged
def _is_fixture_data_file(rel: str) -> bool:
    """True if `rel` sits under a `fixtures/` directory (T-0368): test-data
    corpora (JSON payloads, litmus samples) that arch's size-based checks
    should not judge as architecture at all -- a large CVE fixture JSON is
    data, not a large module. A `fixtures/` path component is the clearest,
    language-independent signal, and only ever appears under test trees, so
    this cannot exempt production source."""
    return "fixtures" in Path(rel).parts


# frob:ticket T-0368
# frob:ticket T-0372
# frob:tests tests/unit/test_arch.py::TestLargeFile.test_large_test_file_not_flagged
# frob:tests tests/unit/test_arch.py::TestLargeFile.test_large_src_file_still_flagged
# frob:tests tests/unit/test_arch.py::TestLargeFile.test_large_json_data_not_flagged
# frob:tests tests/unit/test_arch.py::TestLargeFile.test_large_md_ledger_not_flagged
# frob:tests tests/unit/test_arch.py::TestLargeFile.test_large_py_src_still_flagged
def _check_large_file(
    rel: str,
    lines: list[bytes],
    max_file_lines: int,
    out: list[ArchSuggestion],
    *,
    is_test: bool,
) -> None:
    """Flag a file whose line count exceeds `max_file_lines` (any language).

    T-0368: test files (many arrange-act-assert cases is expected growth,
    not architecture debt) and `fixtures/` data files (not source at all)
    are exempt; production source is never exempt regardless of size.

    T-0372: the caller (`_analyze_one_file`) only invokes this for files
    with a tree-sitter grammar (real source), so generated JSON stamps,
    ticket-ledger markdown, lockfiles, and other data/config files never
    reach this check at all -- they are not "over-large modules"."""
    if is_test or _is_fixture_data_file(rel):
        return
    n = len(lines)
    if n > max_file_lines:
        out.append(
            ArchSuggestion(
                file=rel,
                category="large-file",
                severity="info",
                message=f"file has {n} lines (threshold: {max_file_lines})",
            )
        )


@dataclass(frozen=True)
class _Limits:
    """The five architectural thresholds, bundled so per-file analysis takes
    one argument instead of five parallel ints."""

    max_function_lines: int
    max_class_methods: int
    max_local_imports: int
    max_nesting_depth: int
    max_file_lines: int


def _has_tree_sitter_grammar(path: Path, rel: str) -> bool:
    """Whether `path` has a tree-sitter grammar `raw_tree` can parse (T-0129).

    `raw_tree` is a tree-sitter-only escape hatch (frob.lang docstring) --
    languages like `.strata` with no tree-sitter grammar have nothing for
    arch's structural walks to inspect, so callers should skip them silently
    rather than calling `raw_tree` and logging a spurious "no grammar
    registered" warning per file.
    """
    from frob.lang import tree_sitter_extensions

    if path.suffix.lower() in tree_sitter_extensions():
        return True
    _log.debug("arch: %s has no tree-sitter grammar, skipping", rel)
    return False


def _is_init_file(rel: str) -> bool:
    """Whether `rel` is a package `__init__.py` (T-0360, reviewer-required
    exclusion): an `__init__.py` typically just re-exports names (imports
    plus an `__all__` list of STRING literals), which is not a dispatch
    site -- excluding it from `_is_dispatch_family`'s corpus is
    defense-in-depth on top of the structural (not textual) extraction,
    since a re-export module has no call/dict/list dispatch shapes to
    begin with, but a file this central to false-suppression risk gets an
    explicit belt-and-suspenders skip rather than relying on that alone."""
    return Path(rel).name == "__init__.py"


def _analyze_one_file(
    path: Path,
    root: Path,
    limits: _Limits,
    suggestions: list[ArchSuggestion],
    all_py_sigs: list[tuple[str, str, tuple[str, ...], str, str]],
    all_dispatch_refs: dict[str, set[str]],
    all_constructions: dict[str, set[str]],
) -> None:
    """Run every applicable check on one file, appending to `suggestions`,
    accumulating python signatures for the cross-file pass, (for eligible
    python files) accumulating structural dispatch references for
    `_is_dispatch_family`'s corpus (T-0360), and accumulating class-
    construction sites for `_patterns._check_scattered_construction`'s
    cross-file corpus (T-0332)."""
    from frob.lang import raw_tree

    try:
        rel = str(path.relative_to(root))
    except ValueError:
        return
    try:
        raw = path.read_bytes()
    except OSError as exc:
        _log.debug("arch: cannot read %s: %s", rel, exc)
        return

    is_test = is_test_file(rel)
    if not _has_tree_sitter_grammar(path, rel):
        # T-0372: large-file is a code-module-cohesion check; a file with no
        # tree-sitter grammar (generated JSON, ledger markdown, lockfiles,
        # etc.) is not source arch can even parse, so it is not "an
        # over-large module" -- skip the size check along with everything
        # else that requires a parse tree.
        return
    _check_large_file(
        rel, raw.splitlines(), limits.max_file_lines, suggestions, is_test=is_test
    )

    parsed = raw_tree(path)
    if parsed.is_err:
        _log.debug("arch: %s not parsed (%s)", rel, parsed.err)
        return
    tree, _source, language = parsed.danger_ok

    if language == "python":
        _run_python_checks(
            tree,
            path,
            rel,
            root,
            limits,
            suggestions,
            all_py_sigs,
            all_dispatch_refs,
            all_constructions,
            is_test,
        )
    elif language == "cpp":
        if not is_test:
            _cpp._check_long_functions(
                tree, rel, limits.max_function_lines, suggestions
            )
            _cpp._check_god_classes(tree, rel, limits.max_class_methods, suggestions)


def _run_python_checks(
    tree: object,
    path: Path,
    rel: str,
    root: Path,
    limits: _Limits,
    suggestions: list[ArchSuggestion],
    all_py_sigs: list[tuple[str, str, tuple[str, ...], str, str]],
    all_dispatch_refs: dict[str, set[str]],
    all_constructions: dict[str, set[str]],
    is_test: bool,
) -> None:
    """Every python architectural check on one parsed file, plus signature
    and dispatch-reference accumulation for the cross-file abstraction pass.

    T-0359: `long-function`, `god-class`, and `abstraction-opportunity`
    (via signature accumulation) are advisory categories that skip test
    files -- shared fixture signatures and long arrange-act-assert bodies
    are the nature of tests, not production-architecture debt.
    `high-coupling` still runs on test files unchanged.

    T-0368: `deep-nesting` now also skips test files -- fixture-driven
    arrange blocks and parametrized case tables nest deeper than production
    control flow without being a design smell.

    T-0360: `all_dispatch_refs` (the `_is_dispatch_family` corpus) is only
    populated for non-test, non-`__init__.py` files -- a test file's own
    calls into the functions under test, or an `__init__.py`'s re-export
    list, must never be mistaken for a genuine dispatch site (the
    reviewer-demonstrated false-suppression path this exclusion closes).

    T-0332: the design-pattern recommender's per-file detectors
    (`type-switch`, `state-field-chain`, `telescoping-ctor`,
    `wrap-delegate`, `stringly-typed`) skip test files for the same reason
    as the other advisory categories above; `all_constructions` (the
    `scattered-construction` cross-file corpus) is likewise only
    accumulated from non-test files."""
    if not is_test:
        _python._check_long_functions(tree, rel, limits.max_function_lines, suggestions)
        _python._check_god_classes(tree, rel, limits.max_class_methods, suggestions)
        all_py_sigs.extend(_python._extract_signatures(tree, rel))
        if not _is_init_file(rel):
            all_dispatch_refs[rel] = _python._collect_file_dispatch_refs(tree)
        _patterns._check_type_switch(tree, rel, suggestions)
        _patterns._check_state_field_chain(tree, rel, suggestions)
        _patterns._check_telescoping_ctor(tree, rel, suggestions)
        _patterns._check_wrap_delegate(tree, rel, suggestions)
        _patterns._check_stringly_typed(tree, rel, suggestions)
        _patterns._collect_file_constructions(tree, rel, all_constructions)
    _python._check_high_coupling(path, rel, root, limits.max_local_imports, suggestions)
    if not is_test:
        _python._check_deep_nesting(tree, rel, limits.max_nesting_depth, suggestions)


# frob:doc docs/modules/arch.md#public-api
# frob:doc docs/commands/check.md#run-scoped-memoization
# frob:tests tests/unit/test_memo.py::test_analyze_project_second_call_is_memo_hit
# frob:ticket T-0423
@memoize_per_run
def analyze_project(
    root: Path,
    *,
    max_function_lines: int = 30,
    max_class_methods: int = 12,
    max_local_imports: int = 8,
    max_nesting_depth: int = 4,
    max_file_lines: int = 500,
) -> ArchResult:
    """Scan `root` for long functions, god classes, deep nesting, high
    coupling, large files, shared-signature abstraction opportunities, and
    (T-0332) advisory design-pattern recommendations / anti-pattern
    escapes.

    Memoized per `frob check` run (T-0423, `frob.check._memo.memoize_
    per_run`): a second call with identical arguments in the same run is a
    cache hit, not a re-walk -- this was the root cause of the T-0418 arch
    double-run (`analyze_project` invoked once by the advisory arch stage
    and once by the ARCH001 gate, over the same tree).
    """
    from frob.logging.quiet import quiet_stdout_logs

    limits = _Limits(
        max_function_lines=max_function_lines,
        max_class_methods=max_class_methods,
        max_local_imports=max_local_imports,
        max_nesting_depth=max_nesting_depth,
        max_file_lines=max_file_lines,
    )
    suggestions: list[ArchSuggestion] = []
    all_py_sigs: list[tuple[str, str, tuple[str, ...], str, str]] = []
    all_dispatch_refs: dict[str, set[str]] = {}
    all_constructions = _patterns.new_construction_accumulator()

    # frob.lang logs at INFO/DEBUG per parse; CLI callers piping `--json`
    # need that off stdout, same reasoning as frob.logging.quiet's docstring.
    with quiet_stdout_logs():
        for path in _collect_files(root):
            _analyze_one_file(
                path,
                root,
                limits,
                suggestions,
                all_py_sigs,
                all_dispatch_refs,
                all_constructions,
            )

    _python._check_abstraction_opportunities(
        all_py_sigs, all_dispatch_refs, suggestions
    )
    _patterns._check_scattered_construction(all_constructions, suggestions)
    # T-0332: god-object (anti-pattern-escape) is paired with the
    # already-computed god-class findings above, not a second tree walk --
    # must run after every god-class-producing check has appended. Scans a
    # snapshot (list(suggestions)) so appending the paired escape finding
    # does not mutate the list being iterated.
    _patterns._check_god_object_escape(list(suggestions), suggestions)
    return ArchResult(root=str(root), suggestions=suggestions)

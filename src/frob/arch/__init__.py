"""frob.arch -- lightweight architectural analysis (docs/modules/arch.md).

`analyze_project` walks a repo and flags long functions, god classes, deep
nesting, high coupling, large files, shared-signature abstraction
opportunities, (T-0332/T-0605) advisory design-pattern recommendations /
anti-pattern escapes, and (T-0617) OCP smells (type-dispatch, non-
exhaustive enum match). The per-language rule sets live in cohesive
submodules (`_python`, `_cpp`, `_patterns`, `_ocp`); this package module
owns file collection, the language-agnostic large-file check, and the
orchestration that fans each parsed file out to its language's checks.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from tree_sitter import Tree

from frob.arch import (
    _async_hazards,
    _concurrency,
    _concurrency_model,
    _cpp,
    _cpp_mayraise,
    _lock_ordering,
    _ocp,
    _patterns,
    _python,
    _shared_state_race,
)
from frob.arch._exceptions import check_errors_as_values
from frob.arch._fallibility import (
    check_over_broad_except,
    check_recoverable_error_wrong_signature,
    check_swallowed_exception,
    check_unhandled_result,
    run_fallibility_checks,
)
from frob.arch._ffi import (
    CtypesBoundaryCall,
    PyO3FunctionRaises,
    parse_pyi_declared_raises,
    scan_ctypes_boundary_calls,
    scan_pyo3_raises,
)
from frob.arch._kotlin import KotlinAdapter
from frob.arch._layering import (
    LayeringConfig,
    check_layering_violations,
    check_no_di_construction,
    load_layering_config,
)
from frob.arch._logging_checks import (
    check_print_as_diagnostic,
    check_unlogged_boundary,
    check_unlogged_error_path,
    run_logging_checks,
)
from frob.arch._mayraise import FunctionMayRaise, compute_may_raise
from frob.arch._models import (
    ArchCategory,
    ArchResult,
    ArchSeverity,
    ArchSuggestion,
)
from frob.arch._normalized import (
    LanguageAdapter,
    NormalizedBranch,
    NormalizedCall,
    NormalizedCallArg,
    NormalizedCatch,
    NormalizedClass,
    NormalizedField,
    NormalizedFieldAccess,
    NormalizedFunction,
    NormalizedImport,
    NormalizedLoop,
    NormalizedModule,
    NormalizedParam,
    NormalizedRaise,
    NormalizedReturn,
    NormalizedSubscript,
    NormalizedTypeAlias,
    NormalizedVariant,
    NormalizedVariantPayload,
)
from frob.arch._protocol_excuse import (
    DischargeResult,
    cpp_raii_discharge,
    gc_finalizer_discharge,
    python_with_discharge,
    rust_drop_discharge,
    typescript_using_discharge,
)
from frob.arch._rust import RustAdapter
from frob.arch._smells import (
    check_data_clumps,
    check_dead_private_code,
    check_deep_inheritance,
    check_feature_envy,
    check_magic_literal,
    check_module_dependency_cycles,
    check_mutable_default_arg,
    check_temporal_coupling,
    run_smell_checks,
)
from frob.arch._solid import (
    check_fat_interface,
    check_narrow_client_usage,
    check_noop_override,
    check_override_raises_not_implemented,
    check_override_signature_variance,
    check_override_strengthened_precondition,
    check_override_weakened_postcondition,
    run_isp_checks,
    run_lsp_checks,
)
from frob.arch._srp import (
    GOD_MODULE_MIN_CLUSTERS,
    GOD_MODULE_MIN_EXPORTS,
    LCOM4_MIN_FIELD_USING_METHODS,
    LCOM4_MIN_METHODS,
    MIXED_CONCERN_MIN_DECISION_POINTS,
    check_god_module,
    check_lcom4,
    check_mixed_concern_function,
)
from frob.arch._typedesign import (
    check_boolean_flag_param,
    check_illegal_states_representable,
    check_parse_dont_validate,
    check_primitive_obsession,
    run_typedesign_checks,
)
from frob.arch._typescript import TypeScriptAdapter
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
    "CtypesBoundaryCall",
    "DischargeResult",
    "FunctionMayRaise",
    "KotlinAdapter",
    "LanguageAdapter",
    "LayeringConfig",
    "NormalizedBranch",
    "NormalizedCall",
    "NormalizedCallArg",
    "NormalizedCatch",
    "NormalizedClass",
    "NormalizedField",
    "NormalizedFieldAccess",
    "NormalizedFunction",
    "NormalizedImport",
    "NormalizedLoop",
    "NormalizedModule",
    "NormalizedParam",
    "NormalizedRaise",
    "NormalizedReturn",
    "NormalizedSubscript",
    "NormalizedTypeAlias",
    "NormalizedVariant",
    "NormalizedVariantPayload",
    "PyO3FunctionRaises",
    "RustAdapter",
    "TypeScriptAdapter",
    "analyze_project",
    "check_boolean_flag_param",
    "check_data_clumps",
    "check_dead_private_code",
    "check_deep_inheritance",
    "check_errors_as_values",
    "check_fat_interface",
    "check_feature_envy",
    "check_illegal_states_representable",
    "check_layering_violations",
    "check_magic_literal",
    "check_module_dependency_cycles",
    "check_mutable_default_arg",
    "check_narrow_client_usage",
    "check_no_di_construction",
    "check_noop_override",
    "check_over_broad_except",
    "check_override_raises_not_implemented",
    "check_override_signature_variance",
    "check_override_strengthened_precondition",
    "check_override_weakened_postcondition",
    "check_parse_dont_validate",
    "check_primitive_obsession",
    "check_print_as_diagnostic",
    "check_recoverable_error_wrong_signature",
    "check_swallowed_exception",
    "check_temporal_coupling",
    "check_unhandled_result",
    "check_unlogged_boundary",
    "check_unlogged_error_path",
    "compute_may_raise",
    "cpp_raii_discharge",
    "gc_finalizer_discharge",
    "load_layering_config",
    "parse_pyi_declared_raises",
    "python_with_discharge",
    "run_fallibility_checks",
    "run_isp_checks",
    "run_logging_checks",
    "run_lsp_checks",
    "run_smell_checks",
    "run_typedesign_checks",
    "rust_drop_discharge",
    "scan_ctypes_boundary_calls",
    "scan_pyo3_raises",
    "typescript_using_discharge",
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
    `.git`/`.venv`/`.claude/worktrees` before any filter ran).

    Callers must pass a DIRECTORY -- `frob.excludes.iter_files` assumes
    `root` is one (`(root / ".git").exists()` / `os.walk(root)` both
    silently yield nothing for a plain file). `analyze_project` (T-1102)
    resolves a single-file `root` to its parent directory plus a one-file
    candidate list before this function ever runs, rather than teaching
    this function two different root shapes."""
    exclude_globs = load_exclude_globs(root)
    result: list[Path] = []
    for p in iter_files(root):
        try:
            rel = p.relative_to(root)
        except ValueError:
            continue
        try:
            if exclude_globs and is_excluded(rel.as_posix(), exclude_globs):
                continue
        except Exception as exc:  # noqa: BLE001 -- one bad path must not abort the walk
            _log.debug("_collect_files: is_excluded failed for %s: %s", rel, exc)
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
    """The architectural thresholds, bundled so per-file analysis takes one
    argument instead of a growing list of parallel ints. T-0728 adds the
    five ARCH1xx SRP/cohesion thresholds (`frob.arch._srp`, T-0616) to the
    original five long-function/god-class/high-coupling/deep-nesting/
    large-file knobs."""

    max_function_lines: int
    max_class_methods: int
    max_local_imports: int
    max_nesting_depth: int
    max_file_lines: int
    lcom4_min_methods: int = LCOM4_MIN_METHODS
    lcom4_min_field_using_methods: int = LCOM4_MIN_FIELD_USING_METHODS
    god_module_min_exports: int = GOD_MODULE_MIN_EXPORTS
    god_module_min_clusters: int = GOD_MODULE_MIN_CLUSTERS
    mixed_concern_min_decision_points: int = MIXED_CONCERN_MIN_DECISION_POINTS


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
            # T-0687: noexcept hard-boundary may-throw check -- a raw-text
            # scan over the same `raw` bytes already read above (see
            # frob.arch._cpp_mayraise's own module docstring for why this
            # is a text scan, not a tree-sitter node walk like the two
            # checks above it).
            _cpp_mayraise.check_cpp_noexcept_violations(
                raw.decode("utf-8", errors="replace"), rel, suggestions
            )


# frob:ticket T-0617
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

    T-0332/T-0605: the design-pattern recommender's per-file detectors
    (`type-switch`, `state-field-chain`, `telescoping-ctor`,
    `wrap-delegate`, `stringly-typed`, `interface-translate`,
    `manual-callback-list`, `anemic-accessors`) skip test files for the
    same reason as the other advisory categories above; `all_constructions`
    (the `scattered-construction` cross-file corpus) is likewise only
    accumulated from non-test files.

    T-0617: `type-dispatch-smell` and `non-exhaustive-enum-match` (the OCP
    half of the T-0330 SOLID catalog, `frob.arch._ocp`) skip test files for
    the same reason. `type-dispatch-smell` reuses `_patterns`'
    `iter_type_switch_chains` isinstance-chain detector rather than
    re-walking the tree.

    T-0728: `low-cohesion-class`, `god-module`, and `mixed-concern-function`
    (the SRP/cohesion half of the T-0330 SOLID catalog, `frob.arch._srp`,
    ARCH101-103) skip test files for the same reason -- a test module's
    helper-clustered exports or a fixture class's disjoint setup/assert
    methods are not production SRP debt. Each check runs against the
    `PythonAdapter`-built `NormalizedModule` for this file rather than the
    raw tree, per T-0616's normalized-model design (mirrors `_srp.py`'s own
    module docstring: written once, fires identically for every language
    adapter -- python is the only adapter `analyze_project` dispatches
    through today, matching every other normalized-model check already
    wired here).

    T-0696: `blocking-call-in-async`, `nested-event-loop`,
    `unawaited-coroutine`, and `async-zero-awaits` (the async event-loop
    hazard family, child 3 of the T-0693 concurrency-hazard umbrella,
    `frob.arch._async_hazards`) skip test files for the same reason as the
    fork/pool hazard family above -- an `async def` test helper/fixture is
    not production event-loop debt.

    T-0694: `lock-order-cycle` and `lock-identity-unresolved` (the
    interprocedural lock-ordering hazard family, child 2 of the T-0693
    concurrency-hazard umbrella, `frob.arch._lock_ordering`) skip test
    files for the same reason as the other concurrency-hazard families
    above -- a test fixture's own lock usage is not production deadlock
    debt.

    T-0697: `unguarded-shared-write` (the shared-mutable-state race
    approximation, child 4 of the T-0693 concurrency-hazard umbrella,
    `frob.arch._shared_state_race`) skips test files for the same reason
    as the other concurrency-hazard families above -- a test fixture's own
    shared-state usage is not production race debt.

    T-0698: `gil-bound-in-threadpool` and `ipc-overhead-in-processpool`
    (the concurrency model-mismatch advisory, child 5 of the T-0693
    concurrency-hazard umbrella, `frob.arch._concurrency_model`) skip test
    files for the same reason as the other concurrency-hazard families
    above -- a test fixture's own executor usage is not a production
    model-mismatch."""
    if not is_test:
        _python._check_long_functions(tree, rel, limits.max_function_lines, suggestions)
        _python._check_god_classes(tree, rel, limits.max_class_methods, suggestions)
        all_py_sigs.extend(_python._extract_signatures(tree, rel))
        if not _is_init_file(rel):
            all_dispatch_refs[rel] = _python._collect_file_dispatch_refs(tree)
        # T-1485: _check_type_switch/_check_state_field_chain/
        # _check_stringly_typed each independently walked the whole tree
        # for _find_if_statements before this -- compute it ONCE per file
        # here and thread it through all three instead.
        if_stmts = _patterns._find_if_statements(cast("Tree", tree).root_node)
        _patterns._check_type_switch(tree, rel, suggestions, if_stmts)
        _patterns._check_state_field_chain(tree, rel, suggestions, if_stmts)
        _patterns._check_telescoping_ctor(tree, rel, suggestions)
        _patterns._check_wrap_delegate(tree, rel, suggestions)
        _patterns._check_stringly_typed(tree, rel, suggestions, if_stmts)
        _patterns._check_interface_translate(tree, rel, suggestions)
        _patterns._check_manual_callback_list(tree, rel, suggestions)
        _patterns._check_anemic_accessors(tree, rel, suggestions)
        _patterns._check_dataclass_boilerplate(tree, rel, suggestions)
        _patterns._check_manual_decorator_wrap(tree, rel, suggestions)
        _patterns._collect_file_constructions(tree, rel, all_constructions)
        _ocp._check_type_dispatch_smell(tree, rel, suggestions)
        _ocp._check_non_exhaustive_enum_match(tree, rel, suggestions)
        _concurrency._check_fork_pool_hazards(tree, rel, suggestions)
        _async_hazards._check_async_event_loop_hazards(tree, rel, suggestions)
        _lock_ordering._check_lock_ordering_hazards(tree, rel, suggestions)
        _shared_state_race._check_shared_state_race_hazards(tree, rel, suggestions)
        _concurrency_model._check_concurrency_model_mismatch(tree, rel, suggestions)
        _run_srp_checks_python(tree, rel, limits, suggestions)
    _python._check_high_coupling(path, rel, root, limits.max_local_imports, suggestions)
    if not is_test:
        _python._check_deep_nesting(
            tree, path, rel, limits.max_nesting_depth, suggestions
        )


# frob:ticket T-0728
# frob:tests tests/unit/test_arch_srp.py::TestAnalyzeProjectWiring.test_two_cluster_class_fires_arch101  # noqa: E501
def _run_srp_checks_python(
    tree: object,
    rel: str,
    limits: _Limits,
    suggestions: list[ArchSuggestion],
) -> None:
    """T-0728: run T-0616's ARCH1xx SRP/cohesion family (`check_lcom4`,
    `check_god_module`, `check_mixed_concern_function`) against `rel`'s
    `PythonAdapter`-normalized `NormalizedModule`, threading `limits`'
    five SRP thresholds through -- the wiring T-0616 disclosed as its own
    out-of-scope follow-up (`frob.arch._srp`'s module docstring)."""
    module: NormalizedModule = _python.PythonAdapter().adapt(tree, b"", rel)
    check_lcom4(
        module,
        suggestions,
        min_methods=limits.lcom4_min_methods,
        min_field_using_methods=limits.lcom4_min_field_using_methods,
    )
    check_god_module(
        module,
        suggestions,
        min_exports=limits.god_module_min_exports,
        min_clusters=limits.god_module_min_clusters,
    )
    check_mixed_concern_function(
        module,
        suggestions,
        min_decision_points=limits.mixed_concern_min_decision_points,
    )


# frob:doc docs/modules/arch.md#public-api
# frob:doc docs/commands/check.md#run-scoped-memoization
# frob:doc docs/modules/arch.md#fork-pool-hazards
# frob:doc docs/modules/arch.md#async-event-loop-hazards
# frob:doc docs/modules/arch.md#lock-ordering-hazards
# frob:tests tests/unit/test_memo.py::test_analyze_project_second_call_is_memo_hit
# frob:ticket T-0423
# frob:ticket T-1102
# frob:ticket T-1104
@memoize_per_run
def analyze_project(
    root: Path,
    *,
    max_function_lines: int = 30,
    max_class_methods: int = 12,
    max_local_imports: int = 8,
    max_nesting_depth: int = 4,
    max_file_lines: int = 500,
    lcom4_min_methods: int = LCOM4_MIN_METHODS,
    lcom4_min_field_using_methods: int = LCOM4_MIN_FIELD_USING_METHODS,
    god_module_min_exports: int = GOD_MODULE_MIN_EXPORTS,
    god_module_min_clusters: int = GOD_MODULE_MIN_CLUSTERS,
    mixed_concern_min_decision_points: int = MIXED_CONCERN_MIN_DECISION_POINTS,
) -> ArchResult:
    """Scan `root` for long functions, god classes, deep nesting, high
    coupling, large files, shared-signature abstraction opportunities,
    (T-0332) advisory design-pattern recommendations / anti-pattern
    escapes, and (T-0728) the ARCH1xx SRP/cohesion family (low-cohesion-
    class, god-module, mixed-concern-function, `frob.arch._srp`, T-0616).

    Memoized per `frob check` run (T-0423, `frob.check._memo.memoize_
    per_run`): a second call with identical arguments in the same run is a
    cache hit, not a re-walk -- this was the root cause of the T-0418 arch
    double-run (`analyze_project` invoked once by the advisory arch stage
    and once by the ARCH001 gate, over the same tree).

    T-1102: single-file-mode parity -- `root` may be a single file (`frob
    arch <file>`, or `frob.gates._arch.arch_gate` invoked narrowly), not
    only a directory. `_collect_files`/`frob.excludes.iter_files` assume a
    directory and silently produce zero candidates for a plain file
    (`(root / ".git").exists()` and `os.walk(root)` both no-op on a file),
    which used to make single-file mode print "no architectural issues
    found" even for a multi-thousand-line file -- the large-file finding
    (and every other check) was invisible outside a directory walk. When
    `root` is a file, this resolves the walk root to `root.parent` (so
    every relative path/exclude-glob computation below stays identical to
    a directory walk that happened to contain only this one file) and
    seeds the candidate list with just `root` itself, instead of calling
    `_collect_files` at all -- the single-file finding is then computed by
    the exact same `_analyze_one_file` path a directory walk uses, so it
    prints identically (same category/message shape), not a parallel
    single-file code path that could drift from the directory one.
    """
    from frob.logging.quiet import quiet_stdout_logs

    limits = _Limits(
        max_function_lines=max_function_lines,
        max_class_methods=max_class_methods,
        max_local_imports=max_local_imports,
        max_nesting_depth=max_nesting_depth,
        max_file_lines=max_file_lines,
        lcom4_min_methods=lcom4_min_methods,
        lcom4_min_field_using_methods=lcom4_min_field_using_methods,
        god_module_min_exports=god_module_min_exports,
        god_module_min_clusters=god_module_min_clusters,
        mixed_concern_min_decision_points=mixed_concern_min_decision_points,
    )
    suggestions: list[ArchSuggestion] = []
    all_py_sigs: list[tuple[str, str, tuple[str, ...], str, str]] = []
    all_dispatch_refs: dict[str, set[str]] = {}
    all_constructions = _patterns.new_construction_accumulator()

    # T-1102: single-file-mode parity -- see this function's own docstring.
    scan_root = root.parent if root.is_file() else root
    files = [root] if root.is_file() else _collect_files(root)

    # frob.lang logs at INFO/DEBUG per parse; CLI callers piping `--json`
    # need that off stdout, same reasoning as frob.logging.quiet's docstring.
    with quiet_stdout_logs():
        for path in files:
            _analyze_one_file(
                path,
                scan_root,
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

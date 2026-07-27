# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/app/cycle_runner.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"
from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.cycle.graph import DependencyGraph, find_cycles
from frob.lang import extract_imports, resolve_local_import
from frob.logging import get_logger

_log = get_logger(__name__)

_PY_EXTS = {".py"}
# A superset of frob.lang's cpp extensions (adds .c++/.hxx/.h++, which
# frob.lang's grammar table does not carry -- pre-existing behavior, kept
# as-is rather than narrowed as part of T-0129).
_CPP_EXTS = {".c", ".cc", ".cpp", ".cxx", ".c++", ".h", ".hpp", ".hxx", ".h++"}
# extract_imports (called below) is a tree-sitter-only escape hatch with no
# `.strata` analogue (frob.lang docstring), so cycle detection can only walk
# import edges for languages tree-sitter actually parses (T-0129). `.strata`
# files still become graph nodes via `graph.add_node` in `_process_path`
# below -- they simply get no import edges, which is graceful, not a crash.


# frob:doc docs/modules/app.md#runners
# frob:ticket T-0588
# frob:tests tests/unit/test_app_runners_batch5.py::TestCycleRunner.test_cycle_found_with_suggest  # noqa: E501
# frob:waive ARCH103 reason="T-0977: `frob cycle` CLI entrypoint -- builds the graph, \
# logs per-edge errors, reports cycles found/absent, sets the exit code; this IS the \
# runner's whole job, matching the existing `frob.app.*_runner` module convention"
def run(cfg: AppConfig) -> None:
    if cfg.cycle_path is None:
        _log.error("frob cycle requires <path>")
        sys.exit(1)

    graph, errors = _build_graph(cfg.cycle_path, cfg.cycle_lang)

    for err in errors:
        _log.warning(err)

    cycles = find_cycles(graph)
    if not cycles:
        _log.info("no cycles found")
        return

    for cycle in cycles:
        nodes = " -> ".join(cycle + [cycle[0]])
        _log.info("cycle (%d nodes): %s", len(cycle), nodes)
        if cfg.cycle_suggest:
            _log.info("  suggestion: extract shared symbols into a new module")


def _add_file_edges(
    graph: DependencyGraph, path: Path, rel: str, language: str, scan_root: Path
) -> str | None:
    """Add `path`'s import edges to `graph`; return a parse-error message, if any."""
    result = extract_imports(path)
    if result.is_err:
        return f"parse error in {rel}: {result.danger_err}"
    for spec in result.danger_ok:
        resolved = resolve_local_import(
            spec, language, file_dir=path.parent, root=scan_root
        )
        if resolved is not None:
            graph.add_edge(rel, resolved)
    return None


def _process_path(
    graph: DependencyGraph,
    path: Path,
    scan_root: Path,
    lang: str | None,
    exclude_globs,
) -> str | None:
    """Add one candidate path's node (and import edges, if in-scope) to `graph`."""
    # frob:ticket T-0026
    from frob.excludes import is_excluded, is_skipped_dir

    if not path.is_file():
        return None
    ext = path.suffix.lower()
    try:
        rel_path = path.relative_to(scan_root)
    except ValueError:
        return None
    if any(is_skipped_dir(part) for part in rel_path.parts):
        return None
    if exclude_globs and is_excluded(rel_path.as_posix(), exclude_globs):
        return None
    rel = str(rel_path)

    graph.add_node(rel)

    want_python = ext in _PY_EXTS and lang in (None, "python")
    want_cpp = ext in _CPP_EXTS and lang in (None, "cpp", "c")
    if not (want_python or want_cpp):
        return None
    language = "python" if want_python else "cpp"

    return _add_file_edges(graph, path, rel, language, scan_root)


def _build_graph(root: Path, lang: str | None) -> tuple[DependencyGraph, list[str]]:
    graph = DependencyGraph()
    errors: list[str] = []

    from frob.excludes import iter_files, load_exclude_globs

    files = [root] if root.is_file() else list(iter_files(root))
    scan_root = root.parent if root.is_file() else root
    exclude_globs = load_exclude_globs(scan_root)

    for path in files:
        error = _process_path(graph, path, scan_root, lang, exclude_globs)
        if error is not None:
            errors.append(error)

    return graph, errors

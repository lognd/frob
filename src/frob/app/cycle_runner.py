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
# frob:ticket T-2588
# frob:tests tests/unit/test_app_runners_batch5.py::TestCycleRunner.test_cycle_found_with_suggest  # noqa: E501
# frob:tests tests/unit/test_cycle_runner_root_resolution.py::TestCycleRunnerRootResolution  # noqa: E501
# frob:waive ARCH103 reason="T-0977: `frob cycle` CLI entrypoint -- builds the graph, \
# logs per-edge errors, reports cycles found/absent, sets the exit code; this IS the \
# runner's whole job, matching the existing `frob.app.*_runner` module convention"
# frob:waive AFFECT001 reason="docs/modules/app.md is under T-2582's LIVE \
# cross-worktree lease for the duration of T-2588 -- cannot touch its \
# affects()-closure doc without colliding (ScopeLeaseConflict on frob ticket scope \
# --add); a doc-update follow-up ticket updates the cycle_runner.run bullet's \
# root-resolution/exit-code text once that lease clears"
def run(cfg: AppConfig) -> None:
    """CLI entrypoint for `frob cycle <path>`: measures the import graph
    ROOTED AT `<path>`'s enclosing project (T-2588 -- resolving edges
    relative to whatever directory the user happens to point at, instead
    of the project's real import root, silently dropped every absolute
    intra-project edge and reported a false "no cycles found" for
    `frob cycle src/frob` on a tree `frob check --only cycle` correctly
    flagged as a 160-node cycle). Exits 2 if `<path>` cannot be resolved
    to a project root -- never prints a clean report for an unmeasured
    tree -- and exits 1 (not 0) when real cycles are found, so this is
    finally usable in a gate/hook/script."""
    if cfg.cycle_path is None:
        _log.error("frob cycle requires <path>")
        sys.exit(1)

    build_result = _build_graph(cfg.cycle_path, cfg.cycle_lang)
    if build_result is None:
        _log.error(
            "frob cycle: could not resolve %s to a project root (no "
            "pyproject.toml and no git repository found in any parent "
            "directory) -- imports were NOT measured, this is not a clean "
            "report",
            cfg.cycle_path,
        )
        sys.exit(2)
    graph, errors = build_result

    for err in errors:
        _log.warning(err)

    cycles = find_cycles(graph)
    if not cycles:
        _log.info("no cycles found (measured %d node(s))", len(graph.nodes))
        return

    for cycle in cycles:
        nodes = " -> ".join(cycle + [cycle[0]])
        _log.info("cycle (%d nodes): %s", len(cycle), nodes)
        if cfg.cycle_suggest:
            _log.info("  suggestion: extract shared symbols into a new module")
    sys.exit(1)


# frob:ticket T-2588
def _resolve_project_root(path: Path) -> Path | None:
    """Walk up from `path` to the enclosing project root: the nearest
    ancestor (inclusive) with its own `pyproject.toml`, falling back to
    the enclosing git repo root. This is the SAME root the gate pipeline
    (`frob check --only cycle` / `_build_import_graph`) always uses,
    because it is always invoked with the repo root -- the CLI is the only
    caller that lets a user hand in an arbitrary subdirectory. Returns
    `None` when neither is found, which callers MUST treat as
    "unresolved, did not measure", never as "no cycles" (T-2588)."""
    start = path if path.is_dir() else path.parent
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate

    from frob.gitio import repo_root

    return repo_root(start).ok


def _add_file_edges(
    graph: DependencyGraph, path: Path, rel: str, language: str, project_root: Path
) -> str | None:
    """Add `path`'s import edges to `graph`; return a parse-error message, if any."""
    result = extract_imports(path)
    if result.is_err:
        return f"parse error in {rel}: {result.danger_err}"
    for spec in result.danger_ok:
        resolved = resolve_local_import(
            spec, language, file_dir=path.parent, root=project_root
        )
        if resolved is not None:
            graph.add_edge(rel, resolved)
    return None


def _process_path(
    graph: DependencyGraph,
    path: Path,
    project_root: Path,
    lang: str | None,
    exclude_globs,
) -> str | None:
    """Add one candidate path's node (and import edges, if in-scope) to
    `graph`. Node identity and import resolution are both always relative
    to `project_root` (T-2588), never to whatever subdirectory the user
    pointed the CLI at -- so `frob cycle src`, `frob cycle src/frob`, and
    `frob cycle .` register the SAME node ids and resolve the SAME edges
    for any file they all happen to walk."""
    # frob:ticket T-0026
    from frob.excludes import is_excluded, is_skipped_dir

    if not path.is_file():
        return None
    ext = path.suffix.lower()
    try:
        rel_path = path.relative_to(project_root)
    except ValueError:
        return None
    try:
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

        return _add_file_edges(graph, path, rel, language, project_root)
    except Exception as exc:  # noqa: BLE001 -- per-file scan step must not abort the walk
        _log.debug("_process_path: %s failed: %s", path, exc)
        return f"error processing {path}: {exc}"


# frob:ticket T-2588
def _build_graph(
    root: Path, lang: str | None
) -> tuple[DependencyGraph, list[str]] | None:
    """Build the import graph for every file under `root`, with node ids
    and import-edge resolution both anchored at `root`'s resolved PROJECT
    root (T-2588), not `root` itself -- returns `None` (never an empty
    graph) when `root` cannot be resolved to a project root at all, so a
    caller can tell "measured, found nothing" apart from "could not
    measure"."""
    project_root = _resolve_project_root(root)
    if project_root is None:
        return None

    graph = DependencyGraph()
    errors: list[str] = []

    from frob.excludes import iter_files, load_exclude_globs

    files = [root] if root.is_file() else list(iter_files(root))
    exclude_globs = load_exclude_globs(project_root)

    for path in files:
        error = _process_path(graph, path, project_root, lang, exclude_globs)
        if error is not None:
            errors.append(error)

    return graph, errors

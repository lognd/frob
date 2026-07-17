from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.cycle.graph import DependencyGraph, find_cycles
from frob.lang import extract_imports, resolve_local_import
from frob.logging import get_logger

_log = get_logger(__name__)

_PY_EXTS = {".py"}
_CPP_EXTS = {".c", ".cc", ".cpp", ".cxx", ".c++", ".h", ".hpp", ".hxx", ".h++"}


# frob:doc docs/modules/app.md#runners
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


def _build_graph(root: Path, lang: str | None) -> tuple[DependencyGraph, list[str]]:
    graph = DependencyGraph()
    errors: list[str] = []

    # frob:ticket T-0026
    from frob.excludes import is_excluded, is_skipped_dir, load_exclude_globs

    files = [root] if root.is_file() else list(root.rglob("*"))
    scan_root = root.parent if root.is_file() else root
    exclude_globs = load_exclude_globs(scan_root)

    for path in files:
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        try:
            rel_path = path.relative_to(scan_root)
        except ValueError:
            continue
        if any(is_skipped_dir(part) for part in rel_path.parts):
            continue
        if exclude_globs and is_excluded(rel_path.as_posix(), exclude_globs):
            continue
        rel = str(rel_path)

        graph.add_node(rel)

        want_python = ext in _PY_EXTS and lang in (None, "python")
        want_cpp = ext in _CPP_EXTS and lang in (None, "cpp", "c")
        if not (want_python or want_cpp):
            continue
        language = "python" if want_python else "cpp"

        result = extract_imports(path)
        if result.is_err:
            errors.append(f"parse error in {rel}: {result.danger_err}")
            continue
        for spec in result.danger_ok:
            resolved = resolve_local_import(
                spec, language, file_dir=path.parent, root=scan_root
            )
            if resolved is not None:
                graph.add_edge(rel, resolved)

    return graph, errors

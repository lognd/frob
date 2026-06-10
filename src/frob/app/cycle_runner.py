from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.ast.common import ModuleTag
from frob.cycle.graph import DependencyGraph, find_cycles
from frob.logging import get_logger

_log = get_logger(__name__)


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
    from frob.ast import cpp as _cpp
    from frob.ast import python as _py

    graph = DependencyGraph()
    errors: list[str] = []

    files = [root] if root.is_file() else list(root.rglob("*"))
    scan_root = root.parent if root.is_file() else root

    for path in files:
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        try:
            rel = str(path.relative_to(scan_root))
        except ValueError:
            continue

        graph.add_node(rel)

        try:
            if ext == ".py" and lang in (None, "python"):
                for imp in _py.get_imports(ModuleTag(rel), scan_root):
                    graph.add_edge(rel, imp)
            elif ext in _cpp.ALL_EXTS and lang in (None, "cpp", "c"):
                for imp in _cpp.get_imports(ModuleTag(rel), scan_root):
                    graph.add_edge(rel, imp)
        except Exception as exc:
            errors.append(f"parse error in {rel}: {exc}")

    return graph, errors

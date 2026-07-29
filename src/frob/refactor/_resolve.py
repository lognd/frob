"""Resolve phase: pin a `SymbolRef` to exactly one real file and span
(docs/design/refactor-verb.md's Transaction model, step 1).

Refuses with no writes if the target does not resolve or resolves more
than once -- the Plan/Apply/Verify phases below never re-check this, they
trust the `ResolvedSymbol` this phase hands them.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import ast
from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.logging import get_logger
from frob.refactor._models import RefactorError, ResolvedSymbol, SymbolRef

_log = get_logger(__name__)

__all__ = ["module_to_path", "resolve_symbol"]


# frob:doc docs/commands/refactor.md#module_to_path
# frob:tests tests/test_refactor.py::TestModuleToPath.test_maps_dotted_module_under_src  # noqa: E501
def module_to_path(repo_root: Path, module: str) -> Path:
    """The single place a dotted module path (`pkg.sub.mod`) becomes a
    `src/pkg/sub/mod.py` filesystem path, so Resolve/Apply never diverge
    on the mapping."""
    src_root = repo_root / "src"
    base = src_root if src_root.is_dir() else repo_root
    return base.joinpath(*module.split(".")).with_suffix(".py")


def _find_def(
    tree: ast.Module, qualname: str
) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef, bool] | None:
    """Locate a top-level or one-level-nested (`Class.method`) definition
    matching `qualname`; returns `(node, is_class)` or `None`."""
    parts = qualname.split(".")
    if len(parts) == 1:
        for node in tree.body:
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and node.name == parts[0]
            ):
                return node, isinstance(node, ast.ClassDef)
        return None
    if len(parts) == 2:
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == parts[0]:
                for child in node.body:
                    if (
                        isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and child.name == parts[1]
                    ):
                        return child, False
        return None
    return None


# frob:doc docs/commands/refactor.md#resolve_symbol
# frob:tests tests/test_refactor.py::TestResolveSymbol.test_resolves_top_level_function
def resolve_symbol(
    repo_root: Path, ref: SymbolRef
) -> Result[ResolvedSymbol, RefactorError]:
    """Resolve phase entry point: parse `ref.module`'s source file via
    `ast` and confirm `ref.qualname` names exactly one function/class in
    it. `Err(TargetNotFound)` if the module file does not exist or the
    name is absent; this engine only supports top-level symbols and
    one-level-nested methods (`Class.method`) in v1 -- anything deeper is
    also `TargetNotFound` since the design doc scopes v1 to Python
    move/rename of a single symbol, not arbitrary nesting."""
    file_path = module_to_path(repo_root, ref.module)
    if not file_path.is_file():
        _log.warning("refactor.resolve: module file missing: %s", file_path)
        return Err(RefactorError.TargetNotFound)
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (OSError, SyntaxError) as exc:
        _log.warning("refactor.resolve: cannot parse %s: %s", file_path, exc)
        return Err(RefactorError.TargetNotFound)

    found = _find_def(tree, ref.qualname)
    if found is None:
        _log.info("refactor.resolve: %s not found in %s", ref.qualname, file_path)
        return Err(RefactorError.TargetNotFound)
    node, is_class = found
    end_line = node.end_lineno if node.end_lineno is not None else node.lineno
    _log.info(
        "refactor.resolve: %s resolved to %s:%d-%d",
        ref.dotted,
        file_path,
        node.lineno,
        end_line,
    )
    return Ok(
        ResolvedSymbol(
            ref=ref,
            file_path=str(file_path),
            start_line=node.lineno,
            end_line=end_line,
            is_class=is_class,
        )
    )

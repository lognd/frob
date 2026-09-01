"""Resolve phase: pin a `SymbolRef` to exactly one real file and span
(docs/design/refactor-verb.md's Transaction model, step 1).

Refuses with no writes if the target does not resolve or resolves more
than once -- the Plan/Apply/Verify phases below never re-check this, they
trust the `ResolvedSymbol` this phase hands them.
"""

from __future__ import annotations

import ast
from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.logging import get_logger
from frob.refactor._models import RefactorError, ResolvedSymbol, SymbolRef

_log = get_logger(__name__)

__all__ = ["import_roots", "module_to_path", "root_for_path", "resolve_symbol"]


# frob:ticket T-3587
# frob:doc docs/commands/refactor.md#import_roots
# frob:tests \
#   tests/test_refactor.py::TestImportRoots.test_src_first_then_repo_root  # noqa: E501
def import_roots(repo_root: Path) -> list[Path]:
    """The ordered list of package roots this repo's dotted-module<->path
    mapping tries, most-specific first: `src/` when it exists, then
    `repo_root` itself (the `pythonpath = ["."]` pytest root, covering
    `tests/`, `scripts/`, and any other repo-root-relative package).
    This is the SINGLE list every site in this package that maps a
    dotted module to a path, or a path back to a dotted module, must
    build on -- `module_to_path`, `root_for_path`, `_module_resolve`'s
    non-`.py` fallback, `_module_scan_python`'s relative-import
    resolution, `_operands.validate_module_destination`, and
    `_verify`'s import-check `PYTHONPATH` -- so `src/` keeps resolving
    exactly as it always has while a `tests/**`/`scripts/**` module
    becomes resolvable too, instead of five call sites independently
    deciding (and risking disagreeing on) the same rule."""
    src_root = repo_root / "src"
    roots = [src_root] if src_root.is_dir() else []
    roots.append(repo_root)
    return roots


# frob:ticket T-3587
# frob:doc docs/commands/refactor.md#module_to_path
# frob:tests \
#   tests/test_refactor.py::TestModuleToPath.test_maps_module_under_src  # noqa: E501
# frob:tests \
#   tests/test_refactor.py::TestModuleToPath.test_maps_module_under_root  # noqa: E501
def module_to_path(repo_root: Path, module: str) -> Path:
    """The single place a dotted module path (`pkg.sub.mod`) becomes a
    filesystem path, so Resolve/Apply never diverge on the mapping.
    Tries every `import_roots` candidate (src/ first) and returns the
    first one that names a real file; if none exists yet (a brand-new
    destination module), prefers a root whose top-level package segment
    already exists as a directory, else falls back to the first
    candidate root."""
    roots = import_roots(repo_root)
    parts = module.split(".")
    for base in roots:
        candidate = base.joinpath(*parts).with_suffix(".py")
        if candidate.is_file():
            return candidate
    for base in roots:
        if (base / parts[0]).is_dir():
            return base.joinpath(*parts).with_suffix(".py")
    return roots[0].joinpath(*parts).with_suffix(".py")


# frob:ticket T-3587
# frob:doc docs/commands/refactor.md#root_for_path
# frob:tests \
#   tests/test_refactor.py::TestRootForPath.test_finds_owning_root  # noqa: E501
def root_for_path(repo_root: Path, path: Path) -> Path | None:
    """The `import_roots` entry that contains `path`, or `None` if
    `path` is outside every known root -- the inverse lookup
    `_importing_package`/`_path_to_module`/the import-check
    `PYTHONPATH` builder need, sharing the identical root list
    `module_to_path` uses so a file this engine can resolve one
    direction always resolves the other."""
    try:
        resolved = path.resolve()
    except OSError:
        return None
    for base in import_roots(repo_root):
        try:
            resolved.relative_to(base.resolve())
        except (OSError, ValueError):
            continue
        return base
    return None


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
    # T-3596 gap 4: a decorated def/class's own `node.lineno` is the
    # `def`/`class` KEYWORD line, never its `@decorator` line(s) -- `ast`
    # deliberately gives each decorator its own `lineno` in `decorator_
    # list`. Using `node.lineno` bare as the move span's start silently
    # left every decorator behind at the SOURCE file (a `move`/`split`
    # reporting `success=True` while dropping `@contextmanager` etc. from
    # the moved symbol entirely -- T-3628's `derived_state_lock` repro).
    # Start the span at the FIRST decorator's own line when any exist, so
    # every downstream span consumer (`build_move_ops`, `extend_span_for_
    # attached_directives`, `needed_import_ops_for_symbols`) already sees
    # the decorators as part of the symbol's own text.
    decorator_list = getattr(node, "decorator_list", ())
    start_line = node.lineno
    decorator_names: tuple[str, ...] = ()
    if decorator_list:
        start_line = min(d.lineno for d in decorator_list)
        decorator_names = tuple(ast.unparse(d) for d in decorator_list)
    _log.info(
        "refactor.resolve: %s resolved to %s:%d-%d (decorators=%s)",
        ref.dotted,
        file_path,
        start_line,
        end_line,
        decorator_names,
    )
    return Ok(
        ResolvedSymbol(
            ref=ref,
            file_path=str(file_path),
            start_line=start_line,
            end_line=end_line,
            is_class=is_class,
            decorator_names=decorator_names,
        )
    )

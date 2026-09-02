"""Verify phase: the three in-command post-conditions a transaction must
pass before it is allowed to commit (docs/design/refactor-verb.md's
Transaction model, step 4).

Every check here returns a `VerifyOutcome`, never raises -- a failing
check is exactly as expected an outcome as a passing one; the transaction
orchestrator (`_transaction.py`) decides whether to roll back.
"""

from __future__ import annotations

import ast
import builtins
from pathlib import Path

from frob.logging import get_logger
from frob.refactor._models import ResolvedSymbol, SymbolRef, VerifyOutcome
from frob.refactor._verify_exec import (  # noqa: F401 -- T-1201 split re-export
    _filter_pytest_collect_targets,
    _spawn_pytest_collect,
    verify_check_delta,
    verify_pytest_collect,
)
from frob.refactor._verify_import import (  # noqa: F401 -- T-1201 split re-export
    _import_check_env,
    _local_import_gaps,
    _module_bound_names,
    _path_to_module,
    verify_module_import,
)

_log = get_logger(__name__)

__all__ = [
    "verify_check_delta",
    "verify_decorators_preserved",
    "verify_import_resolution",
    "verify_module_import",
    "verify_no_self_import",
    "verify_no_undefined_names",
    "verify_pytest_collect",
]


def _parse_touched_python_files(
    touched_files: list[Path],
) -> tuple[dict[Path, ast.Module], list[str], list[str]]:
    """Split `touched_files` into (parsed ASTs, syntax-error messages,
    skipped non-`.py` paths) -- the T-1885 filter step
    `verify_import_resolution` needs before it can reason about import
    resolution at all, factored out so that function stays under the
    long-function threshold (ARCH001, T-1889)."""
    trees: dict[Path, ast.Module] = {}
    broken: list[str] = []
    skipped: list[str] = []
    for path in touched_files:
        if not path.is_file():
            continue
        # T-1885: `touched_files` is every path a `RefactorPlan.reference_
        # ops` entry rewrote -- not just Python source. A non-`.py` carrier
        # (a `tickets/<id>/ticket.md` evidence citation, T-1546; a
        # `docs/design/registry/*.yaml` registry citation, T-1200) reaching
        # `ast.parse` unconditionally is not Python and predictably raises
        # `SyntaxError` on ordinary prose/YAML content (observed: "leading
        # zeros in decimal integer literals are not permitted" parsing a
        # ticket.md's `T-0001`-shaped id) -- which this function correctly
        # reported as a failed `VerifyOutcome` (never silently swallowed as
        # a crash), but that failure was spurious AND indistinguishable
        # from a genuine one: nothing about the actual rewrite was broken,
        # only this check's blind assumption that every touched file is
        # Python. A non-`.py` file is recorded in `skipped` -- disclosed
        # explicitly, never silently folded into either `passed=True`
        # ("I looked and it's fine") or `passed=False` ("I looked and it's
        # broken") -- rather than being handed to `ast.parse` at all. This
        # function's whole job is Python syntax/import resolution; a
        # non-Python file was never a real candidate for it.
        if path.suffix != ".py":
            skipped.append(str(path))
            continue
        try:
            trees[path] = ast.parse(
                path.read_text(encoding="utf-8"), filename=str(path)
            )
        except SyntaxError as exc:
            broken.append(f"{path}: {exc}")
    return trees, broken, skipped


# frob:doc docs/commands/refactor.md#verify_import_resolution
# frob:tests \
# tests/test_refactor.py::TestVerify.test_import_resolution_catches_syntax_error
# frob:tests \
# tests/test_refactor.py::TestVerify.test_import_resolution_catches_dangling_reference
def verify_import_resolution(
    touched_files: list[Path], repo_root: Path | None = None
) -> VerifyOutcome:
    """Post-condition 1: every touched `.py` file still parses as valid
    Python AND, for every absolute local-module import it contains, the
    imported name actually resolves against something that module
    currently defines -- a real (scoped, disclosed) import-graph
    resolution check, not merely a syntax parse (see `_local_import_gaps`'s
    docstring for the exact scope). A file that fails to parse, or that
    imports a name a repo-owned module no longer defines, after rewriting
    is exactly the "half-moved symbol" case the design doc's
    refuse-and-rollback rule exists for.

    T-1885: `touched_files` is the FULL set a `RefactorPlan.reference_ops`
    entry rewrote, not just Python source -- a non-Python carrier (a
    `tickets/<id>/ticket.md` evidence citation, T-1546; a
    `docs/design/registry/*.yaml` registry citation, T-1200) is filtered
    out by suffix (`path.suffix != ".py"`) before ever reaching
    `ast.parse`, rather than being handed to it and producing a spurious
    `SyntaxError` on ordinary prose/YAML content. This check verifies
    Python syntax/import resolution only; a non-`.py` file was never a
    real candidate for it and is simply not this check's concern, not a
    weakening of what it verifies.

    `repo_root=None` (the historical call shape, kept so existing callers
    passing loose files with no enclosing repo still work) skips the
    local-module resolution pass and performs the syntax check only --
    the `detail` string says so explicitly rather than silently claiming
    full resolution ran.
    """
    trees, broken, skipped = _parse_touched_python_files(touched_files)
    skipped_note = (
        f" ({len(skipped)} non-.py file(s) skipped, not applicable)" if skipped else ""
    )
    if broken:
        _log.warning("refactor.verify: import resolution failed: %s", broken)
        return VerifyOutcome(
            name="import_resolution",
            passed=False,
            detail="; ".join(broken) + skipped_note,
            skipped=tuple(skipped),
        )

    if repo_root is None:
        return VerifyOutcome(
            name="import_resolution",
            passed=True,
            detail=(
                f"{len(trees)} touched .py file(s) parse cleanly "
                "(no repo_root given -- syntax check only, local-module "
                f"resolution skipped){skipped_note}"
            ),
            skipped=tuple(skipped),
        )

    gaps: list[str] = []
    for path, tree in trees.items():
        gaps.extend(_local_import_gaps(repo_root, path, tree))
    if gaps:
        _log.warning("refactor.verify: local import resolution failed: %s", gaps)
        return VerifyOutcome(
            name="import_resolution",
            passed=False,
            detail="; ".join(gaps) + skipped_note,
            skipped=tuple(skipped),
        )
    return VerifyOutcome(
        name="import_resolution",
        passed=True,
        detail=(
            f"{len(trees)} touched .py file(s) parse cleanly and every "
            f"absolute local-module import resolves{skipped_note}"
        ),
        skipped=tuple(skipped),
    )


# frob:ticket T-3596
_BUILTIN_AND_DUNDER_NAMES = frozenset(dir(builtins)) | frozenset(
    {
        "__name__",
        "__file__",
        "__doc__",
        "__all__",
        "__package__",
        "__spec__",
        "__loader__",
        "__builtins__",
        "__annotations__",
        "__dict__",
        "__class__",
        "__debug__",
    }
)


def _all_bound_names_anywhere(tree: ast.Module) -> set[str]:
    """Every name bound ANYWHERE in `tree` -- module-level, function
    parameters, local assignments in any nested scope, `except ... as`
    names, `global`/`nonlocal` declarations, and nested `def`/`class`
    names. Deliberately whole-file rather than scope-accurate (a name
    local to function A is pooled together with function B's own
    references) -- this trades away catching a genuine same-name
    cross-scope shadowing bug for zero false positives on a legitimate
    reference, which is the right trade for a Verify-phase gate that can
    block a commit: a name this pool does not contain is undefined
    EVERYWHERE in the file, not merely out of scope somewhere, so
    flagging it is always a real finding."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            names.add(node.id)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    names.add(alias.asname or alias.name)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        elif isinstance(node, ast.Global):
            names.update(node.names)
        elif isinstance(node, ast.Nonlocal):
            names.update(node.names)
        elif isinstance(node, ast.MatchAs) and node.name:
            names.add(node.name)
        elif isinstance(node, ast.MatchStar) and node.name:
            names.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            names.add(node.rest)
        elif isinstance(node, getattr(ast, "TypeVar", ())):
            names.add(node.name)
    return names


def _undefined_names_in_tree(tree: ast.Module) -> list[tuple[str, int]]:
    """Every `(name, lineno)` `Name(ctx=Load)` reference in `tree` whose
    `id` is not bound ANYWHERE in the file (`_all_bound_names_anywhere`)
    and is not a builtin/dunder -- the structural scope-walk T-3596
    requires so a moved body's own undefined free variable (gap 3: a
    module global neither moved nor re-imported; gap 4: a self-import
    that resolves to nothing real) is caught by static analysis instead
    of only surfacing as a runtime `NameError` the verb's own
    `success=True` never saw."""
    bound = _all_bound_names_anywhere(tree) | _BUILTIN_AND_DUNDER_NAMES
    hits: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in bound:
                hits.append((node.id, node.lineno))
    return sorted(set(hits))


# frob:doc docs/commands/refactor.md#verify_no_undefined_names
# frob:ticket T-3596
# frob:tests \
# tests/test_refactor.py::TestVerifyStructural.test_no_undefined_names_catches_free_variable  # noqa: E501
# frob:tests \
# tests/test_refactor.py::TestVerifyStructural.test_no_undefined_names_passes_clean_module  # noqa: E501
def verify_no_undefined_names(touched_files: list[Path]) -> VerifyOutcome:
    """T-3596 structural Verify-phase check: every touched `.py` file's
    own free-variable references resolve against SOME binding in that
    same file (a whole-file scope pool, see `_all_bound_names_anywhere`'s
    docstring for the accuracy trade-off) or a builtin.

    This is the check that structurally closes gaps 1/3/4 the way
    `verify_module_import`'s real-`import` alone cannot: `import`ing a
    module only executes its TOP-LEVEL code, so a free variable only
    referenced inside a moved function's BODY (T-3628's `msvcrt`/
    `_process_registry_lock` repro, and a dropped-decorator's resulting
    self-import) never raises until something actually CALLS that
    function -- invisible to every other Verify-phase check this engine
    already runs. A syntax error or unreadable file is skipped here (
    `verify_import_resolution` already owns that failure mode)."""
    findings: list[str] = []
    checked = 0
    for path in touched_files:
        if not path.is_file() or path.suffix != ".py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        checked += 1
        for name, lineno in _undefined_names_in_tree(tree):
            findings.append(
                f"{path}:{lineno}: `{name}` is not defined anywhere in this file"
            )
    if findings:
        _log.warning("refactor.verify: undefined names found: %s", findings)
        return VerifyOutcome(
            name="no_undefined_names", passed=False, detail="; ".join(findings)
        )
    return VerifyOutcome(
        name="no_undefined_names",
        passed=True,
        detail=f"{checked} touched .py file(s) have no undefined free variables",
    )


# frob:doc docs/commands/refactor.md#verify_no_self_import
# frob:ticket T-3596
# frob:tests \
# tests/test_refactor.py::TestVerifyStructural.test_no_self_import_catches_self_reference  # noqa: E501
# frob:tests \
# tests/test_refactor.py::TestVerifyStructural.test_no_self_import_passes_clean_module  # noqa: E501
def verify_no_self_import(touched_files: list[Path], repo_root: Path) -> VerifyOutcome:
    """T-3596 gap 4: `split` was observed inserting a `from <destination
    module> import (...)` line INTO that same destination module (a
    self-import, always a no-op at best and a `NameError` for anything
    the import list actually needed at worst) -- token/grammar-level
    check (parses each touched file's own `ImportFrom` nodes and
    compares `node.module` against that file's OWN dotted module name
    via `_path_to_module`, never a substring/regex match) that a
    transaction must not be able to commit past."""
    findings: list[str] = []
    checked = 0
    for path in touched_files:
        if not path.is_file() or path.suffix != ".py":
            continue
        own_module = _path_to_module(repo_root, path)
        if own_module is None:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError):
            continue
        checked += 1
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.level == 0
                and node.module == own_module
            ):
                findings.append(
                    f"{path}:{node.lineno}: self-import `from {own_module} "
                    "import ...` -- this file importing from its own module"
                )
    if findings:
        _log.warning("refactor.verify: self-import(s) found: %s", findings)
        return VerifyOutcome(
            name="no_self_import", passed=False, detail="; ".join(findings)
        )
    return VerifyOutcome(
        name="no_self_import",
        passed=True,
        detail=f"{checked} touched .py file(s) have no self-imports",
    )


# frob:doc docs/commands/refactor.md#verify_decorators_preserved
# frob:ticket T-3596
# frob:tests \
# tests/test_refactor.py::TestVerifyStructural.test_decorators_preserved_catches_dropped_decorator  # noqa: E501
# frob:tests \
# tests/test_refactor.py::TestVerifyStructural.test_decorators_preserved_passes_when_intact  # noqa: E501
def verify_decorators_preserved(
    repo_root: Path,
    moved_symbols: list[tuple[ResolvedSymbol, SymbolRef]],
) -> VerifyOutcome:
    """T-3596 gap 4: confirm every moved symbol's destination def/class
    header carries the SAME decorator set (compared by `ast.unparse`d
    text, order-sensitive -- decorator STACKING order is semantically
    meaningful) that `resolve_symbol` captured at Plan time, before the
    move touched anything. `moved_symbols` is `(resolved, destination)`
    pairs -- one per symbol an already-applied transaction moved.
    Skipped (passes trivially) for a symbol with no decorators at all,
    since there is nothing to preserve."""
    from frob.refactor._resolve import module_to_path

    findings: list[str] = []
    checked = 0
    for resolved, destination in moved_symbols:
        if not resolved.decorator_names:
            continue
        checked += 1
        dest_path = module_to_path(repo_root, destination.module)
        leaf = destination.qualname.split(".")[-1]
        try:
            tree = ast.parse(
                dest_path.read_text(encoding="utf-8"), filename=str(dest_path)
            )
        except (OSError, SyntaxError):
            findings.append(
                f"{dest_path}: could not parse to verify decorators on {leaf}"
            )
            continue
        found_decorators: tuple[str, ...] | None = None
        for node in tree.body:
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and node.name == leaf
            ):
                found_decorators = tuple(ast.unparse(d) for d in node.decorator_list)
                break
        if found_decorators is None:
            findings.append(f"{dest_path}: {leaf} not found (expected after move)")
        elif found_decorators != resolved.decorator_names:
            findings.append(
                f"{dest_path}: {leaf} decorators {list(found_decorators)} do not "
                f"match source decorators {list(resolved.decorator_names)}"
            )
    if findings:
        _log.warning("refactor.verify: decorator mismatch: %s", findings)
        return VerifyOutcome(
            name="decorators_preserved", passed=False, detail="; ".join(findings)
        )
    return VerifyOutcome(
        name="decorators_preserved",
        passed=True,
        detail=f"{checked} moved decorated symbol(s) kept their decorators intact",
    )

import ast
import os
import sys
from pathlib import Path

from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run
from frob.refactor._models import VerifyOutcome
from frob.refactor._resolve import import_roots, root_for_path

_log = get_logger(__name__)


def _module_bound_names(file_path: Path) -> set[str] | None:
    """Every name bound at `file_path`'s module top level (`def`/`class`,
    plain assignment, and re-exported import aliases) -- `None` if the
    file cannot be read/parsed. Used to check that an absolute-import
    site naming this module actually resolves against something the
    module defines, not merely that the module file exists."""
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    except (OSError, SyntaxError):
        return None
    names: set[str] = set()

    def _collect(stmts: list[ast.stmt]) -> None:
        for node in stmts:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.add(node.target.id)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    names.add(alias.asname or alias.name)
            elif isinstance(node, ast.Try):
                # T-3596 gap 3: a `try: import msvcrt \n except ImportError:
                # msvcrt = None` platform-fallback shim binds its name one
                # level inside a `Try`, not directly in `tree.body` -- a
                # moved body carrying `from <source> import msvcrt` (this
                # engine's own gap-3 fix) must not have THIS check flag
                # that carried import as broken just because the plain
                # top-level walk never looked inside the `try`.
                _collect(node.body)
                for handler in node.handlers:
                    _collect(handler.body)
                _collect(node.orelse)
                _collect(node.finalbody)
            elif isinstance(node, ast.If):
                _collect(node.body)
                _collect(node.orelse)

    try:
        _collect(tree.body)
    except (KeyError, TypeError):
        # "`None` if the file cannot be read/parsed" (this function's own
        # docstring) covers a structurally surprising-but-parseable AST
        # shape too, not just the read/syntax-error case (EXHAUST001/
        # EXHAUST002, T-1371).
        return None
    except Exception:
        return None
    return names


def _local_import_gaps(repo_root: Path, path: Path, tree: ast.Module) -> list[str]:
    """Every absolute `from <local module> import <name>` in `path` whose
    target module resolves to a real repo-owned file but does not
    actually bind `<name>` at that module's top level -- the real
    import-graph check this function performs (not a syntax-only stand-
    in): a rewrite that repoints an import at a module which no longer
    (or never did) define the referenced name is exactly the "half-moved
    symbol" case the design doc's refuse-and-rollback rule targets,
    beyond what a bare syntax parse alone would ever catch.

    Scope, disclosed honestly (docs/commands/refactor.md#verify_import_resolution):
    only ABSOLUTE imports (`node.level == 0`) of modules that resolve to
    a file inside this repo's own `src/` tree are checked -- third-party/
    stdlib imports and relative imports are out of v1's static-AST scope
    (matching `frob.refactor._scan`'s own `resolve_symbol`/`module_to_path`
    local-module convention) and are never flagged as broken here.
    """
    from frob.refactor._resolve import module_to_path

    gaps: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level != 0 or node.module is None:
            continue
        target_path = module_to_path(repo_root, node.module)
        if not target_path.is_file():
            # Not a repo-owned module (third-party/stdlib) -- out of this
            # check's local-module scope, never flagged.
            continue
        bound = _module_bound_names(target_path)
        if bound is None:
            gaps.append(f"{path}:{node.lineno}: {target_path} could not be parsed")
            continue
        for alias in node.names:
            if alias.name == "*":
                continue
            if alias.name not in bound:
                gaps.append(
                    f"{path}:{node.lineno}: `{alias.name}` not defined in "
                    f"{target_path} (imported via `from {node.module} import "
                    f"{alias.name}`)"
                )
    return gaps


# frob:ticket T-3587
def _path_to_module(repo_root: Path, path: Path) -> str | None:
    """Inverse of `_resolve.module_to_path`: the dotted module name a
    file path resolves to, or `None` if `path` is not inside any of
    this repo's own import roots (`_resolve.import_roots` -- `src/` if
    it exists, plus `repo_root` itself, the identical layout convention
    `module_to_path` already encodes) or is not a plain importable
    module file (a `__init__.py` collapses to its package's own dotted
    name; anything else that fails to resolve under a root, or is not
    `.py`, is `None`)."""
    base = root_for_path(repo_root, path)
    if base is None:
        return None
    try:
        rel = path.resolve().relative_to(base.resolve())
    except (OSError, ValueError):
        return None
    if rel.suffix != ".py":
        return None
    parts = rel.with_suffix("").parts
    if not parts:
        return None
    if parts[-1] == "__init__":
        parts = parts[:-1]
        if not parts:
            return None
    return ".".join(parts)


# frob:ticket T-3395
# frob:ticket T-3587
# T-3598: no `frob:waive ARCH103` here anymore -- T-3587 moved this
# function's src-vs-repo-root branch out into `import_roots` (a
# separate function), dropping this body's own decision-point count
# from 2 to 1 (only the PYTHONPATH-prepend ternary remains), below
# ARCH103's MIXED_CONCERN_MIN_DECISION_POINTS=2 threshold -- ARCH103
# genuinely no longer fires raw here, so the waiver was dead weight.
def _import_check_env(repo_root: Path) -> dict[str, str]:
    """The subprocess `env` `verify_module_import` runs a real `import`
    under: the current environment plus every one of this repo's own
    import roots (`_resolve.import_roots` -- `src/` if it exists, plus
    `repo_root`) prepended onto `PYTHONPATH`, same layout convention
    `_resolve.module_to_path` and `_path_to_module` both already
    encode, so a module this repo's own refactor engine can RESOLVE by
    dotted name (whether it lives under `src/` or is a `tests/**`/
    `scripts/**` module resolved via the repo-root candidate) is also
    one a real subprocess interpreter can actually `import`, whether or
    not the target repo happens to be installed editable in the
    current venv."""
    roots = os.pathsep.join(str(root) for root in import_roots(repo_root))
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = roots + os.pathsep + existing if existing else roots
    # Never write a `__pycache__/*.pyc` into the target repo's own
    # working tree as a side effect of this check -- a refactor verb
    # must not dirty the tree it is verifying.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # T-3119: inheriting the CALLING process's own coverage
    # instrumentation (`COVERAGE_PROCESS_START`, set when THIS repo's
    # own test suite runs under coverage) would make this check's own
    # subprocess import write `.coverage.*` data files into the target
    # repo's working tree as a side effect -- strip it so the import
    # check never dirties the tree it is verifying, for the same reason
    # PYTHONDONTWRITEBYTECODE is forced above.
    env.pop("COVERAGE_PROCESS_START", None)
    env.pop("COVERAGE_FILE", None)
    return env


# frob:doc docs/commands/refactor.md#verify_module_import
# frob:ticket T-3119
# frob:tests tests/test_refactor.py::TestVerify.test_module_import_catches_missing_import  # noqa: E501
# frob:tests tests/test_refactor.py::TestVerify.test_module_import_passes_clean_module  # noqa: E501
def verify_module_import(repo_root: Path, touched_files: list[Path]) -> VerifyOutcome:
    """T-3119's fix: `verify_import_resolution` only checks that a
    touched file PARSES and that its own local imports statically
    resolve against a target module's top-level names -- it structurally
    cannot catch a module that parses fine but raises at real `import`
    time, exactly T-3122's defect (a moved class body referencing
    `StrEnum`/`BaseModel` with neither imported: valid syntax, valid
    local-name resolution against nothing THIS file itself imports
    wrong, and still `NameError` the instant something actually imports
    it). PARSE IS NOT IMPORT.

    Runs a REAL interpreter `import <module>` for every touched `.py`
    file's own dotted module, each in its own fresh subprocess (never
    `ast`, never a static name-resolution pass) -- executing top-level
    module code is exactly what proves the module is actually
    importable, which is the only thing a `success=True` report from a
    verb that just rewrote imports is entitled to claim. Always run
    (never gated by a `--skip-*` flag, unlike `pytest_collect`/
    `check_delta`) and appended unconditionally by `run_verify_outcomes`
    -- an import-affecting verb must not be able to report success
    without this running.

    Scope is the plan's own `touched_files` (not a whole-repo sweep):
    importing an arbitrary file executes its top-level code, which is
    unsafe/slow to do unconditionally across an entire unrelated
    codebase on every transaction; the plan's own `touched_files` is
    exactly the set import-affecting edits (T-3105/T-3122's own defect
    class) singly could occur in, matching `verify_import_resolution`'s
    own existing scope."""
    modules = sorted(
        {
            module
            for path in touched_files
            # A touched path that no longer exists (e.g. move-module's
            # own OLD file, `git mv`d away) was never a candidate for a
            # real import check -- matching `_parse_touched_python_files`'s
            # identical `path.is_file()` filter for verify_import_resolution.
            if path.is_file() and path.suffix == ".py"
            for module in (_path_to_module(repo_root, path),)
            if module is not None
        }
    )
    if not modules:
        return VerifyOutcome(
            name="module_import",
            passed=True,
            detail="no touched .py file resolves to an importable module",
        )
    env = _import_check_env(repo_root)
    failures: list[str] = []
    for module in modules:
        result = guarded_subprocess_run(
            [sys.executable, "-B", "-c", f"import {module}"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        if result.is_err:
            failures.append(
                f"{module}: could not run import check: {result.danger_err}"
            )
            continue
        proc = result.danger_ok
        if proc.returncode != 0:
            failures.append(f"{module}: {(proc.stdout + proc.stderr)[-1500:]}")
    if failures:
        _log.warning("refactor.verify: module import check failed: %s", failures)
        return VerifyOutcome(
            name="module_import",
            passed=False,
            detail="; ".join(failures),
        )
    return VerifyOutcome(
        name="module_import",
        passed=True,
        detail=f"{len(modules)} touched module(s) import cleanly",
    )

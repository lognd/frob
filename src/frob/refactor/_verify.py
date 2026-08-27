"""Verify phase: the three in-command post-conditions a transaction must
pass before it is allowed to commit (docs/design/refactor-verb.md's
Transaction model, step 4).

Every check here returns a `VerifyOutcome`, never raises -- a failing
check is exactly as expected an outcome as a passing one; the transaction
orchestrator (`_transaction.py`) decides whether to roll back.
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run
from frob.refactor._models import VerifyOutcome

_log = get_logger(__name__)

__all__ = [
    "verify_check_delta",
    "verify_import_resolution",
    "verify_module_import",
    "verify_pytest_collect",
]


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
    try:
        for node in tree.body:
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


def _path_to_module(repo_root: Path, path: Path) -> str | None:
    """Inverse of `_resolve.module_to_path`: the dotted module name a
    file path resolves to, or `None` if `path` is not inside this
    repo's own import root (`src/` if it exists, else `repo_root`
    itself -- the identical layout convention `module_to_path` already
    encodes) or is not a plain importable module file (a `__init__.py`
    collapses to its package's own dotted name; anything else that
    fails to resolve under the root, or is not `.py`, is `None`)."""
    src_root = repo_root / "src"
    base = src_root if src_root.is_dir() else repo_root
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


def _import_check_env(repo_root: Path) -> dict[str, str]:
    """The subprocess `env` `verify_module_import` runs a real `import`
    under: the current environment plus this repo's own import root
    (`src/` if it exists, else `repo_root`) prepended onto `PYTHONPATH`
    -- the same layout convention `_resolve.module_to_path` and
    `_path_to_module` both already encode, so a module this repo's own
    refactor engine can RESOLVE by dotted name is also one a real
    subprocess interpreter can actually `import`, whether or not the
    target repo happens to be installed editable in the current venv."""
    src_root = repo_root / "src"
    import_root = str(src_root if src_root.is_dir() else repo_root)
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = import_root + os.pathsep + existing if existing else import_root
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


# frob:doc docs/commands/refactor.md#verify_pytest_collect
# frob:tests tests/test_refactor.py::TestVerify.test_pytest_collect_reports_failure
def verify_pytest_collect(
    repo_root: Path, targets: list[Path] | None = None, timeout: int = 100
) -> VerifyOutcome:
    """Post-condition 2: `pytest --collect-only` succeeds with no new
    collection error. `targets=None` collects the whole repo (the design
    doc's literal wording); a caller running inside the 120s
    foreground-cap discipline (agent-playbook.md sec 3b/6b) should pass
    the plan's own `touched_files` instead -- this is the coordinator's
    open design question, exposed here as a parameter rather than decided
    in this engine.
    """
    args = ["pytest", "--collect-only", "-q", "-p", "no:cacheprovider"]
    if targets:
        args.extend(str(t) for t in targets)
    result = guarded_subprocess_run(
        args,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.is_err:
        return VerifyOutcome(
            name="pytest_collect",
            passed=False,
            detail=f"could not run pytest --collect-only: {result.danger_err}",
        )
    proc = result.danger_ok
    passed = proc.returncode == 0
    detail = (
        (proc.stdout or "")[-2000:] if passed else (proc.stdout + proc.stderr)[-4000:]
    )
    if not passed:
        _log.warning(
            "refactor.verify: pytest --collect-only failed rc=%d", proc.returncode
        )
    return VerifyOutcome(name="pytest_collect", passed=passed, detail=detail)


# frob:doc docs/commands/refactor.md#verify_check_delta
# frob:tests tests/test_refactor.py::TestVerify.test_check_delta_reports_command_failure
# frob:tests \
# tests/test_refactor.py::TestVerify.test_check_delta_uses_current_interpreter
def verify_check_delta(repo_root: Path, timeout: int = 100) -> VerifyOutcome:
    """Post-condition 3: `frob check --delta` against a pre-refactor
    baseline is diff-clean. Delegated to the real CLI (not re-implemented
    here) so this stays identical to what an operator would run by hand;
    a missing baseline is reported as a passing-with-warning outcome
    rather than a hard failure, matching `--delta`'s own degrade-to-full
    behavior (agent-playbook.md sec 6).

    Invoked as `sys.executable -m frob` rather than a bare `frob` on
    PATH (agent-playbook.md sec 2): a bare `frob` may resolve to a stale
    globally-installed binary that silently checks against old gate
    logic, whereas `sys.executable -m frob` is guaranteed
    version-consistent with whatever interpreter/venv is running this
    code right now."""
    result = guarded_subprocess_run(
        [sys.executable, "-m", "frob", "check", "--delta"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.is_err:
        return VerifyOutcome(
            name="check_delta",
            passed=False,
            detail=f"could not run frob check --delta: {result.danger_err}",
        )
    proc = result.danger_ok
    passed = proc.returncode == 0
    detail = (proc.stdout + proc.stderr)[-4000:]
    if not passed:
        _log.warning(
            "refactor.verify: frob check --delta failed rc=%d", proc.returncode
        )
    return VerifyOutcome(name="check_delta", passed=passed, detail=detail)

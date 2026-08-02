"""Verify phase: the three in-command post-conditions a transaction must
pass before it is allowed to commit (docs/design/refactor-verb.md's
Transaction model, step 4).

Every check here returns a `VerifyOutcome`, never raises -- a failing
check is exactly as expected an outcome as a passing one; the transaction
orchestrator (`_transaction.py`) decides whether to roll back.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import ast
import sys
from pathlib import Path

from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run
from frob.refactor._models import VerifyOutcome

_log = get_logger(__name__)

__all__ = [
    "verify_check_delta",
    "verify_import_resolution",
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


# frob:doc docs/commands/refactor.md#verify_import_resolution
# frob:tests tests/test_refactor.py::TestVerify.test_import_resolution_catches_syntax_error  # noqa: E501
# frob:tests tests/test_refactor.py::TestVerify.test_import_resolution_catches_dangling_reference  # noqa: E501
def verify_import_resolution(
    touched_files: list[Path], repo_root: Path | None = None
) -> VerifyOutcome:
    """Post-condition 1: every touched file still parses as valid Python
    AND, for every absolute local-module import it contains, the imported
    name actually resolves against something that module currently
    defines -- a real (scoped, disclosed) import-graph resolution check,
    not merely a syntax parse (see `_local_import_gaps`'s docstring for
    the exact scope). A file that fails to parse, or that imports a name
    a repo-owned module no longer defines, after rewriting is exactly the
    "half-moved symbol" case the design doc's refuse-and-rollback rule
    exists for.

    `repo_root=None` (the historical call shape, kept so existing callers
    passing loose files with no enclosing repo still work) skips the
    local-module resolution pass and performs the syntax check only --
    the `detail` string says so explicitly rather than silently claiming
    full resolution ran.
    """
    broken: list[str] = []
    trees: dict[Path, ast.Module] = {}
    for path in touched_files:
        if not path.is_file():
            continue
        try:
            trees[path] = ast.parse(
                path.read_text(encoding="utf-8"), filename=str(path)
            )
        except SyntaxError as exc:
            broken.append(f"{path}: {exc}")
    if broken:
        _log.warning("refactor.verify: import resolution failed: %s", broken)
        return VerifyOutcome(
            name="import_resolution",
            passed=False,
            detail="; ".join(broken),
        )

    if repo_root is None:
        return VerifyOutcome(
            name="import_resolution",
            passed=True,
            detail=(
                f"{len(touched_files)} touched file(s) parse cleanly "
                "(no repo_root given -- syntax check only, local-module "
                "resolution skipped)"
            ),
        )

    gaps: list[str] = []
    for path, tree in trees.items():
        gaps.extend(_local_import_gaps(repo_root, path, tree))
    if gaps:
        _log.warning("refactor.verify: local import resolution failed: %s", gaps)
        return VerifyOutcome(
            name="import_resolution",
            passed=False,
            detail="; ".join(gaps),
        )
    return VerifyOutcome(
        name="import_resolution",
        passed=True,
        detail=(
            f"{len(touched_files)} touched file(s) parse cleanly and every "
            "absolute local-module import resolves"
        ),
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
# frob:tests tests/test_refactor.py::TestVerify.test_check_delta_uses_current_interpreter  # noqa: E501
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

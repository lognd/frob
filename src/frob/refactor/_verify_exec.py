import subprocess
import sys
from pathlib import Path

from typani import Err, Ok, Result

from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run
from frob.process._pytest_spawn import resolve_pytest_argv
from frob.refactor._models import VerifyOutcome

_log = get_logger(__name__)


def _filter_pytest_collect_targets(
    targets: list[Path] | None,
) -> tuple[list[Path] | None, list[str], VerifyOutcome | None]:
    """T-3136: split `targets` into (`.py` paths pytest may collect,
    skipped non-`.py` paths, an early-return `VerifyOutcome` if nothing
    is left to collect) -- factored out of `verify_pytest_collect` to
    keep that function under ARCH001's threshold. Mirrors
    `_parse_touched_python_files`'s own suffix filter (T-1885): a
    non-`.py` carrier handed to pytest's argv is a hard USAGE_ERROR
    (`rc=4`), unrelated to whether any real test collects cleanly."""
    if not targets:
        return targets, [], None
    filtered = [t for t in targets if t.suffix == ".py"]
    skipped = [str(t) for t in targets if t.suffix != ".py"]
    if not filtered:
        skipped_note = f" ({len(skipped)} non-.py file(s) skipped, not applicable)"
        early = VerifyOutcome(
            name="pytest_collect",
            passed=True,
            detail="nothing to collect: all touched files are non-.py" + skipped_note,
            skipped=tuple(skipped),
        )
        return filtered, skipped, early
    return filtered, skipped, None


# frob:ticket T-3311
def _spawn_pytest_collect(
    repo_root: Path, filtered_targets: list[Path] | None, *, timeout: int
) -> Result[subprocess.CompletedProcess[str], str]:
    """`verify_pytest_collect`'s argv-resolution + spawn, split out to
    keep that function under the ARCH001 line threshold (T-3311). Builds
    the `--collect-only` argv via `resolve_pytest_argv` (the shared
    pytest-spawn resolution helper) and spawns it; `Err(str)` carries a
    ready-to-use `VerifyOutcome.detail` message for either failure mode
    (could not resolve an interpreter with pytest importable, or the
    resolved spawn itself failed) rather than a typed error the caller
    would just stringify anyway."""
    collect_args = ["--collect-only", "-q", "-p", "no:cacheprovider"]
    if filtered_targets:
        collect_args.extend(str(t) for t in filtered_targets)
    resolved_argv = resolve_pytest_argv(*collect_args)
    if resolved_argv.is_err:
        return Err(f"could not resolve a pytest spawn: {resolved_argv.danger_err}")
    result = guarded_subprocess_run(
        resolved_argv.danger_ok,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.is_err:
        return Err(f"could not run pytest --collect-only: {result.danger_err}")
    return Ok(result.danger_ok)


# frob:doc docs/commands/refactor.md#verify_pytest_collect
# frob:ticket T-3136
# frob:ticket T-3311
# frob:tests tests/test_refactor.py::TestVerify.test_pytest_collect_reports_failure
# frob:tests \
#   tests/test_refactor.py::TestVerify.test_pytest_collect_skips_non_python_touched_files  # noqa: E501
# frob:tests \
#   tests/test_refactor.py::TestVerify.test_pytest_collect_passes_when_all_touched_files_non_python  # noqa: E501
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

    T-3136: `targets` is the same `touched_files` set `verify_import_
    resolution` receives -- the FULL set a `RefactorPlan.reference_ops`
    entry rewrote, not just Python source. A non-`.py` carrier is
    filtered out by `_filter_pytest_collect_targets` before ever
    reaching pytest's argv (mirroring `_parse_touched_python_files`'s
    own filter) and disclosed via `skipped` rather than silently
    dropped -- same shape as `verify_import_resolution`. If `targets` is
    given but every entry is non-Python, there is nothing to collect:
    passes with a note, exactly as `verify_import_resolution` passes on
    an empty `trees` set.
    """
    filtered_targets, skipped, early = _filter_pytest_collect_targets(targets)
    if early is not None:
        return early
    spawned = _spawn_pytest_collect(repo_root, filtered_targets, timeout=timeout)
    if spawned.is_err:
        return VerifyOutcome(
            name="pytest_collect",
            passed=False,
            detail=spawned.danger_err,
            skipped=tuple(skipped),
        )
    proc = spawned.danger_ok
    passed = proc.returncode == 0
    detail = (
        (proc.stdout or "")[-2000:] if passed else (proc.stdout + proc.stderr)[-4000:]
    )
    skipped_note = (
        f" ({len(skipped)} non-.py file(s) skipped, not applicable)" if skipped else ""
    )
    detail = detail + skipped_note
    if not passed:
        _log.warning(
            "refactor.verify: pytest --collect-only failed rc=%d", proc.returncode
        )
    return VerifyOutcome(
        name="pytest_collect", passed=passed, detail=detail, skipped=tuple(skipped)
    )


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

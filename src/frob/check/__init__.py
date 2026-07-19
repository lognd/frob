"""frob.check -- multi-language quality gate orchestration (docs/commands/check.md).

`run_check` (Python) and its `run_check_cpp`/`run_check_rust`/`run_check_ts`
siblings run each language's tools in parallel and aggregate every
`ToolResult` into a `CheckResult`. The per-tool runner helpers live in the
private `_python`/`_native`/`_ts` submodules to keep this module focused on
the public orchestration surface; the public symbols stay defined here so
their `frob:doc`/`frob:tests` bindings keep their `__init__.py` symref.
"""

# frob:waive TEST005 reason="module line coverage 79.1%, debt T-0160"

from __future__ import annotations

import concurrent.futures
import logging
import sys
from pathlib import Path
from typing import Callable

from pydantic import BaseModel

from frob.check._native import (
    _run_cargo,
    _run_cargo_fmt_check,
    _run_cargo_test,
    _run_clang_format,
    _run_clang_tidy_cmake,
    _run_cmake_build,
    _run_ctest,
)
from frob.check._python import (
    _run_arch,
    _run_bind,
    _run_cycle,
    _run_dup,
    _run_exports,
    _run_gates,
    _run_ruff,
    _run_ty,
)
from frob.check._ts import _run_eslint, _run_prettier, _run_tsc, _run_vitest
from frob.logging import get_logger
from frob.process.parsers.common import Diagnostic, ToolResult

_log = get_logger(__name__)

# The python-mode tool stages --only may name (gate names are accepted too
# and resolved through frob.gates._ALL_GATES at call time).
_TOOL_STAGES = frozenset(
    {"ruff", "ty", "cycle", "dup", "arch", "bind", "exports", "gates"}
)


def _bucket_diags(
    results: list[ToolResult],
) -> dict[str, list[tuple[str, Diagnostic]]]:
    """Partition every diagnostic into error/warning/note buckets in one pass."""
    buckets: dict[str, list[tuple[str, Diagnostic]]] = {
        "error": [],
        "warning": [],
        "note": [],
    }
    for r in results:
        for d in r.diagnostics:
            key = d.severity if d.severity in ("error", "warning") else "note"
            buckets[key].append((r.tool, d))
    return buckets


def _section_lines(
    title: str, style: str, items: list[tuple[str, Diagnostic]], color: bool
) -> list[str]:
    """Rendered lines for one report section (empty if it has no diagnostics)."""
    if not items:
        return []
    from frob.logging.color import CYAN, paint

    lines = [paint(title, style, color)]
    lines.extend(
        f"  {paint(f'[{tool}]', CYAN, color)} {d.as_text()}" for tool, d in items
    )
    lines.append("")
    return lines


# frob:doc docs/commands/check.md#public-api
class CheckResult(BaseModel):
    """Aggregate outcome of one `frob check` run: every tool's `ToolResult`."""

    model_config = {}

    path: str
    results: list[ToolResult]

    @property
    def total_errors(self) -> int:
        # frob:doc docs/commands/check.md#public-api
        """Sum of error-severity diagnostics across every tool that ran."""
        return sum(r.error_count for r in self.results)

    @property
    def total_warnings(self) -> int:
        # frob:doc docs/commands/check.md#public-api
        """Sum of warning-severity diagnostics across every tool that ran."""
        return sum(r.warning_count for r in self.results)

    def as_text(self, color: bool = False) -> str:
        # frob:doc docs/commands/check.md#public-api
        """Human-readable report: errors, then warnings, then notes, then a
        per-tool summary table."""
        from frob.logging.color import BOLD, GREEN, RED, YELLOW, paint

        lines: list[str] = [self._header_line(color), ""]

        buckets = _bucket_diags(self.results)
        lines.extend(
            _section_lines("## Errors", f"{BOLD};{RED}", buckets["error"], color)
        )
        lines.extend(
            _section_lines("## Warnings", f"{BOLD};{YELLOW}", buckets["warning"], color)
        )
        lines.extend(
            _section_lines("## Notes / suggestions", BOLD, buckets["note"], color)
        )

        lines.append(paint("## Tool summary", BOLD, color))
        for r in self.results:
            ok = r.passed and r.error_count == 0
            icon = paint("pass", GREEN, color) if ok else paint("FAIL", RED, color)
            lines.append(f"  {icon}  {r.tool:<22}  {r.summary}")
        return "\n".join(lines)

    def _header_line(self, color: bool) -> str:
        """The single-line status/error/warning-count header for `as_text`."""
        from frob.logging.color import BOLD, DIM, GREEN, RED, YELLOW, paint

        err = self.total_errors
        warn = self.total_warnings
        status = "FAIL" if err > 0 else ("WARN" if warn > 0 else "PASS")
        status_code = {"FAIL": RED, "WARN": YELLOW, "PASS": GREEN}[status]
        errs = f"{err} error{'s' if err != 1 else ''}"
        warns = f"{warn} warning{'s' if warn != 1 else ''}"
        header_status = paint(f"[{status}]", f"{BOLD};{status_code}", color)
        return (
            f"frob check {self.path}  {header_status}  "
            f"{paint(errs, RED if err else DIM, color)}  "
            f"{paint(warns, YELLOW if warn else DIM, color)}"
        )

    # frob:waive TEST005 reason="CheckResult.as_json 50.0% branch cover, debt T-0160"
    def as_json(self) -> str:
        # frob:doc docs/commands/check.md#public-api
        """The full structured result as JSON (`--json` CLI output)."""
        return self.model_dump_json(indent=2)


def _unknown_only_result(root: Path, unknown: frozenset[str]) -> CheckResult:
    """A loud config-error CheckResult for unrecognised `--only` stage names."""
    from frob.gates import _ALL_GATES

    return CheckResult(
        path=str(root),
        results=[
            ToolResult(
                tool="config",
                exit_code=2,
                summary=f"unknown --only stage(s): {sorted(unknown)}",
                diagnostics=[
                    Diagnostic(
                        severity="error",
                        message=(
                            f"unknown --only stage(s) {sorted(unknown)}; "
                            f"tools: {sorted(_TOOL_STAGES)}; "
                            f"gates: {sorted(_ALL_GATES)}"
                        ),
                    )
                ],
            )
        ],
    )


def _resolve_only(
    only: frozenset[str] | None,
) -> tuple[frozenset[str], frozenset[str] | None, frozenset[str]]:
    """Split `--only` into `(gate_only, adjusted_only, unknown)`.

    An unknown name must be a loud config error, never a silently-empty
    selection that passes vacuously (observed: `--only doclink` returned
    PASS having run nothing at all).
    """
    if only is None:
        return frozenset(), None, frozenset()
    from frob.gates import _ALL_GATES

    gate_only = frozenset(only) & _ALL_GATES
    unknown = frozenset(only) - _TOOL_STAGES - _ALL_GATES
    if unknown:
        return gate_only, only, unknown
    adjusted = (frozenset(only) - gate_only) | {"gates"} if gate_only else only
    return gate_only, adjusted, frozenset()


def _python_skip_flags(
    *,
    skip_ruff: bool,
    skip_ty: bool,
    skip_arch: bool,
    skip_cycle: bool,
    skip_dup: bool,
    skip_bind: bool,
    skip_exports: bool,
    skip_gates: bool,
) -> dict[str, bool]:
    """The per-tool skip-flag mapping `_python_tasks` consults."""
    return {
        "ruff": skip_ruff,
        "ty": skip_ty,
        "cycle": skip_cycle,
        "dup": skip_dup,
        "arch": skip_arch,
        "bind": skip_bind,
        "exports": skip_exports,
        "gates": skip_gates,
    }


def _python_tasks(
    root: Path,
    *,
    only: frozenset[str] | None,
    gate_only: frozenset[str],
    ruff_args: list[str] | None,
    ticket: str | None,
    base: str | None,
    skips: dict[str, bool],
    delta: bool = False,
) -> list[Callable[[], ToolResult | list[ToolResult] | None]]:
    """The enabled per-tool jobs for a Python check run."""

    def wanted(name: str) -> bool:
        return only is None or name in only

    tasks: list[Callable[[], ToolResult | list[ToolResult] | None]] = []
    if not skips["ruff"] and wanted("ruff"):
        tasks.append(lambda: _run_ruff(root, ruff_args))
    if not skips["ty"] and wanted("ty"):
        tasks.append(lambda: _run_ty(root))
    if not skips["cycle"] and wanted("cycle"):
        tasks.append(lambda: _run_cycle(root))
    if not skips["dup"] and wanted("dup"):
        tasks.append(lambda: _run_dup(root))
    if not skips["arch"] and wanted("arch"):
        tasks.append(lambda: _run_arch(root))
    if not skips["bind"] and wanted("bind"):
        tasks.append(lambda: _run_bind(root))
    if not skips["exports"] and wanted("exports"):
        tasks.append(lambda: _run_exports(root))
    if not skips["gates"] and wanted("gates"):
        tasks.append(
            lambda: _run_gates(
                root, ticket=ticket, base=base, gates=gate_only, delta=delta
            )
        )
    return tasks


def _stdout_log_handlers() -> list[logging.StreamHandler]:
    """Every root-logger `StreamHandler` currently writing to `sys.stdout`."""
    root_logger = logging.getLogger()
    return [
        h
        for h in root_logger.handlers
        if isinstance(h, logging.StreamHandler) and h.stream is sys.stdout
    ]


def _run_tasks_concurrently(
    tasks: list[Callable[[], ToolResult | list[ToolResult] | None]],
) -> list[ToolResult]:
    """Run `tasks` in a `ThreadPoolExecutor` and flatten results, dropping Nones."""
    results: list[ToolResult] = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(fn) for fn in tasks]
        for future in futures:
            val = future.result()
            if val is None:
                continue
            if isinstance(val, list):
                results.extend(val)
            else:
                results.append(val)
    return results


def _restore_stdout_log_levels(
    handlers: list[logging.StreamHandler], saved_levels: list[int]
) -> None:
    """Force every handler back to its pre-batch level (T-0122).

    Guards against `_run_tasks_concurrently`'s tasks racing the shared,
    process-global stdout log handler and leaving it stuck (see
    `_collect_results`'s docstring for the full mechanism)."""
    for h, level in zip(handlers, saved_levels, strict=True):
        if h.level != level:
            _log.warning(
                "_collect_results: stdout log handler %r left at %s after "
                "concurrent check tasks raced (T-0122); restoring to %s",
                h,
                logging.getLevelName(h.level),
                logging.getLevelName(level),
            )
        h.setLevel(level)


def _collect_results(
    tasks: list[Callable[[], ToolResult | list[ToolResult] | None]],
) -> list[ToolResult]:
    """Run `tasks` in parallel and flatten their results, dropping Nones.

    T-0122: some check-stage tools (`frob.arch.analyze_project`,
    `frob.dup.find_duplicates`) briefly raise the shared, process-global
    stdout log handler to WARNING while they run, to keep `frob.lang`'s
    per-parse INFO/DEBUG logging off stdout. That save/restore is not
    thread-safe: two of these tasks racing inside this same
    `ThreadPoolExecutor` can interleave their enter/exit so the handler is
    left stuck at WARNING after every future has *returned* -- silently
    swallowing the caller's own INFO-level summary log with no exception
    and no trace (reproduced: `frob check` exiting 0 with no printed
    summary at all, 4/5 runs under load). Rather than touch the racy
    tools (out of this ticket's scope), save the stdout handler levels
    before the batch and force-restore them after, so `run_check`'s
    caller always gets a printed summary regardless of how the tasks
    raced with each other.
    """
    stdout_handlers = _stdout_log_handlers()
    saved_levels = [h.level for h in stdout_handlers]
    try:
        return _run_tasks_concurrently(tasks)
    finally:
        _restore_stdout_log_levels(stdout_handlers, saved_levels)


# frob:ticket T-0028
# frob:doc docs/commands/check.md#public-api
# frob:waive TEST005 reason="run_check 83.3% branch cover, debt T-0160"
def run_check(
    root: Path,
    *,
    skip_ruff: bool = False,
    skip_ty: bool = False,
    skip_arch: bool = False,
    skip_cycle: bool = False,
    skip_dup: bool = False,
    skip_bind: bool = False,
    skip_exports: bool = False,
    skip_gates: bool = False,
    ruff_args: list[str] | None = None,
    only: frozenset[str] | None = None,
    ticket: str | None = None,
    base: str | None = None,
    delta: bool = False,
) -> CheckResult:
    """Quality gate for Python projects: ruff, ty, cycle/dup/arch/bind, gates, etc.

    `delta=True` (T-0095) makes the gates stage report only violations new
    since `.frob/baseline` (see `frob.gates.stamp_baseline`/`delta_violations`) --
    an agent-facing signal-only mode; every other tool is unaffected.
    """
    skips = _python_skip_flags(
        skip_ruff=skip_ruff,
        skip_ty=skip_ty,
        skip_arch=skip_arch,
        skip_cycle=skip_cycle,
        skip_dup=skip_dup,
        skip_bind=skip_bind,
        skip_exports=skip_exports,
        skip_gates=skip_gates,
    )
    return _run_check_with_skips(
        root,
        skips=skips,
        ruff_args=ruff_args,
        only=only,
        ticket=ticket,
        base=base,
        delta=delta,
    )


def _run_check_with_skips(
    root: Path,
    *,
    skips: dict[str, bool],
    ruff_args: list[str] | None,
    only: frozenset[str] | None,
    ticket: str | None,
    base: str | None,
    delta: bool,
) -> CheckResult:
    """`run_check`'s task-selection and execution tail, once its many
    `skip_*` flags have been collapsed into `skips`."""
    gate_only, only, unknown = _resolve_only(only)
    if unknown:
        return _unknown_only_result(root, unknown)

    tasks = _python_tasks(
        root,
        only=only,
        gate_only=gate_only,
        ruff_args=ruff_args,
        ticket=ticket,
        base=base,
        skips=skips,
        delta=delta,
    )
    return CheckResult(path=str(root), results=_collect_results(tasks))


# ---------------------------------------------------------------------------
# C/C++ checks
# ---------------------------------------------------------------------------


# frob:doc docs/commands/check.md#public-api
# frob:waive TEST005 reason="run_check_cpp 50.0% branch cover, debt T-0160"
def run_check_cpp(
    root: Path,
    *,
    build_dir: Path | None = None,
    skip_build: bool = False,
    skip_clang_tidy: bool = False,
    skip_clang_format: bool = False,
    skip_tests: bool = False,
    valgrind: bool = False,
) -> CheckResult:
    """Quality gate for CMake C/C++ projects."""
    results: list[ToolResult] = []
    bdir = build_dir or (root / "build")

    if not skip_build:
        r = _run_cmake_build(root, bdir)
        results.append(r)
        if r.exit_code != 0:
            skip_tests = True

    post_build = _cpp_post_build_tasks(
        root,
        bdir,
        skip_clang_tidy=skip_clang_tidy,
        skip_clang_format=skip_clang_format,
        skip_tests=skip_tests,
        valgrind=valgrind,
    )
    results.extend(_run_tasks_concurrently(post_build))
    return CheckResult(path=str(root), results=results)


def _cpp_post_build_tasks(
    root: Path,
    bdir: Path,
    *,
    skip_clang_tidy: bool,
    skip_clang_format: bool,
    skip_tests: bool,
    valgrind: bool,
) -> list[Callable[[], ToolResult | list[ToolResult] | None]]:
    """The enabled post-build job callables for a CMake C/C++ check run."""
    post_build: list[Callable[[], ToolResult | list[ToolResult] | None]] = []
    if not skip_clang_tidy:
        post_build.append(lambda: _run_clang_tidy_cmake(root, bdir))
    if not skip_clang_format:
        post_build.append(lambda: _run_clang_format(root))
    if not skip_tests:
        _valgrind = valgrind
        post_build.append(lambda: _run_ctest(bdir, valgrind=_valgrind))
    return post_build


# ---------------------------------------------------------------------------
# Rust checks
# ---------------------------------------------------------------------------


# frob:doc docs/commands/check.md#public-api
# frob:waive TEST005 reason="run_check_rust 33.3% branch cover, debt T-0160"
def run_check_rust(
    root: Path,
    *,
    skip_check: bool = False,
    skip_clippy: bool = False,
    skip_fmt: bool = False,
    skip_tests: bool = False,
    valgrind: bool = False,
) -> CheckResult:
    """Quality gate for Rust/Cargo projects."""
    results: list[ToolResult] = []

    if not skip_check:
        r = _run_cargo("check", root)
        if r is not None:
            results.append(r)
    if not skip_clippy:
        r = _run_cargo("clippy", root, extra=["--", "-D", "warnings"])
        if r is not None:
            results.append(r)
    if not skip_fmt:
        r = _run_cargo_fmt_check(root)
        if r is not None:
            results.append(r)
    if not skip_tests:
        r = _run_cargo_test(root, valgrind=valgrind)
        if r is not None:
            results.append(r)

    return CheckResult(path=str(root), results=results)


# ---------------------------------------------------------------------------
# TypeScript checks
# ---------------------------------------------------------------------------


# frob:doc docs/commands/check.md#public-api
# frob:waive TEST005 reason="run_check_ts 58.8% branch cover, debt T-0160"
def run_check_ts(
    root: Path,
    *,
    skip_tsc: bool = False,
    skip_eslint: bool = False,
    skip_prettier: bool = False,
    skip_tests: bool = False,
) -> CheckResult:
    """Quality gate for npm/TypeScript projects (tsc/eslint/prettier/vitest)."""
    tasks: list[Callable[[], ToolResult | None]] = []
    if not skip_tsc:
        tasks.append(lambda: _run_tsc(root))
    if not skip_eslint:
        tasks.append(lambda: _run_eslint(root))
    if not skip_prettier:
        tasks.append(lambda: _run_prettier(root))
    if not skip_tests:
        tasks.append(lambda: _run_vitest(root))

    results: list[ToolResult] = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(fn) for fn in tasks]
        for future in futures:
            r = future.result()
            if r is not None:
                results.append(r)

    return CheckResult(path=str(root), results=results)


# ---------------------------------------------------------------------------
# Auto-detect project type
# ---------------------------------------------------------------------------


# frob:doc docs/commands/check.md#public-api
def detect_project_type(root: Path) -> str:
    """Returns 'python', 'cpp', 'rust', 'typescript', or 'unknown'."""
    if (root / "Cargo.toml").exists():
        return "rust"
    if (root / "CMakeLists.txt").exists():
        return "cpp"
    if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        return "python"
    if (root / "package.json").exists() and (root / "tsconfig.json").exists():
        return "typescript"
    if list(root.glob("*.cpp")) or list(root.glob("*.cc")) or list(root.glob("*.c")):
        return "cpp"
    return "unknown"


__all__ = [
    "CheckResult",
    "detect_project_type",
    "run_check",
    "run_check_cpp",
    "run_check_rust",
    "run_check_ts",
]

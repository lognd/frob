"""frob.check -- multi-language quality gate orchestration (docs/commands/check.md).

`run_check` (Python) and its `run_check_cpp`/`run_check_rust`/`run_check_ts`
siblings run each language's tools in parallel and aggregate every
`ToolResult` into a `CheckResult`. The per-tool runner helpers live in the
private `_python`/`_native`/`_ts` submodules to keep this module focused on
the public orchestration surface; the public symbols stay defined here so
their `frob:doc`/`frob:tests` bindings keep their `__init__.py` symref.
`frob.check._memo`'s per-run memoization helpers are consumed cross-module
(`frob.dup._legacy`, `frob.graph`, `frob.arch`, `frob.lang`) and are
re-exported here for the same reason (T-0599).
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/check/__init__.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

# frob:waive TEST005 reason="module line coverage 79.1%, debt T-0160"

from __future__ import annotations

import concurrent.futures
import logging
from pathlib import Path
from typing import Callable

from pydantic import BaseModel

from frob.check._memo import (
    memoize_per_run,
    reset_run_memo,
    run_memo_scope,
    run_memo_stats,
)
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
from frob.doctor import verify_derived_state
from frob.lang import reset_parse_cache
from frob.logging import get_logger
from frob.logging.quiet import _stdout_stream_handlers as _stdout_log_handlers
from frob.process._lock import derived_state_lock
from frob.process.parsers.common import Diagnostic, ToolResult

_log = get_logger(__name__)

# The python-mode tool stages --only may name (gate names are accepted too
# and resolved through frob.gates._ALL_GATES at call time).
_TOOL_STAGES = frozenset(
    {"ruff", "ty", "cycle", "dup", "arch", "bind", "exports", "gates"}
)


# frob:doc docs/modules/gates.md#rule-catalog
# frob:ticket T-0603
# frob:tests tests/unit/test_check.py::TestDerivedStateIntegrityGate.test_corrupt_artifact_fails_closed_before_any_stage_runs  # noqa: E501
# frob:tests tests/unit/test_check.py::TestDerivedStateIntegrityGate.test_absent_artifact_is_not_a_violation  # noqa: E501
# frob:ticket T-0603
def _derived_state_integrity_result(root: Path) -> ToolResult | None:
    """`None` if every derived artifact under `root` is present-and-healthy
    or simply absent (T-0570's `verify_derived_state` fail-open-on-absent
    semantics -- a fresh clone/post-clean tree has no artifacts yet, which
    is not corruption); a single hard-ERROR `ToolResult` naming every
    present-but-corrupt artifact otherwise (T-0603).

    Every `run_check*` entry point calls this exactly ONCE, synchronously,
    BEFORE dispatching any concurrent stage -- never from inside a stage
    that runs concurrently with others. `arch`/`dup`/`gates` all read or
    (re)build the same `.frob/cache.db`/`dup.db` this function fingerprints;
    checking from inside one of those stages while the others run
    concurrently in the same `ThreadPoolExecutor` batch races a live
    writer (a mid-rebuild cache observed by another thread reads as
    "corrupt" when it is merely momentarily empty/in-progress) -- this bit
    for real during T-0603 development, caught by
    `TestCheckBuildsGraphOnce.test_run_check_calls_build_graph_exactly_once`
    turning red. Checking once, up front, serializes the integrity read
    before any writer starts, which is also strictly cheaper than a
    per-stage recheck (one fingerprint pass per `frob check` run, not one
    per gate family)."""
    corrupt = tuple(
        d for d in verify_derived_state(root) if d.present and not d.healthy
    )
    if not corrupt:
        return None
    names = ", ".join(f"{d.name} ({d.path}: {d.detail})" for d in corrupt)
    commands = " ; ".join(f"rm -f {d.path}" for d in corrupt)
    return ToolResult(
        tool="derived-state-integrity",
        exit_code=1,
        diagnostics=[
            Diagnostic(
                file=d.path,
                severity="error",
                code="DERIVED001",
                message=(
                    f"DERIVED001: derived artifact {d.name} ({d.path}) is "
                    f"corrupt: {d.detail}. This is cached/derived state, not "
                    "source of truth -- run `frob doctor` for the full "
                    f"diagnosis, then `rm -f {d.path}` to let it rebuild."
                ),
            )
            for d in corrupt
        ],
        summary=(
            f"derived-state-integrity FAILED: corrupt derived state: {names} "
            f"-- {commands}"
        ),
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
    # frob:ticket T-0588
    # frob:tests tests/unit/test_app_runners_batch6.py::TestCheckRunner.test_json_mode_prints_json_and_errors_exit_1  # noqa: E501
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


# frob:ticket T-0627
#: Named `--only` presets grouping related stages so an agent can budget one
#: chunk of `frob check` per invocation instead of the full run (T-0627: a
#: full `--only gates` pass on this repo measured ~113s wall time, over the
#: ~120s agent foreground cap documented in `docs/guides/agent-playbook.md`
#: section 3b -- past that cap the harness auto-backgrounds the command and
#: a dispatched sub-agent stalls forever waiting on a notification that can
#: never reach it). Membership names are tool names (this module's own
#: `_TOOL_STAGES`) or gate names (`frob.gates._ALL_GATES`); `_resolve_only`
#: expands a group alias into its members before doing its existing
#: gate/tool split, so a group behaves exactly like hand-listing its
#: members on `--only`. The gate-name split mirrors
#: `frob.gates._PROCESS_POOL_GATES` (the CPU-bound gates dispatched to a
#: process pool) vs. the thread-pool remainder: `gates-native`/
#: `gates-security` each take a few of the CPU-bound giants (measured
#: comfortably under the 90s per-stage target), `gates-fast` takes every
#: cheap/I/O-bound gate (also well under budget on its own).
# frob:ticket T-0788
# frob:ticket T-0665
_STAGE_GROUPS: dict[str, frozenset[str]] = {
    "lint": frozenset({"ruff", "ty"}),
    "static": frozenset({"cycle", "dup", "arch", "bind", "exports"}),
    "gates-fast": frozenset(
        {
            "drift",
            "coverage",
            "invariant",
            "test",
            "policy",
            "doclink",
            "docanchor",
            "fuzz",
            "release",
            "decisions",
            "tickets",
            "refs",
            "registry",
            "compliance",
            "docblocks",
            "walk_lint",
            "excludehazard",
            "debt",
            # frob:ticket T-0797
            "deprecated",
            "render_lint",
            "parse_failures",
            "lang_conformance",
            "lang_project_conformance",
            "scope",
            "prework",
            # T-0851: FMT001, diff-scoped like coverage/todo above.
            "fmt",
            # T-0628: AFFECT001/AFFECT002, diff-scoped like coverage/fmt above.
            "affect_drift",
            # frob:ticket T-1044
            # T-1012: FFI001/FFI002 (ffi_boundary_gate, T-0690)
            # was registered in frob.gates._ALL_GATES but never added to a
            # _STAGE_GROUPS member -- it is thread-pool (not in
            # frob.gates._PROCESS_POOL_GATES), the same shape as the rest of
            # this group, so it belongs here, not gates-native/-security.
            "ffi_boundary",
        }
    ),
    # frob:ticket T-0688
    # T-0688: exhaustive_handling (EXHAUST001/EXHAUST002) added alongside
    # archgate -- same process-pool CPU-bound shape (a repo-wide python
    # parse + per-function may-raise fixpoint), required so the new gate
    # this ticket registers in frob.gates._ALL_GATES stays reachable via
    # `--only <group>` and so TestCheckStageGroups' drift-lock stays green.
    "gates-native": frozenset({"archgate", "clones", "perf", "exhaustive_handling"}),
    # frob:ticket T-0824
    "gates-security": frozenset(
        {
            "sys",
            "pii_structural",
            "secrets",
            "dead_symbols",
            "protocol_summary",
            # T-0665: OPAQUE001's tracked-file scan is the same shape/cost
            # class as secrets' own, belongs in the same security group.
            "opaque",
        }
    ),
}


# frob:ticket T-0627
# frob:doc docs/commands/check.md#public-api
# frob:tests tests/system/test_cli_check.py::TestCheckStageGroups.test_available_stages_cover_every_gate_and_tool  # noqa: E501
def available_stages() -> list[str]:
    """Sorted `_STAGE_GROUPS` alias names `frob check --only list` prints (T-0627)."""
    return sorted(_STAGE_GROUPS)


# frob:ticket T-0627
def _expand_stage_groups(only: frozenset[str]) -> frozenset[str]:
    """Expand any `_STAGE_GROUPS` alias in `only` into its member stage names.

    A name that is not a recognized group (a bare tool/gate name, or truly
    unknown) passes through unchanged, so mixing a group alias with
    individual `--only` names in one invocation is additive, never
    contradictory -- `_resolve_only`'s existing unknown-name rejection
    still fires for anything left over that is neither a group, a tool, nor
    a gate name.
    """
    expanded: set[str] = set()
    for name in only:
        expanded |= _STAGE_GROUPS.get(name, {name})
    return frozenset(expanded)


def _resolve_only(
    only: frozenset[str] | None,
) -> tuple[frozenset[str], frozenset[str] | None, frozenset[str]]:
    """Split `--only` into `(gate_only, adjusted_only, unknown)`.

    An unknown name must be a loud config error, never a silently-empty
    selection that passes vacuously (observed: `--only doclink` returned
    PASS having run nothing at all). T-0627: `only` is first expanded
    through `_expand_stage_groups`, so a stage-group alias (`lint`,
    `static`, `gates-fast`, `gates-native`, `gates-security`) resolves to
    exactly the same `(gate_only, adjusted, unknown)` its expansion would.
    """
    if only is None:
        return frozenset(), None, frozenset()
    from frob.gates import _ALL_GATES

    only = _expand_stage_groups(frozenset(only))
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


# T-0364: dropped the private duplicate of
# `frob.logging.quiet._stdout_stream_handlers` (identical body, dup
# group) -- imported below instead; `frob.check` already depends on
# `frob.logging`, so this adds no new edge.


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
    # T-0859: hold a SHARED `derived_state_lock` for the run's entire
    # duration -- precheck through the last stage's read -- so a second
    # frob process's EXCLUSIVE writer cannot rewrite `.frob` between this
    # process's integrity precheck and a later stage's read of the same
    # artifacts (the cross-process TOCTOU window T-0603 disclosed as its
    # own residual). See `derived_state_lock`'s docstring for the
    # shared/exclusive contract.
    with derived_state_lock(root, exclusive=False):
        # T-0603: single, synchronous, pre-dispatch integrity check -- see
        # `_derived_state_integrity_result`'s docstring for why this must
        # run before any concurrent stage starts, not from inside one.
        integrity_failure = _derived_state_integrity_result(root)
        if integrity_failure is not None:
            return CheckResult(path=str(root), results=[integrity_failure])

        # T-0414: fresh parse-cache instrumentation per invocation (see
        # `frob.lang.reset_parse_cache`'s docstring) -- correctness never
        # depends on this reset, only the per-run hit/miss counters do.
        reset_parse_cache()
        gate_only, only, unknown = _resolve_only(only)
        if unknown:
            return _unknown_only_result(root, unknown)

        # T-0423: memoize the heavy pure analyses (build_graph/analyze_
        # project) for exactly the lifetime of this run (`frob.check.
        # _memo.run_memo_scope`'s docstring) -- a stage that calls one
        # twice within this `with` block gets a cache hit; any caller
        # outside it (CLI runners, tests exercising real incremental
        # rebuilds) is unaffected.
        with run_memo_scope():
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
# frob:ticket T-0554
# frob:waive TEST005 reason="run_check_cpp 50.0% branch cover, debt T-0160"
def run_check_cpp(
    root: Path,
    *,
    build_dir: Path | None = None,
    skip_build: bool = False,
    skip_clang_tidy: bool = False,
    skip_clang_format: bool = False,
    skip_tests: bool = False,
    skip_gates: bool = False,
    valgrind: bool = False,
    ticket: str | None = None,
    base: str | None = None,
    delta: bool = False,
) -> CheckResult:
    """Quality gate for CMake C/C++ projects.

    T-0554: the doc/coverage/drift/invariant gates stage now runs here too
    (`_run_gates`, same call `_python_tasks` makes) -- previously only the
    Python pipeline ever called `_run_gates`, so a pure C/C++ repo's
    COV001/DOC001-3/DRIFT001-2/INV/DEC/TODO001 gates silently never
    executed (docs/audits/lang-check-docs.md finding 1).

    T-0603: a corrupt derived artifact (`.frob/cache.db`, `.frob/baseline`,
    etc.) short-circuits everything below with a single
    `derived-state-integrity` ERROR result, checked once before the build
    even starts -- see `_derived_state_integrity_result`'s docstring.

    T-0859: the precheck through the last stage's read is held under one
    SHARED `derived_state_lock`, closing the cross-process TOCTOU window
    a bare precheck leaves open -- see `derived_state_lock`'s docstring.
    """
    with derived_state_lock(root, exclusive=False):
        integrity_failure = _derived_state_integrity_result(root)
        if integrity_failure is not None:
            return CheckResult(path=str(root), results=[integrity_failure])

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
            skip_gates=skip_gates,
            valgrind=valgrind,
            ticket=ticket,
            base=base,
            delta=delta,
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
    skip_gates: bool,
    valgrind: bool,
    ticket: str | None = None,
    base: str | None = None,
    delta: bool = False,
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
    if not skip_gates:
        post_build.append(
            lambda: _run_gates(root, ticket=ticket, base=base, delta=delta)
        )
    return post_build


# ---------------------------------------------------------------------------
# Rust checks
# ---------------------------------------------------------------------------


# frob:doc docs/commands/check.md#public-api
# frob:ticket T-0554
# frob:waive TEST005 reason="run_check_rust 33.3% branch cover, debt T-0160"
def run_check_rust(
    root: Path,
    *,
    skip_check: bool = False,
    skip_clippy: bool = False,
    skip_fmt: bool = False,
    skip_tests: bool = False,
    skip_gates: bool = False,
    valgrind: bool = False,
    ticket: str | None = None,
    base: str | None = None,
    delta: bool = False,
) -> CheckResult:
    """Quality gate for Rust/Cargo projects.

    T-0554: also runs the doc/coverage/drift/invariant gates stage
    (`_run_gates`) -- previously only the Python pipeline ran it, so a pure
    Rust repo's COV001/DOC001-3/DRIFT001-2/INV/DEC/TODO001 gates silently
    never executed (docs/audits/lang-check-docs.md finding 1).

    T-0603: a corrupt derived artifact short-circuits everything below
    with a single `derived-state-integrity` ERROR result, checked once up
    front -- see `_derived_state_integrity_result`'s docstring.

    T-0859: the precheck through the last stage's read is held under one
    SHARED `derived_state_lock` -- see its docstring.
    """
    with derived_state_lock(root, exclusive=False):
        integrity_failure = _derived_state_integrity_result(root)
        if integrity_failure is not None:
            return CheckResult(path=str(root), results=[integrity_failure])

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
        if not skip_gates:
            gate_result = _run_gates(root, ticket=ticket, base=base, delta=delta)
            if isinstance(gate_result, list):
                results.extend(gate_result)
            else:
                results.append(gate_result)

        return CheckResult(path=str(root), results=results)


# ---------------------------------------------------------------------------
# TypeScript checks
# ---------------------------------------------------------------------------


# frob:doc docs/commands/check.md#public-api
# frob:ticket T-0554
# frob:waive TEST005 reason="run_check_ts 58.8% branch cover, debt T-0160"
def run_check_ts(
    root: Path,
    *,
    skip_tsc: bool = False,
    skip_eslint: bool = False,
    skip_prettier: bool = False,
    skip_tests: bool = False,
    skip_gates: bool = False,
    ticket: str | None = None,
    base: str | None = None,
    delta: bool = False,
) -> CheckResult:
    """Quality gate for npm/TypeScript projects (tsc/eslint/prettier/vitest).

    T-0554: also runs the doc/coverage/drift/invariant gates stage
    (`_run_gates`) -- previously only the Python pipeline ran it, so a pure
    TypeScript repo's COV001/DOC001-3/DRIFT001-2/INV/DEC/TODO001 gates
    silently never executed (docs/audits/lang-check-docs.md finding 1).

    T-0603: a corrupt derived artifact short-circuits everything below
    with a single `derived-state-integrity` ERROR result, checked once up
    front -- see `_derived_state_integrity_result`'s docstring.

    T-0859: the precheck through the last stage's read is held under one
    SHARED `derived_state_lock` -- see its docstring.
    """
    with derived_state_lock(root, exclusive=False):
        integrity_failure = _derived_state_integrity_result(root)
        if integrity_failure is not None:
            return CheckResult(path=str(root), results=[integrity_failure])

        tasks: list[Callable[[], ToolResult | list[ToolResult] | None]] = []
        if not skip_tsc:
            tasks.append(lambda: _run_tsc(root))
        if not skip_eslint:
            tasks.append(lambda: _run_eslint(root))
        if not skip_prettier:
            tasks.append(lambda: _run_prettier(root))
        if not skip_tests:
            tasks.append(lambda: _run_vitest(root))
        if not skip_gates:
            tasks.append(
                lambda: _run_gates(root, ticket=ticket, base=base, delta=delta)
            )

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

        return CheckResult(path=str(root), results=results)


# ---------------------------------------------------------------------------
# Auto-detect project type
# ---------------------------------------------------------------------------


# frob:doc docs/commands/check.md#public-api
# frob:ticket T-0551
# frob:ticket T-0718
def detect_project_type(root: Path) -> str:
    """Returns 'python', 'cpp', 'rust', 'typescript', or 'unknown'.

    T-0718: a bare root-level `*.py` file with no `pyproject.toml`/
    `setup.py` used to fall all the way through to
    `_detect_nested_native_project_type` and report 'unknown' -- there was
    no extension-based fallback for Python the way `cpp` already had one.
    Falls back to 'python' when root-level `.py` files exist, mirroring
    the existing bare-C/C++-source fallback above.

    T-0404 finding 11: this single-winner detector used to require BOTH
    `package.json` AND `tsconfig.json` for 'typescript', while
    `app.check_runner._detected_types` (the polyglot enumerator) required
    only `package.json` -- the two "what is a TS repo" definitions
    disagreed, so `_run_auto_detected_stages`'s `_detected_types(root) or
    [detect_project_type(root)]` fallback could pick a different verdict
    than the enumerator for the same tree. `package.json` alone is now the
    single shared contract for both.
    """
    if (root / "Cargo.toml").exists():
        return "rust"
    if (root / "CMakeLists.txt").exists():
        return "cpp"
    if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        return "python"
    if (root / "package.json").exists():
        return "typescript"
    if list(root.glob("*.cpp")) or list(root.glob("*.cc")) or list(root.glob("*.c")):
        return "cpp"
    if list(root.glob("*.py")):
        return "python"
    return _detect_nested_native_project_type(root)


#: Marker filenames `_detect_nested_native_project_type` recognizes when
#: found anywhere under `root` (not just at the top level), mapped to the
#: language they signal.
_NESTED_NATIVE_MARKER_FILES: dict[str, str] = {
    "Cargo.toml": "rust",
    "CMakeLists.txt": "cpp",
}

#: Bare native-source suffixes `_detect_nested_native_project_type` treats
#: as a C/C++ project when no marker file is found anywhere either.
_NESTED_NATIVE_SOURCE_SUFFIXES = (".cpp", ".cc", ".c")


# frob:ticket T-0551
def _detect_nested_native_project_type(root: Path) -> str:
    """`detect_project_type`'s final fallback: a bounded, pruned recursive
    scan for a native marker file or source, before finally admitting
    'unknown' (T-0404 finding 7 / T-0551).

    The root-level checks above return 'unknown' for a C/C++ or Rust
    project whose sources/build files live only under a subdirectory (e.g.
    `src/CMakeLists.txt`, no root `CMakeLists.txt`) -- which used to send
    the whole repo to the Python check pipeline instead of the native
    toolchain (finding 6/T-0546) with no native checks ever running.
    Reuses `frob.excludes.iter_files` (the shared pruned-walk entry point,
    `git ls-files` fast path when available) rather than a second raw
    `rglob`, so this scan skips `.git`/`.venv`/`node_modules`/build output
    the same way every other repo-wide walk in this codebase does.
    """
    from frob.excludes import iter_files

    files = iter_files(root)
    for path in files:
        marker = _NESTED_NATIVE_MARKER_FILES.get(path.name)
        if marker is not None:
            return marker
    for path in files:
        if path.suffix.lower() in _NESTED_NATIVE_SOURCE_SUFFIXES:
            return "cpp"
    return "unknown"


__all__ = [
    "CheckResult",
    "available_stages",
    "detect_project_type",
    "memoize_per_run",
    "reset_run_memo",
    "run_check",
    "run_check_cpp",
    "run_check_rust",
    "run_check_ts",
    "run_memo_scope",
    "run_memo_stats",
]

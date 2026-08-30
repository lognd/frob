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

# frob:waive LARGE001 reason="T-1651-grade: this module's own docstring states the \
# seam directly -- the public orchestration surface (run_check and its \
# run_check_cpp/run_check_rust/run_check_ts siblings, plus the cross-module memo \
# helpers) is kept HERE on purpose so frob:doc/frob:tests bindings keep their \
# __init__.py symref, while the per-tool runner bodies live in the private _python/ \
# _native/_ts submodules already split out. Moving the orchestration surface itself \
# elsewhere would break the exact symref stability this module's docstring names as \
# the reason it stays here."

from __future__ import annotations

import concurrent.futures
import contextlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Callable, Iterator

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
from frob.derived_state import verify_derived_state
from frob.gitio import git_common_dir
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


# ---------------------------------------------------------------------------
# T-3256: cross-process, memory-aware admission budget
# ---------------------------------------------------------------------------
#
# MEASURED 2026-08-28 with six agent series live on a 12-core/23GB box: load
# 35.89, 0GB free, 51 forkserver processes totalling 14.5GB RSS. Every gate
# worker pool downstream of `run_check` (`frob.gates._run_gates`'s
# `proc_workers = max(1, min(len(process_jobs), os.cpu_count() or 4))`,
# plus `frob.lang`/`frob.graph.cache`'s own `os.cpu_count()`-sized pools)
# sizes itself against the WHOLE machine's core count with no cross-process
# awareness -- N concurrent `frob check` runs is an N-fold oversubscription
# no single one of them is wrong about.
#
# THE MECHANISM CHOSEN: `_admission_budget` registers this process in a
# lightweight cross-process file registry under `.frob/check-admission/`
# (one small marker per live `frob check` PID, T-3256's "token file"
# candidate), counts how many OTHER checks are concurrently registered,
# reads real available memory (`/proc/meminfo`'s `MemAvailable`, Linux
# only), and derives a per-process worker budget capped by BOTH the real
# core count and (available memory / a per-worker MB estimate), divided by
# the concurrent-check count. It then monkeypatches `os.cpu_count()` for
# the remainder of this process's life (restored on exit) to return that
# budget -- NOT because patching a stdlib function is the first choice,
# but because it is the one mechanism that reaches every downstream
# `os.cpu_count()`-sized pool (`frob.gates`, `frob.lang`, `frob.graph.
# cache`) WITHOUT editing those modules, which this ticket's scope
# (`src/frob/check/__init__.py` only) does not permit -- and because in
# THIS codebase `os.cpu_count()` gates PROCESS COUNT at each of those call
# sites (not merely a scheduling hint), so shrinking it directly shrinks
# the number of forkserver workers spawned, addressing the MEASURED
# memory constraint, not just CPU scheduling (an `os.sched_setaffinity`-
# only approach would throttle CPU scheduling but leave the same worker
# COUNT -- and therefore the same RSS -- unchanged).
#
# DEGRADE, NEVER REFUSE (T-3256 requirement 2): `_compute_admitted_
# workers` always returns >= 1; `_admission_budget` only patches
# `os.cpu_count()` (and only logs) when the admitted budget is actually
# smaller than the real core count. On an idle box (one check running,
# ample memory) admitted == real core count, nothing is patched, nothing
# is logged (MUST-STAY-QUIET). This also satisfies "do not lower the pool
# size unconditionally" -- the reduction is proportional to OBSERVED
# concurrent load and OBSERVED available memory, never a fixed cap.
#
# OUT OF SCOPE, reported not fixed here (per the ticket's own instruction):
#   - Whether `fleet_status` can distinguish "N checks fighting over the
#     box" from "N agents stalled" -- see T-3256's Done report for what was
#     found; no fleet_status code is touched by this ticket.
#   - Making `frob ticket land`'s own wall-clock timeout budget-aware
#     (extending it while its child `frob check` is demonstrably still
#     progressing) -- a real, distinct fix the coordinator's T-3256 field
#     evidence (a land killed by its own `timeout 540` wrapper while its
#     child check was 335s in at 82.8% CPU, not stalled) argues for, but
#     it touches ticket-land/timeout-wrapper code, not `src/frob/check/
#     __init__.py` -- filed as a follow-up rather than expanding this
#     ticket's scope.

#: Rough per-worker memory budget in MiB for a `frob check` gate worker --
#: derived directly from T-3256's field measurement (14,552MB RSS / 51
#: forkservers ~= 285MB/worker), rounded up to a conservative round number.
#: Overridable per-box via `FROB_CHECK_PER_WORKER_MEM_MB`.
_DEFAULT_PER_WORKER_MEM_MB = 300
_PER_WORKER_MEM_ENV = "FROB_CHECK_PER_WORKER_MEM_MB"

#: Explicit worker-count override/opt-out (mirrors `frob.testing.
#: _coverage_refresh`'s `FROB_COVERAGE_MAX_WORKERS`, T-1672's precedent):
#: `0` disables the admission budget entirely (this process's `os.
#: cpu_count()` is never patched); a positive integer pins an exact
#: admitted worker count regardless of measured memory/concurrency.
_MAX_WORKERS_ENV = "FROB_CHECK_MAX_WORKERS"

_ADMISSION_DIR_NAME = "check-admission"


def _available_memory_mb() -> int | None:
    """Best-effort available memory in MiB (T-3256), delegating to `frob.
    testing._coverage_refresh._available_memory_mb` (`/proc/meminfo`'s
    `MemAvailable` line, Linux only, `None` on any non-Linux/unreadable
    case -- T-1672's own precedent, reused rather than a second,
    100%-identical copy DUP001 caught). Imported LOCALLY, not at module
    level: `frob.testing` transitively imports `frob.graph`, which
    imports `frob.check._memo` -- a top-level import here reintroduces
    exactly the cycle `docs/rework.md`'s layering rule (and `frob.
    tickets._reporting.set_done_report`'s own docstring) already calls
    out. Moving the function to a shared, coverage-agnostic home is out
    of this ticket's `src/frob/check/__init__.py`-only scope; this
    deferred import is the dedup."""
    from frob.testing._coverage_refresh import (
        _available_memory_mb as _shared_available_memory_mb,
    )

    return _shared_available_memory_mb()


def _pid_alive(pid: int) -> bool:
    """Whether `pid` is a live process, best-effort (T-3256): `os.kill(pid,
    0)` sends no signal, only probes existence. A permission error still
    means the process exists (just not ours to signal); any other OSError
    (e.g. an invalid pid) reads as dead rather than raising -- this is a
    registry-reaping heuristic, never allowed to crash a check run."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


# frob:ticket T-3287
# frob:tests tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor.test_non_git_root_falls_back_to_itself kind="unit"  # noqa: E501
# frob:tests tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor.test_primary_checkout_anchors_to_itself kind="unit"  # noqa: E501
# frob:tests tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor.test_two_worktrees_of_one_repo_share_one_anchor kind="unit"  # noqa: E501
# frob:tests tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor.test_two_unrelated_repos_do_not_throttle_each_other kind="unit"  # noqa: E501
def _admission_registry_anchor(root: Path) -> Path:
    """T-3287: the REPOSITORY-wide anchor for the admission registry --
    `git rev-parse --git-common-dir`'s PARENT directory (`frob.gitio.
    git_common_dir`, already memoized per-process), which resolves to
    the SAME primary-checkout path from inside any linked worktree of
    one repo. Falls back to `root` itself (T-3256's original, per-
    worktree behavior) if `root` is not inside a git work tree or the
    `git` call fails -- degrade, never refuse.

    WHY THE COMMON DIR, NOT `root` (T-3256's original choice) OR A
    MACHINE-GLOBAL PATH: T-3256 registered under `root / ".frob"`, and
    every git worktree has its own `.frob/` -- so two agents checking
    the SAME repo from two DIFFERENT worktrees (`frob ticket work`'s own
    normal shape, `.claude/worktrees/<id>`) never saw each other's
    marker at all; each one measured a concurrency of 1 and took the
    full machine budget while genuinely contending with siblings
    (MEASURED 2026-08-28: 11 live `frob check` processes, only 1 marker
    in the primary root's registry, the other worktrees' registries all
    empty). A machine-global path (e.g. under `/tmp`) was explicitly
    ruled out: it would double-count contention already captured by
    `_available_memory_mb` (a REAL machine resource, correctly measured
    process-count-agnostic) and would throttle two unrelated repos'
    checks against each other, plus add a permissions/staleness surface
    a world-writable path invites. The git common dir is the narrowest
    anchor that is still shared: identical across every worktree of ONE
    repo, distinct across different repos, and never a `/tmp` path.
    Confirmed stable against this repo's own unusual layout (worktrees
    live under `.claude/worktrees/` INSIDE the primary checkout) because
    `git rev-parse --git-common-dir` is git's own resolution, not a
    naive parent-directory walk -- the nesting is invisible to it.

    Checks `(root / ".git").exists()` FIRST and skips `git_common_dir`
    entirely when it is absent: `git_common_dir` logs a WARNING on a
    failed `git` call (correct for its OTHER callers, where "not a git
    repo" is an unexpected condition worth surfacing), but here it is
    the NORMAL degrade path (`root` genuinely is not a git checkout, or
    is a bare/unusual layout `frob check` still runs against) -- calling
    it unconditionally would turn every such run noisy, breaking this
    function's own MUST-STAY-QUIET contract."""
    if not (root / ".git").exists():
        return root
    common = git_common_dir(root)
    if common.is_err:
        return root
    return common.danger_ok.parent


# frob:ticket T-3287
# frob:tests tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor.test_two_worktrees_see_each_others_markers kind="unit"  # noqa: E501
# frob:tests tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor.test_stale_marker_from_dead_pid_does_not_permanently_deflate_shared_budget kind="unit"  # noqa: E501
def _admission_dir(root: Path) -> Path:
    """`<repo-root>/.frob/check-admission/` (T-3287: `<repo-root>` is
    `_admission_registry_anchor(root)` -- the git common dir's parent,
    SHARED across every linked worktree of one repo -- not `root` itself,
    which is per-worktree and the reason T-3256's divisor never saw
    cross-worktree siblings) -- the cross-process registry directory
    `_register_admission`/`_live_concurrent_checks` share."""
    return _admission_registry_anchor(root) / ".frob" / _ADMISSION_DIR_NAME


def _register_admission(root: Path) -> Path:
    """Write this process's marker (`{pid}.json`, best-effort content: pid
    + start time, never load-bearing) into the admission registry,
    creating the directory if needed. Returns the marker path so the
    caller can remove it on exit (`_admission_budget`'s `finally`). Never
    raises -- an unwritable `.frob/` (permissions, read-only checkout)
    degrades to "this check is invisible to the registry", which only
    means OTHER concurrent checks under-count it, never a crash here."""
    marker = _admission_dir(root) / f"{os.getpid()}.json"
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(
            json.dumps({"pid": os.getpid(), "started": time.time()}),
            encoding="utf-8",
        )
    except OSError:
        _log.debug("check: admission registry unwritable at %s", marker)
    return marker


def _live_concurrent_checks(root: Path) -> int:
    """Count admission markers whose PID is still alive under `root`'s
    registry, reaping (best-effort `unlink`) any marker whose PID is
    already dead -- so a killed/crashed `frob check` never permanently
    inflates the count later checks divide their budget by. Always >= 1
    when this process's own marker is registered (the normal case);
    returns 0 only if the registry itself could not be read at all."""
    directory = _admission_dir(root)
    if not directory.exists():
        return 0
    alive = 0
    try:
        entries = list(directory.glob("*.json"))
    except OSError:
        return 0
    for entry in entries:
        try:
            pid = int(entry.stem)
        except ValueError:
            continue
        if _pid_alive(pid):
            alive += 1
        else:
            try:
                entry.unlink()
            except OSError:
                pass
    return alive


def _max_workers_override() -> tuple[bool, int | None]:
    """Read `FROB_CHECK_MAX_WORKERS` (T-3256), mirroring `frob.testing.
    _coverage_refresh._max_workers_override`'s T-1672 contract exactly:
    `(True, value)` when the override applies (`value` is `None` for an
    explicit `<= 0` opt-out), `(False, None)` when unset or malformed (the
    caller falls through to the memory/concurrency-based computation)."""
    # frob:waive SEC110 reason="FROB_CHECK_MAX_WORKERS is a numeric worker-count knob \
    # (T-3256), not a secret"
    raw = os.environ.get(_MAX_WORKERS_ENV)
    if raw is None:
        return (False, None)
    try:
        override = int(raw)
    except ValueError:
        _log.warning("check: %s=%r is not an integer, ignoring", _MAX_WORKERS_ENV, raw)
        return (False, None)
    return (True, override if override > 0 else None)


def _per_worker_mem_budget_mb() -> int:
    """Read `FROB_CHECK_PER_WORKER_MEM_MB` (T-3256), falling back to
    `_DEFAULT_PER_WORKER_MEM_MB` on absence or any malformed/non-positive
    value."""
    # frob:waive SEC110 reason="FROB_CHECK_PER_WORKER_MEM_MB is a numeric \
    # memory-budget knob (T-3256), not a secret"
    raw = os.environ.get(_PER_WORKER_MEM_ENV)
    if raw is None:
        return _DEFAULT_PER_WORKER_MEM_MB
    try:
        value = int(raw)
    except ValueError:
        _log.warning(
            "check: %s=%r is not an integer, using default %dMB",
            _PER_WORKER_MEM_ENV,
            raw,
            _DEFAULT_PER_WORKER_MEM_MB,
        )
        return _DEFAULT_PER_WORKER_MEM_MB
    return value if value > 0 else _DEFAULT_PER_WORKER_MEM_MB


def _compute_admitted_workers(root: Path) -> tuple[int, int, int | None, int]:
    """The admission budget's pure math (T-3256): `(admitted, real_cpu,
    available_mem_mb, concurrent_checks)`. `admitted` is always >= 1
    (degrade, never refuse). `available_mem_mb` is `None` when it could
    not be measured (non-Linux, unreadable `/proc/meminfo`) -- the budget
    then falls back to a concurrency-only split of the real core count,
    still never refusing, just without the memory bound.

    `FROB_CHECK_MAX_WORKERS` (checked first) bypasses all of this: an
    explicit override always wins over measurement, matching `frob.
    testing._coverage_refresh`'s T-1672 precedent."""
    real_cpu = os.cpu_count() or 4
    overridden, override_value = _max_workers_override()
    if overridden:
        value = override_value if override_value is not None else real_cpu
        return (max(1, value), real_cpu, None, 1)

    concurrent = max(1, _live_concurrent_checks(root))
    mem_mb = _available_memory_mb()
    if mem_mb is None:
        admitted = max(1, real_cpu // concurrent)
        return (admitted, real_cpu, None, concurrent)

    per_worker = _per_worker_mem_budget_mb()
    total_budget = max(1, min(real_cpu, mem_mb // per_worker))
    admitted = max(1, total_budget // concurrent)
    return (admitted, real_cpu, mem_mb, concurrent)


@contextlib.contextmanager
def _admission_budget(root: Path) -> Iterator[int]:
    """T-3256: register this `frob check` run in the cross-process
    admission registry, compute a memory- and concurrency-aware worker
    budget, and (only if it is smaller than the real core count) patch
    `os.cpu_count()` for the duration of the `yield` so every downstream
    pool sized from it (`frob.gates`/`frob.lang`/`frob.graph.cache`, none
    of which this ticket's scope touches directly) shrinks with it --
    restored in `finally` regardless of how the body exits. Logs the
    reduction once, at WARNING, naming the exact numbers an operator needs
    (admitted/real, concurrent check count, available memory, per-worker
    budget, the override env var) -- MUST-STAY-QUIET when nothing was
    reduced (the idle-box case, T-3256's own must-stay-quiet fixture)."""
    marker = _register_admission(root)
    real_cpu_count_fn = os.cpu_count
    try:
        admitted, real_cpu, mem_mb, concurrent = _compute_admitted_workers(root)
        if admitted < real_cpu:
            if mem_mb is not None:
                _log.warning(
                    "check: admission budget reduced worker pool to %d "
                    "(of %d cores) -- %d concurrent frob check process(es), "
                    "%dMB available memory, %dMB/worker budget; override via %s",
                    admitted,
                    real_cpu,
                    concurrent,
                    mem_mb,
                    _per_worker_mem_budget_mb(),
                    _MAX_WORKERS_ENV,
                )
            else:
                _log.warning(
                    "check: admission budget reduced worker pool to %d "
                    "(of %d cores) -- %d concurrent frob check process(es), "
                    "available memory unmeasurable (non-Linux or /proc/"
                    "meminfo unreadable); override via %s",
                    admitted,
                    real_cpu,
                    concurrent,
                    _MAX_WORKERS_ENV,
                )

            def _admitted_cpu_count(*, _admitted: int = admitted) -> int:
                return _admitted

            os.cpu_count = _admitted_cpu_count  # ty: ignore[invalid-assignment]
        yield admitted
    finally:
        os.cpu_count = real_cpu_count_fn
        try:
            marker.unlink()
        except OSError:
            pass


# frob:ticket T-2764
# frob:tests tests/unit/test_check.py::TestNativeStalenessResult.test_stale_native_fails_closed_when_rebuild_cannot_fix_it  # noqa: E501
# frob:tests tests/unit/test_check.py::TestNativeStalenessResult.test_fresh_native_is_not_a_violation  # noqa: E501
def _native_staleness_result(root: Path) -> ToolResult | None:
    """T-2764: `uv run frob check` used to have NO equivalent of `make
    check`'s separate `check_native_staleness_or_exit` pre-step (T-0248) --
    the gates stage self-heals a stale native in place
    (`frob.gates._maybe_autorebuild_natives`, T-1213), but that self-heal
    only runs when the `gates` stage itself is selected; a `--skip-gates`
    run, or an `--only` selection that never reaches `gates`, silently ran
    ruff/ty/etc. against a stale native with no warning at all -- a real
    workflow-parity gap between the two entry points, not merely a naming
    one (found while working T-2245, filed as T-2764).

    Decision (T-2764): `frob check` SHOULD enforce this, unconditionally,
    the same way `make check` does -- but without regressing T-1213's
    self-heal improvement. This reuses the EXACT SAME rebuild-then-recheck
    machinery the gates stage already uses (`frob.gates.
    _native_autorebuild_disabled` + `frob.natives._build.build_natives`,
    not reimplemented here) so a stale-but-rebuildable native is fixed
    silently regardless of which stages are selected, and only reports a
    hard failure -- mirroring `make check`'s fail-closed posture -- when
    staleness remains after that attempt (auto-rebuild disabled, no
    toolchain, or a genuine build failure). `None` when nothing is stale
    to begin with, matching `_derived_state_integrity_result`'s own
    fail-open-when-healthy contract just above."""
    from frob.gates import _native_autorebuild_disabled
    from frob.strata import stale_native_warning, stale_natives

    if not stale_natives(root):
        return None
    if not _native_autorebuild_disabled(root):
        from frob.natives._build import build_natives

        built = build_natives(root)
        if built.is_ok and built.danger_ok.ok and not stale_natives(root):
            return None
    warning = stale_native_warning(root)
    if warning is None:
        return None
    return ToolResult(
        tool="native-staleness",
        exit_code=1,
        diagnostics=[
            Diagnostic(
                file=str(root),
                severity="error",
                code="NATIVE001",
                message=f"NATIVE001: {warning}",
            )
        ],
        summary=f"native-staleness FAILED: {warning}",
    )


# frob:ticket T-0603
# frob:tests tests/unit/test_check.py::TestDerivedStateIntegrityGate.test_corrupt_artifact_fails_closed_before_any_stage_runs  # noqa: E501
# frob:tests tests/unit/test_check.py::TestDerivedStateIntegrityGate.test_absent_artifact_is_not_a_violation  # noqa: E501
# frob:ticket T-0603
# frob:enforces CHK-GATE-DERIVED001
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


# frob:ticket T-2891
def _is_unresolved_only_gate(r: ToolResult) -> bool:
    """`True` iff `r` is a `gate:<FAMILY>` `ToolResult` whose entire content
    is UNRESOLVED (T-1664's `Severity.UNRESOLVED`, rendered by
    `frob.check._python._diag_severity` as `Diagnostic(severity="info")`)
    -- zero errors, zero warnings, and at least one diagnostic, all of
    them `"info"`-severity.

    T-2891: a gate whose opt-in `known_keys` declaration
    (`_docblocks_shared.resolve_dotted_symbol`'s target) is missing from
    the target project's `frob.toml` correctly reports `UNRESOLVED`, not
    an error -- that part works as designed. But `_gates_family_result`
    sets `exit_code=0` whenever `n_err == 0` (correct: `UNRESOLVED` must
    never fail the exit code, `docs/modules/gates.md#unresolved-t-1664`),
    and `as_text`'s tool-summary row used to key its `pass`/`FAIL` icon
    off exactly that same `exit_code == 0`. For an ordinary gate that
    measured a mix of clean-and-unresolved findings this reads fine; for
    one of the twelve `*SCHEMA`/`FLAGCOV` families that never resolved a
    single real target (the measured off-repo defect: 12 gates against
    `lograder`, each `0 errors, 0 warnings, 1 unresolved, 0 waived`), it
    renders byte-for-byte like a real clean pass -- the entire tool
    result IS the unresolved verdict, not a stray finding inside one.
    This predicate isolates exactly that all-unresolved shape so `as_text`
    can render it as its own third state instead of folding it into
    `pass`, without touching `exit_code`/`total_errors` at all (the
    exit-code contract this ticket deliberately leaves unchanged -- see
    `docs/modules/gates.md#unresolved-t-1664`). Restricted to `gate:`-
    prefixed tools: other stages (`frob-arch`'s `large-file` suggestions,
    for one) also emit `"info"`-severity diagnostics for reasons that
    have nothing to do with T-1664's UNRESOLVED concept, and must not be
    caught by this check.

    T-2391: now a thin wrapper over `ToolResult.measurement` (a computed
    field with the IDENTICAL predicate, promoted onto the model itself so
    `as_json()` discloses it too, not only this text-rendering helper).
    Kept as its own named function rather than inlined at both call
    sites -- `as_text`'s icon selection and (via `measurement`) `as_json`
    -- because the T-2891 docstring above is the canonical explanation of
    WHY this shape matters and is cited from both places."""
    return r.measurement == "not_measured"


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

    # frob:ticket T-2391
    # frob:doc docs/commands/check.md#public-api
    # frob:tests tests/unit/test_check_measurement.py::TestUnmeasuredResults.test_empty_when_every_result_measured  # noqa: E501
    # frob:tests tests/unit/test_check_measurement.py::TestUnmeasuredResults.test_lists_every_not_measured_result  # noqa: E501
    @property
    def unmeasured_results(self) -> list[ToolResult]:
        """Every `results` entry whose `measurement` is not `"measured"`
        (T-2391) -- the roster `as_text` prints automatically (standing
        directive: automatic over commands, a finding that requires
        remembering a second command is not a control) and `as_json`
        callers can derive the identical list from without re-deriving
        the `_is_unresolved_only_gate` predicate by hand."""
        return [r for r in self.results if r.measurement != "measured"]

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

        # T-2391: printed unconditionally whenever non-empty, in the
        # place an operator already looks (this same report), never a
        # second command to remember -- the fail-loudly doctrine's own
        # "automatic over commands" directive applied to gate status.
        unmeasured = self.unmeasured_results
        if unmeasured:
            from frob.logging.color import CYAN

            lines.append(paint("## Unmeasured gates", f"{BOLD};{YELLOW}", color))
            lines.append(
                "  the following gate(s) could not determine an answer for "
                "part or all of their scope -- their zero-error/zero-warning "
                "count above is NOT a clean measurement, do not read it as one:"
            )
            for r in unmeasured:
                lines.append(f"  {paint(r.tool, CYAN, color)}: {r.measurement_reason}")
            lines.append("")

        lines.append(paint("## Tool summary", BOLD, color))
        for r in self.results:
            ok = r.passed and r.error_count == 0
            # T-2891: an all-UNRESOLVED gate (see _is_unresolved_only_gate)
            # is neither a real pass nor a FAIL -- render it as its own
            # third state so it is never visually indistinguishable from
            # a clean pass. exit_code/total_errors are untouched: this is
            # a rendering-only distinction, not an exit-code change.
            if _is_unresolved_only_gate(r):
                icon = paint("UNRES", YELLOW, color)
            elif ok:
                icon = paint("pass", GREEN, color)
            else:
                icon = paint("FAIL", RED, color)
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
            "docstatus",
            "docmake",
            "docseverity",
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
            # T-2344: LEXCHECK001.
            "lexcheck",
            # T-2397: FLAGCOV001 -- thread-pool, sub-second, same shape as
            # lexcheck above; belongs here per the same T-1044/T-1340
            # lesson (a gate registered in frob.gates._ALL_GATES but not
            # added to a _STAGE_GROUPS member is unreachable via
            # `--only <group>`).
            "flag_coverage",
            # T-2390 epic child T-2428: REFSCHEMA001 -- thread-
            # pool, sub-second, same shape as flag_coverage above.
            "refs_schema",
            # T-2390 epic child T-2429: NATIVESCHEMA001, same shape.
            "native_schema",
            # T-2390 epic child T-2430: PROFILESCHEMA001, same shape.
            "profile_schema",
            # T-2390 epic child T-2431: TOPSCALARSCHEMA001, same shape.
            "toplevel_scalar_schema",
            # T-2390 epic child T-2432: TESTINGSCHEMA001, same shape.
            "testing_schema",
            # T-2390 epic child T-2433: ARCHSCHEMA001, same shape.
            "arch_schema",
            # T-2390 epic child T-2434: DOCBLOCKSSCHEMA001, same shape.
            "docblocks_schema",
            # T-2390 epic child T-2435: GATESSCHEMA001, same shape.
            "gates_schema",
            # T-2390 epic child T-2436: TESTRUNNERSCHEMA001, same shape.
            "test_runner_schema",
            # T-2390 epic child T-2437: DUPSCHEMA001/GRAPHSCHEMA001, same shape.
            "dup_schema",
            "graph_schema",
            "parse_failures",
            "lang_conformance",
            "lang_project_conformance",
            # frob:ticket T-2411
            # LANG004, wired into gates/__init__.py's job table alongside
            # lang_conformance/lang_project_conformance -- added here too
            # so it is reachable via `--only gates-fast` (same T-1044/
            # T-1340 registered-but-unreachable lesson this file's own
            # comment names above).
            "capability_conformance",
            "scope",
            "prework",
            # T-3042: VMOD001 (frob.gates._vmodel.vmodel_gate) -- thread-
            # pool, opt-in, sub-second when no V-model graph exists yet
            # (the common case today); reachable via `--only gates-fast`
            # or `--only vmodel` directly, same T-1044/T-1340 registered-
            # but-unreachable lesson this file's own comment above names.
            "vmodel",
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
            # T-1340: suppress (SUPPRESS001) was registered in
            # frob.gates._ALL_GATES but never added to a _STAGE_GROUPS
            # member -- same omission shape as ffi_boundary above. It is a
            # thread-pool, sub-second gate, so it belongs in gates-fast;
            # without this it is unreachable via `--only <group>`.
            "suppress",
            # T-3030: milestone (MILE003/MILE004), env_var_docs (ENVDOC001),
            # root_asset_dirs (ROOTASSET001), and profile_boundary
            # (PROFBOUND001) were registered in frob.gates._ALL_GATES but
            # never added to a _STAGE_GROUPS member -- same omission shape
            # as ffi_boundary/suppress above. All four are thread-pool,
            # sub-second gates (not in frob.gates._PROCESS_POOL_GATES), so
            # they belong in gates-fast; without this an agent looping
            # every `--only <group>` (the documented FROB_AGENT foreground-
            # budget pattern) silently never runs them at all.
            "milestone",
            "env_var_docs",
            "root_asset_dirs",
            "profile_boundary",
            # T-3030: narrative_blocks (NARR001) has the identical omission
            # shape, found while root-causing the same
            # test_available_stages_cover_every_gate_and_tool failure --
            # out of the ticket's four NAMED gates but the same fix, same
            # symbol, same commit; not a separate scope.
            "narrative_blocks",
            # T-3249: comment_placement (CPLACE001/CPLACE002, T-3218) has
            # the identical registered-but-unreachable omission shape as
            # narrative_blocks/T-3030 above -- added to frob.gates._ALL_
            # GATES by T-3218 but never added to any _STAGE_GROUPS member.
            # Thread-pool, sub-second (not in frob.gates._PROCESS_POOL_
            # GATES), so it belongs in gates-fast like every other entry
            # in this same omission class.
            "comment_placement",
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
            "wire",
            "cache",
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
    skip_ruff_check: bool = False,
    skip_ruff_format: bool = False,
) -> dict[str, bool]:
    """The per-tool skip-flag mapping `_python_tasks` consults.

    T-2320: `skip_ruff` (the bundled legacy flag) skips BOTH ruff-check and
    ruff-format, matching its pre-T-2320 behavior unchanged;
    `skip_ruff_check`/`skip_ruff_format` skip just their own half,
    independent of each other and of `skip_ruff` -- either the bundled
    flag or the matching split flag is enough to skip a given stage
    (`or`'d together, never a silent override of one by the other)."""
    return {
        "ruff_check": skip_ruff or skip_ruff_check,
        "ruff_format": skip_ruff or skip_ruff_format,
        "ty": skip_ty,
        "cycle": skip_cycle,
        "dup": skip_dup,
        "arch": skip_arch,
        "bind": skip_bind,
        "exports": skip_exports,
        "gates": skip_gates,
    }


#: T-2978: one enabled check task, paired with the short label a TTY
#: progress line reports it under ("ruff"/"ty"/"gates"/...) -- these are
#: the SAME names `--only`/`skips` already use, so the progress line and
#: the rest of `frob check`'s own vocabulary never diverge.
_NamedTask = tuple[str, Callable[[], "ToolResult | list[ToolResult] | None"]]


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
    no_cache: bool = False,
) -> list[_NamedTask]:
    """The enabled per-tool jobs for a Python check run, each paired with
    its progress-line label (T-2978).

    T-1346: `no_cache` reaches `_run_gates` unchanged -- see its own
    docstring for the default-on gate-cache behavior this threads through.
    """

    def wanted(name: str) -> bool:
        return only is None or name in only

    tasks: list[_NamedTask] = []
    # T-2320: the "ruff" --only/stage name still selects the combined job
    # (both sub-invocations run in the SAME task/thread, same as before
    # T-2320) -- only the skip decision is now independent per half, via
    # `_run_ruff`'s own `skip_check`/`skip_format` params. A caller that
    # wants JUST one half still skips the other through
    # `--skip-ruff-check`/`--skip-ruff-format`, not via `--only`.
    if (not skips["ruff_check"] or not skips["ruff_format"]) and wanted("ruff"):
        tasks.append(
            (
                "ruff",
                lambda: _run_ruff(
                    root,
                    ruff_args,
                    skip_check=skips["ruff_check"],
                    skip_format=skips["ruff_format"],
                ),
            )
        )
    if not skips["ty"] and wanted("ty"):
        tasks.append(("ty", lambda: _run_ty(root)))
    if not skips["cycle"] and wanted("cycle"):
        tasks.append(("cycle", lambda: _run_cycle(root)))
    if not skips["dup"] and wanted("dup"):
        tasks.append(("dup", lambda: _run_dup(root)))
    if not skips["arch"] and wanted("arch"):
        tasks.append(("arch", lambda: _run_arch(root)))
    if not skips["bind"] and wanted("bind"):
        tasks.append(("bind", lambda: _run_bind(root)))
    if not skips["exports"] and wanted("exports"):
        tasks.append(("exports", lambda: _run_exports(root)))
    if not skips["gates"] and wanted("gates"):
        tasks.append(
            (
                "gates",
                lambda: _run_gates(
                    root,
                    ticket=ticket,
                    base=base,
                    gates=gate_only,
                    delta=delta,
                    no_cache=no_cache,
                ),
            )
        )
    return tasks


# T-0364: dropped the private duplicate of
# `frob.logging.quiet._stdout_stream_handlers` (identical body, dup
# group) -- imported below instead; `frob.check` already depends on
# `frob.logging`, so this adds no new edge.


def _run_tasks_concurrently(
    tasks: list[_NamedTask],
    *,
    on_task_done: Callable[[str, int, int], None] | None = None,
) -> list[ToolResult]:
    """Run `tasks` in a `ThreadPoolExecutor` and flatten results, dropping
    Nones.

    T-2978: `on_task_done` (default `None`, every pre-existing caller
    unaffected) is called `(label, done_count, total)` as each task
    ACTUALLY finishes -- real completion order, watched via
    `as_completed` on the side -- but the final `results` list is still
    assembled in the ORIGINAL submission order (`tasks`' own order), not
    completion order: `frob check --json`'s result ordering is part of
    its byte-identical output contract and must not become run-to-run
    nondeterministic just because a progress line now watches completion
    live. The caller (`check_runner`'s TTY `Progress`) is a no-op off a
    TTY, so this callback is cheap and side-effect-free on every non-
    interactive path."""
    total = len(tasks)
    done = 0
    by_future: dict[concurrent.futures.Future, str] = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for label, fn in tasks:
            fut = executor.submit(fn)
            by_future[fut] = label
            futures.append(fut)
        if on_task_done is not None:
            for future in concurrent.futures.as_completed(list(by_future)):
                done += 1
                on_task_done(by_future[future], done, total)
        results: list[ToolResult] = []
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
    tasks: list[_NamedTask],
    *,
    on_task_done: Callable[[str, int, int], None] | None = None,
) -> list[ToolResult]:
    """Run `tasks` in parallel and flatten their results, dropping Nones.
    `on_task_done` (T-2978) passes straight through to
    `_run_tasks_concurrently`; see its own docstring.

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
        return _run_tasks_concurrently(tasks, on_task_done=on_task_done)
    finally:
        _restore_stdout_log_levels(stdout_handlers, saved_levels)


# frob:ticket T-0028
# frob:doc docs/commands/check.md#public-api
# frob:doc docs/modules/gates.md#rule-catalog
def run_check(
    root: Path,
    *,
    skip_ruff: bool = False,
    skip_ruff_check: bool = False,
    skip_ruff_format: bool = False,
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
    no_cache: bool = False,
    on_task_done: Callable[[str, int, int], None] | None = None,
) -> CheckResult:
    """Quality gate for Python projects: ruff, ty, cycle/dup/arch/bind, gates, etc.

    `delta=True` (T-0095) makes the gates stage report only violations new
    since `.frob/baseline` (see `frob.gates.stamp_baseline`/`delta_violations`) --
    an agent-facing signal-only mode; every other tool is unaffected.

    `no_cache=True` (T-1346) forces the gates stage to recompute every gate
    in full, bypassing T-0602's gate-result cache -- the default (`False`)
    now serves cacheable gates from `.frob/gate-cache.db` when their inputs
    are unchanged; see `_run_gates`'s docstring.

    T-2320: `skip_ruff_check`/`skip_ruff_format` independently skip just
    one of the two ruff sub-stages; `skip_ruff` (unchanged) still skips
    both. See `_python_skip_flags`'s docstring for how the three combine.

    T-2978: `on_task_done` (default `None`) is an optional live-progress
    hook, `(label, done_count, total)`, called as each of ruff/ty/cycle/
    dup/arch/bind/exports/gates actually finishes -- see
    `_run_tasks_concurrently`'s own docstring. Every existing caller
    (every one before this ticket) passes nothing and is unaffected.
    """
    skips = _python_skip_flags(
        skip_ruff=skip_ruff,
        skip_ruff_check=skip_ruff_check,
        skip_ruff_format=skip_ruff_format,
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
        no_cache=no_cache,
        on_task_done=on_task_done,
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
    no_cache: bool = False,
    on_task_done: Callable[[str, int, int], None] | None = None,
) -> CheckResult:
    """`run_check`'s task-selection and execution tail, once its many
    `skip_*` flags have been collapsed into `skips`. `on_task_done`
    (T-2978) passes straight through to `_collect_results`."""
    # T-3256: register/size the cross-process, memory-aware admission
    # budget BEFORE the derived-state lock and every downstream stage --
    # see `_admission_budget`'s own docstring for the full mechanism and
    # why it lives here (the one seam every Python-mode check run passes
    # through, upstream of `frob.gates`'s `os.cpu_count()`-sized pool).
    with (
        _admission_budget(root),
        # T-0859: hold a SHARED `derived_state_lock` for the run's entire
        # duration -- precheck through the last stage's read -- so a
        # second frob process's EXCLUSIVE writer cannot rewrite `.frob`
        # between this process's integrity precheck and a later stage's
        # read of the same artifacts (the cross-process TOCTOU window
        # T-0603 disclosed as its own residual). See `derived_state_lock`'s
        # docstring for the shared/exclusive contract.
        derived_state_lock(root, exclusive=False),
    ):
        # T-0603: single, synchronous, pre-dispatch integrity check -- see
        # `_derived_state_integrity_result`'s docstring for why this must
        # run before any concurrent stage starts, not from inside one.
        integrity_failure = _derived_state_integrity_result(root)
        if integrity_failure is not None:
            return CheckResult(path=str(root), results=[integrity_failure])

        # T-2764: same posture as the integrity precheck just above --
        # run once, synchronously, before any stage (including a
        # `--skip-gates`/`--only` selection that never reaches the gates
        # stage's own self-heal) can silently run against a stale native.
        staleness_failure = _native_staleness_result(root)
        if staleness_failure is not None:
            return CheckResult(path=str(root), results=[staleness_failure])

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
                no_cache=no_cache,
            )
            return CheckResult(
                path=str(root),
                results=_collect_results(tasks, on_task_done=on_task_done),
            )


# ---------------------------------------------------------------------------
# C/C++ checks
# ---------------------------------------------------------------------------


# frob:doc docs/commands/check.md#public-api
# frob:ticket T-0554
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
    no_cache: bool = False,
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
            no_cache=no_cache,
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
    no_cache: bool = False,
) -> list[_NamedTask]:
    """The enabled post-build jobs for a CMake C/C++ check run, each paired
    with its label (T-2978: matches `_python_tasks`'s `_NamedTask` shape --
    `_run_tasks_concurrently`/`_collect_results` are shared across every
    language's task list now)."""
    post_build: list[_NamedTask] = []
    if not skip_clang_tidy:
        post_build.append(("clang-tidy", lambda: _run_clang_tidy_cmake(root, bdir)))
    if not skip_clang_format:
        post_build.append(("clang-format", lambda: _run_clang_format(root)))
    if not skip_tests:
        _valgrind = valgrind
        post_build.append(("ctest", lambda: _run_ctest(bdir, valgrind=_valgrind)))
    if not skip_gates:
        post_build.append(
            (
                "gates",
                lambda: _run_gates(
                    root, ticket=ticket, base=base, delta=delta, no_cache=no_cache
                ),
            )
        )
    return post_build


# ---------------------------------------------------------------------------
# Rust checks
# ---------------------------------------------------------------------------


# frob:doc docs/commands/check.md#public-api
# frob:ticket T-0554
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
    no_cache: bool = False,
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
            gate_result = _run_gates(
                root, ticket=ticket, base=base, delta=delta, no_cache=no_cache
            )
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
    no_cache: bool = False,
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
                lambda: _run_gates(
                    root, ticket=ticket, base=base, delta=delta, no_cache=no_cache
                )
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
    return _detect_nested_project_type(root)


#: Marker filenames `_detect_nested_project_type` recognizes when found
#: anywhere under `root` (not just at the top level), mapped to the
#: language they signal.
_NESTED_MARKER_FILES: dict[str, str] = {
    "Cargo.toml": "rust",
    "CMakeLists.txt": "cpp",
    "pyproject.toml": "python",
    "setup.py": "python",
}

#: Bare source suffixes `_detect_nested_project_type` falls back to when
#: no marker file is found anywhere either.
_NESTED_SOURCE_SUFFIXES: dict[str, str] = {
    ".cpp": "cpp",
    ".cc": "cpp",
    ".c": "cpp",
    ".py": "python",
}


# frob:ticket T-0551
# frob:ticket T-3028
def _detect_nested_project_type(root: Path) -> str:
    """`detect_project_type`'s final fallback: a bounded, pruned recursive
    scan for a marker file or source file nested below `root`, before
    finally admitting 'unknown' (T-0404 finding 7 / T-0551).

    The root-level checks above return 'unknown' for a project whose
    sources/build files live only under a subdirectory (e.g.
    `src/CMakeLists.txt`, no root `CMakeLists.txt`; or `src/feature.py`,
    no root `*.py` and no `pyproject.toml`/`setup.py`) -- which used to
    send the whole repo down the wrong pipeline (finding 6/T-0546 for
    C/C++/Rust) or straight to a loud, wrong `CHECK001: unknown project
    type` (T-3028 for Python: a `git worktree`'s own root rarely holds a
    top-level `.py` file even for a perfectly ordinary `src/`-layout
    Python project, so `detect_project_type`'s root-only `*.py` glob
    above missed it entirely -- the ONLY reason this fell through to
    'unknown' rather than 'python' at all, with every downstream
    consequence, including gate:PREWORK/the ticket-lease-pin refusal,
    never getting a chance to run, T-3028's own repro). Originally
    native-language-only (T-0551); T-3028 folds Python's own nested
    fallback into the SAME bounded walk rather than adding a second one,
    since the two needs (a marker file, or a bare source suffix, found
    anywhere under `root`) are identical in shape. Reuses `frob.excludes.
    iter_files` (the shared pruned-walk entry point, `git ls-files` fast
    path when available) rather than a second raw `rglob`, so this scan
    skips `.git`/`.venv`/`node_modules`/build output the same way every
    other repo-wide walk in this codebase does.
    """
    from frob.excludes import iter_files

    files = iter_files(root)
    for path in files:
        marker = _NESTED_MARKER_FILES.get(path.name)
        if marker is not None:
            return marker
    for path in files:
        suffix_type = _NESTED_SOURCE_SUFFIXES.get(path.suffix.lower())
        if suffix_type is not None:
            return suffix_type
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

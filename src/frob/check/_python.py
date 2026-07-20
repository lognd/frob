"""Per-tool runners for the Python `frob check` pipeline (docs/commands/check.md).

Each `_run_*` helper shells out to one tool (ruff, ty, the frob native
analyses, the gates stage) and normalises its output into a `ToolResult`.
They are private helpers of `frob.check`; `run_check` composes them in
parallel.
"""

# frob:waive TEST005 reason="module line coverage 42.0%, debt T-0160"

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

from frob.process._guard import EXEC_KILL_SWITCH_ENV, guarded_subprocess_run
from frob.process.parsers.common import (
    Diagnostic,
    Severity,
    ToolResult,
    tool_disabled_result,
    tool_unavailable_result,
)

if TYPE_CHECKING:
    from frob.gates import Violation


# frob:ticket T-0142
def _run_ruff(root: Path, extra_args: list[str] | None) -> list[ToolResult]:
    """ruff lint + ruff format --check, as two ToolResults. A missing
    `ruff` binary (T-0142: bare-wheel installs may lack it) is a typed
    failing ToolResult for both stages, never a raw FileNotFoundError."""
    from frob.process.parsers import parse_ruff_json

    out: list[ToolResult] = []
    try:
        run_result = guarded_subprocess_run(
            ["ruff", "check", "--output-format", "json", str(root)],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        out.append(tool_unavailable_result("ruff-check", "ruff"))
        out.append(tool_unavailable_result("ruff-format", "ruff"))
        return out
    if run_result.is_err:
        out.append(tool_disabled_result("ruff-check", EXEC_KILL_SWITCH_ENV))
        out.append(tool_disabled_result("ruff-format", EXEC_KILL_SWITCH_ENV))
        return out
    proc = run_result.danger_ok
    r = parse_ruff_json(proc.stdout, exit_code=proc.returncode)
    r.tool = "ruff-check"
    out.append(r)
    out.append(_ruff_format_result(root))
    return out


def _ruff_format_result(root: Path) -> ToolResult:
    """The `ruff format --check` outcome as one ToolResult, or a typed
    failure (T-0142) if `ruff` is not on PATH."""
    try:
        run_result = guarded_subprocess_run(
            ["ruff", "format", "--check", str(root)],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return tool_unavailable_result("ruff-format", "ruff")
    if run_result.is_err:
        return tool_disabled_result("ruff-format", EXEC_KILL_SWITCH_ENV)
    proc = run_result.danger_ok
    if not proc.returncode:
        return ToolResult(
            tool="ruff-format", exit_code=0, summary="all files formatted"
        )
    msg = (proc.stdout + proc.stderr).strip()
    reformat = [ln for ln in msg.splitlines() if "Would reformat" in ln]
    n = len(reformat)
    return ToolResult(
        tool="ruff-format",
        exit_code=proc.returncode,
        diagnostics=_reformat_diagnostics(reformat),
        summary=f"{n} file{'s' if n != 1 else ''} would be reformatted",
    )


def _reformat_diagnostics(reformat_lines: list[str]) -> list[Diagnostic]:
    """One warning `Diagnostic` per `ruff format --check` "Would reformat"
    line."""
    return [
        Diagnostic(
            file=ln.replace("Would reformat ", "").strip(),
            severity="warning",
            message="needs formatting",
        )
        for ln in reformat_lines
    ]


# frob:ticket T-0142
def _run_ty(root: Path) -> ToolResult:
    """ty type-check, honouring a local ty.toml's extra-paths. A missing
    `ty` binary (T-0142) is a typed failing ToolResult, never a silent
    skip -- the previous `None` return vanished the stage entirely."""
    from frob.process.parsers import parse_ty

    scan = root if root.is_dir() else root.parent
    cmd = ["ty", "check", str(root)]
    ty_cfg = scan / "ty.toml"
    if ty_cfg.exists():
        try:
            import tomllib

            with ty_cfg.open("rb") as f:
                cfg = tomllib.load(f)
            for p in cfg.get("environment", {}).get("extra-paths", []):
                cmd += ["--extra-search-path", str((scan / p).resolve())]
        except Exception:
            pass

    try:
        run_result = guarded_subprocess_run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        return tool_unavailable_result("ty", "ty")
    if run_result.is_err:
        return tool_disabled_result("ty", EXEC_KILL_SWITCH_ENV)
    proc = run_result.danger_ok
    r = parse_ty(proc.stdout + proc.stderr, exit_code=proc.returncode)
    r.tool = "ty"
    return r


def _build_import_graph(scan_root: Path):  # noqa: ANN202
    """The intra-project import dependency graph rooted at `scan_root`."""
    from frob.cycle.graph import DependencyGraph
    from frob.lang import extract_imports, resolve_local_import

    graph = DependencyGraph()
    resolved_scan = scan_root.resolve()
    skip = {"__pycache__", ".venv", "build", "dist"}
    for path in scan_root.rglob("*.py"):
        try:
            rel_parts = path.resolve().relative_to(resolved_scan).parts
        except ValueError:
            rel_parts = path.parts
        if any(p in skip or p.startswith(".") for p in rel_parts):
            continue
        try:
            rel = str(path.relative_to(scan_root))
            graph.add_node(rel)
            result = extract_imports(path)
            if result.is_err:
                continue
            for spec in result.danger_ok:
                resolved = resolve_local_import(
                    spec, "python", file_dir=path.parent, root=scan_root
                )
                if resolved is not None:
                    graph.add_edge(rel, resolved)
        except Exception:
            pass
    return graph


# frob:ticket T-0228
def _severity_counts_summary(diags: list[Diagnostic], *, no_issues: str) -> str:
    """`"N error(s), M warning(s)"` over `diags`' severities, honest at a glance.

    T-0228: a stage that only found warn-class findings must never be
    reported with a bare, alarming-looking count ("987 violation(s)") on a
    PASSING run -- error and warning counts are always split so the reader
    can tell severity from the summary line alone, without opening the
    diagnostics. Zero-count categories are omitted; `no_issues` covers the
    fully-clean case.
    """
    n_err = sum(1 for d in diags if d.severity == "error")
    n_warn = sum(1 for d in diags if d.severity == "warning")
    parts = []
    if n_err:
        parts.append(f"{n_err} error{'s' if n_err != 1 else ''}")
    if n_warn:
        parts.append(f"{n_warn} warning{'s' if n_warn != 1 else ''}")
    return ", ".join(parts) if parts else no_issues


def _cycle_severity(n_nodes: int) -> Severity:
    """2-node mutual imports are info, 3-5 a minor cycle, 6+ structural."""
    if n_nodes <= 2:
        return "info"
    if n_nodes <= 5:
        return "warning"
    return "error"


def _cycle_diags(cycles) -> list[Diagnostic]:  # noqa: ANN001
    """One diagnostic per detected import cycle, severity scaled by size."""
    diags: list[Diagnostic] = []
    for cycle in cycles:
        sev = _cycle_severity(len(cycle))
        lines = (
            ["import cycle:"] + [f"  {node}" for node in cycle] + [f"  -> {cycle[0]}"]
        )
        diags.append(Diagnostic(severity=sev, message="\n".join(lines)))
    return diags


def _run_cycle(root: Path) -> ToolResult:
    """Import-cycle detection over the project's local dependency graph."""
    from frob.cycle.graph import find_cycles

    scan_root = root if root.is_dir() else root.parent
    cycles = find_cycles(_build_import_graph(scan_root))
    diags = _cycle_diags(cycles)
    return ToolResult(
        tool="frob-cycle",
        exit_code=1 if any(d.severity == "error" for d in diags) else 0,
        diagnostics=diags,
        # T-0228: split by severity -- a run with only info/warning-class
        # cycles must never render as a bare, alarming "N cycle(s) found"
        # on a passing stage.
        summary=_severity_counts_summary(diags, no_issues="no cycles"),
    )


# frob:ticket T-0375
_DUP_CACHE_REL = Path(".frob") / "cache.db"

# frob:ticket T-0375
# T-0122's dup/arch stages run in the SAME ThreadPoolExecutor batch as
# gates -- an unsynchronized cache would let two threads race into
# `build_graph` concurrently against the same `.frob/cache.db` (sqlite
# "database is locked" territory). A plain lock serializes the
# first-caller-builds-it path; `_snapshot_cache` then makes every later
# caller (same or different stage, same root) reuse that one build instead
# of re-walking the tree.
_snapshot_lock = threading.Lock()
_snapshot_cache: dict[Path, object] = {}


# frob:ticket T-0375
def _cached_snapshot(scan: Path):  # noqa: ANN202
    """`build_graph(scan, ...)`'s snapshot, memoized per `scan` root and
    thread-safe (T-0375): the gates stage already builds this graph once
    per `frob check` run (T-0122's "exactly one build" invariant); the
    dup/arch stages' waiver cross-reference need the SAME snapshot's WAIVE
    edges, so this reuses rather than re-walking the tree a second/third
    time, even when those stages run concurrently. Returns `None` if the
    build failed -- callers degrade to "everything unaccounted", never a
    crash."""
    from frob.graph import build_graph

    with _snapshot_lock:
        if scan in _snapshot_cache:
            return _snapshot_cache[scan]
        result = build_graph(scan, scan / _DUP_CACHE_REL)
        snapshot = result.danger_ok if result.is_ok else None
        _snapshot_cache[scan] = snapshot
        return snapshot


# frob:ticket T-0375
def _waive_edges_for_rule(root: Path, rule: str):  # noqa: ANN202
    """Every `frob:waive` edge in `root`'s obligation graph targeting `rule`,
    or `()` if the graph fails to build (T-0375: a broken graph must never
    crash the advisory dup/arch waiver cross-reference -- it just falls
    back to reporting everything as unaccounted, same as before this
    ticket)."""
    from frob.graph._models import EdgeKind

    scan = (root if root.is_dir() else root.parent).resolve()
    snapshot = _cached_snapshot(scan)
    if snapshot is None:
        return ()
    return tuple(
        e for e in snapshot.edges if e.kind == EdgeKind.WAIVE and e.target == rule
    )


# frob:ticket T-0375
def _dup_group_symrefs(group) -> set[str]:  # noqa: ANN001
    """`{path::symbol}` for every fragment in a `frob.dup` `CloneGroup` --
    the identity a `frob:waive DUP001`/`DUP002` directive binds to via
    `frob.graph.dsl`'s enclosing-symbol resolution."""
    return {f"{frag.file}::{frag.symbol}" for frag in group.fragments}


# frob:ticket T-0375
def _dup_waived_symrefs(waivers) -> set[str]:  # noqa: ANN001
    """The `src` symrefs named by a set of DUP001/DUP002 `frob:waive` edges."""
    return {w.src for w in waivers}


# frob:ticket T-0375
def _dup_group_covering_waivers(group, waived_symrefs: set[str]) -> tuple[str, ...]:  # noqa: ANN001
    """The sorted waiver symrefs covering `group`, or `()` unless EVERY
    fragment's symref is covered.

    T-0375 review fix: `frob.dup._legacy`'s `_exact_groups`/`_renamed_groups`
    deliberately let one symbol sit in BOTH an exact-clone group and a
    DISTINCT, larger renamed-clone superset group (e.g. `foo`/`bar` exact,
    `foo`/`bar`/`baz` renamed). An "ANY fragment symref matches ANY waiver"
    rule would let a single `frob:waive DUP001` reasoned about the `foo`/
    `bar` pair also silently swallow the unrelated, unwaived `baz` in the
    renamed superset group -- exactly the dishonesty this ticket exists to
    prevent. Requiring FULL group coverage (every fragment site named by
    some waiver) means a waiver only ever excludes the specific group it
    was written about: partial overlap leaves the group counted, and its
    diagnostic lists every fragment still unaccounted for."""
    symrefs = _dup_group_symrefs(group)
    if not symrefs or not symrefs <= waived_symrefs:
        return ()
    return tuple(sorted(symrefs))


# frob:ticket T-0375
def _dup_group_diag(g, *, covering_waivers: tuple[str, ...]) -> Diagnostic:  # noqa: ANN001
    """One diagnostic for a `frob.dup` group: `warning` if unaccounted for,
    `note` (naming every covering symref) if `frob:waive DUP001`/`DUP002`
    directives cover ALL of its fragments (see `_dup_group_covering_waivers`)
    -- mirrors `_waived_diags`'s gates-stage treatment so a waived group is
    never silently hidden, only demoted."""
    locs = ", ".join(f"{f.file}:{f.start_line}" for f in g.fragments)
    message = f"{g.size_lines}-line duplicate block at {locs}"
    if covering_waivers:
        return Diagnostic(
            severity="note",
            code=g.clone_type,
            message=f"{message}  [waived: {', '.join(covering_waivers)}]",
        )
    return Diagnostic(severity="warning", code=g.clone_type, message=message)


# frob:ticket T-0375
def _dup_summary(n_unaccounted: int, n_waived: int) -> str:
    """`"N duplicate groups (M waived)"` -- the headline counts only
    unaccounted groups, mirroring the gates stage's error/warning/waived
    split (T-0375); waived groups stay visible via the note diagnostics,
    never hidden."""
    if not n_unaccounted and not n_waived:
        return "no duplicates"
    base = f"{n_unaccounted} duplicate group{'s' if n_unaccounted != 1 else ''}"
    if n_waived:
        base += f" ({n_waived} waived)"
    return base


# frob:doc docs/modules/dup.md#check-stage-summary-is-waiver-aware-t-0375
def _run_dup(root: Path) -> ToolResult:
    """Structural duplicate-block detection, waiver-aware (T-0375): a group
    is excluded from the headline count only when EVERY one of its
    fragments' symrefs is covered by a DUP001/DUP002 `frob:waive`
    (`_dup_group_covering_waivers` -- full-coverage, never a partial-overlap
    match), and even then it stays listed as a `note` diagnostic, never
    hidden -- the same honesty the gates stage already gives its `N waived`
    term."""
    from frob.dup import find_duplicates

    scan = root if root.is_dir() else root.parent
    result = find_duplicates(scan)
    waived_symrefs = _dup_waived_symrefs(
        (*_waive_edges_for_rule(root, "DUP001"), *_waive_edges_for_rule(root, "DUP002"))
    )
    diags: list[Diagnostic] = []
    n_waived = 0
    for g in result.groups:
        covering = _dup_group_covering_waivers(g, waived_symrefs)
        diags.append(_dup_group_diag(g, covering_waivers=covering))
        if covering:
            n_waived += 1
    n_unaccounted = len(result.groups) - n_waived
    return ToolResult(
        tool="frob-dup",
        exit_code=0,
        diagnostics=diags,
        summary=_dup_summary(n_unaccounted, n_waived),
    )


def _arch_summary(n_warn_unaccounted: int, n_warn_waived: int, n_sugg: int) -> str:
    """`"N warnings (M waived), K suggestions"` (or "no issues") over arch
    findings -- T-0375: the warning headline counts only ARCH001
    long-functions NOT covered by a matching `frob:waive ARCH001`; waived
    ones stay visible as `note` diagnostics. Suggestion-severity categories
    are never waivable (T-0101's unwaivable channel) so they pass through
    unchanged."""
    parts = []
    if n_warn_unaccounted or n_warn_waived:
        n_word = "warning" if n_warn_unaccounted == 1 else "warnings"
        warn_part = f"{n_warn_unaccounted} {n_word}"
        if n_warn_waived:
            warn_part += f" ({n_warn_waived} waived)"
        parts.append(warn_part)
    if n_sugg:
        parts.append(f"{n_sugg} suggestion{'s' if n_sugg != 1 else ''}")
    return ", ".join(parts) if parts else "no issues"


# frob:ticket T-0375
def _arch001_violations(suggestions) -> tuple[Violation, ...]:  # noqa: ANN001
    """The ARCH001 `Violation`s `frob.gates._arch.arch_gate` would build from
    `suggestions`, without re-running `analyze_project` a second time --
    `_run_arch` already computed `suggestions` once; T-0375's waiver
    cross-reference reuses them instead of paying for a duplicate arch pass."""
    from frob.gates import Severity as GateSeverity
    from frob.gates import Violation as GateViolation

    return tuple(
        GateViolation(
            rule="ARCH001",
            severity=GateSeverity.WARN,
            file=s.file,
            line=s.line or 0,
            message=f"ARCH001: {s.message}",
            symref=s.symref,
            metric=s.metric,
        )
        for s in suggestions
        if s.category == "long-function"
    )


# frob:ticket T-0375
def _arch_long_function_waived_symrefs(root: Path, suggestions) -> set[str]:  # noqa: ANN001
    """Symrefs of long-functions covered by a matching `frob:waive ARCH001
    reason="..." [ceiling=N]`, matched via `frob.gates`' own waiver-matching
    (`_apply_waivers`) over ARCH001 `Violation`s built from the already-
    computed `suggestions` -- ceiling= honored, identical semantics to the
    real gate, never a hand-rolled second matching rule that could drift
    from it."""
    from frob.gates import _apply_waivers

    scan = (root if root.is_dir() else root.parent).resolve()
    snapshot = _cached_snapshot(scan)
    if snapshot is None:
        return set()
    violations = _arch001_violations(suggestions)
    _kept, waived = _apply_waivers(violations, snapshot)
    return {v.symref for v in waived if v.symref is not None}


# frob:doc docs/modules/arch.md#check-stage-summary-is-waiver-aware-for-arch001-t-0375
# frob:ticket T-0442
def _run_arch(root: Path) -> ToolResult:
    """frob's architectural analysis (long functions, god classes, etc.),
    waiver-aware for ARCH001 long-functions (T-0375): a long-function
    covered by a matching `frob:waive ARCH001` is excluded from the warning
    headline but still listed (as a `note` diagnostic), never hidden. Every
    other arch category stays on T-0101's unwaivable channel, unchanged.

    T-0442: thresholds come from `frob.app.config.load_arch_config` (the
    repo's `[arch]` frob.toml table, calibrated-default fallback), matching
    `frob.gates._arch.arch_gate`'s T-0373 fix -- this tool-summary stage used
    to silently fall back to `analyze_project`'s conservative keyword
    defaults, so its suggestion counts could disagree with the ARCH001 gate
    over the same code."""
    from frob.app.config import load_arch_config
    from frob.arch import analyze_project

    scan_root = root if root.is_dir() else root.parent
    result = analyze_project(scan_root, **load_arch_config(scan_root))
    waived_symrefs = _arch_long_function_waived_symrefs(root, result.suggestions)
    sev_map: dict[str, Severity] = {
        "warning": "warning",
        "suggestion": "note",
        "info": "info",
    }
    diags: list[Diagnostic] = []
    n_warn_unaccounted = 0
    n_warn_waived = 0
    n_sugg = 0
    for s in result.suggestions:
        if s.severity == "warning" and s.symref in waived_symrefs:
            diags.append(
                Diagnostic(
                    file=s.file,
                    line=s.line,
                    severity="note",
                    code=s.category,
                    message=f"{s.message}  [waived: {s.symref}]",
                )
            )
            n_warn_waived += 1
            continue
        diags.append(
            Diagnostic(
                file=s.file,
                line=s.line,
                severity=sev_map.get(s.severity, "note"),
                code=s.category,
                message=s.message,
            )
        )
        if s.severity == "warning":
            n_warn_unaccounted += 1
        else:
            n_sugg += 1
    return ToolResult(
        tool="frob-arch",
        exit_code=0,
        diagnostics=diags,
        summary=_arch_summary(n_warn_unaccounted, n_warn_waived, n_sugg),
    )


def _violation_diags(violations) -> list[Diagnostic]:  # noqa: ANN001
    """Gate violations rendered as error/warning diagnostics."""
    return [
        Diagnostic(
            file=v.file,
            line=v.line,
            severity="error" if v.severity.value == "error" else "warning",
            code=v.rule,
            message=v.message,
        )
        for v in violations
    ]


def _waived_diags(waived) -> list[Diagnostic]:  # noqa: ANN001
    """Waived gate violations rendered as note diagnostics."""
    return [
        Diagnostic(
            file=v.file,
            line=v.line,
            severity="note",
            code=v.rule,
            message=f"{v.message}  [waived: {v.waived.reason if v.waived else ''}]",
        )
        for v in waived
    ]


def _timing_str(stats) -> str:  # noqa: ANN001
    """The per-gate timing table, sorted by gate name."""
    ordered = sorted(stats.timing_s.items())
    return ", ".join(f"{k}={t:.2f}s" for k, t in ordered)


def _error_count(violations) -> int:  # noqa: ANN001
    """Count of error-severity gate violations."""
    return sum(1 for v in violations if v.severity.value == "error")


# frob:ticket T-0028
# frob:ticket T-0102
# frob:ticket T-0095
def _run_gates(
    root: Path,
    *,
    ticket: str | None = None,
    base: str | None = None,
    gates: frozenset[str] = frozenset(),
    delta: bool = False,
) -> ToolResult:
    """Run frob.gates.run_gates as a check stage. Most load failures (git repo
    / tickets dir not guaranteed to exist for every `frob check` caller) are a
    soft skip, but a failure to load the ticket queue is a hard ERROR with
    remedy text (T-0102): a malformed tickets.md must never silently vanish
    every gate while still exiting 0 (the vacuous-pass class). Any
    ERROR-severity violation from a successful run also fails the stage like
    any other tool. `delta=True` (T-0095) filters the kept violations down
    to those absent from `.frob/baseline` before scoring/reporting -- the
    agent-facing signal-only mode; a missing or stale baseline degrades to
    the full (unfiltered) set with a WARN diagnostic, never a silent no-op.
    """
    from frob.gates import GateConfig, GateError, run_gates

    cfg = GateConfig(root=str(root), base=base or "main", ticket=ticket, gates=gates)
    result = run_gates(cfg)
    if result.is_err:
        return _gates_error_result(result.danger_err, GateError)
    return _gates_success_result(result.danger_ok, root=root, delta=delta)


def _gates_error_result(err, gate_error_cls) -> ToolResult:  # noqa: ANN001
    """The `ToolResult` for a failed `run_gates` call: a hard ERROR if the
    ticket queue itself failed to load, else a soft skip."""
    if err is gate_error_cls.QueueUnavailable:
        return ToolResult(
            tool="gates",
            exit_code=1,
            diagnostics=[
                Diagnostic(
                    file="tickets.md",
                    severity="error",
                    message=(
                        "ticket queue failed to load: all gates were skipped. "
                        "This is a hard failure, not a soft skip -- fix the "
                        "malformed entry (check evidence: blocks and YAML "
                        "syntax) and re-run `frob check`."
                    ),
                )
            ],
            summary=("gates FAILED: ticket queue failed to load -- fix tickets.md"),
        )
    return ToolResult(
        tool="gates",
        exit_code=0,
        summary=f"gates skipped: {err.value}",
    )


def _gates_success_result(report, *, root: Path, delta: bool) -> ToolResult:  # noqa: ANN001
    """The `ToolResult` for a successful `run_gates` report: delta-filtering,
    diagnostics, and the error/warning/waived summary line."""
    violations, delta_note = (
        _apply_delta(root, report.violations)
        if delta
        else (
            report.violations,
            None,
        )
    )
    diags = [*_violation_diags(violations), *_waived_diags(report.waived)]
    if delta_note is not None:
        diags.append(Diagnostic(severity="warning", message=delta_note))
    n_err = _error_count(violations)
    summary = _gates_summary(violations, report, n_err=n_err, delta=delta)
    return ToolResult(
        tool="gates",
        exit_code=1 if n_err > 0 else 0,
        diagnostics=diags,
        summary=f"{summary}  [{_timing_str(report.stats)}]",
    )


def _gates_summary(violations, report, *, n_err: int, delta: bool) -> str:  # noqa: ANN001
    """The error/warning/waived count summary line for a gates run,
    prefixed with the new-vs-total count when `delta` filtering applied."""
    n_warn = len(violations) - n_err
    # T-0228: never collapse errors and warnings into one bare "violation(s)"
    # count -- that reads as alarming (or as a failure) even on a passing
    # gate run where every finding is warn-class. Always split, and always
    # report the waived count as its own term.
    parts = [
        f"{n_err} error{'s' if n_err != 1 else ''}",
        f"{n_warn} warning{'s' if n_warn != 1 else ''}",
        f"{len(report.waived)} waived",
    ]
    summary = ", ".join(parts)
    if delta:
        summary = f"{len(violations)}/{len(report.violations)} new  " + summary
    return summary


def _apply_delta(
    root: Path, violations: tuple[Violation, ...]
) -> tuple[tuple[Violation, ...], str | None]:
    """T-0095: filter `violations` to those new since `.frob/baseline`.

    A missing or stale baseline is never a silent no-op -- it degrades to
    the unfiltered set plus a WARN note telling the caller to re-stamp.
    """
    from frob.gates import delta_violations, is_baseline_stale, load_baseline

    baseline = load_baseline(root)
    if baseline is None:
        return violations, (
            "--delta requested but no baseline found; showing all violations. "
            "Run `frob check --stamp-baseline` first."
        )
    if is_baseline_stale(root, baseline):
        return violations, (
            "--delta requested but the baseline is stale (source changed since "
            "stamping); showing all violations. Re-run `frob check "
            "--stamp-baseline`."
        )
    return delta_violations(violations, baseline), None


def _run_bind(root: Path) -> ToolResult | None:
    """Verify BIND comment markers, if any exist in the tree."""
    scan = root if root.is_dir() else root.parent
    if not _has_bind_markers(scan):
        return None

    try:
        from frob.bind import (
            verify_bindings,  # type: ignore[import,attr-defined]  # ty: ignore[unresolved-import]
        )
    except ImportError:
        return None

    result = verify_bindings(scan)
    diags = _bind_mismatch_diagnostics(result)
    n = len(diags)
    return ToolResult(
        tool="frob-bind",
        exit_code=1 if diags else 0,
        diagnostics=diags,
        summary=f"{n} binding mismatch{'es' if n != 1 else ''}"
        if diags
        else "all bindings verified",
    )


def _has_bind_markers(scan: Path) -> bool:
    """Whether any `.py` file under `scan` contains a `# BIND` marker."""
    for path in scan.rglob("*.py"):
        try:
            if b"# BIND" in path.read_bytes():
                return True
        except Exception:
            pass
    return False


def _bind_mismatch_diagnostics(result) -> list[Diagnostic]:  # noqa: ANN001
    """One error `Diagnostic` per BIND mismatch reported by `verify_bindings`."""
    return [
        Diagnostic(file=m.file, line=m.line, severity="error", message=m.message)
        for m in getattr(result, "mismatches", [])
    ]


def _missing_exports(init_src: str, modules) -> list[str]:  # noqa: ANN001
    """Public `module.symbol` names not referenced in the package `__init__.py`."""
    missing: list[str] = []
    for mod in modules:
        for sym in mod.symbols:
            if sym not in init_src:
                missing.append(f"{mod.module}.{sym}")
    return missing


def _exports_for_package(init_file: Path, scan: Path) -> ToolResult | None:
    """The un-exported-public-symbol ToolResult for one package, or None.

    `tests/` (and any nested test package under it) is exempt (T-0362):
    pytest test functions/classes are collected by pytest's own discovery,
    never imported through a package `__init__.py` -- flagging every
    `test_*`/`Test*` symbol as "should be exported" is a mis-scoped check
    for a directory that isn't a public-API package at all.
    """
    from frob.exports import exports_package

    pkg_dir = init_file.parent
    if any(
        p.startswith(".") or p in {"__pycache__", ".venv", "build", "dist", "tests"}
        for p in pkg_dir.parts
    ):
        return None
    sibs = [f for f in pkg_dir.glob("*.py") if f.name != "__init__.py"]
    if not sibs:
        return None

    result = exports_package(pkg_dir, include_private=False)
    if result.is_err:
        return None
    er = result.danger_ok
    if not er.modules:
        return None
    try:
        init_src = init_file.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    missing = _missing_exports(init_src, er.modules)
    if not missing:
        return None
    return _unexported_symbols_result(init_file, pkg_dir, scan, missing)


def _unexported_symbols_result(
    init_file: Path, pkg_dir: Path, scan: Path, missing: list[str]
) -> ToolResult:
    """The `ToolResult` reporting `missing` un-exported public symbols for
    one package's `__init__.py`."""
    diags = [
        Diagnostic(
            file=str(init_file.relative_to(scan)),
            severity="note",
            message=f"public symbol not exported: {s}",
        )
        for s in missing
    ]
    pkg_name = str(pkg_dir.relative_to(scan))
    n = len(missing)
    return ToolResult(
        tool=f"frob-exports({pkg_name})",
        exit_code=0,
        diagnostics=diags,
        summary=f"{n} public symbol{'s' if n != 1 else ''} missing from __init__.py",
    )


def _run_exports(root: Path) -> list[ToolResult]:
    """Report public symbols in sub-modules that are absent from each __init__.py."""
    scan = root if root.is_dir() else root.parent
    init_files = sorted(scan.rglob("__init__.py"))
    out: list[ToolResult] = []
    for init_file in init_files:
        result = _exports_for_package(init_file, scan)
        if result is not None:
            out.append(result)
    return out

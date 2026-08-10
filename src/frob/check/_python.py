"""Per-tool runners for the Python `frob check` pipeline (docs/commands/check.md).

Each `_run_*` helper shells out to one tool (ruff, ty, the frob native
analyses, the gates stage) and normalises its output into a `ToolResult`.
They are private helpers of `frob.check`; `run_check` composes them in
parallel.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from frob.excludes import iter_files
from frob.process._guard import EXEC_KILL_SWITCH_ENV, guarded_subprocess_run
from frob.process.parsers.common import (
    Diagnostic,
    Severity,
    ToolResult,
    tool_crash_result,
    tool_disabled_result,
    tool_unavailable_result,
)

if TYPE_CHECKING:
    from frob.gates import Violation


# frob:ticket T-0142
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to parse_ruff_json (a deferred \
# cross-module import the resolver cannot follow) and _ruff_format_result's own call \
# graph; every locally-visible fallible step here is the guarded subprocess call, \
# already caught below"
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


# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to _reformat_diagnostics, a plain \
# str-splitting helper the resolver cannot follow through the module-local call \
# boundary; the only fallible step (the guarded subprocess call) is caught below"
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
# frob:ticket T-0996
def _run_ty(root: Path) -> ToolResult:
    """ty type-check, honouring a local ty.toml's extra-paths. A missing
    `ty` binary (T-0142) is a typed failing ToolResult, never a silent
    skip -- the previous `None` return vanished the stage entirely.

    T-0996: `ty` resolves first-party imports and its Python environment
    by walking UP the directory tree from `root` looking for the nearest
    `pyproject.toml`/`.venv` -- there is no ty flag that pins that search
    to `root` and disables the upward walk (`--project` only changes the
    walk's starting point, per `ty check --help`). A `root` nested under
    ANY ancestor directory that happens to contain an unrelated
    `pyproject.toml`/`.venv` (a stray scratch file from another process, a
    monorepo parent, ...) silently mis-resolves every first-party import
    and every third-party dependency to that ancestor instead of `root`
    (reproduced against a stray `/tmp/pyproject.toml` + `/tmp/.venv`
    during T-0996's investigation -- a fresh scaffold nested three levels
    under a polluted `/tmp` failed `ty check` with `unresolved-import` on
    its OWN package, while the identical scaffold one level under `$HOME`
    passed cleanly). Passing `--extra-search-path <root>/src` (when a
    src-layout exists) and `--python <root>/.venv` (when a project-local
    venv exists) makes first-party and third-party resolution hermetic to
    `root` regardless of what ancestor directories contain, independent
    of a `ty.toml`."""
    from frob.process.parsers import parse_ty

    scan = root if root.is_dir() else root.parent
    cmd = ["ty", "check", str(root)]
    src_dir = scan / "src"
    if src_dir.is_dir():
        cmd += ["--extra-search-path", str(src_dir.resolve())]
    venv_dir = scan / ".venv"
    if venv_dir.is_dir():
        cmd += ["--python", str(venv_dir.resolve())]
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
    for path in iter_files(scan_root, suffix=".py"):
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


# frob:ticket T-1035
def _dup_symref_covered(symref: str, waived_symrefs: set[str]) -> bool:
    """True if `symref` (`path::a.b.c`) is directly waived, or waived via
    any ANCESTOR qualname prefix (`path::a.b`, `path::a`).

    T-1035: `frob.dup._legacy_py._iter_functions_py` qualifies a nested
    Python closure by its FULL enclosing class/function chain (e.g.
    `path::TestFoo.test_bar._run_new`), but `frob.graph.dsl`'s comment-
    binding never tracks a nested closure as its own addressable symbol --
    a `frob:waive` comment placed directly above the nested `def` binds to
    the nearest OUTER symbol the graph DOES track (here,
    `path::TestFoo.test_bar`, per `_enclosing_src`'s enclosing-symbol
    fallback). Requiring an exact symref match would make such a fragment
    permanently unwaivable no matter where the comment is placed. Walking
    up the dotted qualname one segment at a time and accepting the first
    ancestor found in `waived_symrefs` matches what a human intuitively
    expects (the waiver they wrote directly above the closure does cover
    it) while changing nothing for a symref that already resolves exactly
    (an ordinary top-level function or method, one dot at most, has no
    ancestor prefix to fall back to)."""
    if symref in waived_symrefs:
        return True
    path, sep, symbol = symref.partition("::")
    if not sep:
        return False
    parts = symbol.split(".")
    while len(parts) > 1:
        parts = parts[:-1]
        if f"{path}::{'.'.join(parts)}" in waived_symrefs:
            return True
    return False


# frob:ticket T-0375
def _dup_group_covering_waivers(group, waived_symrefs: set[str]) -> tuple[str, ...]:  # noqa: ANN001
    """The sorted waiver symrefs covering `group`, or `()` unless EVERY
    fragment's symref is covered (directly or via `_dup_symref_covered`'s
    ancestor-prefix fallback, T-1035).

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
    if not symrefs or not all(_dup_symref_covered(s, waived_symrefs) for s in symrefs):
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


# frob:ticket T-1346
#: `FROB_NO_GATE_CACHE=1` (any non-empty value) disables T-0602's gate
#: cache for this invocation -- the escape hatch T-1346's acceptance
#: criteria call for, expressed as an env var rather than a new argparse
#: flag because `_cli_parsers/_check.py`/`app/config.py`/`app/check_runner.py`
#: sit outside this ticket's declared scope (`src/frob/gates/**`,
#: `src/frob/check/**`, `docs/modules/gates.md`); a first-class `--no-cache`
#: CLI flag is filed as a follow-up (see docs/modules/gates.md).
_NO_GATE_CACHE_ENV = "FROB_NO_GATE_CACHE"


# frob:ticket T-1346
# frob:tests \
# tests/unit/test_check.py::TestRunGatesCacheWiring.test_gate_cache_enabled_default_true
# frob:tests tests/unit/test_check.py::TestRunGatesCacheWiring.test_gate_cache_enabled_false_when_no_cache_true  # noqa: E501
# frob:tests tests/unit/test_check.py::TestRunGatesCacheWiring.test_gate_cache_enabled_false_when_env_var_set  # noqa: E501
def _gate_cache_enabled(no_cache: bool) -> bool:
    """Whether this `_run_gates` call should opt into T-0602's gate-result
    cache: `no_cache=True` (a caller's explicit request) or a non-empty
    `FROB_NO_GATE_CACHE` env var both disable it; otherwise caching is ON
    by default (T-1346 -- previously `run_gates`'s `use_cache=True` path
    existed but no `frob check` call site ever passed it, so the cache
    built in T-0602 never actually served a real invocation)."""
    if no_cache:
        return False
    # frob:waive SEC110 reason="FROB_NO_GATE_CACHE feature-flag read (T-1346's cache \
    # escape hatch); a boolean opt-out, carries no secret"
    return not os.environ.get(_NO_GATE_CACHE_ENV)


# frob:ticket T-0028
# frob:ticket T-0102
# frob:ticket T-0095
# frob:ticket T-1346
# frob:tests tests/unit/test_check.py::TestRunGatesCacheWiring.test_run_gates_passes_use_cache_true_by_default  # noqa: E501
# frob:tests tests/unit/test_check.py::TestRunGatesCacheWiring.test_run_gates_no_cache_forces_use_cache_false  # noqa: E501
def _run_gates(
    root: Path,
    *,
    ticket: str | None = None,
    base: str | None = None,
    gates: frozenset[str] = frozenset(),
    delta: bool = False,
    no_cache: bool = False,
) -> ToolResult | list[ToolResult]:
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

    T-1346: `run_gates` is now called with `use_cache=_gate_cache_enabled
    (no_cache)` -- ON by default -- so the T-0602 dependency-tracked
    partial-re-evaluation cache actually serves real `frob check` runs for
    the closed `_CACHEABLE_GATES` allowlist (drift/test/policy/
    parse_failures/debt/lang_conformance/affect_drift). `no_cache=True` (or
    `FROB_NO_GATE_CACHE` set) forces a full recompute, matching every
    pre-T-1346 call byte-for-byte. Cache HIT/MISS is logged per gate
    (`frob.gates._gate_cache`'s own `_log.info` lines, visible under
    `frob check -v`) so a suspect cached result is diagnosable without a
    special flag.

    T-0603: `frob.check._derived_state_integrity_result` (called once,
    synchronously, before any check task is dispatched -- see
    `_run_check_with_skips`/`run_check_cpp`/`run_check_rust`/`run_check_ts`)
    guards this stage against ever running against a corrupt derived
    artifact: a truncated/malformed cache or baseline file is caught
    before dispatch, so by the time `_run_gates` runs concurrently
    alongside stages that are themselves writing to those same caches
    (`arch`/`dup`, T-0603's own regression case), the check has already
    happened and cannot race a live writer.

    T-0420: a successful run now reports as a LIST of `ToolResult`s -- one
    named `gate:<FAMILY>` stage per rule family plus a trailing
    `gate-summary` totals+timing line -- rather than one monolithic
    `gates` line; a load failure still reports as the single `gates`
    `ToolResult` `_gates_error_result` already built (nothing to split,
    there is no report to group by family).
    """
    from frob.gates import GateConfig, GateError, run_gates

    cfg = GateConfig(root=str(root), base=base or "main", ticket=ticket, gates=gates)
    result = run_gates(cfg, use_cache=_gate_cache_enabled(no_cache))
    if result.is_err:
        return _gates_error_result(result.danger_err, GateError)
    return _gates_success_result(
        result.danger_ok, root=root, delta=delta, ticket=ticket, gates=gates
    )


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


# frob:ticket T-0420
def _rule_family(rule: str) -> str:
    """The named-family prefix of a gate rule id (T-0420): `COV001` -> `COV`,
    `PII010` -> `PII`, `SEC110` -> `SEC` -- everything up to the first
    digit. `frob check`'s single monolithic `gates` line used to bury every
    family behind one timing blob; grouping violations/waivers by this
    prefix is what lets each family get its own named pass/FAIL stage line
    instead."""
    for i, ch in enumerate(rule):
        if ch.isdigit():
            return rule[:i]
    return rule


# frob:ticket T-0420
def _gates_family_result(family: str, violations: list, waived: list) -> ToolResult:  # noqa: ANN001
    """One named per-family `ToolResult` (`gate:TEST`, `gate:COV`, ...):
    its own diagnostics and its own error/warning/waived count, so a human
    reads `TEST FAIL 2 errors` instead of hunting inside one shared `gates`
    timing blob for which family actually failed (T-0420)."""
    diags = [*_violation_diags(violations), *_waived_diags(waived)]
    n_err = _error_count(violations)
    n_warn = len(violations) - n_err
    summary = (
        f"{n_err} error{'s' if n_err != 1 else ''}, "
        f"{n_warn} warning{'s' if n_warn != 1 else ''}, "
        f"{len(waived)} waived"
    )
    return ToolResult(
        tool=f"gate:{family}",
        exit_code=1 if n_err > 0 else 0,
        diagnostics=diags,
        summary=summary,
    )


# frob:ticket T-0420
def _gates_family_results(violations, waived) -> list[ToolResult]:  # noqa: ANN001
    """Every named per-family stage (T-0420), ordered alphabetically by
    family name for a stable, scannable list -- families present only in
    `waived` (never in a kept violation) still get their own line, since a
    fully-waived family is real signal ("this family found things, all
    discharged"), not silence."""
    families: dict[str, tuple[list, list]] = {}
    for v in violations:
        families.setdefault(_rule_family(v.rule), ([], []))[0].append(v)
    for w in waived:
        families.setdefault(_rule_family(w.rule), ([], []))[1].append(w)
    return [
        _gates_family_result(family, fam_violations, fam_waived)
        for family, (fam_violations, fam_waived) in sorted(families.items())
    ]


# frob:ticket T-0420
def _gate_summary_result(
    violations, report, *, n_err: int, delta: bool, timing: str
) -> ToolResult:  # noqa: ANN001
    """The final `gate-summary` `ToolResult` (T-0420): overall totals plus
    the per-gate timing blob (kept here, not per-family, since timing is
    measured per underlying gate function, not per rule family) -- the one
    line a human reads after scanning the named per-family stages above
    it."""
    summary = _gates_summary(violations, report, n_err=n_err, delta=delta)
    return ToolResult(
        tool="gate-summary",
        exit_code=1 if n_err > 0 else 0,
        summary=f"{summary}  [{timing}]",
    )


# frob:ticket T-1351
# frob:ticket T-1928
# frob:tests tests/unit/test_check.py::TestScopeDisclosure.test_only_names_the_gate_families_it_did_not_run  # noqa: E501
# frob:tests tests/unit/test_check.py::TestScopeDisclosure.test_ticket_flag_notes_which_families_are_actually_diff_scoped  # noqa: E501
# frob:tests \
# tests/unit/test_check.py::TestScopeDisclosure.test_full_run_discloses_fmt_scope
# frob:tests \
# tests/unit/test_check.py::TestScopeDisclosure.test_no_disclosure_when_fmt_did_not_run
def _scope_disclosure_note(
    *, ticket: str | None, gates: frozenset[str], ran: frozenset[str]
) -> str | None:
    """T-1351 (the T-1293 false-close guard): the one line that must exist
    whenever a scoped `frob check` invocation could otherwise be misread as
    "the whole package is clean".

    Two independent ways a clean-looking run under-covers what it looks
    like it covers (both bit real invocations, T-1293 and T-1337):

    1. `--only <subset>` (`gates`, a proper subset of every gate `frob
       check` knows about) runs ONLY the named gate families -- every
       other family's status is simply unknown this invocation, not clean.
       T-1337 landed 2 new INV006 errors specifically because it verified
       with `--only opaque --ticket T-1337`: gate:INV was never run, so
       its errors were structurally invisible, not absent.
    2. `--ticket T-XXXX` does NOT filter most gate families' violation
       counts to the ticket's scope -- verified directly (T-1351): `gate:
       TEST`/`gate:COV`'s COV001 etc. report the exact same repo-wide
       counts with or without `--ticket`. Only `gate:SCOPE`/`gate:PREWORK`
       and the diff-driven checks folded into `gate:COV` (COV002/TODO001)
       and `gate:FMT`/`gate:AFFECT` are actually scoped to the ticket's
       touched set. T-1293 read a scoped-looking "0 findings" as "my
       package is clean" when the number shown was, in fact, repo-wide --
       the opposite failure from the one `--only` causes, but the same
       "a number that does not mean what the reader thinks it means"
       shape (docs/guides/agent-playbook.md's "catalogued is not
       enforced" lesson, generalized here).

    3. `gate:FMT` (FMT001) is diff-scoped UNCONDITIONALLY, with or without
       `--ticket` -- it only ever inspects `frob:` directive comment lines
       the current uncommitted diff touches (`fmt_gate`,
       `src/frob/gates/_todo_fmt.py`). On a clean tree with no diff (the
       common case for a bare `frob check` on `main`) it examines zero
       files and reports 0 errors in ~0s by construction -- that 0 is
       correct-but-misleading: it says nothing about whether `ruff format
       --check .` or `frob fmt --check` (both unscoped, repo-wide, and
       checking DIFFERENT things -- ruff's own code-style formatting vs.
       `frob:` directive-comment line-wrapping) would report drift
       (T-1928 measured 77 and 265 respectively against a "clean" gate:FMT
       0 on the same tree). This disclosure fires whenever `fmt` is in
       `ran` at all -- including a full, unscoped, unfiltered run -- since
       the diff-scoping is a property of the gate itself, not of `--only`/
       `--ticket` narrowing it further.

    Returns `None` when no condition applies -- there is nothing to
    disclose."""
    from frob.gates import _ALL_GATES

    lines: list[str] = []
    not_run = sorted(_ALL_GATES - ran) if gates else []
    if not_run:
        lines.append(
            f"NOTE: --only ran {len(ran)}/{len(_ALL_GATES)} gate famil"
            f"(ies); NOT run this invocation (status unknown, not clean): "
            f"{', '.join(not_run)}"
        )
    if ticket is not None:
        lines.append(
            f"NOTE: --ticket {ticket} scopes ONLY gate:SCOPE/gate:PREWORK "
            "and the diff-driven checks inside gate:COV (COV002/TODO001) "
            "and gate:FMT/gate:AFFECT to this ticket's touched set -- "
            "every OTHER gate family's counts above are REPO-WIDE, not "
            "filtered to this ticket; a clean count there is not proof "
            "this ticket's own package is clean."
        )
    if "fmt" in ran:
        lines.append(
            "NOTE: gate:FMT (FMT001) only examines frob: directive-comment "
            "lines touched by the CURRENT DIFF -- it never scans the whole "
            "tree and is not a general formatter check. A clean gate:FMT "
            "does NOT mean the repo is `ruff format`-clean or `frob fmt`-"
            "canonical repo-wide; those are separate, unscoped checks "
            "(`ruff format --check .`, `frob fmt --check`) each covering a "
            "different concern (Python code style vs. frob: directive "
            "line-wrapping) -- run them directly to measure repo-wide "
            "drift."
        )
    return "\n".join(lines) if lines else None


# frob:ticket T-0420
# frob:tests tests/unit/test_check.py::TestSummarySeverityHonesty.test_warn_only_gate_summary_splits_errors_and_warnings  # noqa: E501
# frob:tests tests/unit/test_check.py::TestRunGatesDelta.test_no_baseline_falls_back_to_full_set_with_warning  # noqa: E501
# frob:tests tests/system/test_cli_check.py::TestCheckStampBaselineAndDelta.test_delta_reports_only_new_violation  # noqa: E501
def _gates_success_result(
    report,  # noqa: ANN001
    *,
    root: Path,
    delta: bool,
    ticket: str | None = None,
    gates: frozenset[str] = frozenset(),
) -> list[ToolResult]:
    """`run_gates`'s report rendered as `frob check` stages (T-0420):
    one named `gate:<FAMILY>` `ToolResult` per rule family present, plus a
    trailing `gate-summary` totals+timing line -- replacing the single
    monolithic `gates` line that used to bury every family (and its own
    pass/FAIL signal) behind one combined count and timing blob.
    Delta-filtering (T-0095) still applies before grouping, so `--delta`
    narrows both the per-family lines and the summary identically.

    T-1351: also appends a `gate:scope-note` stage (never blocking, never
    itself a violation) whenever `--only`/`--ticket` narrowed this run in
    a way that could be misread as a full clean pass -- see
    `_scope_disclosure_note`."""
    violations, delta_note = (
        _apply_delta(root, report.violations)
        if delta
        else (
            report.violations,
            None,
        )
    )
    n_err = _error_count(violations)
    results = _gates_family_results(violations, report.waived)
    if delta_note is not None:
        results.append(
            ToolResult(
                tool="gate:delta",
                exit_code=0,
                diagnostics=[Diagnostic(severity="warning", message=delta_note)],
                summary=delta_note,
            )
        )
    scope_note = _scope_disclosure_note(
        ticket=ticket, gates=gates, ran=frozenset(report.stats.timing_s)
    )
    if scope_note is not None:
        results.append(
            ToolResult(
                tool="gate:scope-note",
                exit_code=0,
                diagnostics=[Diagnostic(severity="warning", message=scope_note)],
                summary=scope_note,
            )
        )
    results.append(
        _gate_summary_result(
            violations,
            report,
            n_err=n_err,
            delta=delta,
            timing=_timing_str(report.stats),
        )
    )
    return results


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

    try:
        result = verify_bindings(scan)
        diags = _bind_mismatch_diagnostics(result)
    except Exception as exc:
        return tool_crash_result("frob-bind", exc)
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
    for path in iter_files(scan, suffix=".py"):
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
    init_files = sorted(
        p for p in iter_files(scan, suffix=".py") if p.name == "__init__.py"
    )
    out: list[ToolResult] = []
    for init_file in init_files:
        result = _exports_for_package(init_file, scan)
        if result is not None:
            out.append(result)
    return out

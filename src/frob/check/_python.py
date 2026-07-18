"""Per-tool runners for the Python `frob check` pipeline (docs/commands/check.md).

Each `_run_*` helper shells out to one tool (ruff, ty, the frob native
analyses, the gates stage) and normalises its output into a `ToolResult`.
They are private helpers of `frob.check`; `run_check` composes them in
parallel.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from frob.process.parsers.common import Diagnostic, Severity, ToolResult

if TYPE_CHECKING:
    from frob.gates import Violation


def _run_ruff(root: Path, extra_args: list[str] | None) -> list[ToolResult]:
    """ruff lint + ruff format --check, as two ToolResults."""
    from frob.process.parsers import parse_ruff_json

    out: list[ToolResult] = []
    proc = subprocess.run(
        ["ruff", "check", "--output-format", "json", str(root)],
        capture_output=True,
        text=True,
    )
    r = parse_ruff_json(proc.stdout, exit_code=proc.returncode)
    r.tool = "ruff-check"
    out.append(r)
    out.append(_ruff_format_result(root))
    return out


def _ruff_format_result(root: Path) -> ToolResult:
    """The `ruff format --check` outcome as one ToolResult."""
    proc = subprocess.run(
        ["ruff", "format", "--check", str(root)],
        capture_output=True,
        text=True,
    )
    if not proc.returncode:
        return ToolResult(
            tool="ruff-format", exit_code=0, summary="all files formatted"
        )
    msg = (proc.stdout + proc.stderr).strip()
    reformat = [ln for ln in msg.splitlines() if "Would reformat" in ln]
    n = len(reformat)
    diags = [
        Diagnostic(
            file=ln.replace("Would reformat ", "").strip(),
            severity="warning",
            message="needs formatting",
        )
        for ln in reformat
    ]
    return ToolResult(
        tool="ruff-format",
        exit_code=proc.returncode,
        diagnostics=diags,
        summary=f"{n} file{'s' if n != 1 else ''} would be reformatted",
    )


def _run_ty(root: Path) -> ToolResult | None:
    """ty type-check, honouring a local ty.toml's extra-paths."""
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
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        return None
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
    n = len(cycles)
    return ToolResult(
        tool="frob-cycle",
        exit_code=1 if any(d.severity == "error" for d in diags) else 0,
        diagnostics=diags,
        summary=f"{n} cycle{'s' if n != 1 else ''} found" if cycles else "no cycles",
    )


def _run_dup(root: Path) -> ToolResult:
    """Structural duplicate-block detection."""
    from frob.dup import find_duplicates

    result = find_duplicates(root if root.is_dir() else root.parent)
    diags: list[Diagnostic] = []
    for g in result.groups:
        locs = ", ".join(f"{f.file}:{f.start_line}" for f in g.fragments)
        diags.append(
            Diagnostic(
                severity="warning",
                code=g.clone_type,
                message=f"{g.size_lines}-line duplicate block at {locs}",
            )
        )
    n = len(result.groups)
    return ToolResult(
        tool="frob-dup",
        exit_code=0,
        diagnostics=diags,
        summary=f"{n} duplicate group{'s' if n != 1 else ''}" if n else "no duplicates",
    )


def _arch_summary(suggestions) -> str:  # noqa: ANN001
    """`"N warnings, M suggestions"` (or "no issues") over arch suggestions."""
    n_warn = sum(1 for s in suggestions if s.severity == "warning")
    n_sugg = len(suggestions) - n_warn
    parts = []
    if n_warn:
        parts.append(f"{n_warn} warning{'s' if n_warn != 1 else ''}")
    if n_sugg:
        parts.append(f"{n_sugg} suggestion{'s' if n_sugg != 1 else ''}")
    return ", ".join(parts) if parts else "no issues"


def _run_arch(root: Path) -> ToolResult:
    """frob's architectural analysis (long functions, god classes, etc.)."""
    from frob.arch import analyze_project

    result = analyze_project(root if root.is_dir() else root.parent)
    sev_map: dict[str, Severity] = {
        "warning": "warning",
        "suggestion": "note",
        "info": "info",
    }
    diags = [
        Diagnostic(
            file=s.file,
            line=s.line,
            severity=sev_map.get(s.severity, "note"),
            code=s.category,
            message=s.message,
        )
        for s in result.suggestions
    ]
    return ToolResult(
        tool="frob-arch",
        exit_code=0,
        diagnostics=diags,
        summary=_arch_summary(result.suggestions),
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
        err = result.danger_err
        if err is GateError.QueueUnavailable:
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
    report = result.danger_ok
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
    summary = f"{len(violations)} violation(s), {len(report.waived)} waived"
    if delta:
        summary = f"{len(violations)}/{len(report.violations)} new  " + summary
    return ToolResult(
        tool="gates",
        exit_code=1 if n_err > 0 else 0,
        diagnostics=diags,
        summary=f"{summary}  [{_timing_str(report.stats)}]",
    )


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
    has_bind = False
    for path in scan.rglob("*.py"):
        try:
            if b"# BIND" in path.read_bytes():
                has_bind = True
                break
        except Exception:
            pass
    if not has_bind:
        return None

    try:
        from frob.bind import (
            verify_bindings,  # type: ignore[import,attr-defined]  # ty: ignore[unresolved-import]
        )
    except ImportError:
        return None

    result = verify_bindings(scan)
    diags = [
        Diagnostic(file=m.file, line=m.line, severity="error", message=m.message)
        for m in getattr(result, "mismatches", [])
    ]
    n = len(diags)
    return ToolResult(
        tool="frob-bind",
        exit_code=1 if diags else 0,
        diagnostics=diags,
        summary=f"{n} binding mismatch{'es' if n != 1 else ''}"
        if diags
        else "all bindings verified",
    )


def _missing_exports(init_src: str, modules) -> list[str]:  # noqa: ANN001
    """Public `module.symbol` names not referenced in the package `__init__.py`."""
    missing: list[str] = []
    for mod in modules:
        for sym in mod.symbols:
            if sym not in init_src:
                missing.append(f"{mod.module}.{sym}")
    return missing


def _exports_for_package(init_file: Path, scan: Path) -> ToolResult | None:
    """The un-exported-public-symbol ToolResult for one package, or None."""
    from frob.exports import exports_package

    pkg_dir = init_file.parent
    if any(
        p.startswith(".") or p in {"__pycache__", ".venv", "build", "dist"}
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

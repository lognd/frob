from __future__ import annotations

import subprocess
from pathlib import Path

from pydantic import BaseModel

from frob.process.parsers.common import Diagnostic, Severity, ToolResult


class CheckResult(BaseModel):
    model_config = {}

    path: str
    results: list[ToolResult]

    @property
    def total_errors(self) -> int:
        return sum(r.error_count for r in self.results)

    @property
    def total_warnings(self) -> int:
        return sum(r.warning_count for r in self.results)

    def as_text(self) -> str:
        lines: list[str] = []
        err = self.total_errors
        warn = self.total_warnings
        status = "FAIL" if err > 0 else ("WARN" if warn > 0 else "PASS")
        lines.append(
            f"frob check {self.path}  [{status}]  {err} error{'s' if err != 1 else ''}  "
            f"{warn} warning{'s' if warn != 1 else ''}"
        )
        lines.append("")

        all_errors = [
            (r.tool, d)
            for r in self.results
            for d in r.diagnostics
            if d.severity == "error"
        ]
        if all_errors:
            lines.append("## Errors")
            for tool, d in all_errors:
                lines.append(f"  [{tool}] {d.as_text()}")
            lines.append("")

        all_warnings = [
            (r.tool, d)
            for r in self.results
            for d in r.diagnostics
            if d.severity == "warning"
        ]
        if all_warnings:
            lines.append("## Warnings")
            for tool, d in all_warnings:
                lines.append(f"  [{tool}] {d.as_text()}")
            lines.append("")

        all_notes = [
            (r.tool, d)
            for r in self.results
            for d in r.diagnostics
            if d.severity not in ("error", "warning")
        ]
        if all_notes:
            lines.append("## Notes / suggestions")
            for tool, d in all_notes:
                lines.append(f"  [{tool}] {d.as_text()}")
            lines.append("")

        lines.append("## Tool summary")
        for r in self.results:
            icon = "pass" if r.passed and r.error_count == 0 else "FAIL"
            lines.append(f"  {icon}  {r.tool:<22}  {r.summary}")

        return "\n".join(lines)

    def as_json(self) -> str:
        return self.model_dump_json(indent=2)


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
    pycharm_path: Path | None = None,
    ruff_args: list[str] | None = None,
) -> CheckResult:
    results: list[ToolResult] = []

    if not skip_ruff:
        results.extend(_run_ruff(root, ruff_args))

    if not skip_ty:
        r = _run_ty(root)
        if r is not None:
            results.append(r)

    if not skip_cycle:
        results.append(_run_cycle(root))

    if not skip_dup:
        results.append(_run_dup(root))

    if not skip_arch:
        results.append(_run_arch(root))

    if not skip_bind:
        r = _run_bind(root)
        if r is not None:
            results.append(r)

    if not skip_exports:
        results.extend(_run_exports(root))

    if pycharm_path is not None:
        r = _run_pycharm(root, pycharm_path)
        if r is not None:
            results.append(r)

    return CheckResult(path=str(root), results=results)


def _run_ruff(root: Path, extra_args: list[str] | None) -> list[ToolResult]:
    from frob.process.parsers import parse_ruff

    out: list[ToolResult] = []

    # ruff check (lint)
    proc = subprocess.run(
        ["ruff", "check", "--output-format", "text", str(root)],
        capture_output=True,
        text=True,
    )
    r = parse_ruff(proc.stdout + proc.stderr, exit_code=proc.returncode)
    r.tool = "ruff-check"
    out.append(r)

    # ruff format --check (formatting)
    proc2 = subprocess.run(
        ["ruff", "format", "--check", str(root)],
        capture_output=True,
        text=True,
    )
    if proc2.returncode != 0:
        msg = (proc2.stdout + proc2.stderr).strip()
        files = [
            line.strip()
            for line in msg.splitlines()
            if line.strip() and not line.startswith("Would reformat")
        ]
        # Count "Would reformat" lines
        reformat = [l for l in msg.splitlines() if "Would reformat" in l]
        n = len(reformat)
        diags = [
            Diagnostic(file=l.replace("Would reformat ", "").strip(), severity="warning", message="needs formatting")
            for l in reformat
        ]
        out.append(ToolResult(
            tool="ruff-format",
            exit_code=proc2.returncode,
            diagnostics=diags,
            summary=f"{n} file{'s' if n != 1 else ''} would be reformatted",
        ))
    else:
        out.append(ToolResult(tool="ruff-format", exit_code=0, summary="all files formatted"))

    return out


def _run_ty(root: Path) -> ToolResult | None:
    from frob.process.parsers import parse_ty

    try:
        proc = subprocess.run(
            ["ty", "check", str(root)],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    r = parse_ty(proc.stdout + proc.stderr, exit_code=proc.returncode)
    r.tool = "ty"
    return r


def _run_cycle(root: Path) -> ToolResult:
    from frob.ast.common import ModuleTag
    from frob.ast import python as _py
    from frob.cycle.graph import DependencyGraph, find_cycles

    graph = DependencyGraph()
    scan_root = root if root.is_dir() else root.parent
    for path in scan_root.rglob("*.py"):
        if any(p in {"__pycache__", ".venv", "build", "dist"} for p in path.parts):
            continue
        try:
            rel = str(path.relative_to(scan_root))
            graph.add_node(rel)
            for imp in _py.get_imports(ModuleTag(rel), scan_root):
                graph.add_edge(rel, imp)
        except Exception:
            pass

    cycles = find_cycles(graph)
    diags: list[Diagnostic] = []
    for cycle in cycles:
        nodes = " -> ".join(cycle + [cycle[0]])
        diags.append(Diagnostic(severity="error", message=f"import cycle: {nodes}"))

    n = len(cycles)
    return ToolResult(
        tool="frob-cycle",
        exit_code=1 if cycles else 0,
        diagnostics=diags,
        summary=f"{n} cycle{'s' if n != 1 else ''} found" if cycles else "no cycles",
    )


def _run_dup(root: Path) -> ToolResult:
    from frob.dup import find_duplicates

    result = find_duplicates(root if root.is_dir() else root.parent)
    diags: list[Diagnostic] = []
    for g in result.groups:
        locs = ", ".join(f"{f.file}:{f.start_line}" for f in g.fragments)
        diags.append(Diagnostic(
            severity="warning",
            code=g.clone_type,
            message=f"{g.size_lines}-line duplicate block at {locs}",
        ))
    n = len(result.groups)
    return ToolResult(
        tool="frob-dup",
        exit_code=0,
        diagnostics=diags,
        summary=f"{n} duplicate group{'s' if n != 1 else ''}" if n else "no duplicates",
    )


def _run_arch(root: Path) -> ToolResult:
    from frob.arch import analyze_project

    result = analyze_project(root if root.is_dir() else root.parent)
    sev_map: dict[str, Severity] = {"warning": "warning", "suggestion": "note", "info": "info"}
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
    n_warn = sum(1 for s in result.suggestions if s.severity == "warning")
    n_sugg = len(result.suggestions) - n_warn
    parts = []
    if n_warn:
        parts.append(f"{n_warn} warning{'s' if n_warn != 1 else ''}")
    if n_sugg:
        parts.append(f"{n_sugg} suggestion{'s' if n_sugg != 1 else ''}")
    return ToolResult(
        tool="frob-arch",
        exit_code=0,
        diagnostics=diags,
        summary=", ".join(parts) if parts else "no issues",
    )


def _run_bind(root: Path) -> ToolResult | None:
    # Only meaningful if there are BIND comment markers in the tree
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
        from frob.bind import verify_bindings  # type: ignore[import]
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
        summary=f"{n} binding mismatch{'es' if n != 1 else ''}" if diags else "all bindings verified",
    )


def _run_exports(root: Path) -> list[ToolResult]:
    from frob.exports import exports_package

    scan = root if root.is_dir() else root.parent
    out: list[ToolResult] = []

    # Find Python packages (dirs with __init__.py) that have submodules
    for init_file in sorted(scan.rglob("__init__.py")):
        pkg_dir = init_file.parent
        # Skip __pycache__, .venv etc.
        if any(p.startswith(".") or p in {"__pycache__", ".venv", "build", "dist"}
               for p in pkg_dir.parts):
            continue
        # Only check packages that have sibling .py files
        sibs = [f for f in pkg_dir.glob("*.py") if f.name != "__init__.py"]
        if not sibs:
            continue

        result = exports_package(pkg_dir, include_private=False)
        if result.is_err:
            continue
        er = result.danger_ok
        if not er.modules:
            continue

        # Check which symbols are missing from __init__.py
        try:
            init_src = init_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        missing: list[str] = []
        for mod in er.modules:
            for sym in mod.symbols:
                if sym not in init_src:
                    missing.append(f"{mod.module}.{sym}")

        if missing:
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
            out.append(ToolResult(
                tool=f"frob-exports({pkg_name})",
                exit_code=0,
                diagnostics=diags,
                summary=f"{n} public symbol{'s' if n != 1 else ''} missing from __init__.py",
            ))

    return out


def _run_pycharm(root: Path, pycharm_path: Path) -> ToolResult | None:
    import tempfile

    from frob.process.parsers import parse_pycharm_dir

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        try:
            subprocess.run(
                [str(pycharm_path), str(root), tmp_path, "-format", "XML"],
                capture_output=True,
                timeout=120,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        result = parse_pycharm_dir(tmp_path)
        result.tool = "pycharm"
        return result

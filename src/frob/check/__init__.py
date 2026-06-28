from __future__ import annotations

import concurrent.futures
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
        errs = f"{err} error{'s' if err != 1 else ''}"
        warns = f"{warn} warning{'s' if warn != 1 else ''}"
        lines.append(f"frob check {self.path}  [{status}]  {errs}  {warns}")
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
    from typing import Callable

    tasks: list[Callable[[], ToolResult | list[ToolResult] | None]] = []

    if not skip_ruff:
        tasks.append(lambda: _run_ruff(root, ruff_args))
    if not skip_ty:
        tasks.append(lambda: _run_ty(root))
    if not skip_cycle:
        tasks.append(lambda: _run_cycle(root))
    if not skip_dup:
        tasks.append(lambda: _run_dup(root))
    if not skip_arch:
        tasks.append(lambda: _run_arch(root))
    if not skip_bind:
        tasks.append(lambda: _run_bind(root))
    if not skip_exports:
        tasks.append(lambda: _run_exports(root))
    if pycharm_path is not None:
        _pycharm_path = pycharm_path
        tasks.append(lambda: _run_pycharm(root, _pycharm_path))

    results: list[ToolResult] = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(fn) for fn in tasks]
        for future in futures:
            val = future.result()
            if val is None:
                pass
            elif isinstance(val, list):
                results.extend(val)
            else:
                results.append(val)

    return CheckResult(path=str(root), results=results)


def _run_ruff(root: Path, extra_args: list[str] | None) -> list[ToolResult]:
    from frob.process.parsers import parse_ruff_json

    out: list[ToolResult] = []

    # ruff check (lint)
    proc = subprocess.run(
        ["ruff", "check", "--output-format", "json", str(root)],
        capture_output=True,
        text=True,
    )
    r = parse_ruff_json(proc.stdout, exit_code=proc.returncode)
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
        [
            line.strip()
            for line in msg.splitlines()
            if line.strip() and not line.startswith("Would reformat")
        ]
        # Count "Would reformat" lines
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
        out.append(
            ToolResult(
                tool="ruff-format",
                exit_code=proc2.returncode,
                diagnostics=diags,
                summary=f"{n} file{'s' if n != 1 else ''} would be reformatted",
            )
        )
    else:
        out.append(
            ToolResult(tool="ruff-format", exit_code=0, summary="all files formatted")
        )

    return out


def _run_ty(root: Path) -> ToolResult | None:
    from frob.process.parsers import parse_ty

    scan = root if root.is_dir() else root.parent
    cmd = ["ty", "check", str(root)]

    # If a ty.toml exists in the root, resolve its extra-paths and pass them
    # explicitly so ty can find them regardless of the working directory.
    ty_cfg = scan / "ty.toml"
    if ty_cfg.exists():
        try:
            from frob._compat import toml

            with ty_cfg.open("rb") as f:
                cfg = toml.load(f)
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


def _run_cycle(root: Path) -> ToolResult:
    from frob.ast import python as _py
    from frob.ast.common import ModuleTag
    from frob.cycle.graph import DependencyGraph, find_cycles

    graph = DependencyGraph()
    scan_root = root if root.is_dir() else root.parent
    resolved_scan = scan_root.resolve()
    for path in scan_root.rglob("*.py"):
        try:
            rel_parts = path.resolve().relative_to(resolved_scan).parts
        except ValueError:
            rel_parts = path.parts
        _skip = {"__pycache__", ".venv", "build", "dist"}
        if any(p in _skip or p.startswith(".") for p in rel_parts):
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
        n_nodes = len(cycle)
        # 2-node mutual imports are often TYPE_CHECKING patterns -- info only
        # 3-5 nodes is a minor cycle -- warning
        # 6+ is a structural problem -- error
        if n_nodes <= 2:
            sev: Severity = "info"
        elif n_nodes <= 5:
            sev = "warning"
        else:
            sev = "error"
        lines = (
            ["import cycle:"] + [f"  {node}" for node in cycle] + [f"  -> {cycle[0]}"]
        )
        diags.append(Diagnostic(severity=sev, message="\n".join(lines)))

    n = len(cycles)
    return ToolResult(
        tool="frob-cycle",
        exit_code=1 if any(d.severity == "error" for d in diags) else 0,
        diagnostics=diags,
        summary=f"{n} cycle{'s' if n != 1 else ''} found" if cycles else "no cycles",
    )


def _run_dup(root: Path) -> ToolResult:
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


def _run_arch(root: Path) -> ToolResult:
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


def _run_exports(root: Path) -> list[ToolResult]:
    from frob.exports import exports_package

    scan = root if root.is_dir() else root.parent
    out: list[ToolResult] = []

    # Find Python packages (dirs with __init__.py) that have submodules
    for init_file in sorted(scan.rglob("__init__.py")):
        pkg_dir = init_file.parent
        # Skip __pycache__, .venv etc.
        if any(
            p.startswith(".") or p in {"__pycache__", ".venv", "build", "dist"}
            for p in pkg_dir.parts
        ):
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
            out.append(
                ToolResult(
                    tool=f"frob-exports({pkg_name})",
                    exit_code=0,
                    diagnostics=diags,
                    summary=f"{n} public symbol{'s' if n != 1 else ''} missing from"
                    " __init__.py",
                )
            )

    return out


def _run_pycharm(root: Path, pycharm_path: Path | None) -> ToolResult | None:
    import tempfile

    from frob.process.parsers import parse_pycharm_dir

    binary = pycharm_path or _find_pycharm()
    if binary is None:
        return None

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        try:
            subprocess.run(
                [str(binary), str(root), str(tmp_path), "-format", "XML"],
                capture_output=True,
                timeout=180,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        result = parse_pycharm_dir(tmp_path)
        result.tool = "pycharm"
        return result


def _find_pycharm() -> Path | None:
    """Auto-locate JetBrains inspect script on Windows and Linux."""
    import os
    import platform

    system = platform.system()

    if system == "Windows":
        # Toolbox: %LOCALAPPDATA%\JetBrains\Toolbox\apps\PyCharm-P\ch-0\<ver>\bin
        base = (
            Path(os.environ.get("LOCALAPPDATA", "")) / "JetBrains" / "Toolbox" / "apps"
        )
        for app_dir in ("PyCharm-P", "PyCharm-C", "PyCharm"):
            p = base / app_dir / "ch-0"
            if p.exists():
                versions = sorted(p.iterdir(), reverse=True)
                for v in versions:
                    candidate = v / "bin" / "inspect.bat"
                    if candidate.exists():
                        return candidate
        # Direct install
        prog = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
        for name in (
            "JetBrains/PyCharm Professional Edition",
            "JetBrains/PyCharm Community Edition",
            "JetBrains/PyCharm",
        ):
            candidate = prog / name / "bin" / "inspect.bat"
            if candidate.exists():
                return candidate
    else:
        # Linux Toolbox: ~/.local/share/JetBrains/Toolbox/apps/PyCharm-P/ch-0/<ver>/bin
        home = Path.home()
        for base in (
            home / ".local" / "share" / "JetBrains" / "Toolbox" / "apps",
            Path("/opt/jetbrains"),
        ):
            for app_dir in ("PyCharm-P", "PyCharm-C", "PyCharm"):
                p = base / app_dir / "ch-0"
                if not p.exists():
                    p = base / app_dir
                if p.exists():
                    versions = sorted(p.iterdir(), reverse=True)
                    for v in versions:
                        for script in ("bin/inspect.sh", "bin/pycharm.sh"):
                            candidate = v / script
                            if candidate.exists():
                                return candidate
        # Snap / system installs
        for candidate in (
            Path("/snap/pycharm-professional/current/bin/inspect.sh"),
            Path("/snap/pycharm-community/current/bin/inspect.sh"),
            Path("/usr/local/bin/pycharm.sh"),
        ):
            if candidate.exists():
                return candidate

    return None


# ---------------------------------------------------------------------------
# C/C++ checks
# ---------------------------------------------------------------------------


def run_check_cpp(
    root: Path,
    *,
    build_dir: Path | None = None,
    skip_build: bool = False,
    skip_clang_tidy: bool = False,
    skip_clang_format: bool = False,
    skip_tests: bool = False,
    valgrind: bool = False,
    pycharm_path: Path | None = None,
) -> CheckResult:
    """Quality gate for CMake C/C++ projects."""
    from typing import Callable

    results: list[ToolResult] = []
    bdir = build_dir or (root / "build")

    if not skip_build:
        r = _run_cmake_build(root, bdir)
        results.append(r)
        if r.exit_code != 0:
            skip_tests = True

    # clang-tidy, clang-format, and ctest are independent after build
    post_build: list[Callable[[], ToolResult | None]] = []
    if not skip_clang_tidy:
        post_build.append(lambda: _run_clang_tidy_cmake(root, bdir))
    if not skip_clang_format:
        post_build.append(lambda: _run_clang_format(root))
    if not skip_tests:
        _valgrind = valgrind
        post_build.append(lambda: _run_ctest(bdir, valgrind=_valgrind))
    if pycharm_path is not None:
        _pycharm_path = pycharm_path
        post_build.append(lambda: _run_pycharm(root, _pycharm_path))

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(fn) for fn in post_build]
        for future in futures:
            r = future.result()
            if r is not None:
                results.append(r)

    return CheckResult(path=str(root), results=results)


def _run_cmake_build(root: Path, build_dir: Path) -> ToolResult:
    from frob.process.parsers import parse_clang

    build_dir.mkdir(parents=True, exist_ok=True)
    # Configure
    cfg = subprocess.run(
        ["cmake", str(root), "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"],
        cwd=str(build_dir),
        capture_output=True,
        text=True,
    )
    if cfg.returncode != 0:
        return ToolResult(
            tool="cmake-configure",
            exit_code=cfg.returncode,
            diagnostics=[
                Diagnostic(severity="error", message=ln.strip())
                for ln in (cfg.stderr or cfg.stdout).splitlines()
                if ln.strip()
            ],
            summary="cmake configure failed",
        )
    # Build
    proc = subprocess.run(
        ["cmake", "--build", ".", "--", "-j4"],
        cwd=str(build_dir),
        capture_output=True,
        text=True,
    )
    r = parse_clang(
        proc.stdout + proc.stderr, exit_code=proc.returncode, tool="cmake-build"
    )
    r.tool = "cmake-build"
    if not r.summary or r.summary == "no issues":
        r.summary = "build succeeded" if proc.returncode == 0 else "build failed"
    return r


def _run_clang_tidy_cmake(root: Path, build_dir: Path) -> ToolResult | None:
    from frob.process.parsers import parse_clang_tidy

    # Prefer compile_commands.json in build_dir
    compile_commands = build_dir / "compile_commands.json"
    if not compile_commands.exists():
        compile_commands = root / "compile_commands.json"
    if not compile_commands.exists():
        return None

    src_files = (
        list(root.rglob("*.cpp")) + list(root.rglob("*.cc")) + list(root.rglob("*.c"))
    )
    src_files = [
        f
        for f in src_files
        if not any(p in {"build", ".venv", "third_party", "extern"} for p in f.parts)
    ]
    if not src_files:
        return None

    proc = subprocess.run(
        ["clang-tidy", f"-p={build_dir}", "--quiet"] + [str(f) for f in src_files[:50]],
        capture_output=True,
        text=True,
    )
    r = parse_clang_tidy(proc.stdout + proc.stderr, exit_code=proc.returncode)
    return r


def _run_clang_format(root: Path) -> ToolResult | None:
    src_files = (
        list(root.rglob("*.cpp"))
        + list(root.rglob("*.cc"))
        + list(root.rglob("*.c"))
        + list(root.rglob("*.h"))
        + list(root.rglob("*.hpp"))
    )
    src_files = [
        f
        for f in src_files
        if not any(p in {"build", ".venv", "third_party", "extern"} for p in f.parts)
    ]
    if not src_files:
        return None

    proc = subprocess.run(
        ["clang-format", "--dry-run", "--Werror"] + [str(f) for f in src_files],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return ToolResult(
            tool="clang-format", exit_code=0, summary="all files formatted"
        )

    needs_format = [
        ln
        for ln in (proc.stderr or proc.stdout).splitlines()
        if "warning:" in ln or "error:" in ln
    ]
    n = len(needs_format)
    diags = [Diagnostic(severity="warning", message=ln.strip()) for ln in needs_format]
    return ToolResult(
        tool="clang-format",
        exit_code=proc.returncode,
        diagnostics=diags,
        summary=f"{n} file{'s' if n != 1 else ''} need formatting",
    )


def _run_ctest(build_dir: Path, *, valgrind: bool = False) -> ToolResult | None:
    if not build_dir.exists():
        return None

    if valgrind:
        proc = subprocess.run(
            [
                "ctest",
                "--test-dir",
                str(build_dir),
                "--output-on-failure",
                "-T",
                "memcheck",
                "--output-junit",
                "results.xml",
            ],
            capture_output=True,
            text=True,
            cwd=str(build_dir),
        )
    else:
        proc = subprocess.run(
            [
                "ctest",
                "--test-dir",
                str(build_dir),
                "--output-on-failure",
                "--output-junit",
                "results.xml",
            ],
            capture_output=True,
            text=True,
            cwd=str(build_dir),
        )

    junit_file = build_dir / "results.xml"
    if junit_file.exists():
        from frob.process.parsers import parse_junit_xml

        r = parse_junit_xml(junit_file.read_text(), tool="ctest")
        r.tool = "ctest"
        return r

    # Fall back to text parsing
    from frob.process.parsers import parse_clang

    r = parse_clang(proc.stdout + proc.stderr, exit_code=proc.returncode, tool="ctest")
    r.tool = "ctest"
    if not r.diagnostics:
        r.summary = "tests passed" if proc.returncode == 0 else "tests failed"
    return r


# ---------------------------------------------------------------------------
# Rust checks
# ---------------------------------------------------------------------------


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


def _run_cargo(
    subcmd: str, root: Path, extra: list[str] | None = None
) -> ToolResult | None:
    from frob.process.parsers import parse_cargo

    try:
        proc = subprocess.run(
            ["cargo", subcmd, "--message-format", "json"] + (extra or []),
            capture_output=True,
            text=True,
            cwd=str(root),
        )
    except FileNotFoundError:
        return None
    r = parse_cargo(
        proc.stdout + proc.stderr, exit_code=proc.returncode, tool=f"cargo-{subcmd}"
    )
    return r


def _run_cargo_fmt_check(root: Path) -> ToolResult | None:
    try:
        proc = subprocess.run(
            ["cargo", "fmt", "--check"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
    except FileNotFoundError:
        return None
    if proc.returncode == 0:
        return ToolResult(tool="cargo-fmt", exit_code=0, summary="all files formatted")
    lines = (proc.stdout + proc.stderr).strip().splitlines()
    diags = [
        Diagnostic(severity="warning", message=ln.strip()) for ln in lines if ln.strip()
    ]
    return ToolResult(
        tool="cargo-fmt",
        exit_code=proc.returncode,
        diagnostics=diags,
        summary=f"{len(diags)} formatting issues",
    )


def _run_cargo_test(root: Path, *, valgrind: bool = False) -> ToolResult | None:
    from frob.process.parsers import parse_cargo, parse_valgrind

    try:
        if valgrind:
            # cargo test --no-run first, then run binary under valgrind
            build_proc = subprocess.run(
                ["cargo", "test", "--no-run", "--message-format", "json"],
                capture_output=True,
                text=True,
                cwd=str(root),
            )
            # Find test binary from JSON output
            binary = _find_test_binary_from_cargo_json(build_proc.stdout)
            if binary:
                proc = subprocess.run(
                    [
                        "valgrind",
                        "--leak-check=full",
                        "--error-exitcode=1",
                        str(binary),
                    ],
                    capture_output=True,
                    text=True,
                    cwd=str(root),
                )
                r = parse_valgrind(proc.stdout + proc.stderr, exit_code=proc.returncode)
                r.tool = "cargo-test(valgrind)"
                return r
        proc = subprocess.run(
            ["cargo", "test"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
    except FileNotFoundError:
        return None
    r = parse_cargo(
        proc.stdout + proc.stderr, exit_code=proc.returncode, tool="cargo-test"
    )
    return r


def _find_test_binary_from_cargo_json(stdout: str) -> Path | None:
    import json

    for line in stdout.splitlines():
        try:
            msg = json.loads(line)
            if msg.get("reason") == "compiler-artifact":
                profile = msg.get("profile", {})
                if profile.get("test"):
                    executables = msg.get("executable")
                    if executables:
                        return Path(executables)
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------
# Auto-detect project type
# ---------------------------------------------------------------------------


def detect_project_type(root: Path) -> str:
    """Returns 'python', 'cpp', 'rust', or 'unknown'."""
    if (root / "Cargo.toml").exists():
        return "rust"
    if (root / "CMakeLists.txt").exists():
        return "cpp"
    if (root / "pyproject.toml").exists() or (root / "setup.py").exists():
        return "python"
    if list(root.glob("*.cpp")) or list(root.glob("*.cc")) or list(root.glob("*.c")):
        return "cpp"
    return "unknown"

"""Per-tool runners for the C/C++ (CMake) and Rust (Cargo) check pipelines.

Private helpers of `frob.check`; `run_check_cpp` and `run_check_rust`
compose them. Each shells out to one tool and normalises to a `ToolResult`.
"""

# frob:waive TEST005 reason="module line coverage 21.9%, debt T-0160"

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.process.parsers.common import Diagnostic, ToolResult, tool_unavailable_result

_CPP_EXCLUDED_DIRS = {"build", ".venv", "third_party", "extern"}


def _collect_sources(root: Path, exts: tuple[str, ...]) -> list[Path]:
    """Source files under `root` with any of `exts`, excluding vendored dirs."""
    files: list[Path] = []
    for ext in exts:
        files.extend(root.rglob(f"*{ext}"))
    return [f for f in files if not any(p in _CPP_EXCLUDED_DIRS for p in f.parts)]


# ---------------------------------------------------------------------------
# C / C++ (CMake)
# ---------------------------------------------------------------------------


# frob:ticket T-0142
def _cmake_configure(root: Path, build_dir: Path) -> ToolResult | None:
    """Run `cmake` configure; a failure ToolResult, or None on success.
    A missing `cmake` binary (T-0142) is a typed failing ToolResult, never
    a raw FileNotFoundError."""
    try:
        cfg = subprocess.run(
            ["cmake", str(root), "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"],
            cwd=str(build_dir),
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return tool_unavailable_result("cmake-configure", "cmake")
    if cfg.returncode == 0:
        return None
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


def _run_cmake_build(root: Path, build_dir: Path) -> ToolResult:
    """Configure then build a CMake project, parsing compiler diagnostics.
    A missing `cmake` binary (T-0142) is a typed failing ToolResult."""
    from frob.process.parsers import parse_clang

    build_dir.mkdir(parents=True, exist_ok=True)
    configure_failure = _cmake_configure(root, build_dir)
    if configure_failure is not None:
        return configure_failure
    try:
        proc = subprocess.run(
            ["cmake", "--build", ".", "--", "-j4"],
            cwd=str(build_dir),
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return tool_unavailable_result("cmake-build", "cmake")
    r = parse_clang(
        proc.stdout + proc.stderr, exit_code=proc.returncode, tool="cmake-build"
    )
    r.tool = "cmake-build"
    if not r.summary or r.summary == "no issues":
        r.summary = "build succeeded" if proc.returncode == 0 else "build failed"
    return r


def _run_clang_tidy_cmake(root: Path, build_dir: Path) -> ToolResult | None:
    """clang-tidy over the project's C/C++ sources using compile_commands.json.
    Returns `None` when there is nothing to check (no compile db / no
    sources) -- that is a real skip, not a missing tool. A missing
    `clang-tidy` binary (T-0142) is a typed failing ToolResult."""
    from frob.process.parsers import parse_clang_tidy

    compile_commands = build_dir / "compile_commands.json"
    if not compile_commands.exists():
        compile_commands = root / "compile_commands.json"
    if not compile_commands.exists():
        return None

    src_files = _collect_sources(root, (".cpp", ".cc", ".c"))
    if not src_files:
        return None

    try:
        proc = subprocess.run(
            ["clang-tidy", f"-p={build_dir}", "--quiet"]
            + [str(f) for f in src_files[:50]],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return tool_unavailable_result("clang-tidy", "clang-tidy")
    return parse_clang_tidy(proc.stdout + proc.stderr, exit_code=proc.returncode)


def _run_clang_format(root: Path) -> ToolResult | None:
    """clang-format dry-run over C/C++ sources; a warning per unformatted
    file. Returns `None` when there are no sources -- a real skip. A
    missing `clang-format` binary (T-0142) is a typed failing ToolResult."""
    src_files = _collect_sources(root, (".cpp", ".cc", ".c", ".h", ".hpp"))
    if not src_files:
        return None

    try:
        proc = subprocess.run(
            ["clang-format", "--dry-run", "--Werror"] + [str(f) for f in src_files],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return tool_unavailable_result("clang-format", "clang-format")
    if not proc.returncode:
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


def _ctest_cmd(build_dir: Path, *, valgrind: bool) -> list[str]:
    """The ctest invocation, with a memcheck stage when `valgrind` is set."""
    cmd = ["ctest", "--test-dir", str(build_dir), "--output-on-failure"]
    if valgrind:
        cmd += ["-T", "memcheck"]
    cmd += ["--output-junit", "results.xml"]
    return cmd


def _run_ctest(build_dir: Path, *, valgrind: bool = False) -> ToolResult | None:
    """Run ctest, preferring the JUnit report and falling back to text
    parsing. Returns `None` when there is no build dir -- a real skip. A
    missing `ctest` binary (T-0142) is a typed failing ToolResult."""
    if not build_dir.exists():
        return None

    try:
        proc = subprocess.run(
            _ctest_cmd(build_dir, valgrind=valgrind),
            capture_output=True,
            text=True,
            cwd=str(build_dir),
        )
    except FileNotFoundError:
        return tool_unavailable_result("ctest", "ctest")

    junit_file = build_dir / "results.xml"
    if junit_file.exists():
        from frob.process.parsers import parse_junit_xml

        r = parse_junit_xml(junit_file.read_text(), tool="ctest")
        r.tool = "ctest"
        return r

    from frob.process.parsers import parse_clang

    r = parse_clang(proc.stdout + proc.stderr, exit_code=proc.returncode, tool="ctest")
    r.tool = "ctest"
    if not r.diagnostics:
        r.summary = "tests passed" if proc.returncode == 0 else "tests failed"
    return r


# ---------------------------------------------------------------------------
# Rust (Cargo)
# ---------------------------------------------------------------------------


def _run_cargo(
    subcmd: str, root: Path, extra: list[str] | None = None
) -> ToolResult | None:
    """Run one `cargo <subcmd>` in JSON message mode. A missing `cargo`
    binary (T-0142) is a typed failing ToolResult, not a silent skip."""
    from frob.process.parsers import parse_cargo

    try:
        proc = subprocess.run(
            ["cargo", subcmd, "--message-format", "json"] + (extra or []),
            capture_output=True,
            text=True,
            cwd=str(root),
        )
    except FileNotFoundError:
        return tool_unavailable_result(f"cargo-{subcmd}", "cargo")
    return parse_cargo(
        proc.stdout + proc.stderr, exit_code=proc.returncode, tool=f"cargo-{subcmd}"
    )


def _run_cargo_fmt_check(root: Path) -> ToolResult | None:
    """`cargo fmt --check`, a warning per offending line. A missing
    `cargo` binary (T-0142) is a typed failing ToolResult."""
    try:
        proc = subprocess.run(
            ["cargo", "fmt", "--check"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
    except FileNotFoundError:
        return tool_unavailable_result("cargo-fmt", "cargo")
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


def _find_test_binary_from_cargo_json(stdout: str) -> Path | None:
    """The first test executable path in `cargo test --no-run` JSON output."""
    import json

    for line in stdout.splitlines():
        try:
            msg = json.loads(line)
        except Exception:
            continue
        if msg.get("reason") != "compiler-artifact":
            continue
        if not msg.get("profile", {}).get("test"):
            continue
        executable = msg.get("executable")
        if executable:
            return Path(executable)
    return None


def _run_cargo_valgrind(root: Path) -> ToolResult | None:
    """Build tests with `--no-run`, then run the test binary under
    valgrind. A missing `cargo` or `valgrind` binary (T-0142) is a typed
    failing ToolResult; `None` is only returned when the build produced no
    test binary to run (a real skip)."""
    from frob.process.parsers import parse_valgrind

    try:
        build_proc = subprocess.run(
            ["cargo", "test", "--no-run", "--message-format", "json"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
    except FileNotFoundError:
        return tool_unavailable_result("cargo-test(valgrind)", "cargo")
    binary = _find_test_binary_from_cargo_json(build_proc.stdout)
    if binary is None:
        return None
    try:
        proc = subprocess.run(
            ["valgrind", "--leak-check=full", "--error-exitcode=1", str(binary)],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
    except FileNotFoundError:
        return tool_unavailable_result("cargo-test(valgrind)", "valgrind")
    r = parse_valgrind(proc.stdout + proc.stderr, exit_code=proc.returncode)
    r.tool = "cargo-test(valgrind)"
    return r


def _run_cargo_test(root: Path, *, valgrind: bool = False) -> ToolResult | None:
    """`cargo test`, optionally under valgrind memcheck. A missing `cargo`
    binary (T-0142) is a typed failing ToolResult."""
    from frob.process.parsers import parse_cargo

    try:
        if valgrind:
            vg = _run_cargo_valgrind(root)
            if vg is not None:
                return vg
        proc = subprocess.run(
            ["cargo", "test"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
    except FileNotFoundError:
        return tool_unavailable_result("cargo-test", "cargo")
    return parse_cargo(
        proc.stdout + proc.stderr, exit_code=proc.returncode, tool="cargo-test"
    )

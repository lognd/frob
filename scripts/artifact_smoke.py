#!/usr/bin/env python3
"""T-3884: the artifact smoke stage -- proves the BUILT wheel installs,
starts, and reports healthy before `.github/workflows/release.yml`'s
`upload` job is allowed to run. This is not a test-suite run against the
installed artifact (that would be slow and duplicate `ci.yml`); it is the
narrow, real question a release actually depends on: does the thing we
are about to publish install, start, and report healthy.

WHY THIS EXISTS: `frob`'s CI proves the SOURCE TREE passes its tests. It
never installs the built wheel into a clean environment and runs it, so
dependency-resolution faults (a bad extra pin resolving against the real
index, rather than this checkout's `uv.lock`), packaging metadata, entry
points, and missing runtime files can all ship green and broken. T-3857
is the live example this stage exists to catch: `pyproject.toml`'s
`serve` extra pinned `mcp>=1.28.1` with no upper bound, so a FRESH
resolve picked up mcp 2.x (which renamed `FastMCP` to `MCPServer`) and
`frob serve` failed on import -- while this checkout, which already
resolves mcp 1.28.1, stayed green throughout. See
docs/guides/release.md's "Artifact smoke stage" section for the full
decision record (local wheel + real index resolution, not TestPyPI; one
call per extra to `python -c` against the installed interpreter, not a
`frob check` run).

Each `check_*` function creates its OWN clean venv (via `uv venv`),
installs from the given wheel path (resolving every OTHER dependency
from the configured index -- exactly what an adopter's `pip install
"frob[...]"` does), and runs a REAL command, never just an import
statement in isolation from frob's own entrypoint. `main()` runs every
check, reports each one, and exits non-zero the moment any of them
fails -- this script's own exit code is what
`.github/workflows/release.yml`'s `artifact-smoke` job gates `upload` on
(frob:ticket T-3884).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


# frob:doc docs/guides/release.md#artifact-smoke-stage-t-3884
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestCheckBaseInstall.test_failing_doctor_ra\
# ises_smoke_check_error
@dataclass(frozen=True)
class SmokeCheckError(Exception):
    """One `check_*` step failed; `name` identifies which, `detail` is the
    captured stdout/stderr an operator needs to diagnose it."""

    name: str
    detail: str

    def __str__(self) -> str:  # noqa: D105
        return f"{self.name}: {self.detail}"


def _run(argv: list[str], *, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run `argv`, capturing output, never raising on a non-zero exit --
    callers inspect `.returncode` themselves so a failure can be wrapped
    in a `SmokeCheckError` naming which smoke stage it belongs to."""
    return subprocess.run(
        argv, capture_output=True, text=True, timeout=timeout, check=False
    )


def _make_venv(venv_dir: Path) -> Path:
    """A fresh venv at `venv_dir` via `uv venv`; returns its python
    executable. Raises `SmokeCheckError` if venv creation itself fails --
    that is an environment problem, not a finding about the wheel."""
    result = _run(["uv", "venv", str(venv_dir)])
    if result.returncode != 0:
        raise SmokeCheckError("venv-create", result.stdout + result.stderr)
    bin_dir = "Scripts" if sys.platform == "win32" else "bin"
    exe = "python.exe" if sys.platform == "win32" else "python"
    return venv_dir / bin_dir / exe


def _pip_install(python: Path, spec: str, *, find_links: Path | None = None) -> None:
    """`uv pip install --python <python> <spec>`, resolving every
    dependency OTHER than the local wheel from the real, configured
    index -- a local `spec` (a `.whl` path, optionally with `[extras]`)
    is a direct reference for the ONE package it names; uv still
    resolves the rest of that package's dependency tree from the index,
    which is exactly the T-3857 regression shape this stage exists to
    catch (an extra's pin failing to resolve against a REAL index, not a
    frozen local one). `find_links` adds a local wheel directory to the
    search path ALONGSIDE the index, for `frob[native]`'s exact-pinned
    `frob-core`/`strata-core` wheels, which do not exist on the index yet
    at smoke-test time (this stage runs BEFORE publish)."""
    argv = ["uv", "pip", "install", "--python", str(python), spec]
    if find_links is not None:
        argv += ["--find-links", str(find_links)]
    result = _run(argv, timeout=600)
    if result.returncode != 0:
        raise SmokeCheckError(f"pip-install {spec}", result.stdout + result.stderr)


def _python_c(python: Path, code: str, *, name: str) -> None:
    """Run `code` with `python`; wraps a non-zero exit in a
    `SmokeCheckError` named `name` so the reported failure names which
    smoke stage produced it."""
    result = _run([str(python), "-c", code])
    if result.returncode != 0:
        raise SmokeCheckError(name, result.stdout + result.stderr)


def _run_module(python: Path, *args: str, name: str) -> subprocess.CompletedProcess:
    """`python -m frob <args>`; wraps a non-zero exit in a `SmokeCheckError`
    named `name`."""
    result = _run([str(python), "-m", "frob", *args])
    if result.returncode != 0:
        raise SmokeCheckError(name, result.stdout + result.stderr)
    return result


# frob:doc docs/guides/release.md#artifact-smoke-stage-t-3884
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestCheckBaseInstall.test_installs_and_runs\
# _version_and_doctor
# frob:tests \
# tests/system/test_artifact_smoke.py::TestArtifactSmokeMustStayQuiet.test_current_pin_\
# passes_serve_extra_check
def check_base_install(wheel_path: Path, work_dir: Path, core_wheels_dir: Path) -> None:
    """Bare `frob` (no extras) must install into a clean venv and run a
    real command: `frob --version` (entry point wiring) AND `frob
    doctor` (T-3884's own acceptance -- it exists precisely to report
    native-extension and environment health, so it exercises the
    dependency surface, not just the CLI parser). `core_wheels_dir` is
    required even here (T-3845: `frob-core`/`strata-core` are now plain
    DEFAULT dependencies of `frob` itself, not only of the `native`
    extra, so even a bare install needs them resolvable and the index
    does not have this release's cores yet at smoke-test time)."""
    python = _make_venv(work_dir / "venv-base")
    _pip_install(python, str(wheel_path), find_links=core_wheels_dir)
    _run_module(python, "--version", name="frob --version")
    _run_module(python, "doctor", name="frob doctor")


# frob:doc docs/guides/release.md#artifact-smoke-stage-t-3884
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestCheckServeExtra.test_installs_and_impor\
# ts_mcp
# frob:tests \
# tests/system/test_artifact_smoke.py::TestArtifactSmokeMustFire.test_unbounded_mcp_pin\
# _fails_serve_extra_check
# frob:tests \
# tests/system/test_artifact_smoke.py::TestArtifactSmokeMustStayQuiet.test_current_pin_\
# passes_serve_extra_check
def check_serve_extra(wheel_path: Path, work_dir: Path, core_wheels_dir: Path) -> None:
    """`frob[serve]` must install into a clean venv AND the mcp import
    must actually resolve -- the exact T-3857 shape (an unbounded lower
    bound let a fresh resolve pick up mcp 2.x, which renamed `FastMCP` to
    `MCPServer` and broke this import). Calls
    `frob.serve.server._require_mcp()` directly rather than a bare
    `import mcp` -- that is the real code path `frob serve` runs, so a
    working bare mcp import with a broken `frob.serve.server` adapter
    would still be caught."""
    python = _make_venv(work_dir / "venv-serve")
    _pip_install(python, f"{wheel_path}[serve]", find_links=core_wheels_dir)
    _python_c(
        python,
        "from frob.serve.server import _require_mcp; _require_mcp()",
        name="serve-extra mcp import",
    )


# frob:doc docs/guides/release.md#artifact-smoke-stage-t-3884
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestCheckNativeExtra.test_installs_and_impo\
# rts_natives_via_doctor
def check_native_extra(wheel_path: Path, work_dir: Path, core_wheels_dir: Path) -> None:
    """`frob[native]` must install into a clean venv (resolving
    `frob-core`/`strata-core`'s exact pins against `core_wheels_dir` --
    the just-built platform wheels, since the smoke stage runs BEFORE
    publish and the index does not have this release's cores yet) and
    the natives must import through FROB'S OWN code path
    (`frob.doctor.native_degrade_warning`), not just a bare `import
    frob_core, strata_core` -- the acceptance text's own distinction."""
    python = _make_venv(work_dir / "venv-native")
    _pip_install(python, f"{wheel_path}[native]", find_links=core_wheels_dir)
    _python_c(
        python,
        "import frob_core, strata_core; "
        "print(frob_core.__name__, strata_core.__name__)",
        name="native extra bare import",
    )
    result = _run_module(python, "doctor", name="frob doctor (native)")
    if "native" not in (result.stdout + result.stderr).lower():
        raise SmokeCheckError(
            "frob doctor (native)",
            "doctor output did not mention native extensions at all -- "
            "cannot confirm it exercised the native code path\n"
            + result.stdout
            + result.stderr,
        )


def _build_checks(
    wheel_path: Path, core_dir: Path, *, skip_native: bool
) -> list[tuple[str, Callable[[Path], None]]]:
    """The ordered `(name, check)` pairs `main` runs -- split out of
    `main` itself so its own body stays under ARCH001's line threshold
    (T-3884's own gate:ARCH obligation)."""
    checks: list[tuple[str, Callable[[Path], None]]] = [
        ("base-install", lambda wd: check_base_install(wheel_path, wd, core_dir)),
        ("serve-extra", lambda wd: check_serve_extra(wheel_path, wd, core_dir)),
    ]
    if not skip_native:
        checks.append(
            ("native-extra", lambda wd: check_native_extra(wheel_path, wd, core_dir))
        )
    return checks


def _run_checks(checks: list[tuple[str, Callable[[Path], None]]]) -> int:
    """Run each `(name, check)` pair in its own scratch dir, printing a
    PASS/FAIL line per stage; returns the failure count."""
    failures = 0
    with tempfile.TemporaryDirectory(prefix="frob-artifact-smoke-") as tmp:
        tmp_path = Path(tmp)
        for name, check in checks:
            work_dir = tmp_path / name
            work_dir.mkdir()
            try:
                check(work_dir)
            except SmokeCheckError as exc:
                print(f"FAIL {name}: {exc}", file=sys.stderr)
                failures += 1
            except subprocess.TimeoutExpired as exc:
                print(f"FAIL {name}: timed out ({exc})", file=sys.stderr)
                failures += 1
            else:
                # frob:waive RENDER001 reason="scripts/** standalone-CLI posture, same \
                # as \
                # scripts/branch_stranded_work_analysis.py's/scripts/verify_release_ci_\
                # status.py's own identical bare-print waivers -- this runs as a \
                # release.yml step, not through frob's own gate-rendered output surface"
                print(f"PASS {name}")
            finally:
                shutil.rmtree(work_dir, ignore_errors=True)
    return failures


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """CLI argument parsing for `main`, split out for ARCH001's line
    threshold the same way `_build_checks`/`_run_checks` are."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wheel", required=True, type=Path, help="path to the built frob wheel"
    )
    parser.add_argument(
        "--core-wheels-dir",
        required=True,
        type=Path,
        help="directory holding this platform's frob-core/strata-core wheels "
        "(T-3845: required for every check, not just [native] -- both are "
        "now plain default dependencies of frob itself)",
    )
    parser.add_argument(
        "--skip-native",
        action="store_true",
        help="skip the explicit [native] extra behavioral check (base-install "
        "already exercises the same cores as a default dependency)",
    )
    return parser.parse_args(argv)


# frob:doc docs/guides/release.md#artifact-smoke-stage-t-3884
# frob:tests \
# tests/system/test_artifact_smoke.py::TestArtifactSmokeMustFire.test_unbounded_mcp_pin\
# _fails_serve_extra_check
# frob:tests \
# tests/system/test_artifact_smoke.py::TestArtifactSmokeMustStayQuiet.test_current_pin_\
# passes_serve_extra_check
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestMain.test_all_checks_pass_exits_zero
def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: run every requested smoke check, print a PASS/FAIL
    line per stage, and return 1 the moment any stage fails (0 if every
    requested stage passed). This return value is what
    `.github/workflows/release.yml`'s `artifact-smoke` job step gates
    `upload` on."""
    args = _parse_args(argv)

    wheel_path = args.wheel.resolve()
    if not wheel_path.is_file():
        print(f"FAIL setup: wheel not found at {wheel_path}", file=sys.stderr)
        return 1
    core_dir = args.core_wheels_dir.resolve()

    checks = _build_checks(wheel_path, core_dir, skip_native=args.skip_native)
    failures = _run_checks(checks)

    if failures:
        msg = f"artifact-smoke: {failures} of {len(checks)} check(s) FAILED"
        print(msg, file=sys.stderr)
        return 1
    # frob:waive RENDER001 reason="scripts/** standalone-CLI posture, same as \
    # scripts/branch_stranded_work_analysis.py's/scripts/verify_release_ci_status.py's \
    # own identical bare-print waivers -- this runs as a release.yml step, not through \
    # frob's own gate-rendered output surface"
    print(f"artifact-smoke: all {len(checks)} check(s) passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

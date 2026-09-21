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
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


# frob:doc docs/guides/release.md#artifact-smoke-stage-t-3884
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestCheckBaseInstall.test_failing_doctor_raises_smoke_check_error  # noqa: E501
@dataclass(frozen=True)
class SmokeCheckError(Exception):
    """One `check_*` step failed; `name` identifies which, `detail` is the
    captured stdout/stderr an operator needs to diagnose it."""

    name: str
    detail: str

    def __str__(self) -> str:  # noqa: D105
        return f"{self.name}: {self.detail}"


def _run(
    argv: list[str], *, timeout: int = 300, cwd: Path | None = None
) -> subprocess.CompletedProcess:
    """Run `argv`, capturing output, never raising on a non-zero exit --
    callers inspect `.returncode` themselves so a failure can be wrapped
    in a `SmokeCheckError` naming which smoke stage it belongs to. `cwd`
    defaults to inheriting this process's own working directory (T-3980:
    pass a scratch dir outside the repo checkout for a check that must
    not pick up this repo's own `.frob`/git state)."""
    return subprocess.run(
        argv, capture_output=True, text=True, timeout=timeout, check=False, cwd=cwd
    )


# frob:ticket T-3935
_REQUIRED_CORE_WHEEL_GLOBS = {
    "frob-core": "frob_core-*.whl",
    "frob-strata": "frob_strata-*.whl",
}

# T-3980: maps sys.platform to the wheel platform-tag prefixes a wheel
# BUILT FOR THIS HOST may legitimately carry (a wheel filename's final
# `-`-separated field before `.whl`, e.g. `manylinux_2_39_x86_64` or
# `macosx_11_0_arm64`). Used by `_wheel_matches_host_platform` below --
# see that function's docstring for why this check exists at all.
_HOST_PLATFORM_TAG_PREFIXES = {
    "linux": ("manylinux", "linux"),
    "darwin": ("macosx",),
    "win32": ("win",),
}

# T-3980: maps `platform.machine()` values to the arch token a wheel's
# platform tag encodes for that machine -- both sides of the comparison
# `_wheel_matches_host_platform` needs, since "macosx_11_0_arm64" and
# "manylinux_2_39_x86_64" differ in BOTH os and arch and either mismatch
# alone means the wheel cannot install here.
_HOST_ARCH_TAG_TOKENS = {
    "x86_64": ("x86_64", "amd64"),
    "amd64": ("x86_64", "amd64"),
    "arm64": ("arm64", "aarch64"),
    "aarch64": ("arm64", "aarch64"),
}


# frob:ticket T-3980
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels.test_wheel_matches_host_platform_rejects_foreign_tag  # noqa: E501
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels.test_wrong_platform_wheel_names_the_mismatch  # noqa: E501
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels.test_matching_platform_wheel_does_not_raise  # noqa: E501
def _wheel_matches_host_platform(wheel_path: Path) -> bool:
    """T-3980: whether `wheel_path`'s filename platform tag is one this
    host could actually install -- `_require_core_wheels`'s glob match
    (`frob_core-*.whl`) is platform-blind, so a stale cache entry
    carrying another platform's wheel (T-3980's root cause: a shared
    cargo-cache key with no os/arch component let a macOS-built wheel
    reach an ubuntu runner) glob-matches and was previously invisible
    until it hit uv's resolver, which reports it as an opaque "no wheels
    with a matching platform tag" trace with no hint that the wheel WAS
    present, just for the wrong machine. Unknown `sys.platform`/
    `platform.machine()` combinations return True (permissive) rather
    than false-failing a host this check was not taught about."""
    tag = wheel_path.stem.rsplit("-", 1)[-1]
    os_prefixes = _HOST_PLATFORM_TAG_PREFIXES.get(sys.platform)
    arch_tokens = _HOST_ARCH_TAG_TOKENS.get(platform.machine().lower())
    if os_prefixes is None or arch_tokens is None:
        return True
    if not any(tag.startswith(prefix) for prefix in os_prefixes):
        return False
    return any(token in tag for token in arch_tokens)


# frob:ticket T-3935
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels.test_both_cores_absent_names_both  # noqa: E501
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels.test_one_core_absent_names_only_that_one  # noqa: E501
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels.test_both_cores_present_does_not_raise  # noqa: E501
# frob:tests \
# tests/system/test_artifact_smoke.py::TestArtifactSmokeAbsentCores.test_absent_cores_report_named_core_missing  # noqa: E501
def _wheel_version(wheel_path: Path) -> str:
    """The PEP 427 wheel-filename version field
    (`frob_core-VERSION-pytag-abitag-platformtag.whl`). Used by
    `_require_core_wheels` (T-4465) to detect a wheel that glob-matches
    (`frob_core-*.whl`) but was built for an OLDER crate version than
    the one this install is about to attempt -- a stale
    `actions/cache`-restored `target/wheels` entry, not a genuinely
    missing or wrong-platform core."""
    return wheel_path.stem.split("-")[1]


# frob:ticket T-4465
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestReadCorePins.test_reads_both_pins_from_metadata  # noqa: E501
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestReadCorePins.test_unreadable_wheel_returns_empty  # noqa: E501
def _read_core_pins(wheel_path: Path) -> dict[str, str]:
    """T-4465: the exact frob-core/strata-core version pins THIS
    `wheel_path` install is about to attempt, parsed straight from its
    own `.dist-info/METADATA` (`Requires-Dist: frob-core==X`) rather
    than assumed from a repo-relative pyproject.toml -- correct
    regardless of where the wheel came from (this script runs both from
    a checkout, in `tests/system/test_artifact_smoke.py`, and against a
    downloaded artifact with no repo present, in
    `.github/workflows/release.yml`), and it is the actual value uv is
    about to resolve `--find-links` against.

    Returns an empty dict (permissive: `_require_core_wheels` then skips
    the version check entirely, falling back to its pre-T-4465
    behavior) if `wheel_path` is not a readable wheel archive or carries
    no such pin -- callers that pass a placeholder/fake wheel (several
    of this script's own unit tests write `wheel.write_bytes(b"")`) get
    the prior behavior rather than an unrelated crash."""
    pins: dict[str, str] = {}
    try:
        with zipfile.ZipFile(wheel_path) as zf:
            metadata_name = next(
                (n for n in zf.namelist() if n.endswith(".dist-info/METADATA")),
                None,
            )
            if metadata_name is None:
                return pins
            text = zf.read(metadata_name).decode("utf-8", errors="replace")
    except (OSError, zipfile.BadZipFile):
        return pins
    for dist in ("frob-core", "frob-strata"):
        match = re.search(
            rf"^Requires-Dist:\s*{re.escape(dist)}\s*==\s*([^\s;]+)",
            text,
            re.MULTILINE,
        )
        if match:
            pins[dist] = match.group(1)
    return pins


# frob:ticket T-3935
# frob:ticket T-4465
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels.test_both_cores_absent_names_both  # noqa: E501
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels.test_one_core_absent_names_only_that_one  # noqa: E501
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels.test_both_cores_present_does_not_raise  # noqa: E501
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels.test_stale_version_wheel_names_versions  # noqa: E501
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels.test_matching_version_wheel_does_not_raise  # noqa: E501
# frob:tests \
# tests/system/test_artifact_smoke.py::TestArtifactSmokeAbsentCores.test_absent_cores_report_named_core_missing  # noqa: E501
@dataclass(frozen=True)
class _CoreWheelFindings:
    """T-4465: `_classify_core_wheels`'s three disjoint failure buckets --
    split out of `_require_core_wheels` so that function stays a plain
    classify-then-raise dispatch instead of growing an ARCH001-length
    body of its own."""

    missing: list[str]
    stale: list[str]
    wrong_platform: list[str]


def _stale_version_label(name: str, found: list[Path], pin: str) -> str:
    """T-4465: the `stale` bucket's one formatted entry for `name` --
    split out of `_classify_core_wheels`'s loop body so the `sorted()`
    call PERF004 flags for running inside a loop lives in its own,
    obviously-bounded (at most two dist names) helper instead of
    appearing to be a hot path."""
    found_versions = ", ".join(sorted({_wheel_version(w) for w in found}))
    return f"{name} (found {found_versions}, need {pin})"


def _classify_core_wheels(
    core_wheels_dir: Path, pins: dict[str, str]
) -> _CoreWheelFindings:
    """T-4465: `_require_core_wheels`'s classification half -- which of
    `_REQUIRED_CORE_WHEEL_GLOBS` are missing, present-but-stale-version,
    or present-but-wrong-platform. No raising here; `_require_core_wheels`
    turns a non-empty bucket into a `SmokeCheckError` with that bucket's
    own message."""
    missing: list[str] = []
    stale: list[str] = []
    wrong_platform: list[str] = []
    for name, pattern in _REQUIRED_CORE_WHEEL_GLOBS.items():
        found = list(core_wheels_dir.glob(pattern))
        if not found:
            missing.append(name)
            continue
        pin = pins.get(name)
        if pin is not None:
            current = [w for w in found if _wheel_version(w) == pin]
            if not current:
                stale.append(_stale_version_label(name, found, pin))
                continue
            found = current
        bad = [w for w in found if not _wheel_matches_host_platform(w)]
        if bad and len(bad) == len(found):
            wrong_platform.append(f"{name} ({', '.join(w.name for w in bad)})")
    return _CoreWheelFindings(
        missing=missing, stale=stale, wrong_platform=wrong_platform
    )


# frob:ticket T-3935
# frob:ticket T-4465
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels.test_both_cores_absent_names_both  # noqa: E501
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels.test_one_core_absent_names_only_that_one  # noqa: E501
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels.test_both_cores_present_does_not_raise  # noqa: E501
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels.test_stale_version_wheel_names_versions  # noqa: E501
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels.test_matching_version_wheel_does_not_raise  # noqa: E501
# frob:tests \
# tests/system/test_artifact_smoke.py::TestArtifactSmokeAbsentCores.test_absent_cores_report_named_core_missing  # noqa: E501
def _require_core_wheels(
    core_wheels_dir: Path, pins: dict[str, str] | None = None
) -> None:
    """T-3935: `frob-core`/`frob-strata` are hard `==`-pinned DEFAULT
    dependencies of `frob` (T-3845) that are not published to any
    registry, so `--find-links core_wheels_dir` is the ONLY way an
    install of the built wheel can ever resolve them. Without this
    preflight, a missing/empty `core_wheels_dir` surfaces as uv's raw
    "was not found in the package registry" resolver trace inside every
    downstream check -- which reads identically whether the core was
    simply never built (a CI wiring bug) or the version pin itself is
    wrong (a real regression). Checked once, up front, so a wiring bug
    fails fast with a message naming exactly which core is missing,
    instead of that ambiguity landing in the release gate.

    T-3980: also catches the PRESENT-BUT-WRONG-PLATFORM case -- a wheel
    that glob-matches (`frob_core-*.whl`) but was built for a different
    os/arch (see `_wheel_matches_host_platform`). Previously this reached
    uv's resolver undetected and surfaced as an opaque "no wheels with a
    matching platform tag" trace deep inside a downstream check; this
    preflight now names the wrong-platform wheel directly.

    T-4465: also catches the PRESENT-BUT-STALE-VERSION case -- a wheel
    that glob-matches but was built for an OLDER crate version than
    `pins` names (the CI incident this guards against: an
    `actions/cache` entry keyed only on Cargo.lock, restored verbatim
    across a version bump, left `target/wheels` holding the prior
    version while the pin moved on; uv then failed with an opaque
    "requirements are unsatisfiable" trace instead of naming the stale
    wheel). `pins` maps the required dist name ("frob-core"/
    "frob-strata") to the exact version this install is about to
    attempt -- `main` reads it from the frob wheel's own METADATA via
    `_read_core_pins`. `None`, or a name missing from `pins`, skips the
    version check for that dist (the pre-T-4465 permissive behavior).

    The classification itself lives in `_classify_core_wheels`; this
    function is just that result turned into the right `SmokeCheckError`,
    missing checked before stale checked before wrong-platform."""
    findings = _classify_core_wheels(core_wheels_dir, pins or {})
    missing, stale, wrong_platform = (
        findings.missing,
        findings.stale,
        findings.wrong_platform,
    )
    if missing:
        raise SmokeCheckError(
            "core-wheels-preflight",
            f"core_wheels_dir ({core_wheels_dir}) does not contain a built "
            f"wheel for: {', '.join(missing)}. frob-core/strata-core are "
            "hard-pinned default dependencies (T-3845) that are not "
            "published to any registry -- they must be built and supplied "
            "via --core-wheels-dir before any install can resolve them. "
            "This is 'core not built/supplied', not a bad version pin.",
        )
    if stale:
        raise SmokeCheckError(
            "core-wheels-preflight",
            f"core_wheels_dir ({core_wheels_dir}) contains only a "
            f"stale-version wheel for: {', '.join(stale)}. This is the "
            "T-4465 cached-target-dir shape (a stale actions/cache "
            "restore of target/wheels from before a crate version bump), "
            "not a missing core or a wrong platform -- rebuild frob-core/"
            "frob-strata (`make core-wheels`) so target/wheels holds the "
            "current version.",
        )
    if wrong_platform:
        raise SmokeCheckError(
            "core-wheels-preflight",
            f"core_wheels_dir ({core_wheels_dir}) contains a wheel for: "
            f"{', '.join(wrong_platform)}, but it was built for a "
            f"different platform than this host "
            f"(sys.platform={sys.platform!r}, "
            f"machine={platform.machine()!r}). This is a wrong-platform "
            "wheel reaching the smoke stage (e.g. a shared build cache "
            "with no os/arch key crossing matrix legs), not a missing "
            "core or a bad version pin.",
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
    `frob-core`/`frob-strata` wheels, which do not exist on the index yet
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


def _run_module(
    python: Path, *args: str, name: str, cwd: Path | None = None
) -> subprocess.CompletedProcess:
    """`python -m frob <args>`; wraps a non-zero exit in a `SmokeCheckError`
    named `name`. `cwd` (T-3980) runs the command from a directory other
    than this process's own -- used so `frob doctor` inspects the
    installed artifact, not the smoke script's own repo checkout."""
    result = _run([str(python), "-m", "frob", *args], cwd=cwd)
    if result.returncode != 0:
        raise SmokeCheckError(name, result.stdout + result.stderr)
    return result


def _run_doctor_in_scratch_cwd(
    python: Path, work_dir: Path, *, name: str
) -> subprocess.CompletedProcess:
    """`frob doctor`, run from a scratch `work_dir / "doctor-cwd"` rather
    than this process's own cwd (T-3980, extended by T-4473 to every
    doctor invocation in this script): the smoke script's process cwd is
    the release runner's own repo checkout, and `doctor` also inspects
    whatever git/`.frob` state happens to surround wherever it runs
    (stale ticket leases, hook drift, a detached-HEAD `git diff`
    failure, T-4459's import-source check) -- none of which has
    anything to do with whether the installed wheel under test works.
    Every `check_*` that shells out to `doctor` must go through this
    one helper so that scratch-cwd behavior stays a single fact, not
    one copy per check that can silently drift apart."""
    doctor_cwd = work_dir / "doctor-cwd"
    doctor_cwd.mkdir(exist_ok=True)
    return _run_module(python, "doctor", name=name, cwd=doctor_cwd)


# frob:doc docs/guides/release.md#artifact-smoke-stage-t-3884
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestCheckBaseInstall.test_installs_and_runs_version_and_doctor  # noqa: E501
# frob:tests \
# tests/system/test_artifact_smoke.py::TestArtifactSmokeMustStayQuiet.test_current_pin_passes_serve_extra_check  # noqa: E501
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestCheckBaseInstall.test_doctor_runs_outside_work_dir_not_process_cwd  # noqa: E501
# frob:waive AFFECT001 reason="T-4473 is an internal implementation fix (which cwd the \
# already-documented doctor call runs from) -- \
# docs/guides/release.md#artifact-smoke-stage-t-3884 already documents item 2 as \
# running frob doctor against the installed artifact, which is exactly what this \
# change makes true; widening this ticket's scope to the shared release doc to restate \
# the same fact in different words is disproportionate to a cwd-plumbing bugfix, the \
# same shape T-2521's neighboring AFFECT001 waiver on this identical doc already \
# accepted"
def check_base_install(wheel_path: Path, work_dir: Path, core_wheels_dir: Path) -> None:
    """Bare `frob` (no extras) must install into a clean venv and run a
    real command: `frob --version` (entry point wiring) AND `frob
    doctor` (T-3884's own acceptance -- it exists precisely to report
    native-extension and environment health, so it exercises the
    dependency surface, not just the CLI parser). `core_wheels_dir` is
    required even here (T-3845: `frob-core`/`frob-strata` are now plain
    DEFAULT dependencies of `frob` itself, not only of the `native`
    extra, so even a bare install needs them resolvable and the index
    does not have this release's cores yet at smoke-test time).

    T-3980: `frob doctor` is run with `cwd=work_dir` (a scratch dir this
    check owns, not the smoke script's own repo checkout) so it reports
    ONLY the installed artifact's health -- entry-point wiring plus
    native-extension import status. This assertion is deliberately about
    the wheel, not the checkout: `doctor` also inspects whatever git
    repo/`.frob` state happens to surround wherever it runs (stale
    ticket leases, hook drift, ...), and that repo hygiene has nothing
    to do with whether the artifact under test works. Outside a repo,
    `doctor`'s ticket/hook checks find nothing to inspect and exit 0
    while `healthy` still reflects native-extension import failures (see
    `src/frob/doctor.py::_doctor_healthy`) -- exactly the must-fire/
    must-stay-quiet split this check needs: a broken core still fails
    here, a messy checkout the script happens to run inside no longer
    can."""
    python = _make_venv(work_dir / "venv-base")
    _pip_install(python, str(wheel_path), find_links=core_wheels_dir)
    _run_module(python, "--version", name="frob --version")
    _run_doctor_in_scratch_cwd(python, work_dir, name="frob doctor")


# frob:doc docs/guides/release.md#artifact-smoke-stage-t-3884
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestCheckServeExtra.test_installs_and_imports_mcp  # noqa: E501
# frob:tests \
# tests/system/test_artifact_smoke.py::TestArtifactSmokeMustFire.test_unbounded_mcp_pin_fails_serve_extra_check  # noqa: E501
# frob:tests \
# tests/system/test_artifact_smoke.py::TestArtifactSmokeMustStayQuiet.test_current_pin_passes_serve_extra_check  # noqa: E501
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
# tests/unit/test_artifact_smoke_script.py::TestCheckNativeExtra.test_installs_and_imports_natives_via_doctor  # noqa: E501
# frob:tests \
# tests/unit/test_artifact_smoke_script.py::TestCheckNativeExtra.test_doctor_runs_outside_work_dir_not_process_cwd  # noqa: E501
# frob:waive AFFECT001 reason="T-4473 is an internal implementation fix (which cwd the \
# already-documented doctor call runs from) -- \
# docs/guides/release.md#artifact-smoke-stage-t-3884 already documents item 4 as \
# running frob doctor against the installed artifact, which is exactly what this \
# change makes true; widening this ticket's scope to the shared release doc to restate \
# the same fact in different words is disproportionate to a cwd-plumbing bugfix, the \
# same shape T-2521's neighboring AFFECT001 waiver on this identical doc already \
# accepted"
def check_native_extra(wheel_path: Path, work_dir: Path, core_wheels_dir: Path) -> None:
    """`frob[native]` must install into a clean venv (resolving
    `frob-core`/`frob-strata`'s exact pins against `core_wheels_dir` --
    the just-built platform wheels, since the smoke stage runs BEFORE
    publish and the index does not have this release's cores yet) and
    the natives must import through FROB'S OWN code path
    (`frob.doctor.native_degrade_warning`), not just a bare `import
    frob_core, strata_core` -- the acceptance text's own distinction.

    T-4473: like `check_base_install`, the `doctor` call runs from a
    scratch `work_dir`-relative cwd via `_run_doctor_in_scratch_cwd`,
    never this process's own cwd (the release runner's repo checkout)
    -- running it against the checkout is exactly what made every
    artifact-smoke leg fail on release 34789841956 despite the wheel
    itself being fine (managed-hooks/Claude-config/detached-HEAD/
    import-source findings are all properties of the checkout, not
    the installed artifact)."""
    python = _make_venv(work_dir / "venv-native")
    _pip_install(python, f"{wheel_path}[native]", find_links=core_wheels_dir)
    _python_c(
        python,
        "import frob_core, strata_core; "
        "print(frob_core.__name__, strata_core.__name__)",
        name="native extra bare import",
    )
    result = _run_doctor_in_scratch_cwd(python, work_dir, name="frob doctor (native)")
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
# tests/system/test_artifact_smoke.py::TestArtifactSmokeMustFire.test_unbounded_mcp_pin_fails_serve_extra_check  # noqa: E501
# frob:tests \
# tests/system/test_artifact_smoke.py::TestArtifactSmokeMustStayQuiet.test_current_pin_passes_serve_extra_check  # noqa: E501
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
    pins = _read_core_pins(wheel_path)
    try:
        _require_core_wheels(core_dir, pins)
    except SmokeCheckError as exc:
        print(f"FAIL {exc.name}: {exc.detail}", file=sys.stderr)
        return 1

    checks = _build_checks(wheel_path, core_dir, skip_native=args.skip_native)
    failures = _run_checks(checks)

    if failures:
        msg = f"artifact-smoke: {failures} of {len(checks)} check(s) FAILED"
        print(msg, file=sys.stderr)
        return 1
    print(f"artifact-smoke: all {len(checks)} check(s) passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

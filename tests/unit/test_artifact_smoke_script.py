"""T-3884: fast, mocked unit tests for `scripts/artifact_smoke.py`'s
`check_*` functions -- these never spawn a real `uv`/venv/pip, they patch
`artifact_smoke._run` to return canned `CompletedProcess` results, so
they cover control flow (which command each check runs, and how a
non-zero exit becomes a `SmokeCheckError`) instantly and offline. The
REAL regression proof against a genuine index resolve lives in
tests/system/test_artifact_smoke.py (T-3884's must-fire/must-stay-quiet
fixtures) -- these two files are complementary, not redundant: one
proves the logic, the other proves the actual bug is caught.
"""

from __future__ import annotations

import importlib.util
import platform
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "artifact_smoke.py"
_spec = importlib.util.spec_from_file_location("artifact_smoke", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None, f"could not load spec for {_SCRIPT_PATH}"
artifact_smoke = importlib.util.module_from_spec(_spec)
# frob:waive OPAQUE001 reason="standard importlib.util.module_from_spec recipe for loading a standalone script (scripts/ is not an importable package) as a module under test; this sys.modules entry is a private name registered once at collection time, never mutated per-test, not a runtime swap of a name other code resolves via import elsewhere in the process"  # noqa: E501
sys.modules["artifact_smoke"] = artifact_smoke
_spec.loader.exec_module(artifact_smoke)


def _ok(stdout: str = "") -> subprocess.CompletedProcess:
    """A successful `CompletedProcess` stand-in."""
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


def _fail(stderr: str = "boom") -> subprocess.CompletedProcess:
    """A failing `CompletedProcess` stand-in."""
    return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr=stderr)


def _host_platform_tag() -> str:
    """T-3980: a wheel platform tag `_wheel_matches_host_platform` accepts
    on THIS host, whatever it is -- `_touch_core_wheels` must stay
    host-agnostic (these unit tests run on every CI platform), so it
    cannot hardcode a single tag like the pre-T-3980 `linux_x86_64`
    literal did (that would fail every test on macOS/Windows once the
    platform check exists)."""
    machine = platform.machine().lower()
    if sys.platform == "darwin":
        return f"macosx_11_0_{machine}"
    if sys.platform == "win32":
        return f"win_{machine}"
    return f"manylinux_2_39_{machine}"


def _touch_core_wheels(core_dir: Path) -> None:
    """T-3935: `main`'s `_require_core_wheels` preflight checks the real
    filesystem for `frob_core-*.whl`/`strata_core-*.whl` (it runs before
    any mocked `_run` call), so every `main`-level test that mocks
    installs green must still drop matching placeholder files here or
    the preflight itself fails the test before the mocked checks run.
    T-3980: the wheel filenames now carry a platform tag matching THIS
    host (see `_host_platform_tag`), since `_require_core_wheels` also
    checks platform match as of T-3980 -- a hardcoded tag would fail
    this helper's callers on any host it does not happen to match."""
    core_dir.mkdir(exist_ok=True)
    tag = _host_platform_tag()
    (core_dir / f"frob_core-0.1.0-cp311-abi3-{tag}.whl").write_bytes(b"")
    (core_dir / f"strata_core-0.1.0-cp311-abi3-{tag}.whl").write_bytes(b"")


class TestCheckBaseInstall:
    """`check_base_install`: venv, install, `--version`, `doctor`."""

    def test_installs_and_runs_version_and_doctor(self, tmp_path: Path) -> None:
        """All four underlying commands succeed -> no exception, and the
        install call includes `--find-links` for the core wheels dir."""
        calls: list[list[str]] = []

        def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
            calls.append(argv)
            return _ok()

        with patch.object(artifact_smoke, "_run", side_effect=fake_run):
            artifact_smoke.check_base_install(
                tmp_path / "frob-0.1.0-py3-none-any.whl", tmp_path, tmp_path / "cores"
            )

        install_call = next(c for c in calls if "install" in c)
        assert "--find-links" in install_call
        assert any("--version" in c for c in calls)
        assert any("doctor" in c for c in calls)

    def test_failing_doctor_raises_smoke_check_error(self, tmp_path: Path) -> None:
        """A non-zero `frob doctor` must raise `SmokeCheckError`, not pass
        silently -- this is the exact failure mode the gate exists to
        surface, so the check function itself must not swallow it."""

        def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
            if "doctor" in argv:
                return _fail("doctor is unhappy")
            return _ok()

        with patch.object(artifact_smoke, "_run", side_effect=fake_run):
            with pytest.raises(artifact_smoke.SmokeCheckError):
                artifact_smoke.check_base_install(
                    tmp_path / "frob.whl", tmp_path, tmp_path / "cores"
                )

    def test_doctor_runs_outside_work_dir_not_process_cwd(self, tmp_path: Path) -> None:
        """T-3980: `frob doctor`'s subprocess call must pass a `cwd` that
        is NOT `None` (i.e. not "inherit the smoke script's own process
        cwd", which in CI is the `frob` repo checkout itself) -- doctor
        inspecting this repo's own ticket/hook hygiene, rather than the
        installed artifact's health, is exactly the coupling T-3980
        fixes. The `cwd` must also live under `work_dir` (this check's
        own scratch area), never `None`/the real repo root."""
        seen_cwd: dict[str, object] = {}

        def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess:
            if "doctor" in argv:
                seen_cwd["cwd"] = kwargs.get("cwd")
            return _ok()

        with patch.object(artifact_smoke, "_run", side_effect=fake_run):
            artifact_smoke.check_base_install(
                tmp_path / "frob.whl", tmp_path, tmp_path / "cores"
            )

        cwd = seen_cwd["cwd"]
        assert isinstance(cwd, Path)
        assert cwd.is_relative_to(tmp_path)


class TestCheckServeExtra:
    """`check_serve_extra`: the exact T-3857 regression shape, mocked."""

    def test_installs_and_imports_mcp(self, tmp_path: Path) -> None:
        """A clean install and a clean mcp import -> no exception, and
        the install spec carries the `[serve]` extra."""
        calls: list[list[str]] = []

        def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
            calls.append(argv)
            return _ok()

        with patch.object(artifact_smoke, "_run", side_effect=fake_run):
            artifact_smoke.check_serve_extra(
                tmp_path / "frob.whl", tmp_path, tmp_path / "cores"
            )

        install_call = next(c for c in calls if "install" in c)
        assert any("[serve]" in arg for arg in install_call)

    def test_mcp_import_failure_raises_smoke_check_error(self, tmp_path: Path) -> None:
        """MUST-FIRE (unit level): a failing mcp import -- exactly what
        mcp 2.x's `mcp.server.fastmcp` compat shim produces -- must raise
        `SmokeCheckError`, never pass."""

        def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
            if "-c" in argv:
                return _fail("ModuleNotFoundError: mcp.server.fastmcp")
            return _ok()

        with patch.object(artifact_smoke, "_run", side_effect=fake_run):
            with pytest.raises(artifact_smoke.SmokeCheckError, match="mcp"):
                artifact_smoke.check_serve_extra(
                    tmp_path / "frob.whl", tmp_path, tmp_path / "cores"
                )


class TestCheckNativeExtra:
    """`check_native_extra`: bare import AND frob's own doctor path."""

    def test_installs_and_imports_natives_via_doctor(self, tmp_path: Path) -> None:
        """A clean install, a clean bare import, and a `doctor` output
        that mentions "native" -> no exception."""

        def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
            if "doctor" in argv:
                return _ok(stdout="native extensions: accelerated")
            return _ok()

        with patch.object(artifact_smoke, "_run", side_effect=fake_run):
            artifact_smoke.check_native_extra(
                tmp_path / "frob.whl", tmp_path, tmp_path / "cores"
            )

    def test_doctor_silent_on_native_raises(self, tmp_path: Path) -> None:
        """MUST-FIRE (unit level, missing-runtime-file shape): `doctor`
        exits 0 but says nothing about native extensions at all -- this
        must still be treated as a failure, since it cannot confirm the
        natives actually loaded through frob's own code path."""

        def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
            if "doctor" in argv:
                return _ok(stdout="everything is fine")
            return _ok()

        with patch.object(artifact_smoke, "_run", side_effect=fake_run):
            with pytest.raises(artifact_smoke.SmokeCheckError):
                artifact_smoke.check_native_extra(
                    tmp_path / "frob.whl", tmp_path, tmp_path / "cores"
                )


class TestRequireCoreWheels:
    """T-3935 MUST-FIRE fixture: `_require_core_wheels` (and `main`'s use
    of it) must name the specific missing core, never surface as an
    ambiguous downstream resolver trace -- this is the fast, offline
    proof; tests/system/test_artifact_smoke.py's
    ``test_absent_cores_report_named_core_missing`` is the real,
    unmocked proof against `main` end-to-end."""

    def test_both_cores_absent_names_both(self, tmp_path: Path) -> None:
        """An empty `core_wheels_dir` -> `SmokeCheckError` naming BOTH
        missing cores, not a generic failure."""
        core_dir = tmp_path / "cores"
        core_dir.mkdir()
        with pytest.raises(artifact_smoke.SmokeCheckError) as exc_info:
            artifact_smoke._require_core_wheels(core_dir)
        assert "frob-core" in str(exc_info.value)
        assert "strata-core" in str(exc_info.value)

    def test_one_core_absent_names_only_that_one(self, tmp_path: Path) -> None:
        """Only `strata-core`'s wheel is missing -> the error names
        exactly that one, not `frob-core` (which IS present)."""
        core_dir = tmp_path / "cores"
        core_dir.mkdir()
        tag = _host_platform_tag()
        (core_dir / f"frob_core-0.1.0-cp311-abi3-{tag}.whl").write_bytes(b"")
        with pytest.raises(artifact_smoke.SmokeCheckError) as exc_info:
            artifact_smoke._require_core_wheels(core_dir)
        # the missing-list clause names exactly strata-core, not frob-core
        # (which IS present) -- the boilerplate sentence after it mentions
        # frob-core by name regardless, so check the specific clause.
        assert "wheel for: strata-core." in str(exc_info.value)

    def test_both_cores_present_does_not_raise(self, tmp_path: Path) -> None:
        """Both wheels present -> no exception."""
        core_dir = tmp_path / "cores"
        _touch_core_wheels(core_dir)
        artifact_smoke._require_core_wheels(core_dir)  # must not raise

    def test_wrong_platform_wheel_names_the_mismatch(self, tmp_path: Path) -> None:
        """T-3980 MUST-FIRE fixture: a wheel that glob-matches
        `frob_core-*.whl`/`strata_core-*.whl` but was built for a
        DIFFERENT platform than this host must fail with a message
        naming it as a platform mismatch, not silently pass the preflight
        (only to surface as an opaque resolver trace downstream, or --
        worse -- actually get pip-installed)."""
        core_dir = tmp_path / "cores"
        core_dir.mkdir()
        # a tag guaranteed to be wrong for whatever host runs this test:
        # not macosx/win/manylinux-or-linux at all.
        wrong_tag = "some_other_os_never_a_real_host_9999"
        (core_dir / f"frob_core-0.1.0-cp311-abi3-{wrong_tag}.whl").write_bytes(b"")
        (core_dir / f"strata_core-0.1.0-cp311-abi3-{wrong_tag}.whl").write_bytes(b"")

        with pytest.raises(artifact_smoke.SmokeCheckError) as exc_info:
            artifact_smoke._require_core_wheels(core_dir)
        message = str(exc_info.value)
        assert "different platform" in message
        assert "frob-core" in message
        assert "strata-core" in message

    def test_matching_platform_wheel_does_not_raise(self, tmp_path: Path) -> None:
        """T-3980 MUST-STAY-QUIET fixture: a wheel tagged for THIS host
        must not be flagged as wrong-platform."""
        core_dir = tmp_path / "cores"
        _touch_core_wheels(core_dir)
        artifact_smoke._require_core_wheels(core_dir)  # must not raise

    def test_wheel_matches_host_platform_rejects_foreign_tag(self) -> None:
        """`_wheel_matches_host_platform` directly: a wheel tagged for a
        foreign os+arch is rejected regardless of this test's own host."""
        foreign = Path("strata_core-0.1.0-cp311-abi3-macosx_11_0_arm64.whl")
        other_foreign = Path("strata_core-0.1.0-cp311-abi3-manylinux_2_39_x86_64.whl")
        # exactly one of these is a genuine match for the current host (or
        # neither, on an untaught host) -- never both, since darwin/arm64
        # and linux/x86_64 are mutually exclusive tags.
        results = {
            artifact_smoke._wheel_matches_host_platform(foreign),
            artifact_smoke._wheel_matches_host_platform(other_foreign),
        }
        assert results != {True}

    def test_main_reports_missing_core_before_any_install_attempt(
        self, tmp_path: Path
    ) -> None:
        """`main` end-to-end (still mocked at the `_run` boundary, but the
        preflight itself hits the real filesystem): an empty
        `core_wheels_dir` must fail with the named-core message and never
        reach a mocked install call at all."""
        wheel = tmp_path / "frob.whl"
        wheel.write_bytes(b"")
        core_dir = tmp_path / "cores"
        core_dir.mkdir()

        with patch.object(artifact_smoke, "_run") as mock_run:
            code = artifact_smoke.main(
                ["--wheel", str(wheel), "--core-wheels-dir", str(core_dir)]
            )

        assert code == 1
        mock_run.assert_not_called()


class TestMain:
    """`main`: end-to-end argv parsing and the aggregate pass/fail exit
    code, with every underlying command mocked."""

    def test_all_checks_pass_exits_zero(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Every check green -> exit 0, "all N check(s) passed" printed."""
        wheel = tmp_path / "frob-0.1.0-py3-none-any.whl"
        wheel.write_bytes(b"")
        core_dir = tmp_path / "cores"
        _touch_core_wheels(core_dir)

        with patch.object(artifact_smoke, "_run", return_value=_ok(stdout="native")):
            code = artifact_smoke.main(
                ["--wheel", str(wheel), "--core-wheels-dir", str(core_dir)]
            )

        assert code == 0
        assert "all 3 check(s) passed" in capsys.readouterr().out

    def test_missing_wheel_exits_nonzero_without_spawning(self, tmp_path: Path) -> None:
        """A wheel path that does not exist must fail fast (setup error)
        without ever spawning a subprocess -- there is nothing to install."""
        with patch.object(artifact_smoke, "_run") as mock_run:
            code = artifact_smoke.main(
                [
                    "--wheel",
                    str(tmp_path / "does-not-exist.whl"),
                    "--core-wheels-dir",
                    str(tmp_path),
                ]
            )
        assert code == 1
        mock_run.assert_not_called()

    def test_one_failing_check_exits_nonzero(self, tmp_path: Path) -> None:
        """The T-3857 shape at the `main` level: the serve-extra mcp
        import fails while everything else passes -> overall exit 1."""
        wheel = tmp_path / "frob.whl"
        wheel.write_bytes(b"")
        core_dir = tmp_path / "cores"
        _touch_core_wheels(core_dir)

        def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
            if "-c" in argv:
                return _fail("mcp 2.x rename error")
            return _ok(stdout="native")

        with patch.object(artifact_smoke, "_run", side_effect=fake_run):
            code = artifact_smoke.main(
                ["--wheel", str(wheel), "--core-wheels-dir", str(core_dir)]
            )
        assert code == 1

    def test_skip_native_runs_only_two_checks(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """`--skip-native` must drop the native-extra check entirely, not
        just make it always pass."""
        wheel = tmp_path / "frob.whl"
        wheel.write_bytes(b"")
        core_dir = tmp_path / "cores"
        _touch_core_wheels(core_dir)

        with patch.object(artifact_smoke, "_run", return_value=_ok()):
            code = artifact_smoke.main(
                [
                    "--wheel",
                    str(wheel),
                    "--core-wheels-dir",
                    str(core_dir),
                    "--skip-native",
                ]
            )
        assert code == 0
        out = capsys.readouterr().out
        assert "all 2 check(s) passed" in out
        assert "native-extra" not in out

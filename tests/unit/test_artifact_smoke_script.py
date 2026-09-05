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


class TestMain:
    """`main`: end-to-end argv parsing and the aggregate pass/fail exit
    code, with every underlying command mocked."""

    def test_all_checks_pass_exits_zero(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Every check green -> exit 0, "all N check(s) passed" printed."""
        wheel = tmp_path / "frob-0.1.0-py3-none-any.whl"
        wheel.write_bytes(b"")
        core_dir = tmp_path / "cores"
        core_dir.mkdir()

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
        core_dir.mkdir()

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
        core_dir.mkdir()

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

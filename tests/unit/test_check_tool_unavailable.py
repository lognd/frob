"""T-0142: a missing check-stage tool binary (ruff/ty/cargo/npx/cmake/...)
must be a typed failing `ToolResult`, never a raw `FileNotFoundError`
traceback and never a silent skip (vacuous-pass doctrine). One monkeypatched
-absence test per stage family, plus a `CheckResult.as_text` rendering
check confirming the unavailable-tool line is visible.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.check import CheckResult
from frob.check._native import _run_cargo, _run_cargo_fmt_check, _run_cargo_test
from frob.check._python import _ruff_format_result, _run_ruff, _run_ty
from frob.check._ts import _run_tsc
from frob.process.parsers.common import ToolResult


# frob:ticket T-0142
def _raise_file_not_found(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
    """A `subprocess.run` stand-in that always raises `FileNotFoundError`."""
    raise FileNotFoundError("binary not found")


# frob:ticket T-0142
class TestToolUnavailableResult:
    def test_shape_is_a_failing_diagnostic(self) -> None:
        # frob:tests src/frob/process/parsers/common.py::tool_unavailable_result \
        # kind="unit"
        from frob.process.parsers.common import tool_unavailable_result

        r = tool_unavailable_result("ruff-check", "ruff")
        assert not r.passed
        assert r.exit_code == 1
        assert r.tool == "ruff-check"
        assert "tool unavailable: ruff" in r.summary
        assert len(r.diagnostics) == 1
        assert r.diagnostics[0].severity == "error"


# frob:ticket T-0142
class TestRuffUnavailable:
    def test_run_ruff_missing_binary_returns_failing_results(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_ruff kind="unit"
        monkeypatch.setattr(subprocess, "run", _raise_file_not_found)
        results = _run_ruff(tmp_path, None)
        assert len(results) == 2
        for r in results:
            assert isinstance(r, ToolResult)
            assert r.exit_code != 0
            assert not r.passed
            assert "tool unavailable: ruff" in r.summary

    def test_ruff_format_result_missing_binary_returns_failing_result(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_ruff_format_result kind="unit"
        monkeypatch.setattr(subprocess, "run", _raise_file_not_found)
        r = _ruff_format_result(tmp_path)
        assert not r.passed
        assert "tool unavailable: ruff" in r.summary


# frob:ticket T-0142
class TestTyUnavailable:
    def test_run_ty_missing_binary_returns_failing_result(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_ty kind="unit"
        monkeypatch.setattr(subprocess, "run", _raise_file_not_found)
        r = _run_ty(tmp_path)
        assert isinstance(r, ToolResult)
        assert not r.passed
        assert "tool unavailable: ty" in r.summary


# frob:ticket T-0996
class TestTyHermeticRootResolution:
    """T-0996: `_run_ty` must pin `ty`'s module/venv resolution to the
    checked `root` itself via explicit CLI flags, never `ty`'s own
    ambient upward directory walk (docs/modules/check.md's
    `_run_ty`) -- exercised directly against the constructed argv, not
    just via a real subprocess, so a regression here fails fast without
    needing a polluted ancestor directory to reproduce."""

    def test_extra_search_path_and_python_pin_to_root(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_ty kind="unit"
        (tmp_path / "src").mkdir()
        (tmp_path / ".venv").mkdir()
        captured: list[list[str]] = []

        def _fake_run(args, **kwargs):  # noqa: ANN001, ANN002, ANN003
            captured.append(list(args))
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="All checks passed!\n", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", _fake_run)
        r = _run_ty(tmp_path)
        assert isinstance(r, ToolResult)
        assert r.passed

        assert len(captured) == 1
        argv = captured[0]
        expected_src = str((tmp_path / "src").resolve())
        expected_venv = str((tmp_path / ".venv").resolve())
        assert "--extra-search-path" in argv
        assert argv[argv.index("--extra-search-path") + 1] == expected_src
        assert "--python" in argv
        assert argv[argv.index("--python") + 1] == expected_venv

    def test_no_src_or_venv_omits_the_pinning_flags(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_python.py::_run_ty kind="unit"
        captured: list[list[str]] = []

        def _fake_run(args, **kwargs):  # noqa: ANN001, ANN002, ANN003
            captured.append(list(args))
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout="All checks passed!\n", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", _fake_run)
        _run_ty(tmp_path)

        assert len(captured) == 1
        argv = captured[0]
        assert "--extra-search-path" not in argv
        assert "--python" not in argv


# frob:ticket T-0142
class TestCargoUnavailable:
    def test_run_cargo_missing_binary_returns_failing_result(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_native.py::_run_cargo kind="unit"
        monkeypatch.setattr(subprocess, "run", _raise_file_not_found)
        r = _run_cargo("check", tmp_path)
        assert r is not None
        assert not r.passed
        assert "tool unavailable: cargo" in r.summary

    def test_run_cargo_fmt_check_missing_binary_returns_failing_result(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_native.py::_run_cargo_fmt_check kind="unit"
        monkeypatch.setattr(subprocess, "run", _raise_file_not_found)
        r = _run_cargo_fmt_check(tmp_path)
        assert r is not None
        assert not r.passed
        assert "tool unavailable: cargo" in r.summary

    def test_run_cargo_test_missing_binary_returns_failing_result(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_native.py::_run_cargo_test kind="unit"
        monkeypatch.setattr(subprocess, "run", _raise_file_not_found)
        r = _run_cargo_test(tmp_path)
        assert r is not None
        assert not r.passed
        assert "tool unavailable: cargo" in r.summary


# frob:ticket T-0142
class TestTscUnavailable:
    def test_run_tsc_missing_npx_returns_failing_result(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_ts.py::_run_tsc kind="unit"
        monkeypatch.setattr("shutil.which", lambda name: None)
        r = _run_tsc(tmp_path)
        assert not r.passed
        assert "tool unavailable: npx" in r.summary


# frob:ticket T-0404
class TestVitestUnverifiedZeroExit:
    def test_run_vitest_warns_on_unparseable_zero_exit(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """T-0404 finding 10: vitest exiting 0 with non-JSON stdout (a crash
        that somehow returns 0, or an output shape this parser doesn't
        understand) used to be reported as a bare "tests passed" summary
        with zero diagnostics -- indistinguishable from a real, verified
        pass. It must instead attach a WARNING diagnostic so the ambiguity
        is visible, not silently swallowed.
        """
        # frob:tests src/frob/check/_ts.py::_run_vitest kind="unit"
        import frob.check._ts as ts_mod

        fake_proc = subprocess.CompletedProcess(
            args=["npx", "vitest"], returncode=0, stdout="not json", stderr=""
        )
        monkeypatch.setattr(ts_mod, "_run_npx", lambda root, args, tool: fake_proc)
        r = ts_mod._run_vitest(tmp_path)
        assert r.passed  # exit code alone still reads as 0/passed
        assert r.tests == []
        assert len(r.diagnostics) == 1
        assert r.diagnostics[0].severity == "warning"
        assert "unverified" in r.summary


# frob:ticket T-0142
class TestCheckResultRendersUnavailableTool:
    def test_as_text_shows_unavailable_tool_line(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/__init__.py::CheckResult.as_text kind="unit"
        monkeypatch.setattr(subprocess, "run", _raise_file_not_found)
        r = _run_ty(tmp_path)
        result = CheckResult(path=str(tmp_path), results=[r])
        text = result.as_text()
        assert "tool unavailable: ty" in text


# frob:ticket T-1022
class TestToolCrashResult:
    def test_shape_is_a_failing_diagnostic(self) -> None:
        # frob:tests src/frob/process/parsers/common.py::tool_crash_result \
        # kind="unit"
        from frob.process.parsers.common import tool_crash_result

        r = tool_crash_result("cargo-test", ValueError("boom"))
        assert not r.passed
        assert r.exit_code == 1
        assert r.tool == "cargo-test"
        assert "ValueError" in r.summary
        assert len(r.diagnostics) == 1
        assert r.diagnostics[0].severity == "error"
        assert "boom" in r.diagnostics[0].message


# frob:ticket T-1022
class TestNativeCrashIsTypedResult:
    """T-1022: an unexpected exception from a native check-stage runner (not
    a missing binary, not a kill-switch refusal) must surface as a typed
    failing ToolResult too -- EXHAUST001/002 burn-down."""

    def test_run_cargo_unexpected_crash_returns_failing_result(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_native.py::_run_cargo kind="unit"
        def _boom(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
            raise ValueError("unexpected native crash")

        monkeypatch.setattr(subprocess, "run", _boom)
        r = _run_cargo("check", tmp_path)
        assert r is not None
        assert not r.passed
        assert "cargo-check crashed" in r.summary

    def test_run_cargo_test_unexpected_crash_returns_failing_result(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/check/_native.py::_run_cargo_test kind="unit"
        def _boom(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003
            raise ValueError("unexpected native crash")

        monkeypatch.setattr(subprocess, "run", _boom)
        r = _run_cargo_test(tmp_path)
        assert r is not None
        assert not r.passed
        assert "cargo-test crashed" in r.summary

"""T-2251: `frob format` -- write-mode ruff autofix + ruff format, the
frob-native replacement for the Makefile's `format`/`lint-fix`/`all`
targets. Default path delegates to `frob.check._python._run_ruff_autofix`
(T-2320/T-2252); `--select-imports-only` runs a narrower `ruff check --fix
--select I` instead."""

from __future__ import annotations

from pathlib import Path

import pytest
from typani import Ok

import frob.app.pyfmt_runner as pyfmt_mod
from frob.app.config import AppConfig


# frob:ticket T-2251
def _FakeProc(stdout: str = "", returncode: int = 0, stderr: str = ""):  # noqa: N802
    """Minimal `subprocess.CompletedProcess`-shaped stand-in, mirroring
    `tests/unit/test_check.py::_FakeProc` (T-1507's precedent)."""

    class _P:
        def __init__(self):
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = returncode

    return _P()


# frob:ticket T-2251
class TestRun:
    def test_default_delegates_to_run_ruff_autofix(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        # frob:tests src/frob/app/pyfmt_runner.py::run kind="unit"
        calls: list[Path] = []

        def _fake_autofix(root: Path):
            calls.append(root)
            from frob.process.parsers.common import ToolResult

            return [ToolResult(tool="ruff-check-fix", exit_code=0, summary="clean")]

        monkeypatch.setattr(pyfmt_mod, "_run_ruff_autofix", _fake_autofix)
        cfg = AppConfig(format_path=tmp_path, format_select_imports_only=False)
        pyfmt_mod.run(cfg)
        assert calls == [tmp_path.resolve()]
        assert "ruff-check-fix" in capsys.readouterr().out

    def test_select_imports_only_uses_dash_dash_select_i(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        # frob:tests src/frob/app/pyfmt_runner.py::run kind="unit"
        seen_cmds: list[list[str]] = []

        def _fake_run(cmd, **kw):
            seen_cmds.append(cmd)
            return Ok(_FakeProc("", 0))

        monkeypatch.setattr(pyfmt_mod, "guarded_subprocess_run", _fake_run)

        def _fail_autofix(root: Path):
            raise AssertionError("_run_ruff_autofix must not be called in this mode")

        monkeypatch.setattr(pyfmt_mod, "_run_ruff_autofix", _fail_autofix)

        cfg = AppConfig(format_path=tmp_path, format_select_imports_only=True)
        pyfmt_mod.run(cfg)

        assert any(
            "check" in cmd and "--select" in cmd and "I" in cmd for cmd in seen_cmds
        )
        assert any("format" in cmd for cmd in seen_cmds)
        out = capsys.readouterr().out
        assert "ruff-check-fix" in out
        assert "ruff-format-write" in out

    def test_nonzero_exit_propagates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        # frob:tests src/frob/app/pyfmt_runner.py::run kind="unit"
        def _fake_autofix(root: Path):
            from frob.process.parsers.common import Diagnostic, ToolResult

            return [
                ToolResult(
                    tool="ruff-check-fix",
                    exit_code=1,
                    diagnostics=[Diagnostic(severity="error", message="E501 boom")],
                    summary="1 error",
                )
            ]

        monkeypatch.setattr(pyfmt_mod, "_run_ruff_autofix", _fake_autofix)
        cfg = AppConfig(format_path=tmp_path, format_select_imports_only=False)
        with pytest.raises(SystemExit) as exc_info:
            pyfmt_mod.run(cfg)
        assert exc_info.value.code == 1
        assert "E501 boom" in capsys.readouterr().out


# frob:ticket T-2251
class TestRunRuffCheckFixSelectImports:
    def test_missing_binary_yields_typed_result(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/pyfmt_runner.py::_run_ruff_check_fix_select_imports kind="unit"  # noqa: E501
        def _raise(*a, **kw):
            raise FileNotFoundError("ruff not found")

        monkeypatch.setattr(pyfmt_mod, "guarded_subprocess_run", _raise)
        result = pyfmt_mod._run_ruff_check_fix_select_imports(tmp_path)
        assert not result.passed
        assert "tool unavailable" in result.diagnostics[0].message


# frob:ticket T-2251
class TestRuffFormatWriteOnly:
    def test_missing_binary_yields_typed_result(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/pyfmt_runner.py::_ruff_format_write_only kind="unit"
        def _raise(*a, **kw):
            raise FileNotFoundError("ruff not found")

        monkeypatch.setattr(pyfmt_mod, "guarded_subprocess_run", _raise)
        results = pyfmt_mod._ruff_format_write_only(tmp_path)
        assert len(results) == 1
        assert not results[0].passed

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
from frob.app import fmt_runner
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
# frob:ticket T-3906
class TestRun:
    # frob:ticket T-3906
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
        cfg = AppConfig(format_paths=[tmp_path], format_select_imports_only=False)
        pyfmt_mod.run(cfg)
        assert calls == [tmp_path.resolve()]
        assert "ruff-check-fix" in capsys.readouterr().out

    # frob:ticket T-3906
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

        cfg = AppConfig(format_paths=[tmp_path], format_select_imports_only=True)
        pyfmt_mod.run(cfg)

        assert any(
            "check" in cmd and "--select" in cmd and "I" in cmd for cmd in seen_cmds
        )
        assert any("format" in cmd for cmd in seen_cmds)
        out = capsys.readouterr().out
        assert "ruff-check-fix" in out
        assert "ruff-format-write" in out

    # frob:ticket T-3906
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
        cfg = AppConfig(format_paths=[tmp_path], format_select_imports_only=False)
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


# frob:ticket T-3906
class TestRunCheckModeDoesNotWrite:
    """T-3906 acceptance: `frob format --check` closes the gap where only
    the directive half had a preview-without-writing mode -- the code
    half must now do the same."""

    # frob:ticket T-3906
    def test_check_mode_does_not_write(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        # frob:tests src/frob/app/pyfmt_runner.py::run kind="unit"
        write_calls: list[Path] = []

        def _fake_autofix(root: Path):
            write_calls.append(root)
            raise AssertionError("write-mode _run_ruff_autofix must not run --check")

        check_calls: list[Path] = []

        def _fake_check(root, extra_args):
            check_calls.append(root)
            from frob.process.parsers.common import ToolResult

            return [ToolResult(tool="ruff-check", exit_code=0, summary="clean")]

        monkeypatch.setattr(pyfmt_mod, "_run_ruff_autofix", _fake_autofix)
        monkeypatch.setattr(pyfmt_mod, "_run_ruff", _fake_check)
        cfg = AppConfig(format_paths=[tmp_path], format_check=True)
        pyfmt_mod.run(cfg)
        assert not write_calls
        assert check_calls == [tmp_path.resolve()]

    # frob:ticket T-3906
    def test_check_mode_nonzero_exit_on_dirty_tree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/pyfmt_runner.py::run kind="unit"
        def _fake_check(root, extra_args):
            from frob.process.parsers.common import ToolResult

            return [
                ToolResult(
                    tool="ruff-format", exit_code=1, summary="1 file would reformat"
                )
            ]

        monkeypatch.setattr(pyfmt_mod, "_run_ruff", _fake_check)
        cfg = AppConfig(format_paths=[tmp_path], format_check=True)
        with pytest.raises(SystemExit) as exc_info:
            pyfmt_mod.run(cfg)
        assert exc_info.value.code == 1


# frob:ticket T-3906
class TestRunScopeFlags:
    """`--code`/`--directives` scope which half of `frob format` runs;
    neither flag runs both (the pre-consolidation default)."""

    # frob:ticket T-3906
    def test_code_only_skips_directives(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/pyfmt_runner.py::run kind="unit"
        called = []

        def _fail_directives(*a, **kw):
            called.append(True)
            raise AssertionError("directive half must not run under --code")

        monkeypatch.setattr("frob.gates._fmt_directives.format_paths", _fail_directives)

        def _fake_autofix(root: Path):
            from frob.process.parsers.common import ToolResult

            return [ToolResult(tool="ruff-check-fix", exit_code=0, summary="clean")]

        monkeypatch.setattr(pyfmt_mod, "_run_ruff_autofix", _fake_autofix)
        cfg = AppConfig(format_paths=[tmp_path], format_code=True)
        pyfmt_mod.run(cfg)
        assert not called

    # frob:ticket T-3906
    def test_directives_only_skips_ruff(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/pyfmt_runner.py::run kind="unit"
        def _fail_autofix(root: Path):
            raise AssertionError("ruff half must not run under --directives")

        monkeypatch.setattr(pyfmt_mod, "_run_ruff_autofix", _fail_autofix)

        def _fake_directives(root, **kw):
            from frob.gates._fmt_directives import FmtReport

            return FmtReport(changes=())

        monkeypatch.setattr("frob.gates._fmt_directives.format_paths", _fake_directives)
        cfg = AppConfig(format_paths=[tmp_path], format_directives=True)
        pyfmt_mod.run(cfg)


# frob:ticket T-3906
class TestRunRuffCheckSelectImportsNoFix:
    # frob:waive DUP001 reason="the missing-binary-yields-typed-result shape is the \
    # established pattern every sibling ruff-subprocess-wrapper test in this file uses \
    # (TestRunRuffCheckFixSelectImports/TestRuffFormatWriteOnly above); this is a \
    # fourth instance of the SAME established shape over a different wrapped function, \
    # not a new clone to extract"
    # frob:waive DUP002 reason="same established per-wrapper missing-binary shape as \
    # DUP001's waiver above"
    # frob:ticket T-3906
    def test_missing_binary_yields_typed_result(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/pyfmt_runner.py::_run_ruff_check_select_imports_no_fix kind="unit"  # noqa: E501
        # frob:waive FMT001 reason="single-line frob:tests directive naming a long \
        # symref -- already at frob fmt's own canonical form, same unwrappable shape \
        # as the sibling TestRunRuffCheckFixSelectImports directive above"
        def _raise(*a, **kw):
            raise FileNotFoundError("ruff not found")

        monkeypatch.setattr(pyfmt_mod, "guarded_subprocess_run", _raise)
        result = pyfmt_mod._run_ruff_check_select_imports_no_fix(tmp_path)
        assert not result.passed
        assert "tool unavailable" in result.diagnostics[0].message


# frob:ticket T-3906
class TestRuffFormatCheckOnly:
    # frob:waive DUP001 reason="the missing-binary-yields-typed-result shape is the \
    # established pattern every sibling ruff-subprocess-wrapper test in this file uses \
    # (TestRunRuffCheckFixSelectImports/TestRuffFormatWriteOnly above); this is a \
    # fourth instance of the SAME established shape over a different wrapped function, \
    # not a new clone to extract"
    # frob:ticket T-3906
    def test_missing_binary_yields_typed_result(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/pyfmt_runner.py::_ruff_format_check_only kind="unit"
        def _raise(*a, **kw):
            raise FileNotFoundError("ruff not found")

        monkeypatch.setattr(pyfmt_mod, "guarded_subprocess_run", _raise)
        result = pyfmt_mod._ruff_format_check_only(tmp_path)
        assert not result.passed
        assert "tool unavailable" in result.diagnostics[0].message


# frob:ticket T-3906
class TestRunMultiplePaths:
    """T-3312 (folded into T-3906): `frob format`'s path argument is a
    LIST, not one path."""

    # frob:ticket T-3906
    def test_multiple_paths_each_get_processed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/pyfmt_runner.py::run kind="unit"
        a = tmp_path / "a"
        b = tmp_path / "b"
        a.mkdir()
        b.mkdir()
        calls: list[Path] = []

        def _fake_autofix(root: Path):
            calls.append(root)
            from frob.process.parsers.common import ToolResult

            return [ToolResult(tool="ruff-check-fix", exit_code=0, summary="clean")]

        monkeypatch.setattr(pyfmt_mod, "_run_ruff_autofix", _fake_autofix)
        cfg = AppConfig(format_paths=[a, b], format_code=True)
        pyfmt_mod.run(cfg)
        assert calls == [a.resolve(), b.resolve()]


# frob:ticket T-3906
class TestFormattedTreePassesCheckCleanly:
    """MUST-STAY-QUIET fixture: a formatted tree passes `--check` cleanly
    for both halves. Mocked at the same boundary every other test in this
    file uses -- no real fs.write/fs.read, matching this file's own
    established no-real-filesystem pattern."""

    # frob:tests tests/unit/test_pyfmt_runner.py::TestFormattedTreePassesCheckCleanly.test_clean_tree_check_exits_zero_for_both_halves  # noqa: E501
    # frob:waive FMT001 reason="single-line frob:tests directive naming a long test \
    # node id -- already at frob fmt's own canonical form, same unwrappable shape as \
    # the other MUST-FIRE/MUST-STAY-QUIET fixture directives in this class group"
    # frob:ticket T-3906
    def test_clean_tree_check_exits_zero_for_both_halves(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _fake_check(root, extra_args):
            from frob.process.parsers.common import ToolResult

            return [ToolResult(tool="ruff-check", exit_code=0, summary="clean")]

        monkeypatch.setattr(pyfmt_mod, "_run_ruff", _fake_check)

        def _fake_directives(root, **kw):
            from frob.gates._fmt_directives import FmtReport

            return FmtReport(changes=())

        monkeypatch.setattr("frob.gates._fmt_directives.format_paths", _fake_directives)

        cfg = AppConfig(format_paths=[tmp_path], format_check=True)
        pyfmt_mod.run(cfg)  # must not raise SystemExit


# frob:ticket T-3906
class TestDeprecatedAliasStillWorks:
    """MUST-FIRE fixture: the deprecated `frob fmt` alias still works and
    emits its deprecation notice. Mocked at the directive-canonicalizer
    boundary, same no-real-filesystem pattern as every other test here."""

    # frob:tests tests/unit/test_pyfmt_runner.py::TestDeprecatedAliasStillWorks.test_fmt_alias_still_formats_and_warns  # noqa: E501
    # frob:waive FMT001 reason="single-line frob:tests directive naming a long test \
    # node id -- already at frob fmt's own canonical form, same unwrappable shape as \
    # the other MUST-FIRE/MUST-STAY-QUIET fixture directives in this class group"
    # frob:ticket T-3906
    def test_fmt_alias_still_formats_and_warns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
    ) -> None:
        def _fake_directives(root, **kw):
            from frob.gates._fmt_directives import FmtReport

            return FmtReport(changes=())

        monkeypatch.setattr("frob.gates._fmt_directives.format_paths", _fake_directives)

        cfg = AppConfig(fmt_paths=[tmp_path], fmt_check=False, fmt_json=False)
        fmt_runner.run(cfg)

        captured = capsys.readouterr()
        assert "DEPRECATED" in captured.err
        assert "frob format --directives" in captured.err

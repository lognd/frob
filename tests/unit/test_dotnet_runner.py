"""Unit tests for `frob.testing._dotnet_runner`'s dotnet evidence channel
(T-4508): `_csharp_fqn`/`_dotnet_filter_expr` transforms, `_parse_trx`
against a static TRX fixture, and `run_dotnet_tests` end-to-end against a
fake `dotnet` executable placed on `PATH` (never a real `dotnet`/Unity
binary, per this ticket's own instruction)."""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

from frob.testing._dotnet_runner import (
    _csharp_fqn,
    _dotnet_filter_expr,
    _parse_trx,
    run_dotnet_tests,
)
from frob.testing._runners import TestingError

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "lang" / "csharp" / "tests"

_NODE_A = (
    "tests/SampleNunitTests.cs::Frob.Fixtures.Csharp.SampleNunitTests::AddsTwoNumbers"
)
_NODE_B = "tests/SampleNunitTests.cs::Frob.Fixtures.Csharp.SampleNunitTests::AddsPair"


class TestCsharpFqn:
    """`_csharp_fqn`'s node-id-to-dotted-FQN transform (T-4508)."""

    # frob:tests tests/unit/test_dotnet_runner.py::TestCsharpFqn.test_three_part_node_id_drops_path_joins_dots  # noqa: E501
    def test_three_part_node_id_drops_path_joins_dots(self) -> None:
        # frob:tests src/frob/testing/_dotnet_runner.py::_csharp_fqn
        assert (
            _csharp_fqn(_NODE_A)
            == "Frob.Fixtures.Csharp.SampleNunitTests.AddsTwoNumbers"
        )

    # frob:tests tests/unit/test_dotnet_runner.py::TestCsharpFqn.test_no_separator_passes_through_unchanged  # noqa: E501
    def test_no_separator_passes_through_unchanged(self) -> None:
        # frob:tests src/frob/testing/_dotnet_runner.py::_csharp_fqn
        assert _csharp_fqn("bare-id") == "bare-id"


class TestDotnetFilterExpr:
    """`_dotnet_filter_expr`'s `--filter` expression rendering (T-4508)."""

    # frob:tests tests/unit/test_dotnet_runner.py::TestDotnetFilterExpr.test_single_item_no_or_operator  # noqa: E501
    def test_single_item_no_or_operator(self) -> None:
        # frob:tests src/frob/testing/_dotnet_runner.py::_dotnet_filter_expr
        assert (
            _dotnet_filter_expr((_NODE_A,))
            == "FullyQualifiedName=Frob.Fixtures.Csharp.SampleNunitTests.AddsTwoNumbers"
        )

    # frob:tests tests/unit/test_dotnet_runner.py::TestDotnetFilterExpr.test_multiple_items_ored  # noqa: E501
    def test_multiple_items_ored(self) -> None:
        # frob:tests src/frob/testing/_dotnet_runner.py::_dotnet_filter_expr
        expr = _dotnet_filter_expr((_NODE_A, _NODE_B))
        assert expr == (
            "FullyQualifiedName=Frob.Fixtures.Csharp.SampleNunitTests.AddsTwoNumbers"
            "|FullyQualifiedName=Frob.Fixtures.Csharp.SampleNunitTests.AddsPair"
        )


class TestParseTrx:
    """`_parse_trx`'s TRX-XML-to-outcome-map parse (T-4508), against the
    static fixture `tests/fixtures/lang/csharp/tests/sample_results.trx`."""

    # frob:tests tests/unit/test_dotnet_runner.py::TestParseTrx.test_parses_static_fixture_into_fqn_outcome_map  # noqa: E501
    def test_parses_static_fixture_into_fqn_outcome_map(self) -> None:
        # frob:tests src/frob/testing/_dotnet_runner.py::_parse_trx
        text = (_FIXTURES_DIR / "sample_results.trx").read_text(encoding="utf-8")
        result = _parse_trx(text)
        assert result.is_ok
        assert result.danger_ok == {
            "Frob.Fixtures.Csharp.SampleNunitTests.AddsTwoNumbers": "Passed",
            "Frob.Fixtures.Csharp.SampleNunitTests.AddsPair": "Failed",
        }

    # frob:tests tests/unit/test_dotnet_runner.py::TestParseTrx.test_malformed_xml_is_err_not_empty  # noqa: E501
    def test_malformed_xml_is_err_not_empty(self) -> None:
        # frob:tests src/frob/testing/_dotnet_runner.py::_parse_trx
        text = (_FIXTURES_DIR / "malformed_results.xml").read_text(encoding="utf-8")
        result = _parse_trx(text)
        assert result.is_err
        assert result.danger_err == TestingError.DotnetResultsUnreadable


# frob:waive WIRE001 reason="a fixture helper used only by this file's own tests to \
# fake a dotnet binary on PATH -- there is no production caller to wire it to by \
# design" permanent="true"
def _write_fake_dotnet(bin_dir: Path, fixture_name: str, exit_code: int = 0) -> None:
    """A fake `dotnet` on `bin_dir` that copies the named static TRX
    fixture to whatever `--logger trx;LogFileName=<path>` names, then
    exits `exit_code` -- never a real `dotnet`/Unity binary (T-4508's own
    instruction). On Windows, a POSIX `#!/bin/sh` script is not
    executable (no shebang interpreter, and PATHEXT requires .exe/.bat/
    .cmd) -- write a `dotnet.cmd` batch equivalent there instead (T-5384)."""
    fixture_path = _FIXTURES_DIR / fixture_name
    if sys.platform == "win32":
        script = bin_dir / "dotnet.cmd"
        script.write_text(
            "@echo off\r\n"
            "set OUT=\r\n"
            ":parse\r\n"
            'if "%~1"=="" goto after\r\n'
            'echo %~1 | findstr /b "trx;LogFileName=" >nul && '
            "set OUT=%~1\r\n"
            "shift\r\n"
            "goto parse\r\n"
            ":after\r\n"
            'if not "%OUT%"=="" copy /y '
            f'"{fixture_path}" "%OUT:trx;LogFileName=%"\r\n'
            f"exit /b {exit_code}\r\n",
            encoding="utf-8",
        )
        return
    script = bin_dir / "dotnet"
    script.write_text(
        "#!/bin/sh\n"
        'out=""\n'
        'for arg in "$@"; do\n'
        '  case "$arg" in\n'
        '    trx\\;LogFileName=*) out="${arg#trx;LogFileName=}" ;;\n'
        "  esac\n"
        "done\n"
        f'if [ -n "$out" ]; then cp "{fixture_path}" "$out"; fi\n'
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


# frob:waive WIRE001 reason="a fixture helper used only by this file's own tests to \
# fake a crashing dotnet binary on PATH -- there is no production caller to wire it to \
# by design" permanent="true"
def _write_crashing_dotnet(bin_dir: Path) -> None:
    """A fake `dotnet` that crashes without ever writing a results file
    (T-4508's third acceptance criterion, applied here to dotnet too). See
    `_write_fake_dotnet` for why Windows needs its own `.cmd` (T-5384)."""
    if sys.platform == "win32":
        script = bin_dir / "dotnet.cmd"
        script.write_text(
            "@echo off\r\necho fatal error 1>&2\r\nexit /b 1\r\n",
            encoding="utf-8",
        )
        return
    script = bin_dir / "dotnet"
    script.write_text("#!/bin/sh\necho 'fatal error' >&2\nexit 1\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


class TestRunDotnetTests:
    """`run_dotnet_tests` end-to-end (T-4508), driven entirely by a fake
    `dotnet` placed first on `PATH` via `tmp_path` -- no real `dotnet`
    process is ever spawned."""

    # frob:tests tests/unit/test_dotnet_runner.py::TestRunDotnetTests.test_maps_passing_and_failing_ids  # noqa: E501
    def test_maps_passing_and_failing_ids(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/testing/_dotnet_runner.py::run_dotnet_tests
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        _write_fake_dotnet(bin_dir, "sample_results.trx")
        monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

        result = run_dotnet_tests((_NODE_A, _NODE_B), tmp_path)
        assert result.is_ok
        assert result.danger_ok == {_NODE_A: True, _NODE_B: False}

    # frob:tests tests/unit/test_dotnet_runner.py::TestRunDotnetTests.test_no_items_is_ok_empty  # noqa: E501
    def test_no_items_is_ok_empty(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_dotnet_runner.py::run_dotnet_tests
        result = run_dotnet_tests((), tmp_path)
        assert result.is_ok
        assert result.danger_ok == {}

    # frob:tests tests/unit/test_dotnet_runner.py::TestRunDotnetTests.test_crash_with_no_results_file_is_run_failed  # noqa: E501
    def test_crash_with_no_results_file_is_run_failed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/testing/_dotnet_runner.py::run_dotnet_tests
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        _write_crashing_dotnet(bin_dir)
        monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

        result = run_dotnet_tests((_NODE_A,), tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.DotnetRunFailed

    # frob:tests tests/unit/test_dotnet_runner.py::TestRunDotnetTests.test_requested_id_missing_from_results_is_err  # noqa: E501
    def test_requested_id_missing_from_results_is_err(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/testing/_dotnet_runner.py::run_dotnet_tests
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        _write_fake_dotnet(bin_dir, "sample_results.trx")
        monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

        unknown_node = "tests/SampleNunitTests.cs::Frob.Fixtures.Csharp.SampleNunitTests::NoSuchMethod"
        result = run_dotnet_tests((unknown_node,), tmp_path)
        assert result.is_err
        assert result.danger_err == TestingError.DotnetResultsUnreadable

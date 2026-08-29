"""T-3311: `frob.process._pytest_spawn`'s `resolve_pytest_argv`/
`pytest_importable` -- the ONE pytest-spawn resolution helper collapsing
the three divergent conventions measured across this codebase
(`sys.executable -m pytest`, hardcoded `uv run pytest`, and a bare
`pytest` PATH lookup)."""

from __future__ import annotations

import sys
from unittest.mock import patch

from frob.process._pytest_spawn import (
    PytestSpawnError,
    pytest_importable,
    resolve_pytest_argv,
)


class TestPytestImportable:
    # frob:ticket T-3311
    def test_true_when_importable(self) -> None:
        # frob:tests tests/unit/test_pytest_spawn.py::TestPytestImportable.test_true_when_importable  # noqa: E501
        assert pytest_importable(sys.executable) is True

    # frob:ticket T-3311
    def test_false_when_not_importable(self) -> None:
        # frob:tests tests/unit/test_pytest_spawn.py::TestPytestImportable.test_false_when_not_importable  # noqa: E501
        # A python that genuinely does not exist -- guarded_subprocess_run's
        # own spawn refusal path (not a probe-truthiness assumption).
        assert pytest_importable("/nonexistent/interpreter/binary") is False


class TestResolvePytestArgv:
    """resolve_pytest_argv must default to sys.executable (T-3268's
    adopted convention), never a bare PATH lookup or a hardcoded `uv run`."""

    # frob:ticket T-3311
    def test_ok_uses_sys_executable(self) -> None:
        # frob:tests tests/unit/test_pytest_spawn.py::TestResolvePytestArgv.test_ok_uses_sys_executable  # noqa: E501
        result = resolve_pytest_argv("-q")
        assert result.is_ok
        argv = result.danger_ok
        assert argv[0] == sys.executable
        assert argv[1:3] == ["-m", "pytest"]

    # frob:ticket T-3311
    def test_appends_extra_args(self) -> None:
        # frob:tests tests/unit/test_pytest_spawn.py::TestResolvePytestArgv.test_appends_extra_args  # noqa: E501
        result = resolve_pytest_argv("tests/test_x.py::test_y", "-q", "-o", "addopts=")
        assert result.is_ok
        assert result.danger_ok == [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_x.py::test_y",
            "-q",
            "-o",
            "addopts=",
        ]

    # frob:ticket T-3311
    def test_err_when_not_importable(self) -> None:
        # frob:tests tests/unit/test_pytest_spawn.py::TestResolvePytestArgv.test_err_when_not_importable  # noqa: E501
        with patch("frob.process._pytest_spawn.pytest_importable", return_value=False):
            result = resolve_pytest_argv("-q")
        assert result.is_err
        assert result.danger_err == PytestSpawnError.NotImportable

    # frob:ticket T-3311
    def test_honors_explicit_python_override(self) -> None:
        # frob:tests tests/unit/test_pytest_spawn.py::TestResolvePytestArgv.test_honors_explicit_python_override  # noqa: E501
        with patch(
            "frob.process._pytest_spawn.pytest_importable", return_value=True
        ) as probe:
            result = resolve_pytest_argv("-q", python="/some/other/python")
        probe.assert_called_once_with("/some/other/python")
        assert result.is_ok
        assert result.danger_ok == ["/some/other/python", "-m", "pytest", "-q"]

"""Unit tests for `scripts/_require_python.py` (T-2236): the shared
interpreter-version guard `scripts/fleet_status.py` and
`scripts/frob-telemetry-hook` both call before any 3.11+-only import.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from tests.unit.conftest import _load_script

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO_ROOT / "scripts"

require_python_mod = _load_script("_require_python")


class TestRequiredVersion:
    """`_require_python._required_version`."""

    def test_parses_a_real_requires_python_line(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "x"\nrequires-python = ">=3.11"\n', encoding="utf-8"
        )
        assert require_python_mod._required_version(pyproject) == (3, 11)

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert require_python_mod._required_version(tmp_path / "nope.toml") is None

    def test_missing_requires_python_line_returns_none(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "x"\n', encoding="utf-8")
        assert require_python_mod._required_version(pyproject) is None


class TestRequirePython:
    """`_require_python.require_python` (T-2236)."""

    def test_older_interpreter_exits_nonzero_with_actionable_message(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """(MUST FAIL FIRST) An interpreter older than requires-python
        prints the required version, the found version, and the correct
        `uv run python ...` invocation, and exits non-zero -- never a
        raw ImportError traceback."""
        with mock.patch.object(sys, "version_info", (3, 9, 0, "final", 0)):
            with pytest.raises(SystemExit) as exc_info:
                require_python_mod.require_python(str(_SCRIPTS / "fleet_status.py"))
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "3.11" in err
        assert "3.9.0" in err
        assert "uv run python" in err
        assert "fleet_status.py" in err

    def test_supported_interpreter_is_a_silent_noop(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """MUST-STILL-PASS: the current (supported) interpreter passes
        through with no output and no exit -- the guard is invisible on
        the happy path."""
        require_python_mod.require_python(str(_SCRIPTS / "fleet_status.py"))
        out = capsys.readouterr()
        assert out.out == ""
        assert out.err == ""

    def test_exact_boundary_version_passes(self) -> None:
        """A `sys.version_info` exactly equal to the requirement (not
        just strictly newer) must pass -- `>=`, not `>`."""
        with mock.patch.object(sys, "version_info", (3, 11, 0, "final", 0)):
            require_python_mod.require_python(str(_SCRIPTS / "fleet_status.py"))

    def test_unknown_requirement_fails_open_never_blocks(
        self, tmp_path: Path
    ) -> None:
        """MUST-STILL-PASS: when the requirement cannot be determined at
        all (e.g. this guard invoked against a script outside a repo with
        a readable pyproject.toml), it must fail OPEN -- never block a
        script it cannot evaluate."""
        fake_script = tmp_path / "somewhere" / "script.py"
        fake_script.parent.mkdir(parents=True)
        fake_script.write_text("", encoding="utf-8")
        with mock.patch.object(sys, "version_info", (3, 0, 0, "final", 0)):
            require_python_mod.require_python(str(fake_script))


class TestFleetStatusHappyPathUnaffected:
    """MUST-STILL-PASS (T-2236 acceptance [3]): under a supported
    interpreter, scripts/fleet_status.py's output is byte-identical
    before and after this ticket's diff. Verified manually against
    main's own copy during implementation; this test pins the guard's
    own silence so a regression here is caught mechanically."""

    def test_fleet_status_runs_clean_under_the_project_venv(self) -> None:
        result = subprocess.run(
            [sys.executable, str(_SCRIPTS / "fleet_status.py")],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert "ERROR:" not in result.stdout
        assert "requires Python" not in result.stdout
        assert "requires Python" not in result.stderr

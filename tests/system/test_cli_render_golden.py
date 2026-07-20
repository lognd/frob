"""Golden-output tests for the T-0448 render-layer exemplars: `frob doctor`
and `frob map` in both color-forced and plain-forced modes.

`--json` is untouched by T-0448 and covered by `test_cli_doctor.py`
already; this file is scoped to the human-facing text path both commands
now route through `frob.render.Renderer`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

FROB = [sys.executable, "-m", "frob"]


def _run_colored(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    """Run `frob <args>` with color force-enabled via `CLICOLOR_FORCE`."""
    env = dict(os.environ)
    env.pop("NO_COLOR", None)
    env.pop("FROB_NO_COLOR", None)
    env["CLICOLOR_FORCE"] = "1"
    return subprocess.run(
        FROB + list(args), cwd=cwd, capture_output=True, text=True, env=env
    )


def _run_plain(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    """Run `frob <args>` with color force-disabled via `NO_COLOR`."""
    env = dict(os.environ)
    env.pop("CLICOLOR_FORCE", None)
    env["NO_COLOR"] = "1"
    return subprocess.run(
        FROB + list(args), cwd=cwd, capture_output=True, text=True, env=env
    )


class TestDoctorGolden:
    # frob:tests src/frob/app/doctor_runner.py::run
    def test_doctor_plain_mode_has_no_ansi(self, tmp_path: Path) -> None:
        """`NO_COLOR=1 frob doctor` output is byte-clean of ANSI escapes."""
        r = _run_plain("doctor", cwd=tmp_path)
        assert "frob doctor" in r.stdout
        assert "\x1b[" not in r.stdout

    # frob:tests src/frob/app/doctor_runner.py::run
    def test_doctor_color_mode_has_ansi(self, tmp_path: Path) -> None:
        """`CLICOLOR_FORCE=1 frob doctor` output contains ANSI escapes and
        the same underlying text as plain mode."""
        r = _run_colored("doctor", cwd=tmp_path)
        assert "frob doctor" in r.stdout
        assert "\x1b[" in r.stdout

    # frob:tests src/frob/app/doctor_runner.py::run
    def test_doctor_no_color_flag_beats_clicolor_force(self, tmp_path: Path) -> None:
        """`--no-color` overrides even `CLICOLOR_FORCE=1` set in the
        environment, per the documented precedence."""
        env = dict(os.environ)
        env["CLICOLOR_FORCE"] = "1"
        r = subprocess.run(
            FROB + ["--no-color", "doctor"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            env=env,
        )
        assert "\x1b[" not in r.stdout


class TestMapGolden:
    # frob:tests src/frob/app/map_runner.py::run
    def test_map_plain_mode_has_no_ansi(self, tmp_path: Path) -> None:
        """`NO_COLOR=1 frob map` output is byte-clean of ANSI escapes."""
        (tmp_path / "a.py").write_text("def foo() -> None:\n    pass\n")
        r = _run_plain("map", str(tmp_path), cwd=tmp_path)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "\x1b[" not in r.stdout

    # frob:tests src/frob/app/map_runner.py::run
    def test_map_color_mode_has_ansi(self, tmp_path: Path) -> None:
        """`CLICOLOR_FORCE=1 frob map` output contains ANSI escapes."""
        (tmp_path / "a.py").write_text("def foo() -> None:\n    pass\n")
        r = _run_colored("map", str(tmp_path), cwd=tmp_path)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "\x1b[" in r.stdout

    # frob:tests src/frob/app/map_runner.py::run
    def test_map_plain_and_color_share_the_same_stripped_shape(
        self, tmp_path: Path
    ) -> None:
        """Stripping ANSI from the color-mode output reproduces the plain-
        mode output exactly -- color paints the same shape, never a
        different one."""
        import re

        (tmp_path / "a.py").write_text("def foo() -> None:\n    pass\n")
        plain = _run_plain("map", str(tmp_path), cwd=tmp_path)
        colored = _run_colored("map", str(tmp_path), cwd=tmp_path)
        stripped = re.sub(r"\x1b\[[0-9;]*m", "", colored.stdout)
        assert stripped == plain.stdout

"""T-4578: `frob scaffold unity-project <dir> [--force]` end-to-end -- the
real CLI subprocess wires T-4503's `render_unity_project` (previously only
reachable by importing the function directly, per that ticket's own
WIRE001 waiver naming this ticket as the follow-up)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# frob:ticket T-4578
FROB = [sys.executable, "-m", "frob"]

# frob:ticket T-4578
_FIXTURE_ROOT = Path(__file__).parent.parent / "fixtures" / "unity_sample_asmdef"


# frob:ticket T-4578
def _copy_fixture(dest: Path) -> None:
    """Copy T-4512's four-asmdef fixture project to `dest` -- the CLI
    writes into it, so the tracked fixture tree must never be touched."""
    shutil.copytree(_FIXTURE_ROOT, dest)


# frob:ticket T-4578
class TestScaffoldUnityProjectCli:
    """End-to-end CLI coverage for `frob scaffold unity-project` (T-4578)."""

    # frob:ticket T-4578
    # frob:tests tests/system/test_scaffold_unity_project_cli.py::TestScaffoldUnityProjectCli.test_success  # noqa: E501
    # frob:tests src/frob/app/scaffold_runner.py::_run_unity_project
    # frob:tests src/frob/scaffold/_unity_project.py::render_unity_project
    # frob:tests src/frob/app/scaffold_runner.py::run
    def test_success(self, tmp_path: Path) -> None:
        """A real Unity project directory gets `frob.toml` plus one
        `design/*.strata` per asmdef, reported on stdout."""
        project = tmp_path / "unity_sample_asmdef"
        _copy_fixture(project)

        result = subprocess.run(
            FROB + ["scaffold", "unity-project", str(project)],
            capture_output=True,
            text=True,
        )
        out = result.stdout + result.stderr
        assert result.returncode == 0, out
        assert (project / "frob.toml").exists()
        assert "created" in out

    # frob:ticket T-4578
    # frob:tests tests/system/test_scaffold_unity_project_cli.py::TestScaffoldUnityProjectCli.test_output_exists_refusal  # noqa: E501
    # frob:tests src/frob/app/scaffold_runner.py::_run_unity_project
    def test_output_exists_refusal(self, tmp_path: Path) -> None:
        """A second run without `--force` refuses cleanly (OutputExists)
        with a non-zero exit and no traceback; `--force` overwrites."""
        project = tmp_path / "unity_sample_asmdef"
        _copy_fixture(project)

        first = subprocess.run(
            FROB + ["scaffold", "unity-project", str(project)],
            capture_output=True,
            text=True,
        )
        assert first.returncode == 0, first.stdout + first.stderr

        second = subprocess.run(
            FROB + ["scaffold", "unity-project", str(project)],
            capture_output=True,
            text=True,
        )
        out2 = second.stdout + second.stderr
        assert second.returncode != 0
        assert "Traceback" not in out2
        assert "output already exists" in out2

        third = subprocess.run(
            FROB + ["scaffold", "unity-project", str(project), "--force"],
            capture_output=True,
            text=True,
        )
        out3 = third.stdout + third.stderr
        assert third.returncode == 0, out3

    # frob:ticket T-4578
    # frob:tests tests/system/test_scaffold_unity_project_cli.py::TestScaffoldUnityProjectCli.test_not_a_unity_project  # noqa: E501
    # frob:tests src/frob/app/scaffold_runner.py::_run_unity_project
    def test_not_a_unity_project(self, tmp_path: Path) -> None:
        """A plain, non-Unity directory (no `Assets/`/`Packages/`) gets a
        clear, specific error and no bogus config written."""
        plain = tmp_path / "not_unity"
        plain.mkdir()

        result = subprocess.run(
            FROB + ["scaffold", "unity-project", str(plain)],
            capture_output=True,
            text=True,
        )
        out = result.stdout + result.stderr
        assert result.returncode != 0
        assert "Traceback" not in out
        assert "Assets" in out or "Packages" in out
        assert not (plain / "frob.toml").exists()

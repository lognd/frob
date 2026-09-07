"""T-4132: `pyproject.toml` declares `py.typed` in package-data, but a
declaration is not the artifact. Setuptools does not error on a
package-data pattern matching zero files -- it silently includes nothing --
which is exactly how this repo shipped untyped for as long as it did. A
fixture that reads `pyproject.toml` would have passed throughout that whole
period; only inspecting a BUILT wheel catches it, so every test in this
module builds a real wheel and looks inside it.
"""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from frob.scaffold.project import render_project

pytestmark = pytest.mark.slow

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _uv_available() -> bool:
    """Whether `uv` is on PATH -- these tests need it to build real wheels,
    skipped (not failed) when it is not, same posture as this suite's other
    toolchain-dependent system tests."""
    return shutil.which("uv") is not None


def _wheel_members(wheel: Path) -> list[str]:
    """The full file list inside `wheel`, for asserting on what a real
    built artifact actually contains rather than what config claims it
    contains."""
    with zipfile.ZipFile(wheel) as zf:
        return zf.namelist()


@pytest.mark.skipif(not _uv_available(), reason="uv not on PATH")
class TestFrobWheelShipsPyTyped:
    """MUST-FIRE fixture: a wheel built from this repository must contain a
    `py.typed` marker at the `frob` package root. This is the exact
    regression T-4132 found -- the declaration existed, the file backing it
    did not, and the built artifact carried zero matching entries."""

    def test_built_wheel_contains_py_typed_marker(self, tmp_path: Path) -> None:
        """A wheel built straight from this checkout carries `frob/py.typed`
        -- the MUST-FIRE fixture: this test would have failed throughout
        the entire period the marker file did not exist."""
        out_dir = tmp_path / "dist"
        result = subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(out_dir)],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        (wheel,) = out_dir.glob("frob-*.whl")
        members = _wheel_members(wheel)
        assert "frob/py.typed" in members, (
            "built wheel is missing the py.typed marker at the package "
            f"root; contents sample: {members[:10]}"
        )

    def test_built_wheel_does_not_duplicate_or_drop_other_package_data(
        self, tmp_path: Path
    ) -> None:
        """MUST-STAY-QUIET: adding the marker must not disturb the other
        declared package-data files (`logging/config.toml`) -- each should
        appear exactly once."""
        out_dir = tmp_path / "dist"
        result = subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(out_dir)],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        (wheel,) = out_dir.glob("frob-*.whl")
        members = _wheel_members(wheel)
        assert members.count("frob/logging/config.toml") == 1
        assert members.count("frob/py.typed") == 1


@pytest.mark.skipif(not _uv_available(), reason="uv not on PATH")
@pytest.mark.parametrize("project_type", ["python-library", "python-tool"])
class TestScaffoldedProjectShipsPyTyped:
    """THIRD FIXTURE: a freshly scaffolded project must build a wheel that
    contains its OWN `py.typed` marker -- the same declaration is templated
    into the shared scaffold packaging config, so every scaffolded project
    inherited the identical false claim until the scaffold manifest also
    wrote the marker file, not just the declaration."""

    def test_scaffolded_project_wheel_contains_py_typed_marker(
        self, tmp_path: Path, project_type: str
    ) -> None:
        """Scaffold `project_type` into a temp directory, build a real
        wheel from it, and confirm the wheel -- not the generated
        pyproject.toml -- carries its own py.typed marker."""
        name = "demoproj"
        result = render_project(project_type, name, tmp_path)
        assert result.is_ok, result.err

        project_dir = tmp_path / name
        out_dir = tmp_path / "dist"
        build = subprocess.run(
            ["uv", "build", "--wheel", "--out-dir", str(out_dir)],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert build.returncode == 0, build.stdout + build.stderr
        (wheel,) = out_dir.glob(f"{name}-*.whl")
        members = _wheel_members(wheel)
        assert f"{name}/py.typed" in members, (
            f"wheel built from a freshly scaffolded {project_type} project "
            f"is missing its own py.typed marker; contents sample: "
            f"{members[:10]}"
        )

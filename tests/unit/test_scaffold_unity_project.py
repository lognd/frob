"""Unit tests for `frob.scaffold.project.render_unity_project` (T-4503):
direct calls against a copy of T-4512's `unity_sample_asmdef` fixture, no
subprocess/uv -- covers this ticket's three acceptance criteria (frob.toml
with Unity excludes + one design/*.strata per asmdef; OutputExists refusal
without --force; a clear error for a non-Unity directory)."""

from __future__ import annotations

import shutil
import tomllib
from pathlib import Path

import pytest

from frob.excludes import UNITY_EXCLUDE_GLOBS
from frob.scaffold._unity_project import render_unity_project
from frob.scaffold.project import ScaffoldError

_FIXTURE_ROOT = Path(__file__).parent.parent / "fixtures" / "unity_sample_asmdef"


@pytest.fixture
def unity_project(tmp_path: Path) -> Path:
    """A private, writable copy of T-4512's four-asmdef fixture project --
    `render_unity_project` writes into its root, so the tracked fixture
    tree itself must never be touched."""
    dest = tmp_path / "unity_sample_asmdef"
    shutil.copytree(_FIXTURE_ROOT, dest)
    return dest


class TestRenderUnityProject:
    """Acceptance criterion 1: frob.toml with Unity excludes pre-populated
    plus one design/*.strata file per detected .asmdef."""

    # frob:tests tests/unit/test_scaffold_unity_project.py::TestRenderUnityProject.test_writes_frob_toml_with_unity_excludes  # noqa: E501
    # frob:tests src/frob/scaffold/_unity_project.py::render_unity_project  # noqa: E501
    def test_writes_frob_toml_with_unity_excludes(self, unity_project: Path) -> None:
        result = render_unity_project(unity_project)
        assert result.is_ok, result.err

        toml_path = unity_project / "frob.toml"
        assert toml_path.exists()
        with toml_path.open("rb") as f:
            doc = tomllib.load(f)
        excludes = doc.get("graph", {}).get("exclude", [])
        for glob in UNITY_EXCLUDE_GLOBS:
            assert glob in excludes

    # frob:tests src/frob/scaffold/_unity_project.py::render_unity_project  # noqa: E501
    # frob:tests tests/unit/test_scaffold_unity_project.py::TestRenderUnityProject.test_one_strata_file_per_asmdef  # noqa: E501
    def test_one_strata_file_per_asmdef(self, unity_project: Path) -> None:
        result = render_unity_project(unity_project)
        assert result.is_ok, result.err

        design_dir = unity_project / "design"
        strata_files = sorted(p.name for p in design_dir.glob("*.strata"))
        # The fixture has four .asmdef files (Editor, Runtime, RuntimeUtils,
        # Tests) plus the always-present default-assembly node (T-4512's
        # own acceptance criterion 3) -- five files total, one per node.
        assert len(strata_files) == 5
        assert "unity_default_assembly.strata" in strata_files
# frob:tests src/frob/scaffold/_unity_project.py::render_unity_project  # noqa: E501

    # frob:tests tests/unit/test_scaffold_unity_project.py::TestRenderUnityProject.test_returned_paths_all_exist  # noqa: E501
    def test_returned_paths_all_exist(self, unity_project: Path) -> None:
        result = render_unity_project(unity_project)
        assert result.is_ok, result.err
        for path in result.danger_ok:
            assert path.exists()


class TestOutputExistsRefusal:
    """Acceptance criterion 2: a second run without --force refuses rather
    # frob:tests src/frob/scaffold/_unity_project.py::render_unity_project  # noqa: E501
    than silently overwriting."""

    # frob:tests tests/unit/test_scaffold_unity_project.py::TestOutputExistsRefusal.test_second_run_without_force_is_output_exists  # noqa: E501
    def test_second_run_without_force_is_output_exists(
        self, unity_project: Path
    ) -> None:
        first = render_unity_project(unity_project)
        assert first.is_ok, first.err

        second = render_unity_project(unity_project)
        # frob:tests src/frob/scaffold/_unity_project.py::render_unity_project  # noqa: E501
        assert second.is_err
        assert second.danger_err is ScaffoldError.OutputExists

    # frob:tests tests/unit/test_scaffold_unity_project.py::TestOutputExistsRefusal.test_refusal_leaves_no_partial_scaffold  # noqa: E501
    # frob:tests src/frob/scaffold/_unity_project.py::render_unity_project  # noqa: E501
    def test_refusal_leaves_no_partial_scaffold(self, unity_project: Path) -> None:
        # A pre-existing frob.toml alone (no design/ yet) must still
        # refuse -- the OutputExists check runs before ANY file is
        # written, so a partial prior scaffold is never silently
        # completed either.
        (unity_project / "frob.toml").write_text("# pre-existing\n", encoding="utf-8")
        result = render_unity_project(unity_project)
        assert result.is_err
        assert result.danger_err is ScaffoldError.OutputExists
        assert not (unity_project / "design").exists()

    # frob:tests tests/unit/test_scaffold_unity_project.py::TestOutputExistsRefusal.test_force_true_overwrites  # noqa: E501
    def test_force_true_overwrites(self, unity_project: Path) -> None:
        first = render_unity_project(unity_project)
        assert first.is_ok, first.err

        second = render_unity_project(unity_project, force=True)
        assert second.is_ok, second.err


class TestNotAUnityProject:
    """Acceptance criterion 3: a non-Unity directory errors clearly
    instead of producing a bogus config."""

    # frob:tests tests/unit/test_scaffold_unity_project.py::TestNotAUnityProject.test_plain_directory_is_not_a_unity_project  # noqa: E501
    def test_plain_directory_is_not_a_unity_project(self, tmp_path: Path) -> None:
        plain_dir = tmp_path / "not_unity"
        plain_dir.mkdir()
        (plain_dir / "README.md").write_text("hello\n", encoding="utf-8")

        result = render_unity_project(plain_dir)
        assert result.is_err
        assert result.danger_err is ScaffoldError.NotAUnityProject

    # frob:tests tests/unit/test_scaffold_unity_project.py::TestNotAUnityProject.test_no_bogus_config_written  # noqa: E501
    def test_no_bogus_config_written(self, tmp_path: Path) -> None:
        plain_dir = tmp_path / "not_unity"
        plain_dir.mkdir()

        result = render_unity_project(plain_dir)
        assert result.is_err
        assert not (plain_dir / "frob.toml").exists()
        assert not (plain_dir / "design").exists()

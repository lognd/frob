"""Unity project detection (T-4515): `frob.lang._project_detect`."""

from __future__ import annotations

from pathlib import Path

from frob.lang._project_detect import (
    UnityProjectDetectError,
    detect_unity_project,
)


def _make_unity_project(root: Path, *, with_manifest: bool = True) -> None:
    """Write the minimal marker files a real Unity project always has."""
    (root / "Assets").mkdir()
    settings = root / "ProjectSettings"
    settings.mkdir()
    (settings / "ProjectVersion.txt").write_text(
        "m_EditorVersion: 2022.3.5f1\nm_EditorVersionWithRevision: "
        "2022.3.5f1 (goodhash)\n"
    )
    if with_manifest:
        packages = root / "Packages"
        packages.mkdir()
        (packages / "manifest.json").write_text("{}\n")


# frob:tests src/frob/lang/_project_detect.py::UnityProjectInfo
def test_detects_unity_project(tmp_path: Path):
    """MUST-FIRE: Assets/ + ProjectSettings/ProjectVersion.txt +
    Packages/manifest.json all present detects as a Unity project and
    parses the editor version."""
    # frob:tests src/frob/lang/_project_detect.py::detect_unity_project kind="unit"
    _make_unity_project(tmp_path)
    result = detect_unity_project(tmp_path)
    assert result.is_ok
    info = result.danger_ok
    assert info.root == tmp_path
    assert info.editor_version == "2022.3.5f1"
    assert info.has_packages_manifest is True


def test_reports_packages_manifest_presence(tmp_path: Path):
    """A Unity project missing Packages/manifest.json still detects (it is
    not a required marker), and `has_packages_manifest` reflects the
    absence."""
    # frob:tests src/frob/lang/_project_detect.py::detect_unity_project kind="unit"
    _make_unity_project(tmp_path, with_manifest=False)
    result = detect_unity_project(tmp_path)
    assert result.is_ok
    assert result.danger_ok.has_packages_manifest is False


# frob:tests src/frob/lang/_project_detect.py::UnityProjectDetectError
def test_not_unity_project_without_markers(tmp_path: Path):
    """MUST-NOT-FIRE: a plain (non-Unity) tree with no Assets/ directory is
    not misidentified as a Unity project."""
    # frob:tests src/frob/lang/_project_detect.py::detect_unity_project kind="unit"
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "Program.cs").write_text("class Program {}\n")
    result = detect_unity_project(tmp_path)
    assert result.is_err
    assert result.danger_err is UnityProjectDetectError.NotUnityProject


def test_unreadable_version_file(tmp_path: Path):
    """Both required markers present, but ProjectVersion.txt is a
    directory (not a file) -- unreadable, not a false-positive detect."""
    # frob:tests src/frob/lang/_project_detect.py::detect_unity_project kind="unit"
    (tmp_path / "Assets").mkdir()
    settings = tmp_path / "ProjectSettings"
    settings.mkdir()
    (settings / "ProjectVersion.txt").mkdir()
    result = detect_unity_project(tmp_path)
    assert result.is_err
    assert result.danger_err is UnityProjectDetectError.NotUnityProject


# frob:tests src/frob/lang/_project_detect.py::UnityProjectDetectError
def test_malformed_version_file(tmp_path: Path):
    """ProjectVersion.txt exists but has no `m_EditorVersion` line."""
    # frob:tests src/frob/lang/_project_detect.py::detect_unity_project kind="unit"
    (tmp_path / "Assets").mkdir()
    settings = tmp_path / "ProjectSettings"
    settings.mkdir()
    (settings / "ProjectVersion.txt").write_text("not the right format\n")
    result = detect_unity_project(tmp_path)
    assert result.is_err
    assert result.danger_err is UnityProjectDetectError.VersionFileMalformed


# frob:tests src/frob/lang/_project_detect.py::_parse_editor_version
# frob:tests src/frob/lang/_project_detect.py::_EDITOR_VERSION_RE
# frob:tests src/frob/lang/_project_detect.py::UnityProjectInfo
def test_parses_editor_version(tmp_path: Path):
    """The editor version parsed matches the `m_EditorVersion:` value
    exactly, ignoring the trailing revision-hash line."""
    # frob:tests src/frob/lang/_project_detect.py::detect_unity_project kind="unit"
    _make_unity_project(tmp_path)
    result = detect_unity_project(tmp_path)
    assert result.danger_ok.editor_version == "2022.3.5f1"


# frob:tests src/frob/lang/_project_detect.py::_parse_editor_version
def test_missing_editor_version_line_is_malformed(tmp_path: Path):
    """A ProjectVersion.txt with only unrelated keys is malformed, not a
    silent empty-string version."""
    # frob:tests src/frob/lang/_project_detect.py::detect_unity_project kind="unit"
    (tmp_path / "Assets").mkdir()
    settings = tmp_path / "ProjectSettings"
    settings.mkdir()
    (settings / "ProjectVersion.txt").write_text("m_SomeOtherField: 1\n")
    result = detect_unity_project(tmp_path)
    assert result.is_err
    assert result.danger_err is UnityProjectDetectError.VersionFileMalformed

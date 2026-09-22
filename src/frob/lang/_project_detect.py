"""Unity project detection (T-4515).

The Unity C# ecosystem needs its own "is this root a Unity project"
signal, distinct from the plain-C# case: a Unity project root has
`Assets/`, `ProjectSettings/ProjectVersion.txt`, and usually
`Packages/manifest.json`, but no `.csproj`/`.sln` a walker can key off of
at the root level (Unity generates those lazily, inside `Library/`, and
they are gitignored in every real-world Unity repo). This module is the
one place that knows those three signals and how to read the Unity
editor version back out of `ProjectVersion.txt` -- `frob.excludes` calls
into it to decide whether to add Unity's own generated-output globs
(`Library/`, `Temp/`, `Logs/`, `obj/`, `*.meta`) to a walk, and the
sibling scaffold/doctor tickets (T-draft-e7dd275c's other three leaves)
are expected to reuse this exact detector rather than re-deriving the
same three-file check.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = [
    "UnityProjectInfo",
    "UnityProjectDetectError",
    "detect_unity_project",
]


# frob:doc docs/modules/lang.md#unity-project-detection
# tests/unit/test_lang_project_detect.py::test_not_unity_project_without_markers
class UnityProjectDetectError(ErrorSet):
    """Failure modes for `detect_unity_project`."""

    NotUnityProject = "root has none of the Unity project marker files"
    VersionFileUnreadable = "ProjectSettings/ProjectVersion.txt could not be read"
    VersionFileMalformed = (
        "ProjectSettings/ProjectVersion.txt has no m_EditorVersion line"
    )


# frob:doc docs/modules/lang.md#unity-project-detection
class UnityProjectInfo(BaseModel):
    """A confirmed Unity project root plus the editor version it was
    authored against (parsed from `ProjectVersion.txt`'s `m_EditorVersion`
    line, e.g. `"2022.3.5f1"`)."""

    model_config = {}

    root: Path
    editor_version: str
    has_packages_manifest: bool


# Marker paths that jointly signal a Unity project root. `Assets/` and
# `ProjectSettings/ProjectVersion.txt` are REQUIRED (every Unity project,
# from 3.x onward, has both); `Packages/manifest.json` is common (UPM,
# 2018.1+) but not load-bearing for detection -- an older or manually
# stripped project can lack it while still genuinely being a Unity
# project, so it is reported on `UnityProjectInfo.has_packages_manifest`
# rather than gating detection itself.
_ASSETS_DIRNAME = "Assets"
_PROJECT_VERSION_REL = Path("ProjectSettings") / "ProjectVersion.txt"
_PACKAGES_MANIFEST_REL = Path("Packages") / "manifest.json"

_EDITOR_VERSION_RE = re.compile(r"^m_EditorVersion:\s*(?P<version>\S+)", re.MULTILINE)


def _parse_editor_version(text: str) -> Result[str, UnityProjectDetectError]:
    """Extract the `m_EditorVersion` value out of a `ProjectVersion.txt`
    body (a two-line YAML-ish file Unity writes verbatim, never round-
    tripped through a real YAML parser here since only this one field is
    needed)."""
    match = _EDITOR_VERSION_RE.search(text)
    if match is None:
        return Err(UnityProjectDetectError.VersionFileMalformed)
    return Ok(match.group("version"))


# frob:doc docs/modules/lang.md#unity-project-detection
# frob:ticket T-4515
def detect_unity_project(
    root: Path,
) -> Result[UnityProjectInfo, UnityProjectDetectError]:
    """Identify `root` as a Unity project root: `Assets/` AND
    `ProjectSettings/ProjectVersion.txt` both present (`Packages/
    manifest.json` is recorded but not required -- see the module-level
    comment on `_PACKAGES_MANIFEST_REL`).

    Returns `Err(NotUnityProject)` when either required marker is absent
    (the common case for every non-Unity root -- deliberately quiet, not
    logged, since every walk/detect call site probes many roots that are
    never Unity projects). Returns `Err(VersionFileUnreadable)` or
    `Err(VersionFileMalformed)` when the required markers ARE present but
    the version file cannot be read or parsed -- both logged at WARNING
    since that combination means a genuine Unity project is present but
    its version could not be determined.
    """
    version_path = root / _PROJECT_VERSION_REL
    if not (root / _ASSETS_DIRNAME).is_dir() or not version_path.is_file():
        return Err(UnityProjectDetectError.NotUnityProject)

    try:
        text = version_path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.warning("project_detect: could not read %s: %s", version_path, exc)
        return Err(UnityProjectDetectError.VersionFileUnreadable)

    parsed = _parse_editor_version(text)
    if parsed.is_err:
        _log.warning("project_detect: %s has no m_EditorVersion line", version_path)
        return Err(parsed.danger_err)

    has_manifest = (root / _PACKAGES_MANIFEST_REL).is_file()
    info = UnityProjectInfo(
        root=root,
        editor_version=parsed.danger_ok,
        has_packages_manifest=has_manifest,
    )
    _log.info(
        "project_detect: detected Unity project at %s (editor %s, "
        "packages manifest %s)",
        root,
        info.editor_version,
        "present" if has_manifest else "absent",
    )
    return Ok(info)

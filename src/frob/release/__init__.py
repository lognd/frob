"""frob.release -- mechanical semver from the obligation graph (T-0003).

The graph already knows every public symbol's signature digest, so the
correct version-bump class is computable, not a judgment call: a removed or
changed public signature is BREAKING (major), a new public symbol is
ADDITIVE (minor), and body/doc-only change is a PATCH. `frob release stamp`
records the public API at release time into a tracked `.frob-release.json`;
`frob release check` (and the REL001 gate) compares the current API against
it and fails when the declared version does not cover the observed change,
or when the changelog does not mention the version.

The manifest is tracked text (source of truth); the graph is derived. The
gate is opt-in: it runs only once a manifest exists, so a repo adopts it by
running `frob release stamp` once.
"""

from __future__ import annotations

import json
import re
from enum import IntEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.graph import GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)

_MANIFEST_NAME = ".frob-release.json"
_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


# frob:doc docs/release.md#public-api
class BumpClass(IntEnum):
    """The semver change class implied by a public-API diff (ordered)."""

    NONE = 0
    PATCH = 1
    MINOR = 2
    MAJOR = 3


# frob:doc docs/release.md#public-api
class ReleaseManifest(BaseModel):
    """The public API digest snapshot recorded at a release (tracked file)."""

    model_config = ConfigDict(frozen=True)

    version: str
    # public symref -> signature digest at release time
    api: dict[str, str]


# frob:doc docs/release.md#public-api
class ReleaseError(ErrorSet):
    """Fallible outcomes of release operations."""

    NoManifest = "No .frob-release.json; run `frob release stamp` first"
    Malformed = "Release manifest is not valid JSON"
    BadVersion = "Version string is not X.Y.Z"


def _public_api(snapshot: GraphSnapshot) -> dict[str, str]:
    """The `{public symref: sig digest}` map -- the release-relevant surface."""
    return {
        ref: rec.digests.sig
        for ref, rec in snapshot.symbols.items()
        if rec.public and not _is_test_or_private_path(rec.id.path)
    }


def _is_test_or_private_path(path: str) -> bool:
    """Test code and dotted-private paths are not public API surface."""
    parts = Path(path).parts
    name = Path(path).name
    return "tests" in parts or name.startswith("test_") or name.endswith("_test.py")


# frob:doc docs/release.md#public-api
def manifest_path(root: Path) -> Path:
    """The tracked `.frob-release.json` path at the repo root."""
    return root / _MANIFEST_NAME


# frob:doc docs/release.md#public-api
def load_manifest(root: Path) -> Result[ReleaseManifest, ReleaseError]:
    """Read the release manifest, or Err(NoManifest)/Err(Malformed)."""
    path = manifest_path(root)
    if not path.exists():
        return Err(ReleaseError.NoManifest)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Ok(ReleaseManifest.model_validate(data))
    except (OSError, ValueError) as exc:
        _log.error("release: manifest unreadable: %s", exc)
        return Err(ReleaseError.Malformed)


# frob:doc docs/release.md#public-api
def stamp(
    root: Path, snapshot: GraphSnapshot, version: str
) -> Result[str, ReleaseError]:
    """Write the current public API + `version` to the tracked manifest."""
    manifest = ReleaseManifest(version=version, api=_public_api(snapshot))
    path = manifest_path(root)
    path.write_text(
        json.dumps(manifest.model_dump(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _log.info("release: stamped %d public symbol(s) at %s", len(manifest.api), version)
    return Ok(version)


# frob:doc docs/release.md#public-api
def diff_class(manifest: ReleaseManifest, snapshot: GraphSnapshot) -> BumpClass:
    """The semver bump class implied by the current API vs the manifest."""
    current = _public_api(snapshot)
    old = manifest.api
    removed = set(old) - set(current)
    changed = {ref for ref in set(old) & set(current) if old[ref] != current[ref]}
    added = set(current) - set(old)
    if removed or changed:
        return BumpClass.MAJOR
    if added:
        return BumpClass.MINOR
    return BumpClass.NONE


def _parse(version: str) -> tuple[int, int, int] | None:
    """`(major, minor, patch)` from an X.Y.Z(-suffix) string, or None."""
    match = _VERSION_RE.match(version.strip())
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


# frob:doc docs/release.md#public-api
def required_version(previous: str, bump: BumpClass) -> Result[str, ReleaseError]:
    """The minimum acceptable version after a `bump`-class change."""
    parsed = _parse(previous)
    if parsed is None:
        return Err(ReleaseError.BadVersion)
    major, minor, patch = parsed
    if bump == BumpClass.MAJOR:
        return Ok(f"{major + 1}.0.0")
    if bump == BumpClass.MINOR:
        return Ok(f"{major}.{minor + 1}.0")
    if bump == BumpClass.PATCH:
        return Ok(f"{major}.{minor}.{patch + 1}")
    return Ok(previous)


# frob:doc docs/release.md#public-api
def satisfies(current: str, minimum: str) -> bool:
    """True if `current` >= `minimum` by (major, minor, patch) ordering."""
    c, m = _parse(current), _parse(minimum)
    if c is None or m is None:
        return False
    return c >= m


__all__ = [
    "BumpClass",
    "ReleaseError",
    "ReleaseManifest",
    "diff_class",
    "load_manifest",
    "manifest_path",
    "required_version",
    "satisfies",
    "stamp",
]

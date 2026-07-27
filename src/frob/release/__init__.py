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
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/release/__init__.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"
# frob:waive ARCH102 reason="T-1009: authoritative_version/rewrite_pyproject_version/ \
# changelog_skeleton_entry are the sync half of the SAME single-version-authority \
# concern this module's docstring already scopes it to (stamp/diff_class/ \
# required_version being the stamp/diff half); the naming/usage clustering heuristic \
# groups by call-graph edges, and sync's helpers are new leaf functions with no \
# existing caller in this module yet (frob.app.release_runner._sync/frob.tickets._land \
# call them from outside) -- not a second concern to split out, the module still has \
# exactly one job: mechanical semver, now including its derived-artifact regeneration"

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
from frob.tickets._worktree_guard import enforce_worktree_lease

_log = get_logger(__name__)

_MANIFEST_NAME = ".frob-release.json"
_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


# frob:doc docs/modules/release.md#public-api
class BumpClass(IntEnum):
    """The semver change class implied by a public-API diff (ordered)."""

    NONE = 0
    PATCH = 1
    MINOR = 2
    MAJOR = 3


# frob:doc docs/modules/release.md#public-api
class ReleaseManifest(BaseModel):
    """The public API digest snapshot recorded at a release (tracked file)."""

    model_config = ConfigDict(frozen=True)

    version: str
    # public symref -> signature digest at release time
    api: dict[str, str]


# frob:doc docs/modules/release.md#public-api
class ReleaseError(ErrorSet):
    """Fallible outcomes of release operations."""

    NoManifest = "No .frob-release.json; run `frob release stamp` first"
    Malformed = "Release manifest is not valid JSON"
    BadVersion = "Version string is not X.Y.Z"
    WorktreeLeaseViolation = (
        "FROB_WORKTREE is leased to a different worktree than this command's cwd"
    )


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


# frob:doc docs/modules/release.md#public-api
def manifest_path(root: Path) -> Path:
    """The tracked `.frob-release.json` path at the repo root."""
    return root / _MANIFEST_NAME


# frob:doc docs/modules/release.md#public-api
# frob:waive TEST005 reason="load_manifest 87.5% branch cover, debt T-0160"
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


# frob:doc docs/modules/release.md#public-api
# frob:tests tests/test_release_worktree_lease.py::TestStampWorktreeLease.test_mismatched_lease_refuses  # noqa: E501
# frob:tests tests/test_release_worktree_lease.py::TestStampWorktreeLease.test_no_lease_succeeds  # noqa: E501
def stamp(
    root: Path, snapshot: GraphSnapshot, version: str
) -> Result[str, ReleaseError]:
    """Write the current public API + `version` to the tracked manifest
    (T-0507: refuses with `Err(WorktreeLeaseViolation)` if `FROB_WORKTREE`
    names a different worktree than `root`, same guard as `frob check
    --stamp-baseline`/`--stamp-coverage` (T-0431))."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(ReleaseError.WorktreeLeaseViolation)
    manifest = ReleaseManifest(version=version, api=_public_api(snapshot))
    path = manifest_path(root)
    path.write_text(
        json.dumps(manifest.model_dump(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _log.info("release: stamped %d public symbol(s) at %s", len(manifest.api), version)
    return Ok(version)


# frob:ticket T-1009
_PYPROJECT_VERSION_RE = re.compile(r'(?m)^version\s*=\s*"[^"]*"')


# frob:doc docs/modules/release.md#public-api
# frob:ticket T-1009
def authoritative_version(root: Path) -> Result[str, ReleaseError]:
    """The ONE version authority (T-1009): `.frob-release.json`'s `version`
    field. `pyproject.toml`, `uv.lock`, and CHANGELOG.md are all derived
    artifacts regenerated FROM this by `sync`/`frob release sync` -- never
    the other way around. `Err(NoManifest)`/`Err(Malformed)` propagate from
    `load_manifest` unchanged."""
    loaded = load_manifest(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    return Ok(loaded.danger_ok.version)


# frob:doc docs/modules/release.md#public-api
# frob:ticket T-1009
def rewrite_pyproject_version(root: Path, version: str) -> Result[bool, ReleaseError]:
    """Rewrite `root/pyproject.toml`'s `version = "..."` line to `version`
    (T-1009). Returns `Ok(True)` if the file changed, `Ok(False)` if it
    already matched, `Err(BadVersion)` if no `version = "..."` line was
    found to rewrite."""
    path = root / "pyproject.toml"
    if not path.exists():
        return Err(ReleaseError.BadVersion)
    text = path.read_text(encoding="utf-8")
    new_text, count = _PYPROJECT_VERSION_RE.subn(
        f'version = "{version}"', text, count=1
    )
    if count != 1:
        return Err(ReleaseError.BadVersion)
    if new_text == text:
        return Ok(False)
    path.write_text(new_text, encoding="utf-8")
    return Ok(True)


# frob:doc docs/modules/release.md#public-api
# frob:ticket T-1009
def changelog_skeleton_entry(root: Path, version: str, note: str | None = None) -> bool:
    """Insert a `## [version] - unreleased` skeleton entry at the top of
    `root/CHANGELOG.md` (T-1009) unless a heading entry for `version`
    already exists (mirrors `_changelog_mentions`'s heading-anchored match
    in `frob.gates`, kept independent to avoid a gates<->release import
    cycle). Returns `True` if it wrote a new entry, `False` if one already
    existed or CHANGELOG.md is absent (nothing to skeleton into)."""
    path = root / "CHANGELOG.md"
    if not path.exists():
        return False
    pattern = re.compile(r"(?<![0-9.])" + re.escape(version) + r"(?![0-9.])")
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if any(line.lstrip().startswith("#") and pattern.search(line) for line in lines):
        return False
    body = f"- {note}\n\n" if note else "\n"
    entry = f"## [{version}] - unreleased\n\n{body}"
    insert_at = next(
        (i for i, line in enumerate(lines) if line.startswith("## ")), len(lines)
    )
    lines[insert_at:insert_at] = [entry]
    path.write_text("".join(lines), encoding="utf-8")
    return True


# frob:doc docs/modules/release.md#public-api
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


# frob:doc docs/modules/release.md#public-api
# frob:waive TEST005 reason="required_version 83.3% branch cover, debt T-0160"
def required_version(previous: str, bump: BumpClass) -> Result[str, ReleaseError]:
    """The minimum acceptable version after a `bump`-class change."""
    parsed = _parse(previous)
    if parsed is None:
        return Err(ReleaseError.BadVersion)
    major, minor, patch = parsed
    if bump == BumpClass.MAJOR:
        # semver spec section 4: "Major version zero (0.y.z) is for initial
        # development. Anything MAY change at any time." So a BREAKING change
        # while still in 0.x bumps the MINOR (0.y -> 0.(y+1)), it does NOT
        # force 1.0.0 -- committing to 1.0.0 is a deliberate API-stability
        # decision, not something a breaking change should mandate. Only once
        # you are already at >=1.0.0 does a breaking change bump the major.
        if major == 0:
            return Ok(f"0.{minor + 1}.0")
        return Ok(f"{major + 1}.0.0")
    if bump == BumpClass.MINOR:
        return Ok(f"{major}.{minor + 1}.0")
    if bump == BumpClass.PATCH:
        return Ok(f"{major}.{minor}.{patch + 1}")
    return Ok(previous)


# frob:doc docs/modules/release.md#public-api
# frob:waive TEST005 reason="satisfies 75.0% branch cover, debt T-0160"
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
    "authoritative_version",
    "changelog_skeleton_entry",
    "diff_class",
    "load_manifest",
    "manifest_path",
    "required_version",
    "rewrite_pyproject_version",
    "satisfies",
    "stamp",
]

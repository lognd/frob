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
from frob.tickets._store import atomic_write
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
    UnbumpedApiChange = (
        "the public API changed but the version was not bumped -- stamping now "
        "would rebaseline the API at the OLD version and silence REL001 without "
        "the release ever happening"
    )
    # frob:ticket T-1359
    WriteFailed = (
        "the crash-safe write of a release-owned file failed (see logs for the "
        "underlying OSError)"
    )


# frob:ticket T-1359
def _atomic_write_release(path: Path, content: str) -> Result[None, ReleaseError]:
    """Crash-safe write for every release-owned file this module rewrites
    (`.frob-release.json`, `pyproject.toml`'s version line, CHANGELOG.md's
    skeleton entry -- T-1359: these used to be bare `Path.write_text`
    calls, the same half-written-file hazard T-1348 already closed for
    `frob.gates._fix_engine`'s own direct writes). Delegates to
    `frob.tickets._store.atomic_write` (temp file + fsync + `os.replace`)
    rather than a second copy of that primitive, translating its
    `TicketError` into this module's own `ReleaseError.WriteFailed` so
    callers keep a single error vocabulary."""
    written = atomic_write(path, content)
    if written.is_err:
        _log.error("release: atomic write to %s failed: %s", path, written.danger_err)
        return Err(ReleaseError.WriteFailed)
    return Ok(None)


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


# frob:doc docs/modules/release.md#stamp-refuses-an-un-bumped-api-change-t-1381
# frob:tests tests/test_release_worktree_lease.py::TestStampWorktreeLease.test_mismatched_lease_refuses  # noqa: E501
# frob:tests tests/test_release_worktree_lease.py::TestStampWorktreeLease.test_no_lease_succeeds  # noqa: E501
# frob:ticket T-1381
# frob:tests tests/unit/test_release_stamp_guard.py::TestStampRefusesUnbumped.test_refuses_when_api_changed_and_version_not_bumped  # noqa: E501
# frob:tests tests/unit/test_release_stamp_guard.py::TestStampRefusesUnbumped.test_allows_when_version_is_bumped  # noqa: E501
# T-1636: retargeted from #public-api (a COV007 finding -- this
# private helper is not in that section's own `frob:describes` list, and
# the T-1381 feature it implements is documented right here instead) to
# the section that genuinely describes it, matching `stamp`'s own anchor
# immediately below.
# frob:waive COV007 reason="T-1636: docs/modules/release.md's Stamp-refuses section \
# (T-1381) is a deliberate architecture doc walking through this exact private \
# helper's own contract (the SAME computation REL001 uses, applied at stamp time) -- \
# same T-0524/T-0529 per-function architecture-doc precedent every other COV007 waiver \
# in this repo already carries, not accidental drift onto a private helper"
def _bump_shortfall(
    root: Path, snapshot: GraphSnapshot, version: str
) -> tuple[str, str, str, str] | None:
    """`(bump_class, previous_version, required_version, current_version)` when
    `version` is short of what the API change demands, else `None`.

    T-1381: this is the SAME computation REL001 uses to decide the required
    bump, applied at the moment of stamping. Stamping rebaselines the
    recorded API at whatever version is current, so without this check
    `frob release stamp` at an un-bumped version silences REL001 and the
    release silently never happens -- exactly the footgun that produced
    this ticket.
    """
    previous = load_manifest(root)
    if previous.is_err:
        # Nothing to compare against: the first stamp cannot be under-bumped.
        return None
    manifest = previous.danger_ok
    bump = diff_class(manifest, snapshot)
    need = required_version(manifest.version, bump)
    if need.is_err or satisfies(version, need.danger_ok):
        return None
    return (bump.name.lower(), manifest.version, need.danger_ok, version)


# frob:doc docs/modules/release.md#stamp-refuses-an-un-bumped-api-change-t-1381
def stamp(
    root: Path,
    snapshot: GraphSnapshot,
    version: str,
    *,
    allow_unbumped: bool = False,
) -> Result[str, ReleaseError]:
    """Write the current public API + `version` to the tracked manifest
    (T-0507: refuses with `Err(WorktreeLeaseViolation)` if `FROB_WORKTREE`
    names a different worktree than `root`, same guard as `frob check
    --stamp-baseline`/`--stamp-coverage` (T-0431)). Writes via
    `atomic_write` (T-1359): `Err(WriteFailed)` on the (should-never-
    happen) I/O failure path, original file left intact."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(ReleaseError.WorktreeLeaseViolation)
    if not allow_unbumped:
        shortfall = _bump_shortfall(root, snapshot, version)
        if shortfall is not None:
            _log.error(
                "release: refusing to stamp -- public API changed (%s) since %s, "
                "so the version must be >= %s (currently %s). Bump it first, then "
                "stamp; stamping now would rebaseline the API at the OLD version "
                "and silence REL001 without the release ever happening. Pass "
                "allow_unbumped=True (`--allow-unbumped`) only with a reason.",
                *shortfall,
            )
            return Err(ReleaseError.UnbumpedApiChange)
    manifest = ReleaseManifest(version=version, api=_public_api(snapshot))
    path = manifest_path(root)
    written = _atomic_write_release(
        path, json.dumps(manifest.model_dump(), indent=2, sort_keys=True) + "\n"
    )
    if written.is_err:
        return Err(written.danger_err)
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
    found to rewrite, `Err(WriteFailed)` (T-1359) on the (should-never-
    happen) atomic-write I/O failure path -- original file left intact."""
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
    written = _atomic_write_release(path, new_text)
    if written.is_err:
        return Err(written.danger_err)
    return Ok(True)


# frob:doc docs/modules/release.md#public-api
# frob:ticket T-1009
def changelog_skeleton_entry(root: Path, version: str, note: str | None = None) -> bool:
    """Insert a `## [version] - unreleased` skeleton entry at the top of
    `root/CHANGELOG.md` (T-1009) unless a heading entry for `version`
    already exists (mirrors `_changelog_mentions`'s heading-anchored match
    in `frob.gates`, kept independent to avoid a gates<->release import
    cycle). Returns `True` if it wrote a new entry, `False` if one already
    existed, CHANGELOG.md is absent (nothing to skeleton into), or the
    write itself failed (T-1359: `atomic_write`'s I/O failure path,
    logged, original left intact -- this function's bool contract has no
    error channel, matching `frob.gates._fix_engine_shared._write_text`'s same
    posture, T-1348)."""
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
    written = _atomic_write_release(path, "".join(lines))
    if written.is_err:
        # T-1359: matches `frob.gates._fix_engine_shared._write_text`'s posture
        # (T-1348) -- a write failure logs and reports "nothing changed"
        # rather than raising, since this function's bool contract has no
        # error channel to carry a `Result` through to its existing
        # callers without widening THEIR scope too.
        return False
    return True


# frob:doc docs/modules/release.md#public-api
# frob:ticket T-1078
# frob:tests tests/test_ticket_land.py::TestReleaseBumpQuartetAtomicity.test_manifest_version_written_same_step_as_pyproject  # noqa: E501
def set_manifest_version(root: Path, version: str) -> Result[str, ReleaseError]:
    """Rewrite ONLY the `version` field of the tracked `.frob-release.json`
    manifest in place, preserving its recorded `api` map unchanged (T-1078:
    the write-side companion to the T-1009 read-side authority). Used by
    `frob.tickets._land._apply_release_bump` as a forced resync step,
    invoked immediately after a `bump_version` callback reports success, so
    the manifest's version is guaranteed coherent with `pyproject.toml`/
    `CHANGELOG.md` in the SAME land step regardless of whether the
    callback itself remembered to (or was able to) write the manifest --
    the exact gap that let a land's REL001 bump update pyproject/CHANGELOG
    while `.frob-release.json` stayed on the old version (three lands
    blocked on the T-0992 monotonicity guard until a coordinator hand-
    reconciled, commit b7fa63d9). Returns `Err(NoManifest)` if no manifest
    exists yet -- a repo that never adopted `frob release stamp` has
    nothing here to keep coherent -- or `Err(Malformed)` if the existing
    file is not valid JSON. Writes via `atomic_write` (T-1359):
    `Err(WriteFailed)` on the (should-never-happen) I/O failure path."""
    loaded = load_manifest(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    manifest = ReleaseManifest(version=version, api=loaded.danger_ok.api)
    path = manifest_path(root)
    written = _atomic_write_release(
        path, json.dumps(manifest.model_dump(), indent=2, sort_keys=True) + "\n"
    )
    if written.is_err:
        return Err(written.danger_err)
    _log.info("release: manifest version resynced to %s at %s", version, path)
    return Ok(version)


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
    "set_manifest_version",
    "stamp",
]

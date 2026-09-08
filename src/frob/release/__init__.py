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

from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.graph import GraphSnapshot
from frob.logging import get_logger
from frob.tickets._store import atomic_write
from frob.tickets._worktree_guard import enforce_worktree_lease

_log = get_logger(__name__)

_MANIFEST_NAME = ".frob-release.json"


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
    # frob:ticket T-1768
    UnbumpedReasonMissing = (
        "--allow-unbumped bypasses a real shortfall and requires --reason/"
        "--reason-file (T-1768) -- this permanently redefines the REL001 "
        "baseline, unlike a one-invocation --force bypass"
    )
    UnbumpedReasonRecordFailed = (
        "--allow-unbumped's reason could not be recorded to "
        "force-overrides.jsonl; the manifest was NOT rewritten"
    )
    # frob:ticket T-1359
    WriteFailed = (
        "the crash-safe write of a release-owned file failed (see logs for the "
        "underlying OSError)"
    )
    # frob:ticket T-2242
    SyncFailed = "release publish's inline sync step (uv lock) failed"
    GitAddFailed = "git add of the release-owned files failed"
    GitCommitFailed = "git commit of the version bump failed"
    GitPushFailed = "git push failed"
    BuildFailed = "uv build failed"
    PublishFailed = "uv publish failed"
    # frob:ticket T-4184
    MajorVersionAckRequired = (
        "the automatic per-land dev-version bump would cross into a new major "
        "series with [tool.frob] dev_version_bump still on -- either set "
        "[tool.frob] dev_version_bump = false for this release, or record "
        "[tool.frob] dev_version_major_ack = <major> in pyproject.toml to "
        "explicitly keep auto-bumping across the boundary"
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


def _changed_symbol_count(old_api: dict[str, str], new_api: dict[str, str]) -> int:
    """The count of symrefs added, removed, or digest-changed between two
    `ReleaseManifest.api` maps (T-1768) -- part of the audit record an
    `--allow-unbumped` bypass now writes, so the entry names not just THAT
    the baseline moved but roughly how much surface it silently accepted."""
    all_refs = old_api.keys() | new_api.keys()
    return sum(1 for ref in all_refs if old_api.get(ref) != new_api.get(ref))


# frob:ticket T-1768
def _record_unbumped_stamp_override(
    root: Path,
    shortfall: tuple[str, str, str, str],
    new_api: dict[str, str],
    reason: str,
) -> Result[None, ReleaseError]:
    """`--allow-unbumped`'s require-reason/record-audit half (T-1768),
    mirroring T-1762's `record_force_override` shape exactly rather than
    inventing a second one: refuses `Err(UnbumpedReasonMissing)` on a
    blank reason, else appends one `ForceOverrideEntry` to
    `force-overrides.jsonl` naming the version move, the bump class that
    was skipped, and the count of symbols whose digest changed -- so the
    audit trail says not just THAT the baseline moved but by how much.
    Split out of `stamp` to keep that function's body under ARCH103's
    decision-point budget."""
    if not reason or not reason.strip():
        _log.error(
            "release stamp: --allow-unbumped requires --reason/--reason-file "
            "(T-1768) -- refusing to rebaseline REL001 at %s (a required %s "
            "bump to >= %s was skipped) with no recorded justification",
            shortfall[1],
            shortfall[0],
            shortfall[2],
        )
        return Err(ReleaseError.UnbumpedReasonMissing)
    from frob.tickets._force_override import record_force_override

    bump_class, previous_version, required_version_str, current_version = shortfall
    previous = load_manifest(root)
    old_api = previous.danger_ok.api if previous.is_ok else {}
    changed = _changed_symbol_count(old_api, new_api)
    recorded = record_force_override(
        root,
        command="release stamp --allow-unbumped",
        guard="T-1381 unbumped-api-change refusal",
        target=(
            f"version {previous_version}->{current_version} (required "
            f">={required_version_str}, bump={bump_class}, "
            f"{changed} symbol digest(s) changed)"
        ),
        reason=reason,
    )
    if recorded.is_err:
        _log.error("release stamp: %s", recorded.danger_err)
        return Err(ReleaseError.UnbumpedReasonRecordFailed)
    _log.warning(
        "release stamp: rebaselining REL001 manifest %s -> %s, skipping a "
        "required %s bump to >= %s (%d symbol digest(s) changed), reason=%r",
        previous_version,
        current_version,
        bump_class,
        required_version_str,
        changed,
        reason,
    )
    return Ok(None)


# frob:doc docs/modules/release.md#stamp-refuses-an-un-bumped-api-change-t-1381
# frob:ticket T-1768
# frob:tests tests/unit/test_release_stamp_guard.py::TestAllowUnbumpedRequiresReason.test_refuses_with_no_reason_when_shortfall_is_real  # noqa: E501
# frob:tests tests/unit/test_release_stamp_guard.py::TestAllowUnbumpedRequiresReason.test_refuses_with_blank_reason  # noqa: E501
# frob:tests tests/unit/test_release_stamp_guard.py::TestAllowUnbumpedRequiresReason.test_succeeds_with_reason_and_writes_audit_record  # noqa: E501
# frob:tests tests/unit/test_release_stamp_guard.py::TestAllowUnbumpedRequiresReason.test_no_reason_required_when_no_real_shortfall  # noqa: E501
def stamp(
    root: Path,
    snapshot: GraphSnapshot,
    version: str,
    *,
    allow_unbumped: bool = False,
    reason: str | None = None,
) -> Result[str, ReleaseError]:
    """Write the current public API + `version` to the tracked manifest
    (T-0507: refuses with `Err(WorktreeLeaseViolation)` if `FROB_WORKTREE`
    names a different worktree than `root`, same guard as `frob check
    --stamp-baseline`/`--stamp-coverage` (T-0431)). Writes via
    `atomic_write` (T-1359): `Err(WriteFailed)` on the (should-never-
    happen) I/O failure path, original file left intact.

    T-1768: `allow_unbumped=True` no longer silently bypasses a real
    shortfall. When one exists, `reason` is now REQUIRED
    (`Err(UnbumpedReasonMissing)` on a blank/missing one) and the bypass
    is appended to `force-overrides.jsonl` (`_record_unbumped_stamp_
    override`, reusing T-1762's `ForceOverrideEntry` shape) before the
    manifest is rewritten -- mirroring `ticket archive --force`/`ticket
    land --finish --force`'s landed remedy exactly. `allow_unbumped=True`
    with NO real shortfall (the version already covers the change) is
    still a no-op guard-wise and demands no reason, same posture
    `_require_reason_for_archive_force` already established: nothing was
    actually bypassed."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(ReleaseError.WorktreeLeaseViolation)
    shortfall = _bump_shortfall(root, snapshot, version)
    if shortfall is not None:
        if not allow_unbumped:
            _log.error(
                "release: refusing to stamp -- public API changed (%s) since %s, "
                "so the version must be >= %s (currently %s). Bump it first, then "
                "stamp; stamping now would rebaseline the API at the OLD version "
                "and silence REL001 without the release ever happening. Pass "
                "allow_unbumped=True (`--allow-unbumped`) only with a reason.",
                *shortfall,
            )
            return Err(ReleaseError.UnbumpedApiChange)
        recorded = _record_unbumped_stamp_override(
            root, shortfall, _public_api(snapshot), reason or ""
        )
        if recorded.is_err:
            return Err(recorded.danger_err)
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
# frob:ticket T-2242
# frob:tests tests/test_release.py::TestCurrentVersion.test_reads_pyproject_version  # noqa: E501
def current_version(root: Path) -> Result[str, ReleaseError]:
    """`root/pyproject.toml`'s `[project].version`, read-only (T-2242) --
    never mutates anything, unlike `rewrite_pyproject_version`. `Err(
    BadVersion)` if the file is missing, unparsable, or has no string
    `version` field."""
    import tomllib

    path = root / "pyproject.toml"
    if not path.exists():
        return Err(ReleaseError.BadVersion)
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return Err(ReleaseError.BadVersion)
    version = data.get("project", {}).get("version")
    if not isinstance(version, str):
        return Err(ReleaseError.BadVersion)
    return Ok(version)


# frob:doc docs/modules/release.md#public-api
# frob:ticket T-2242
# frob:tests tests/test_release.py::TestNextPatchVersion.test_increments_patch_component  # noqa: E501
def next_patch_version(version: str) -> Result[str, ReleaseError]:
    """`X.Y.Z -> X.Y.(Z+1)` (T-2242), pure -- no I/O, no mutation. The same
    unconditional-patch-bump rule `scripts/bump_version.py` implemented
    inline before this ticket; that script is now a thin wrapper over this
    plus `bump_patch_version` below, so the rule has exactly one home."""
    parts = version.split(".")
    if len(parts) != 3 or not parts[-1].isdigit():
        return Err(ReleaseError.BadVersion)
    parts[-1] = str(int(parts[-1]) + 1)
    return Ok(".".join(parts))


# frob:doc docs/modules/release.md#public-api
# frob:ticket T-2242
# frob:tests tests/test_release.py::TestBumpPatchVersion.test_bumps_and_writes_pyproject  # noqa: E501
def bump_patch_version(root: Path) -> Result[str, ReleaseError]:
    """Bump `root/pyproject.toml`'s patch version unconditionally, in
    place (T-2242) -- the canonical implementation `scripts/bump_
    version.py` and `frob release publish` both call, so the rule has one
    home instead of two (the script used to hand-roll this same regex
    substitution independently). Returns the NEW version on success."""
    current = current_version(root)
    if current.is_err:
        return current
    nxt = next_patch_version(current.danger_ok)
    if nxt.is_err:
        return nxt
    rewritten = rewrite_pyproject_version(root, nxt.danger_ok)
    if rewritten.is_err:
        return Err(rewritten.danger_err)
    return Ok(nxt.danger_ok)


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
# frob:tests tests/ticket_land_suite/test_release.py::TestReleaseBumpQuartetAtomicity.test_manifest_version_written_same_step_as_pyproject  # noqa: E501
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


# frob:ticket T-4270
# frob:tests tests/test_release.py::test_dev_prerelease_and_final_sort_in_pep440_order
# frob:tests \
# tests/test_release.py::test_unparseable_version_is_inspectable_failure_not_truncated_\
# value
def _parse(version: str) -> Version | None:
    """Full PEP 440 parse of `version` (T-4270), or `None` if the packaging
    standard cannot interpret it. Replaces a hand-rolled `^(\\d+)\\.(\\d+)\\.
    (\\d+)` regex that matched only a leading X.Y.Z and silently discarded
    any pre-release/dev/post-release suffix past that point, so a
    pre-release and its final release parsed to an identical tuple and
    every comparison in this module was blind to the distinction. Using
    `packaging.version.Version` -- the library this project already
    depends on for exactly this -- means ordering across dev/pre/final/
    post builds is the ecosystem's own PEP 440 rule, not a hand-rolled one
    (a bare hyphen-number suffix, for instance, is a POST-release under
    PEP 440 and sorts AFTER the final version, not before it as a
    semver-style reading would suggest)."""
    try:
        return Version(version.strip())
    except InvalidVersion:
        return None


# frob:doc docs/modules/release.md#public-api
def required_version(previous: str, bump: BumpClass) -> Result[str, ReleaseError]:
    """The minimum acceptable version after a `bump`-class change."""
    parsed = _parse(previous)
    if parsed is None:
        return Err(ReleaseError.BadVersion)
    major, minor, patch = (tuple(parsed.release) + (0, 0, 0))[:3]
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
# frob:ticket T-4270
# frob:tests tests/test_release.py::test_required_version_and_satisfies
# frob:tests \
# tests/test_release.py::test_prerelease_does_not_satisfy_its_final_release_minimum
# frob:tests \
# tests/test_release.py::test_trailing_hyphen_number_parses_as_post_release_not_prerele\
# ase
def satisfies(current: str, minimum: str) -> bool:
    """True if `current` >= `minimum` under full PEP 440 ordering (T-4270:
    was (major, minor, patch)-only, so a pre-release/dev build of `minimum`'s
    final version compared equal to it; `packaging.version.Version`
    ordering correctly ranks dev < pre-release < final < post-release, so a
    pre-release no longer satisfies its own final release's minimum)."""
    c, m = _parse(current), _parse(minimum)
    if c is None or m is None:
        return False
    return c >= m


# frob:doc docs/modules/release.md#per-land-dev-version-bump-t-4184
# frob:ticket T-4184
# frob:tests tests/test_release.py::test_dev_prerelease_and_final_sort_in_pep440_order
# frob:tests tests/test_release.py::test_next_dev_version_starts_and_advances_a_cycle
def next_dev_version(version: str) -> Result[str, ReleaseError]:
    """The next automatic per-land PEP 440 development version after
    `version` (T-4184: the counter this feature exists to advance,
    closing the "a version that never moves cannot identify a build"
    problem measured four times in one day). `version` with an existing
    `.devN` suffix advances the counter in place (`X.Y.Z.devN ->
    X.Y.Z.dev(N+1)`); a plain final release starts a new dev cycle ON TOP
    OF the next patch (`X.Y.Z -> X.Y.(Z+1).dev1`), matching the ordering
    `0.530.0 < 0.531.0.dev1 < 0.531.0.dev2 < ... < 0.531.0` the ticket's
    own must-fire fixture requires. Uses the dev-release spelling PEP 440
    actually defines (`.devN`), never a semver-style hyphen suffix -- that
    parses as a POST-release under PEP 440 (see `_parse`'s own docstring)
    and would sort AFTER the final release, the exact inverse of the
    intent. `Err(BadVersion)` if `version` cannot be parsed, or is itself
    a pre-release/post-release -- the per-land counter only ever advances
    on top of a plain final release or an already-running dev cycle, it
    is not defined for any other PEP 440 release kind this project does
    not otherwise use."""
    parsed = _parse(version)
    if parsed is None:
        return Err(ReleaseError.BadVersion)
    if parsed.pre is not None or parsed.post is not None:
        return Err(ReleaseError.BadVersion)
    major, minor, patch = (tuple(parsed.release) + (0, 0, 0))[:3]
    if parsed.dev is not None:
        return Ok(f"{major}.{minor}.{patch}.dev{parsed.dev + 1}")
    return Ok(f"{major}.{minor}.{patch + 1}.dev1")


# frob:doc docs/modules/release.md#per-land-dev-version-bump-t-4184
# frob:ticket T-4184
# frob:tests tests/test_release.py::test_dev_version_bump_enabled_defaults_true_and_reads_pyproject kind="unit"  # noqa: E501
def dev_version_bump_enabled(root: Path) -> bool:
    """Whether `root`'s `pyproject.toml` `[tool.frob]` table has the
    automatic per-land dev-version bump (T-4184) turned on -- read
    directly off the file on disk, default `True` (the feature is core
    functionality for every consumer, on by default; a release toggles it
    off explicitly -- see this module's docs anchor for the scaffolded-
    project default and the major-version interaction). Missing/
    unparsable `pyproject.toml`, or a `[tool.frob]` table without the key
    at all, both read as the default (`True`); only an explicit `false`
    turns it off. Public read-only introspection API for any consumer
    that wants to ask "is this on?" outside a land -- `frob ticket land`'s
    OWN internal decision instead reads `[tool.frob]` from root's git
    object at `pre_land_tip` (`frob.tickets._land_release._read_root_
    tool_frob_table`), never this on-disk read, because the T-1805
    field-scoped `pyproject.toml` reset can leave the on-disk copy
    missing this table entirely mid-land (see that function's own
    docstring)."""
    table = _read_tool_frob_table(root)
    return bool(table.get("dev_version_bump", True))


# frob:doc docs/modules/release.md#per-land-dev-version-bump-t-4184
# frob:ticket T-4184
# frob:tests tests/test_release.py::test_dev_version_major_ack_defaults_zero_and_reads_pyproject kind="unit"  # noqa: E501
def dev_version_major_ack(root: Path) -> int:
    """The major version series `root`'s `pyproject.toml` `[tool.frob]`
    table has explicitly acknowledged continuing to auto-bump dev builds
    into (T-4184's major-version guard) -- `0` (nothing acknowledged) if
    the key is absent, unparsable, or not an integer. A land whose
    computed dev-version bump would cross into a major series greater
    than this value refuses (`ReleaseError.MajorVersionAckRequired`)
    instead of silently bumping across the boundary, per the owner's own
    framing: an intention stated in prose is not enforcement, so keeping
    the toggle on across a major bump requires this configuration value,
    not a comment. Public read-only introspection API, same posture as
    `dev_version_bump_enabled` -- `frob ticket land`'s own internal
    refusal check reads this key from root's git object instead, for the
    same field-scoped-reset reason documented on that function."""
    table = _read_tool_frob_table(root)
    ack = table.get("dev_version_major_ack", 0)
    return ack if isinstance(ack, int) else 0


def _read_tool_frob_table(root: Path) -> dict:
    """Shared `pyproject.toml` `[tool.frob]` table reader for `dev_
    version_bump_enabled`/`dev_version_major_ack` (T-4184) -- `{}` on any
    missing file or parse failure, so both callers default open rather
    than raising on a malformed `pyproject.toml` a land's own REL001
    machinery would separately catch."""
    import tomllib

    path = root / "pyproject.toml"
    if not path.exists():
        return {}
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    table = data.get("tool", {}).get("frob", {})
    return table if isinstance(table, dict) else {}


__all__ = [
    "BumpClass",
    "ReleaseError",
    "ReleaseManifest",
    "authoritative_version",
    "bump_patch_version",
    "changelog_skeleton_entry",
    "current_version",
    "dev_version_bump_enabled",
    "dev_version_major_ack",
    "diff_class",
    "load_manifest",
    "manifest_path",
    "next_dev_version",
    "next_patch_version",
    "required_version",
    "rewrite_pyproject_version",
    "satisfies",
    "set_manifest_version",
    "stamp",
]

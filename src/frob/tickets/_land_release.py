"""`frob ticket land` -- release-bump/uv.lock/native-rebuild stage.

See docs/modules/tickets-landing.md#frob-ticket-land.

Split out of `frob.tickets._land_finalize` (T-1334, continuing the
verbatim-move discipline T-1186/T-1189/T-1192/T-1194/T-1251 established):
the REL001 version-bump family (`_read_root_pyproject_version`/
`_read_root_manifest_version`/`_release_bump_is_monotonic`/
`_log_monotonicity_refusal`/`_resync_release_manifest`/
`_apply_release_bump`), the gate-rule registry sync callback
(`_apply_gate_rule_sync`), the uv.lock re-sync helper
(`_sync_uv_lock_for_land`), and the native-staleness/rebuild pair
(`_warn_if_native_stale`/`_touches_native_source`/`_maybe_rebuild_natives`).
Zero caller-visible behavior change -- every moved function keeps its
original body, docstring, and `frob:ticket`/`frob:tests` directives
verbatim; `frob.tickets._land_squash` (the squash-apply/close family,
T-1334's other split-out module) imports what it still needs back from
here.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.tickets._land_git_ops import _verified_reset_root
from frob.tickets._models import LandError, Ticket

_log = get_logger(__name__)


# frob:ticket T-0248
def _warn_if_native_stale(root: Path, final_id: str) -> None:
    """LOUD, non-blocking log warning if `root`'s just-squashed source tree
    now outpaces its own built native extension(s) (T-0248): the incident
    class from T-0166's review, where a landed `strata-core/**` grammar
    change left main's built `strata_core` behind and `frob check` silently
    ran the OLD grammar until a human noticed a confusing SYS004. Fires
    regardless of whether a `rebuild_natives` callback is also supplied --
    a rebuild that runs but is not this warning's business to suppress, and
    a `rebuild_natives=None` caller still gets the loud heads-up either way."""
    from frob.strata._native_staleness import stale_native_warning

    warning = stale_native_warning(root)
    if warning is not None:
        _log.warning("land: %s -- %s", final_id, warning)


# frob:ticket T-0338
_NATIVE_SOURCE_PREFIXES = ("frob-core/", "strata-core/")


def _touches_native_source(changeset: frozenset[str]) -> bool:
    """Whether any path in `changeset` falls under a native-extension source
    tree (T-0338) -- the trigger condition for `rebuild_natives`: a landed
    change that never touched frob-core/strata-core has nothing stale to
    rebuild, so the (potentially slow, minutes-long cargo) rebuild is only
    ever invoked when it can actually matter."""
    return any(path.startswith(_NATIVE_SOURCE_PREFIXES) for path in changeset)


# frob:ticket T-0338
# frob:ticket T-0992
_LAND_PYPROJECT_VERSION_RE = re.compile(r'(?m)^version\s*=\s*"([^"]*)"')


# frob:ticket T-0992
def _read_root_pyproject_version(root: Path, pre_land_tip: str) -> str | None:
    """Read `pyproject.toml`'s `version = "..."` value as it stood at
    `pre_land_tip` -- MAIN's own last-committed state BEFORE this land's
    squash-apply touched the working tree -- via `git show`, or `None` if
    the file did not exist there / is unparsable. This is the T-0992
    monotonicity check's ground truth for "what MAIN already has".

    Deliberately reads the git OBJECT at `pre_land_tip`, never the
    working-tree file on disk: `pyproject.toml` is not protected from a
    ticket's own scope, so `git merge --squash` can (and, per the T-0976
    incident, did) carry a worktree's stale `pyproject.toml` straight into
    `root`'s working tree as part of the squash-apply itself, before
    `bump_version` ever runs -- reading the on-disk file at that point
    would just re-read the very corruption this check exists to catch.
    `pre_land_tip` (captured once, before any mutation, by `land`'s own
    `_rev_parse(root, "HEAD")`) is the one value in this whole flow that is
    guaranteed to still name MAIN's true pre-land commit."""
    shown = run_argv(["git", "-C", str(root), "show", f"{pre_land_tip}:pyproject.toml"])
    if shown.is_err or shown.danger_ok.returncode != 0:
        return None
    match = _LAND_PYPROJECT_VERSION_RE.search(shown.danger_ok.stdout)
    return match.group(1) if match else None


# frob:ticket T-1078
def _read_root_manifest_version(root: Path, pre_land_tip: str) -> str | None:
    """Read `.frob-release.json`'s `version` field as it stood at
    `pre_land_tip` (T-1078) -- the same git-object-read technique
    `_read_root_pyproject_version` uses for `pyproject.toml`, applied to
    the release manifest so an incoherent quartet (manifest lagging
    pyproject, the T-1078 incident class) can be DETECTED from ground
    truth rather than the worktree-carried on-disk copy the squash-apply
    may have already overwritten. `None` if the manifest did not exist at
    `pre_land_tip`, is unparsable JSON, or has no string `version` field --
    all treated as "nothing to compare", never raised."""
    shown = run_argv(
        ["git", "-C", str(root), "show", f"{pre_land_tip}:.frob-release.json"]
    )
    if shown.is_err or shown.danger_ok.returncode != 0:
        return None
    try:
        data = json.loads(shown.danger_ok.stdout)
    except ValueError:
        return None
    except Exception:
        # "All treated as 'nothing to compare', never raised" (this
        # function's own docstring) covers a genuinely unresolvable JSON
        # decode surprise too, not just `ValueError` (EXHAUST001, T-1371).
        return None
    version = data.get("version") if isinstance(data, dict) else None
    return version if isinstance(version, str) else None


# frob:ticket T-0992
def _release_bump_is_monotonic(pre_bump_version: str | None, new_version: str) -> bool:
    """Whether `new_version` is strictly greater than `pre_bump_version`
    (T-0992's hard monotonicity refusal, sibling of T-0959's archive
    assertion and T-0740's ledger integrity check). No prior version on
    disk (`pre_bump_version=None`, e.g. a `pyproject.toml`-less test root)
    is vacuously monotonic -- there is nothing to regress against. Falls
    back to a plain string inequality if either side fails PEP 440 parsing
    (e.g. a synthetic non-numeric version in a unit-test fixture) rather
    than raising -- this is a refusal gate, not a place to crash the whole
    land on a malformed version string."""
    if pre_bump_version is None:
        return True
    try:
        from packaging.version import Version

        return Version(new_version) > Version(pre_bump_version)
    except Exception:
        return new_version != pre_bump_version and new_version > pre_bump_version


# frob:ticket T-1760
def _version_not_regressed(pre_version: str | None, current_version: str) -> bool:
    """Whether `current_version` is greater than OR EQUAL TO `pre_version`
    (T-1760) -- the `>=` sibling of `_release_bump_is_monotonic`'s strict
    `>`. A REPORTED bump must be strictly greater (a bump that computes to
    the same version it started from is a bug in the bump math, not a
    legitimate no-op); but `_assert_no_monotonicity_regression`'s
    unconditional belt-and-braces check runs even when NO bump was
    reported at all, where "unchanged" is the expected, correct outcome
    (this ticket's own diff needed no new version) -- using the strict
    `>` there would wrongly refuse every land that legitimately bumps
    nothing. No prior version (`pre_version=None`) is vacuously not
    regressed, same as `_release_bump_is_monotonic`."""
    if pre_version is None:
        return True
    try:
        from packaging.version import Version

        return Version(current_version) >= Version(pre_version)
    except Exception:
        return current_version == pre_version or current_version > pre_version


# frob:ticket T-0338
# frob:ticket T-0907
# frob:ticket T-0992
# frob:ticket T-1078
def _log_monotonicity_refusal(
    final_id: str,
    new_version: str,
    pre_bump_version: str | None,
    pre_manifest_version: str | None,
) -> None:
    """Log the T-0992 monotonicity refusal (T-1078: split out of
    `_apply_release_bump` for ARCH001) -- names an incoherent quartet
    (`.frob-release.json` lagging `pyproject.toml` at `pre_land_tip`)
    explicitly and prescribes `frob release sync` when that desync is the
    actual cause, instead of the bare "not strictly greater" message that
    reads like a genuine version regression."""
    quartet_desynced = (
        pre_manifest_version is not None
        and pre_bump_version is not None
        and pre_manifest_version != pre_bump_version
    )
    if quartet_desynced:
        _log.error(
            "land: %s REL001 version-bump callback computed %s from "
            "a release manifest still at %s, but pyproject.toml is "
            "already at %s -- the release quartet (pyproject.toml/"
            "CHANGELOG.md/.frob-release.json) is INCOHERENT on main "
            "(manifest lagging pyproject); refusing (T-0992 "
            "monotonicity assertion) and unwinding the staged "
            "squash -- run `frob release sync` to reconcile the "
            "manifest to pyproject's actual version, then retry "
            "the land",
            final_id,
            new_version,
            pre_manifest_version,
            pre_bump_version,
        )
    else:
        _log.error(
            "land: %s REL001 version-bump callback computed %s, "
            "which is not strictly greater than main's pre-land "
            "version %s -- refusing (T-0992 monotonicity assertion) "
            "and unwinding the staged squash; the bump input must "
            "be derived from root's current state, never a stale "
            "worktree-carried value",
            final_id,
            new_version,
            pre_bump_version,
        )


# frob:ticket T-1358
def _read_working_pyproject_version(root: Path) -> str | None:
    """Read `pyproject.toml`'s `version = "..."` value straight off `root`'s
    WORKING TREE (never a git object) -- the ground truth for whatever a
    `bump_version` callback (or a stray worktree-carried squash-apply file)
    actually left on disk, as opposed to `_read_root_pyproject_version`'s
    pre-land git-object read. `None` if the file is missing or unparsable,
    treated by `_ensure_release_quartet_coherent` as "nothing to compare"."""
    path = root / "pyproject.toml"
    if not path.exists():
        return None
    match = _LAND_PYPROJECT_VERSION_RE.search(path.read_text(encoding="utf-8"))
    return match.group(1) if match else None


# frob:ticket T-1358
def _read_working_manifest_version(root: Path) -> str | None:
    """Read `.frob-release.json`'s `version` field straight off `root`'s
    WORKING TREE (never a git object) -- the write-side companion to
    `_read_working_pyproject_version`, used by `_ensure_release_quartet_
    coherent` to detect a manifest that is already staged/committed-stale
    relative to `pyproject.toml`'s on-disk value. `None` if the manifest is
    missing, unparsable, or has no string `version` field."""
    path = root / ".frob-release.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return None
    except json.JSONDecodeError:
        return None
    except ValueError:
        return None
    except Exception:
        # "`None` if the manifest is missing, unparsable, or has no
        # string `version` field" (this function's own docstring) covers
        # any read/decode surprise, not just the two named cases
        # (EXHAUST001/EXHAUST002, T-1371).
        return None
    version = data.get("version") if isinstance(data, dict) else None
    return version if isinstance(version, str) else None


# frob:ticket T-1358
# frob:ticket T-1771
# frob:tests tests/unit/test_land_release_coherence.py::TestUvLockCoherenceWhenAlreadyBumped.test_stale_lock_resynced_even_when_pyproject_and_manifest_agree  # noqa: E501
# frob:tests tests/unit/test_land_release_coherence.py::TestUvLockCoherenceWhenAlreadyBumped.test_lock_already_coherent_is_untouched  # noqa: E501
def _ensure_release_quartet_coherent(
    root: Path, final_id: str
) -> Result[None, LandError]:
    """Unconditional, final coherence check between `pyproject.toml`'s
    on-disk version and `.frob-release.json`'s on-disk version (T-1358):
    closes the gap `_apply_release_bump`'s existing `_resync_release_
    manifest` step left open -- that step only fires inside the `if
    bumped.danger_ok is not None` branch, so a `bump_version` callback that
    reports `Ok(None)` (e.g. because IT ALREADY wrote pyproject.toml/the
    manifest itself, or believed no bump was needed) skips the resync
    entirely, even if pyproject.toml's actual on-disk version has since
    diverged from the manifest's (the exact T-1340 incident: pyproject.toml
    bumped 0.289.0 -> 0.290.0, `.frob-release.json` left at 0.289.0,
    blocking every subsequent land on the T-0992 monotonicity guard).

    Called at the very end of `_apply_release_bump`, after every other
    branch, regardless of whether a bump was reported at all -- this is a
    structural guarantee ("the quartet is coherent when land finishes"),
    not a bump-path-specific patch. `Ok(None)` (no-op) when either file is
    unreadable/unparsable (nothing to compare) or the two versions already
    agree; force-resyncs and stages `.frob-release.json` to pyproject.
    toml's value otherwise. A resync failure here is `Err(LandError.
    ReleaseBumpFailed)`, same fail-closed posture as every other release
    step in this module -- caller unwinds via `_verified_reset_root`.

    T-1771: `_ensure_uv_lock_coherent` used to be called ONLY from inside
    the `pyproject_version != manifest_version` branch below -- so the
    COMMON case (pyproject and the manifest already agree, no bump
    needed) skipped the `uv.lock` check entirely, leaving it exactly the
    "quartet is really a trio" gap this ticket's own body describes. The
    lock check now runs whenever `pyproject_version` is known at all,
    independent of whether the manifest half needed a resync -- the two
    checks are siblings under the same "always verify this member of the
    quartet" umbrella, not one nested inside the other.

    NAME NOTE (T-1771 item 3, written down rather than silently fixed by
    a rename that would touch every caller/test referencing this name):
    this function verifies THREE of the release quartet's four members
    at LAND time -- `pyproject.toml`, `.frob-release.json`, `uv.lock`.
    The fourth, `CHANGELOG.md`, is deliberately NOT checked here -- it is
    checked by REL001 (`frob.gates.release_gate`, `_no CHANGELOG.md
    entry for {version}` check) at GATE time instead, since a missing
    entry is a `frob check` finding an operator can see and fix before
    landing, not a land-time auto-resync the way the other three members
    are (there is no single "correct" changelog PROSE to force-write the
    way there is a correct version NUMBER). If this function is ever
    renamed, keep this split explicit in the new name/docstring rather
    than re-litigating where CHANGELOG.md belongs."""
    pyproject_version = _read_working_pyproject_version(root)
    manifest_version = _read_working_manifest_version(root)
    if pyproject_version is not None and manifest_version is not None:
        resynced = _resync_manifest_if_diverged(
            root, final_id, pyproject_version, manifest_version
        )
        if resynced.is_err:
            return resynced
    if pyproject_version is None:
        return Ok(None)
    return _ensure_uv_lock_coherent(root, final_id, pyproject_version)


# frob:ticket T-1771
def _resync_manifest_if_diverged(
    root: Path, final_id: str, pyproject_version: str, manifest_version: str
) -> Result[None, LandError]:
    """The manifest half of `_ensure_release_quartet_coherent`'s check --
    split out purely to keep the parent under ARCH001's line threshold,
    no behavior change. `Ok(None)` when the two already agree."""
    if pyproject_version == manifest_version:
        return Ok(None)
    _log.warning(
        "land: %s release quartet incoherent after bump step "
        "(pyproject.toml=%s, .frob-release.json=%s) -- force-resyncing "
        "the manifest to pyproject.toml's on-disk version",
        final_id,
        pyproject_version,
        manifest_version,
    )
    return _resync_release_manifest(root, final_id, pyproject_version)


# frob:ticket T-1771
def _read_working_uv_lock_version(root: Path) -> str | None:
    """The `frob` package's own `version` as `uv.lock` currently records
    it on disk, or `None` when there is no lock or the entry cannot be
    found -- `None` means "nothing to compare", never "they agree"."""
    import re

    lock = root / "uv.lock"
    if not lock.exists():
        return None
    try:
        text = lock.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(
        r'\[\[package\]\]\nname = "frob"\nversion = "([^"]+)"', text
    )
    return match.group(1) if match else None


# frob:ticket T-1771
def _ensure_uv_lock_coherent(
    root: Path, final_id: str, pyproject_version: str
) -> Result[None, LandError]:
    """Keep `uv.lock`'s recorded `frob` version in step with
    `pyproject.toml`, unconditionally, at the end of every land.

    `_sync_uv_lock_for_land` only ever ran inside `_apply_release_bump`'s
    "a bump was reported" branch, and `_ensure_release_quartet_coherent`
    compared only pyproject against the manifest -- so the "quartet" was
    in practice a trio and `uv.lock` could drift a version behind without
    anything noticing. It then flapped dirty on the next `uv run`
    anywhere in the repo, tripping REL002/DirtyMain for whichever
    worktree looked next (T-1770; observed on main at
    pyproject/manifest 0.368.0 against a lock still recording 0.367.0).

    Version syncing is meant to be automatic, so this is a structural
    guarantee rather than a bump-path patch: if the lock disagrees, it is
    re-derived and staged regardless of how the version got where it is."""
    lock_version = _read_working_uv_lock_version(root)
    if lock_version is None or lock_version == pyproject_version:
        return Ok(None)
    _log.warning(
        "land: %s uv.lock records frob %s but pyproject.toml declares %s "
        "-- re-syncing the lock so it does not flap dirty on the next "
        "invocation (T-1770)",
        final_id,
        lock_version,
        pyproject_version,
    )
    return _sync_uv_lock_for_land(root, final_id)


# frob:ticket T-1078
def _resync_release_manifest(
    root: Path, final_id: str, new_version: str
) -> Result[None, LandError]:
    """Force `.frob-release.json`'s version to `new_version` and stage it
    (T-1078: split out of `_apply_release_bump` for ARCH001) -- the
    atomic-write fix for the incident where a REL001 bump updated
    `pyproject.toml`/`CHANGELOG.md` but left the manifest on its old
    version, regardless of whether the `bump_version` callback itself
    wrote (or correctly wrote) the manifest. `Ok(None)` when there was
    nothing to resync (`ReleaseError.NoManifest` -- a repo that never
    adopted `frob release stamp`) as well as on a successful resync;
    `Err(LandError.ReleaseBumpFailed)` if the write or the `git add`
    fails."""
    from frob.release import ReleaseError, set_manifest_version

    resynced = set_manifest_version(root, new_version)
    if resynced.is_err and resynced.danger_err != ReleaseError.NoManifest:
        _log.error(
            "land: %s could not resync .frob-release.json to %s (%s) -- "
            "unwinding the staged squash",
            final_id,
            new_version,
            resynced.danger_err,
        )
        return Err(LandError.ReleaseBumpFailed)
    if resynced.is_ok:
        staged = run_argv(["git", "-C", str(root), "add", ".frob-release.json"])
        if staged.is_err or staged.danger_ok.returncode != 0:
            _log.error("land: %s failed to stage resynced .frob-release.json", final_id)
            return Err(LandError.ReleaseBumpFailed)
    return Ok(None)


#: T-1760: the three files a land-time release bump governs together --
#: `pyproject.toml`'s version line, the changelog, and the REL001 baseline
#: manifest. `uv.lock` is a fourth, separately-synced artifact
#: (`_sync_uv_lock_for_land`) with its own re-derivation from
#: `pyproject.toml`, not part of this specific reset (a stale `uv.lock` is
#: harmless -- it gets re-synced unconditionally after the bump either
#: way -- unlike these three, which are the ones a stale worktree copy can
#: silently regress).
_LAND_OWNED_RELEASE_FILES = ("pyproject.toml", "CHANGELOG.md", ".frob-release.json")

#: T-1805 (the land-composition-hole ticket): `CHANGELOG.md` and
#: `.frob-release.json` are reset WHOLE-FILE (below) because both are
#: genuinely, entirely land-owned in practice -- the scaffolded
#: pre-commit hook (`src/frob/scaffold/project.py`'s worktree-lease
#: install) refuses ANY worktree commit touching `CHANGELOG.md` at all,
#: and `.frob-release.json` is a wholly land-derived manifest no ticket
#: has a legitimate reason to hand-edit. `pyproject.toml` is different:
#: that same hook only refuses a commit that changes the `version = `
#: line specifically (`playbook.md#4b`) -- every OTHER field
#: (`[project.optional-dependencies]`, `[tool.*]`, `[build-system]`,
#: entry points, ...) is explicit, legitimate worktree-agent territory.
#: A whole-file reset therefore silently discarded real ticket work
#: whenever a landing ticket's only change happened to be a non-version
#: `pyproject.toml` edit (confirmed: T-1508's one-line dependency pin,
#: dropped four consecutive times). `_RESET_FIELD_LEVEL` names the one
#: file that gets a field-scoped reset instead of a whole-file one.
#:
#: T-1760 ROOT CAUSE this whole reset exists to close: none of these
#: three files is protected by `ticket.scope`
#: (`_auto_resolve_out_of_scope_conflicts` only fires on a genuine git
#: CONFLICT, keep="ours"), and `git merge --squash` performs an ordinary
#: clean 3-way merge on any file that does NOT conflict. A worktree
#: branched before a sibling's land already advanced these files carries
#: its own (older) copies at whatever content they held at the
#: worktree's OWN merge-base -- when that differs from root's current
#: HEAD, the squash's per-file 3-way merge can resolve CLEANLY (no
#: conflict object at all) by taking the worktree's side, silently
#: regressing root's working tree to a version/manifest OLDER than what
#: root's last real commit already declared. Measured on main across
#: four consecutive lands (T-1692/T-1754/T-1755/T-1756): the version
#: oscillated 0.366.0 -> 0.365.0 -> 0.366.0 -> 0.365.0, each backward
#: step exactly this shape. Resetting FIRST, unconditionally, on every
#: land (not just when a regression is detected) is the fix T-1760 asked
#: for directly: the bump is a function of (root's manifest, the landing
#: API) and should be evaluated from root's own state at squash time,
#: never from whatever a worktree happened to carry.
_RESET_FIELD_LEVEL = frozenset({"pyproject.toml"})


# frob:ticket T-1760
# frob:ticket T-1805
def _reset_release_artifacts_to_pre_land(root: Path, pre_land_tip: str) -> None:
    """RECOMPUTE, DO NOT CARRY (T-1760, narrowed to field granularity by
    T-1805): discard whatever `git merge --squash` staged for the
    LAND-OWNED portion of `pyproject.toml`/`CHANGELOG.md`/
    `.frob-release.json` in `root`'s working tree and INDEX, resetting it
    back to `pre_land_tip` -- root's own true, last-committed state --
    before `bump_version` (or anything else in this module) ever reads or
    writes it. See the module-level "T-1760/T-1805 reset rationale"
    comment above `_LAND_OWNED_RELEASE_FILES` for the full root-cause
    history (why this exists, and why T-1805 narrowed pyproject.toml's
    reset from whole-file to field-scoped). Per-file work is delegated to
    `_reset_one_land_owned_file` so this loop itself stays short; a
    reset failure for any one file is logged and treated as a no-op,
    never fatal -- consistent with every other absence case this module
    already treats as "nothing to compare" (`_read_root_pyproject_
    version`/`_read_root_manifest_version` both return `None` the same
    way)."""
    for rel in _LAND_OWNED_RELEASE_FILES:
        _reset_one_land_owned_file(root, pre_land_tip, rel)


# frob:ticket T-1760
# frob:ticket T-1805
def _reset_one_land_owned_file(root: Path, pre_land_tip: str, rel: str) -> None:
    """One file's worth of `_reset_release_artifacts_to_pre_land`'s work
    (split out purely to keep that loop under ARCH001's line threshold,
    no behavior change from inlining): `pyproject.toml` gets the T-1805
    FIELD-scoped reset (`_reset_pyproject_version_field_only`, only its
    `version = "..."` line is rewound); every other `_LAND_OWNED_RELEASE_
    FILES` entry gets the original T-1760 whole-file `git checkout`
    reset. Both branches degrade to a logged no-op on failure, never
    raise."""
    if rel in _RESET_FIELD_LEVEL:
        ok = _reset_pyproject_version_field_only(root, pre_land_tip)
        if not ok:
            _log.debug(
                "land: %s field-level version reset of %s to pre-land "
                "%s skipped (not present at that commit, unparsable, "
                "or nothing to reset) -- treated as a no-op",
                root,
                rel,
                pre_land_tip,
            )
        return
    checkout = run_argv(["git", "-C", str(root), "checkout", pre_land_tip, "--", rel])
    if checkout.is_err or checkout.danger_ok.returncode != 0:
        _log.debug(
            "land: %s reset of %s to pre-land %s skipped (not present at "
            "that commit, or nothing to reset) -- treated as a no-op",
            root,
            rel,
            pre_land_tip,
        )
        return
    staged = run_argv(["git", "-C", str(root), "add", "--", rel])
    if staged.is_err or staged.danger_ok.returncode != 0:
        _log.warning(
            "land: %s could not stage the pre-land reset of %s -- a stale "
            "squash-carried copy may still be in the index",
            root,
            rel,
        )


# frob:ticket T-1805
def _reset_pyproject_version_field_only(root: Path, pre_land_tip: str) -> bool:
    """T-1805: rewind ONLY `pyproject.toml`'s `version = "..."` line to
    its `pre_land_tip` value, leaving every other line -- and therefore
    every other field a landing ticket legitimately touched
    (`[project.optional-dependencies]`, `[tool.*]`, `[build-system]`,
    entry points, ...) -- exactly as the squash staged it. Returns
    `True` if a rewrite (or a confirmed no-op, e.g. the line already
    matches) happened, `False` if there was nothing safe to do (no
    `pre_land_tip` version, no on-disk file, or the on-disk file has no
    version line to rewrite) -- callers treat `False` as a no-op, never a
    fatal condition, matching every other absence case in this module.

    Reads `pre_land_tip`'s version via `_read_root_pyproject_version`
    (the same git-object read `_apply_release_bump`'s own monotonicity
    check already trusts as ground truth), then substitutes it into the
    WORKING TREE's current `pyproject.toml` text via
    `_LAND_PYPROJECT_VERSION_RE` -- never a whole-file overwrite, so a
    squash-staged edit to any other field survives untouched."""
    pre_version = _read_root_pyproject_version(root, pre_land_tip)
    if pre_version is None:
        return False
    pyproject_path = root / "pyproject.toml"
    try:
        current_text = pyproject_path.read_text(encoding="utf-8")
    except OSError:
        return False
    if not _LAND_PYPROJECT_VERSION_RE.search(current_text):
        return False
    new_text = _LAND_PYPROJECT_VERSION_RE.sub(
        f'version = "{pre_version}"', current_text, count=1
    )
    if new_text == current_text:
        return True
    try:
        pyproject_path.write_text(new_text, encoding="utf-8")
    except OSError:
        _log.warning(
            "land: %s could not rewrite pyproject.toml's version field back "
            "to pre-land %s -- a stale squash-carried version may still be "
            "on disk",
            root,
            pre_land_tip,
        )
        return False
    staged = run_argv(["git", "-C", str(root), "add", "--", "pyproject.toml"])
    if staged.is_err or staged.danger_ok.returncode != 0:
        _log.warning(
            "land: %s could not stage the pre-land version-field reset of "
            "pyproject.toml -- a stale squash-carried copy may still be in "
            "the index",
            root,
        )
    return True


def _apply_release_bump(
    root: Path,
    ticket: Ticket,
    final_id: str,
    bump_version: Callable[[Path, Ticket, str], Result[str | None, LandError]] | None,
    pre_land_tip: str,
) -> Result[str | None, LandError]:
    """Invoke `bump_version(root, ticket, final_id)` if supplied, unwinding
    the staged squash via `_verified_reset_root` (T-0907) on failure
    (T-0338). `bump_version=None` is a no-op returning `Ok(None)` -- see
    `land`'s docstring for why this is a caller-supplied callback.

    T-1760: BEFORE any of that, `_reset_release_artifacts_to_pre_land`
    unconditionally discards whatever `git merge --squash` carried for
    `pyproject.toml`/`CHANGELOG.md`/`.frob-release.json`, resetting all
    three to root's own pre-land committed state -- RECOMPUTE, DO NOT
    CARRY, closing the class of regression this ticket exists for at its
    source rather than only detecting it after the fact.

    T-0992: captures main's own pre-`pre_land_tip` `pyproject.toml`
    version and hard-refuses (via `_log_monotonicity_refusal`, T-1078)
    unless a reported bump is strictly greater than it -- guards against a
    `bump_version` implementation computing its "next version" from a
    stale, worktree-carried input (T-0976, T-0989).

    T-1078: after a successful, monotonic bump, `_resync_release_manifest`
    force-resyncs `.frob-release.json`'s version to `new_version` in this
    SAME step, regardless of whether `bump_version` itself wrote the
    manifest correctly -- the fix for a REL001 bump that updated
    pyproject.toml/CHANGELOG.md but left the manifest stale, desyncing the
    quartet and blocking every subsequent land on the T-0992 guard.

    T-1760: even when `bump_version` reports `Ok(None)` (no new bump
    needed), `_assert_no_monotonicity_regression` is now still run as an
    unconditional belt-and-braces assertion -- required item 4 of T-1760:
    "never less than its own manifest's, and never less than the previous
    commit's" -- defense in depth alongside the reset above, in case a
    future caller reintroduces a carry path this function does not yet
    know about."""
    if bump_version is None:
        return Ok(None)
    _reset_release_artifacts_to_pre_land(root, pre_land_tip)
    pre_bump_version = _read_root_pyproject_version(root, pre_land_tip)
    pre_manifest_version = _read_root_manifest_version(root, pre_land_tip)
    bumped = bump_version(root, ticket, final_id)
    if bumped.is_err:
        _log.error(
            "land: %s REL001 version-bump callback failed (%s) -- unwinding "
            "the staged squash; bump pyproject.toml/CHANGELOG.md by hand "
            "(`frob release stamp` once fixed) and retry",
            final_id,
            bumped.danger_err,
        )
        unwound = _verified_reset_root(root, pre_land_tip, final_id)
        return Err(unwound.danger_err if unwound.is_err else bumped.danger_err)
    if bumped.danger_ok is not None:
        applied = _apply_reported_bump(
            root, final_id, bumped.danger_ok, pre_bump_version, pre_manifest_version
        )
        if applied.is_err:
            unwound = _verified_reset_root(root, pre_land_tip, final_id)
            return Err(unwound.danger_err if unwound.is_err else applied.danger_err)
    finalized = _finalize_release_coherence(
        root, final_id, pre_land_tip, pre_bump_version, pre_manifest_version
    )
    if finalized.is_err:
        return Err(finalized.danger_err)
    return bumped


# frob:ticket T-1760
def _finalize_release_coherence(
    root: Path,
    final_id: str,
    pre_land_tip: str,
    pre_bump_version: str | None,
    pre_manifest_version: str | None,
) -> Result[None, LandError]:
    """`_apply_release_bump`'s last two checks (T-1760: split out to keep
    the parent under ARCH001's line threshold), run unconditionally
    regardless of which branch above produced `root`'s current working
    tree: T-1358's quartet-coherence check, then T-1760's own belt-and-
    braces monotonicity assertion. Either failing unwinds the staged
    squash via `_verified_reset_root`, same as every other failure path
    in this module."""
    # T-1358: unconditional final coherence check -- covers the gap the
    # caller's own branch above leaves open (a `bump_version` callback
    # reporting `Ok(None)` while pyproject.toml's on-disk version has
    # already diverged from the manifest, e.g. a worktree-carried stale
    # file, or a callback that wrote pyproject.toml itself without
    # reporting it back through the return value) as well as defense-in-
    # depth against that branch's own resync silently not sticking.
    coherent = _ensure_release_quartet_coherent(root, final_id)
    if coherent.is_err:
        unwound = _verified_reset_root(root, pre_land_tip, final_id)
        return Err(unwound.danger_err if unwound.is_err else coherent.danger_err)
    regressed = _assert_no_monotonicity_regression(
        root, final_id, pre_bump_version, pre_manifest_version
    )
    if regressed.is_err:
        unwound = _verified_reset_root(root, pre_land_tip, final_id)
        return Err(unwound.danger_err if unwound.is_err else regressed.danger_err)
    return Ok(None)


# frob:ticket T-1760
def _assert_no_monotonicity_regression(
    root: Path,
    final_id: str,
    pre_bump_version: str | None,
    pre_manifest_version: str | None,
) -> Result[None, LandError]:
    """Required item 4 of T-1760: an unconditional final check that
    `root`'s working-tree `pyproject.toml`/`.frob-release.json` versions
    are never LESS than main's own pre-land versions (`pre_bump_version`/
    `pre_manifest_version`), run regardless of whether `bump_version`
    reported a new bump. Belt-and-braces alongside `_reset_release_
    artifacts_to_pre_land`'s prevention: that reset already makes a
    regression structurally unreachable through the path this module
    controls, so this assertion should never actually fire in practice --
    it exists so a regression introduced by a FUTURE change to this
    module (or a caller that bypasses the reset) fails LOUDLY and refuses
    the land, instead of silently repeating the T-1760 incident. `None`
    inputs (no prior version recorded, e.g. a manifest-less test root) are
    vacuously fine -- nothing to regress against, mirrors `_release_bump_
    is_monotonic`'s own `pre_bump_version is None` short-circuit."""
    working_pyproject = _read_working_pyproject_version(root)
    working_manifest = _read_working_manifest_version(root)
    if working_pyproject is not None and pre_bump_version is not None:
        if not _version_not_regressed(pre_bump_version, working_pyproject):
            _log.error(
                "land: %s pyproject.toml version %s is not >= main's "
                "pre-land version %s after the release-bump step -- T-1760 "
                "monotonicity assertion refusing rather than landing a "
                "backward version move",
                final_id,
                working_pyproject,
                pre_bump_version,
            )
            return Err(LandError.ReleaseBumpFailed)
    if working_manifest is not None and pre_manifest_version is not None:
        if not _version_not_regressed(pre_manifest_version, working_manifest):
            _log.error(
                "land: %s .frob-release.json version %s is not >= main's "
                "pre-land manifest version %s after the release-bump step "
                "-- T-1760 monotonicity assertion refusing rather than "
                "landing a regressed REL001 baseline",
                final_id,
                working_manifest,
                pre_manifest_version,
            )
            return Err(LandError.ReleaseBumpFailed)
    return Ok(None)


# frob:ticket T-1358
def _apply_reported_bump(
    root: Path,
    final_id: str,
    new_version: str,
    pre_bump_version: str | None,
    pre_manifest_version: str | None,
) -> Result[None, LandError]:
    """The `bumped.danger_ok is not None` half of `_apply_release_bump`
    (T-1358: split out to keep the parent under ARCH001's line threshold,
    zero behavior change) -- monotonicity check, forced manifest resync,
    and `uv.lock` re-sync, in that order, for a `bump_version` callback
    that reported a real `new_version`."""
    if not _release_bump_is_monotonic(pre_bump_version, new_version):
        _log_monotonicity_refusal(
            final_id, new_version, pre_bump_version, pre_manifest_version
        )
        return Err(LandError.ReleaseBumpFailed)
    resynced = _resync_release_manifest(root, final_id, new_version)
    if resynced.is_err:
        return Err(resynced.danger_err)
    _log.info(
        "land: %s REL001 version bump applied and staged: -> %s",
        final_id,
        new_version,
    )
    return _sync_uv_lock_for_land(root, final_id)


# frob:ticket T-1011
# frob:tests \
# tests/test_ticket_land.py::TestSyncGateRulesCallback.test_sync_gate_rules_none_is_noop
# frob:tests tests/test_ticket_land.py::TestSyncGateRulesCallback.test_sync_gate_rules_applies_and_stages  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestSyncGateRulesCallback.test_sync_gate_rules_failure_unwinds  # noqa: E501
def _apply_gate_rule_sync(
    root: Path,
    final_id: str,
    sync_gate_rules: Callable[[Path, str], Result[tuple[str, ...] | None, LandError]]
    | None,
    pre_land_tip: str,
) -> Result[tuple[str, ...] | None, LandError]:
    """Invoke `sync_gate_rules(root, pre_land_tip)` if supplied, unwinding
    the staged squash via `_verified_reset_root` (same T-0907 pattern as
    `_apply_release_bump`) on failure (T-1011). `sync_gate_rules=None` (the
    library default) is a no-op returning `Ok(None)` -- see `land`'s
    docstring for why this is a caller-supplied callback rather than
    computed here (cycle-avoidance, docs/rework.md). A failure here is
    treated with the same fail-closed posture as a `bump_version` failure:
    a silently-skipped sync would let a landed gate-rule change slip past
    REG010 registry staleness undetected."""
    if sync_gate_rules is None:
        return Ok(None)
    synced = sync_gate_rules(root, pre_land_tip)
    if synced.is_err:
        _log.error(
            "land: %s gate-rule registry sync callback failed (%s) -- "
            "unwinding the staged squash; run `frob registry audit "
            "--sync-gate-rules` by hand and retry",
            final_id,
            synced.danger_err,
        )
        unwound = _verified_reset_root(root, pre_land_tip, final_id)
        return Err(unwound.danger_err if unwound.is_err else synced.danger_err)
    if synced.danger_ok:
        _log.info(
            "land: %s gate-rule registry auto-synced: filed %d rule id(s): %s",
            final_id,
            len(synced.danger_ok),
            ", ".join(synced.danger_ok),
        )
    return synced


# frob:ticket T-0793
def _sync_uv_lock_for_land(root: Path, final_id: str) -> Result[None, LandError]:
    """Re-sync `root`'s `uv.lock` and stage it in the SAME land commit as
    a just-applied REL001 version bump (T-0793): `uv run`/`uv lock` re-
    derives the `frob` package's `version = "..."` line from `pyproject.
    toml` on every invocation, so a bumped pyproject with a stale lock
    flaps that one line dirty on every subsequent invocation anywhere in
    the repo, tripping DirtyMain/SCOPE001 for whichever worktree notices
    next. Runs `uv lock` through `run_argv` (the guarded T-0778 seam --
    never a bare `subprocess` call, so `FROB_DISABLE_EXEC=1` still
    refuses it like every other spawn in this module) and `git add`s the
    result. This is only invoked right after `bump_version` reports a real
    version change, never on every land.

    Skipped entirely (returns `Ok(None)` without spawning anything) when
    `root` has no `pyproject.toml` -- not every `land()` caller's tree is
    a real uv project (test fixtures, other callers of this library), and
    there is nothing to lock in that case."""
    if not (root / "pyproject.toml").exists():
        _log.debug(
            "land: %s no pyproject.toml at %s, skipping uv.lock re-sync",
            final_id,
            root,
        )
        return Ok(None)
    synced = run_argv(["uv", "lock"], cwd=root, timeout_s=120.0)
    if synced.is_err or synced.danger_ok.returncode != 0:
        _log.error(
            "land: %s uv.lock re-sync failed after version bump -- %s",
            final_id,
            synced.danger_err if synced.is_err else synced.danger_ok.stderr,
        )
        return Err(LandError.ReleaseBumpFailed)
    staged = run_argv(["git", "-C", str(root), "add", "uv.lock"])
    if staged.is_err or staged.danger_ok.returncode != 0:
        _log.error("land: %s failed to stage re-synced uv.lock", final_id)
        return Err(LandError.GitFailed)
    _log.info("land: %s re-synced and staged uv.lock after version bump", final_id)
    return Ok(None)


# frob:ticket T-0338
def _maybe_rebuild_natives(
    root: Path,
    final_id: str,
    changeset: frozenset[str],
    rebuild_natives: Callable[[Path], bool] | None,
) -> bool:
    """Invoke `rebuild_natives(root)` when `changeset` touches a native
    source tree (T-0338); best-effort -- a `False`/exception-free failure
    is logged but never unwinds or blocks the land (the T-0248 stale-native
    warning already covers the "you must rebuild before trusting checks"
    heads-up; this is the "land tried to do it for you" upgrade, not a new
    hard gate). `rebuild_natives=None` (the library default) or a changeset
    that never touches frob-core/strata-core is a no-op returning `False`."""
    if rebuild_natives is None or not _touches_native_source(changeset):
        return False
    rebuilt = rebuild_natives(root)
    if rebuilt:
        _log.info("land: %s native extension(s) rebuilt after landing", final_id)
    else:
        _log.warning(
            "land: %s native source changed but the rebuild callback "
            "reported failure -- run `make core` manually before trusting "
            "`frob check`/`frob test` against %s",
            final_id,
            root,
        )
    return rebuilt

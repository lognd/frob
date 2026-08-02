"""`frob ticket land` -- release-bump/uv.lock/native-rebuild stage.

See docs/modules/tickets.md#frob-ticket-land.

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
# frob:waive INV006 preset="split-carried-prose"

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
    step in this module -- caller unwinds via `_verified_reset_root`."""
    pyproject_version = _read_working_pyproject_version(root)
    manifest_version = _read_working_manifest_version(root)
    if pyproject_version is None or manifest_version is None:
        return Ok(None)
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
    quartet and blocking every subsequent land on the T-0992 guard."""
    if bump_version is None:
        return Ok(None)
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
    # T-1358: unconditional final coherence check -- covers the gap the
    # branch above leaves open (a `bump_version` callback reporting
    # `Ok(None)` while pyproject.toml's on-disk version has already
    # diverged from the manifest, e.g. a worktree-carried stale file, or a
    # callback that wrote pyproject.toml itself without reporting it back
    # through this return value) as well as defense-in-depth against the
    # branch above's own resync silently not sticking.
    coherent = _ensure_release_quartet_coherent(root, final_id)
    if coherent.is_err:
        unwound = _verified_reset_root(root, pre_land_tip, final_id)
        return Err(unwound.danger_err if unwound.is_err else coherent.danger_err)
    return bumped


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
# frob:tests tests/test_ticket_land.py::TestSyncGateRulesCallback.test_sync_gate_rules_none_is_noop  # noqa: E501
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

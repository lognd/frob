"""`frob sync-skills` (T-2241): bidirectional, cross-platform sync of this
repo's `agents/`/`skills/` directories into `~/.claude/agents`/
`~/.claude/skills`, replacing Makefile's `sync-skills:` bash recipe (two
POSIX `for` loops copying in, two more removing stale entries) -- pure
`pathlib`/`shutil`, no shelled-out loop, `basename`, or `[ -d ]` test, so
it runs identically on Windows (T-1205 acceptance[3]).

The recipe this replaces is genuinely bidirectional, not a one-way copy:
an entry present in the repo is created/updated under `~/.claude`, and an
entry present under `~/.claude` with no repo-side counterpart is removed
(`~/.claude` is kept in sync WITH the repo, not merely seeded from it
once). `sync_skills` implements that directly; `run` is the thin CLI
entry point `frob.__main__._dispatch` calls the same way it dispatches
`bind`/`agent`/`worktree` -- see this module's own `run` docstring for
why this subcommand is dispatched directly rather than through
`frob.app.app`'s uniform `AppConfig`-based runner registry.

T-2386 (child of T-2384): the pre-fix version of `_sync_one_kind` removed
every `claude_kind_dir` entry with no repo-side counterpart, full stop --
correct for a single repo mirroring itself into `~/.claude`, actively
destructive the moment a SECOND frob-enabled repo syncs `agents/`/
`skills/` into the same shared `~/.claude`: each repo's sync deleted the
other's entries wholesale, and alternating runs flapped them in and out.
It also `copytree(dirs_exist_ok=True)`'d over any existing destination
unconditionally, silently overwriting a hand-maintained or other-repo
entry sharing a name.

The fix is provenance tracking, not a new cooperative primitive --
`scaffold/project.py` already has the convention this needed
(`render_project`/`install_worktree_lease_hook`'s `exists() ->
Err(OutputExists)-without-force` guard, see `SyncCollision` below) and
this module reuses it rather than inventing a third mechanism (`scaffold/
_managed.py`'s BEGIN/END marker convention does not fit here -- that
rewrites known regions of ONE file in place; this rewrites whole,
arbitrarily-named directory trees, a shape markers cannot express).

A `SyncManifest` (`<claude_dir>/.frob-sync-manifest.json`, keyed by this
repo's own resolved root path) records exactly which `<kind>/<name>`
entries THIS repo installed. Two rules follow directly from that record:

- Removal is restricted to entries the manifest says THIS repo installed
  and that are now absent repo-side -- an entry another repo installed,
  or one nobody's manifest ever claimed (hand-maintained), is never
  removed, regardless of what the current repo-side listing says.
- Copy-in refuses (a `SyncCollision`, reported, not silently applied)
  when the destination already exists and this repo's manifest does not
  already own it -- i.e. the first time any repo tries to write over
  something it did not itself put there. `--force` overrides a
  collision and claims ownership going forward; the default posture
  never overwrites blind."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from pydantic import BaseModel

from frob.logging import get_logger
from frob.render import Renderer

_log = get_logger(__name__)

#: The two directory kinds this recipe syncs -- `agents/<name>/` ->
#: `~/.claude/agents/<name>/`, `skills/<name>/` -> `~/.claude/skills/<name>/`,
#: identical treatment for both (mirrors the old recipe's two near-identical
#: `for` loop pairs).
_SYNCED_KINDS = ("agents", "skills")

#: T-2386: the provenance manifest's filename, directly under `claude_dir`.
#: Dotfile so it reads as tooling state, not a synced `<kind>/<name>` entry
#: itself (`_repo_entry_names` only considers directories, so this file
#: would be inert either way, but the dotfile naming keeps intent obvious
#: to a human browsing `~/.claude`).
_MANIFEST_FILENAME = ".frob-sync-manifest.json"


# frob:ticket T-2241
# frob:ticket T-2386
# frob:doc docs/commands/sync-skills.md#public-api
# frob:tests tests/unit/test_skills_sync.py::TestSyncSkills.test_syncs_new_repo_entries  # noqa: E501
class SkillsSyncReport(BaseModel):
    """One `sync_skills` call's effect: which `<kind>/<name>` entries were
    created-or-updated under `claude_dir`, which stale, THIS-REPO-OWNED
    ones (present under `claude_dir`, absent from the repo, previously
    recorded in this repo's manifest) were removed, and which repo-side
    entries were skipped because the destination exists and is not owned
    by this repo (T-2386's `SyncCollision` guard -- never overwritten
    without `--force`)."""

    model_config = {}

    synced: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    collisions: tuple[str, ...] = ()


def _repo_entry_names(kind_dir: Path) -> set[str]:
    """Directory names directly under `kind_dir` (e.g. `agents/*/`), or the
    empty set if `kind_dir` does not exist -- mirrors the old recipe's `for
    d in agents/*/` which (unlike this function) left a literal, non-
    existent `*` glob artifact when the directory was absent; this returns
    a clean empty set instead, never a phantom entry."""
    if not kind_dir.is_dir():
        return set()
    return {p.name for p in kind_dir.iterdir() if p.is_dir()}


def _manifest_path(claude_dir: Path) -> Path:
    """T-2386: the provenance manifest's path for a given `claude_dir` --
    always `<claude_dir>/.frob-sync-manifest.json`, never repo-specific
    (one shared file across every repo that syncs into this `claude_dir`,
    keyed internally by repo identity -- see `_load_manifest`)."""
    return claude_dir / _MANIFEST_FILENAME


def _repo_id(repo_root: Path) -> str:
    """T-2386: this repo's identity key into the shared manifest --
    `repo_root`'s resolved absolute path, stable across repeated runs from
    the same checkout and distinct across different repos/clones (the
    provenance question this manifest answers is "which repo installed
    this", not "which commit" -- a path is the right granularity)."""
    return str(repo_root.resolve())


def _load_manifest(claude_dir: Path) -> dict[str, dict[str, list[str]]]:
    """T-2386: load `<claude_dir>/.frob-sync-manifest.json`, or an empty
    manifest if it does not exist yet or fails to parse (a corrupt/absent
    manifest degrades to "this repo owns nothing recorded yet" -- the safe
    direction, since owning nothing means removal never fires and copy-in
    treats every existing destination as a collision rather than silently
    assuming ownership it cannot prove)."""
    path = _manifest_path(claude_dir)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        _log.warning(
            "sync_skills: manifest %s unreadable (%s) -- treating as empty", path, exc
        )
        return {}
    if not isinstance(data, dict):
        _log.warning(
            "sync_skills: manifest %s is not a JSON object -- treating as empty", path
        )
        return {}
    return data


def _save_manifest(claude_dir: Path, manifest: dict[str, dict[str, list[str]]]) -> None:
    """T-2386: write the manifest back, creating `claude_dir` if needed."""
    claude_dir.mkdir(parents=True, exist_ok=True)
    _manifest_path(claude_dir).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _sync_one_kind(
    repo_dir: Path,
    claude_kind_dir: Path,
    *,
    kind: str,
    owned: set[str],
    other_owned: set[str],
    force: bool,
) -> tuple[SkillsSyncReport, set[str]]:
    """Sync one `<kind>` (agents or skills): copy/update every repo-side
    entry into `claude_kind_dir` UNLESS the destination already exists and
    is neither already `owned` by this repo nor `force`d (a `SyncCollision`
    -- T-2386), then remove any `claude_kind_dir` entry this repo `owned`
    (per the manifest) that no longer has a repo-side counterpart. An
    entry in `other_owned` (another repo's manifest claims it) is always
    treated as a collision on copy-in and is never a removal candidate,
    matching `owned`'s own removal restriction. `claude_kind_dir` is
    always created (even when `repo_dir` has nothing to sync), matching
    the old recipe's unconditional `mkdir -p` at the top. Returns the
    report plus the UPDATED owned-name set (what the caller should record
    back into this repo's manifest entry for `kind`)."""
    claude_kind_dir.mkdir(parents=True, exist_ok=True)
    repo_names = _repo_entry_names(repo_dir)

    synced: list[str] = []
    collisions: list[str] = []
    new_owned: set[str] = set()
    for name in sorted(repo_names):
        src = repo_dir / name
        dst = claude_kind_dir / name
        already_owned = name in owned
        if dst.exists() and not already_owned and not force:
            collisions.append(name)
            _log.warning(
                "sync_skills: collision at %s -- exists and is not owned by "
                "this repo (pass --force to claim it); skipping",
                dst,
            )
            continue
        shutil.copytree(src, dst, dirs_exist_ok=True)
        synced.append(name)
        new_owned.add(name)
        _log.info("sync_skills: synced %s -> %s", src, dst)

    removed: list[str] = []
    for name in sorted(owned - repo_names):
        entry = claude_kind_dir / name
        if entry.is_dir():
            shutil.rmtree(entry)
            removed.append(name)
            _log.info("sync_skills: removed stale (owned) %s", entry)
        # else: already gone (hand-removed since last sync) -- just drop
        # it from this repo's manifest below, nothing to rmtree.

    return (
        SkillsSyncReport(
            synced=tuple(synced), removed=tuple(removed), collisions=tuple(collisions)
        ),
        new_owned,
    )


# frob:ticket T-2241
# frob:ticket T-2386
# frob:doc docs/commands/sync-skills.md#public-api
# frob:tests tests/unit/test_skills_sync.py::TestSyncSkills.test_syncs_new_repo_entries  # noqa: E501
# frob:tests tests/unit/test_skills_sync.py::TestSyncSkills.test_updates_existing_entry_in_place  # noqa: E501
# frob:tests tests/unit/test_skills_sync.py::TestSyncSkills.test_removes_stale_claude_side_entry_this_repo_previously_installed  # noqa: E501
# frob:tests tests/unit/test_skills_sync.py::TestSyncSkills.test_missing_repo_directories_are_a_no_op  # noqa: E501
# frob:tests tests/unit/test_skills_sync.py::TestSyncSkillsProvenance.test_second_repo_does_not_delete_first_repos_entries  # noqa: E501
# frob:tests tests/unit/test_skills_sync.py::TestSyncSkillsProvenance.test_hand_maintained_entry_is_never_deleted_or_overwritten  # noqa: E501
# frob:tests tests/unit/test_skills_sync.py::TestSyncSkillsProvenance.test_same_repo_sync_twice_is_a_no_op_second_run  # noqa: E501
# frob:tests tests/unit/test_skills_sync.py::TestSyncSkillsProvenance.test_force_overwrites_collision_and_claims_ownership  # noqa: E501
def sync_skills(
    repo_root: Path, claude_dir: Path, *, force: bool = False
) -> dict[str, SkillsSyncReport]:
    """Bidirectionally sync `repo_root`'s `agents/`/`skills/` directories
    into `claude_dir`'s `agents/`/`skills/` (T-2241), provenance-aware
    (T-2386): every repo-side `<kind>/<name>/` is copied/updated under
    `claude_dir/<kind>/<name>/` UNLESS the destination exists and is not
    already owned by THIS repo (a `SyncCollision`, skipped and reported
    rather than silently overwritten, unless `force=True`); every
    `claude_dir/<kind>/<name>/` this repo's own manifest previously
    recorded installing, with no repo-side counterpart left, is removed --
    an entry another repo installed, or a hand-maintained one no manifest
    ever claimed, is NEVER removed regardless of the current repo-side
    listing. Returns one `SkillsSyncReport` per kind, keyed by `"agents"`/
    `"skills"`. A repo with neither directory present is a clean no-op
    (both `claude_dir` subdirectories are still created, matching the old
    recipe's unconditional `mkdir -p`, but nothing is synced or removed).
    The provenance manifest (`<claude_dir>/.frob-sync-manifest.json`) is
    updated in the same call to reflect what this repo owns afterward."""
    manifest = _load_manifest(claude_dir)
    repo_id = _repo_id(repo_root)
    repo_entry = manifest.get(repo_id, {})

    other_owned: dict[str, set[str]] = {kind: set() for kind in _SYNCED_KINDS}
    for other_id, other_entry in manifest.items():
        if other_id == repo_id:
            continue
        for kind in _SYNCED_KINDS:
            other_owned[kind].update(other_entry.get(kind, []))

    reports: dict[str, SkillsSyncReport] = {}
    new_repo_entry: dict[str, list[str]] = {}
    for kind in _SYNCED_KINDS:
        owned = set(repo_entry.get(kind, []))
        report, new_owned = _sync_one_kind(
            repo_root / kind,
            claude_dir / kind,
            kind=kind,
            owned=owned,
            other_owned=other_owned[kind],
            force=force,
        )
        reports[kind] = report
        # frob:waive PERF004 reason="loop bound is _SYNCED_KINDS, a fixed 2-element constant tuple, not repo-scale data; sort is required for deterministic manifest ordering, not a hot-path re-sort"  # noqa: E501
        new_repo_entry[kind] = sorted(new_owned)

    manifest[repo_id] = new_repo_entry
    _save_manifest(claude_dir, manifest)
    return reports


def _default_claude_dir() -> Path:
    """`~/.claude`, resolved the same way `Makefile`'s `CLAUDE_DIR :=
    $(HOME)/.claude` did."""
    return Path.home() / ".claude"


# frob:ticket T-2241
# frob:doc docs/commands/sync-skills.md#public-api
# frob:tests tests/unit/test_skills_sync.py::TestRun.test_run_reports_synced_and_removed_counts  # noqa: E501
def run(argv: list[str]) -> None:
    """`frob sync-skills [path] [--claude-dir DIR] [--force]` (T-2241,
    T-2386): the CLI entry point `frob.__main__._dispatch` calls directly,
    mirroring `bind`/`agent`/`worktree`'s own special case (T-0355/T-0574/
    T-0836) -- this subcommand needs no `AppConfig` field of its own (just
    a repo root and a target directory), so it is dispatched straight to
    this function from raw `argv` rather than added to `frob.app.app`'s
    uniform `AppConfig`-based runner registry, the same reasoning those
    three commands' own module docstrings already give. `--claude-dir`
    exists for a caller (a test, or a maintainer syncing into a non-
    default location) that wants to point somewhere other than
    `~/.claude` -- the sync logic itself never assumes it. `--force`
    (T-2386) overrides a `SyncCollision` (a destination another repo or a
    hand-maintained `~/.claude` already owns): without it, a collision is
    reported and skipped, never silently overwritten."""
    import argparse

    parser = argparse.ArgumentParser(prog="frob sync-skills")
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--claude-dir", dest="claude_dir", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(args.path).resolve()
    claude_dir = (
        Path(args.claude_dir).resolve() if args.claude_dir else _default_claude_dir()
    )

    reports = sync_skills(repo_root, claude_dir, force=args.force)
    total_synced = sum(len(r.synced) for r in reports.values())
    total_removed = sum(len(r.removed) for r in reports.values())
    total_collisions = sum(len(r.collisions) for r in reports.values())
    renderer = Renderer.for_stream(sys.stdout)
    for kind, report in reports.items():
        for name in report.synced:
            renderer.line(f"  synced {kind[:-1]}: {name}")
        for name in report.removed:
            renderer.line(f"  removed stale {kind[:-1]}: {name}")
        for name in report.collisions:
            renderer.line(
                f"  SKIPPED {kind[:-1]}: {name} (exists, not owned by this repo -- "
                "pass --force to overwrite)"
            )
    renderer.line(
        f"sync-skills: {total_synced} synced, {total_removed} removed, "
        f"{total_collisions} collision(s) skipped"
    )
    sys.exit(0)


__all__ = ["SkillsSyncReport", "run", "sync_skills"]

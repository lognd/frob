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
`frob.app.app`'s uniform `AppConfig`-based runner registry."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from pydantic import BaseModel

from frob.logging import get_logger

_log = get_logger(__name__)

#: The two directory kinds this recipe syncs -- `agents/<name>/` ->
#: `~/.claude/agents/<name>/`, `skills/<name>/` -> `~/.claude/skills/<name>/`,
#: identical treatment for both (mirrors the old recipe's two near-identical
#: `for` loop pairs).
_SYNCED_KINDS = ("agents", "skills")


# frob:ticket T-2241
# frob:doc docs/commands/sync-skills.md
# frob:tests tests/unit/test_skills_sync.py::TestSyncSkills.test_syncs_new_repo_entries  # noqa: E501
class SkillsSyncReport(BaseModel):
    """One `sync_skills` call's effect: which `<kind>/<name>` entries were
    created-or-updated under `claude_dir`, and which stale ones (present
    under `claude_dir`, absent from the repo) were removed."""

    model_config = {}

    synced: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()


def _repo_entry_names(kind_dir: Path) -> set[str]:
    """Directory names directly under `kind_dir` (e.g. `agents/*/`), or the
    empty set if `kind_dir` does not exist -- mirrors the old recipe's `for
    d in agents/*/` which (unlike this function) left a literal, non-
    existent `*` glob artifact when the directory was absent; this returns
    a clean empty set instead, never a phantom entry."""
    if not kind_dir.is_dir():
        return set()
    return {p.name for p in kind_dir.iterdir() if p.is_dir()}


def _sync_one_kind(repo_dir: Path, claude_kind_dir: Path) -> SkillsSyncReport:
    """Sync one `<kind>` (agents or skills): copy/update every repo-side
    entry into `claude_kind_dir`, then remove any `claude_kind_dir` entry
    with no repo-side counterpart. `claude_kind_dir` is always created
    (even when `repo_dir` has nothing to sync), matching the old recipe's
    unconditional `mkdir -p` at the top."""
    claude_kind_dir.mkdir(parents=True, exist_ok=True)
    repo_names = _repo_entry_names(repo_dir)

    synced: list[str] = []
    for name in sorted(repo_names):
        src = repo_dir / name
        dst = claude_kind_dir / name
        shutil.copytree(src, dst, dirs_exist_ok=True)
        synced.append(name)
        _log.info("sync_skills: synced %s -> %s", src, dst)

    removed: list[str] = []
    if claude_kind_dir.is_dir():
        for entry in sorted(claude_kind_dir.iterdir()):
            if entry.is_dir() and entry.name not in repo_names:
                shutil.rmtree(entry)
                removed.append(entry.name)
                _log.info("sync_skills: removed stale %s", entry)

    return SkillsSyncReport(synced=tuple(synced), removed=tuple(removed))


# frob:ticket T-2241
# frob:doc docs/commands/sync-skills.md
# frob:tests tests/unit/test_skills_sync.py::TestSyncSkills.test_syncs_new_repo_entries  # noqa: E501
# frob:tests tests/unit/test_skills_sync.py::TestSyncSkills.test_updates_existing_entry_in_place  # noqa: E501
# frob:tests tests/unit/test_skills_sync.py::TestSyncSkills.test_removes_stale_claude_side_entry  # noqa: E501
# frob:tests tests/unit/test_skills_sync.py::TestSyncSkills.test_missing_repo_directories_are_a_no_op  # noqa: E501
def sync_skills(repo_root: Path, claude_dir: Path) -> dict[str, SkillsSyncReport]:
    """Bidirectionally sync `repo_root`'s `agents/`/`skills/` directories
    into `claude_dir`'s `agents/`/`skills/` (T-2241): every repo-side
    `<kind>/<name>/` is copied/updated under `claude_dir/<kind>/<name>/`,
    and every `claude_dir/<kind>/<name>/` with no repo-side counterpart is
    removed. Returns one `SkillsSyncReport` per kind, keyed by `"agents"`/
    `"skills"`. A repo with neither directory present is a clean no-op
    (both `claude_dir` subdirectories are still created, matching the old
    recipe's unconditional `mkdir -p`, but nothing is synced or removed)."""
    return {
        kind: _sync_one_kind(repo_root / kind, claude_dir / kind)
        for kind in _SYNCED_KINDS
    }


def _default_claude_dir() -> Path:
    """`~/.claude`, resolved the same way `Makefile`'s `CLAUDE_DIR :=
    $(HOME)/.claude` did."""
    return Path.home() / ".claude"


# frob:ticket T-2241
# frob:doc docs/commands/sync-skills.md
# frob:tests tests/unit/test_skills_sync.py::TestRun.test_run_reports_synced_and_removed_counts  # noqa: E501
def run(argv: list[str]) -> None:
    """`frob sync-skills [path] [--claude-dir DIR]` (T-2241): the CLI entry
    point `frob.__main__._dispatch` calls directly, mirroring `bind`/
    `agent`/`worktree`'s own special case (T-0355/T-0574/T-0836) -- this
    subcommand needs no `AppConfig` field of its own (just a repo root and
    a target directory), so it is dispatched straight to this function
    from raw `argv` rather than added to `frob.app.app`'s uniform
    `AppConfig`-based runner registry, the same reasoning those three
    commands' own module docstrings already give. `--claude-dir` exists
    for a caller (a test, or a maintainer syncing into a non-default
    location) that wants to point somewhere other than `~/.claude` --
    the sync logic itself never assumes it."""
    import argparse

    parser = argparse.ArgumentParser(prog="frob sync-skills")
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--claude-dir", dest="claude_dir", default=None)
    args = parser.parse_args(argv)

    repo_root = Path(args.path).resolve()
    claude_dir = (
        Path(args.claude_dir).resolve() if args.claude_dir else _default_claude_dir()
    )

    reports = sync_skills(repo_root, claude_dir)
    total_synced = sum(len(r.synced) for r in reports.values())
    total_removed = sum(len(r.removed) for r in reports.values())
    for kind, report in reports.items():
        for name in report.synced:
            print(f"  synced {kind[:-1]}: {name}")
        for name in report.removed:
            print(f"  removed stale {kind[:-1]}: {name}")
    print(f"sync-skills: {total_synced} synced, {total_removed} removed")
    sys.exit(0)


__all__ = ["SkillsSyncReport", "run", "sync_skills"]

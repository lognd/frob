"""Sync git-tracked Claude config from this repo out to `~/.claude/`.

THE REPO IS CANONICAL. Hooks and the agent playbook are versioned, reviewed,
and diffable here; `~/.claude/` holds materialized COPIES. That direction is
the whole point: a hook that only exists in one developer's home directory
is an undocumented behaviour change that no review ever saw, and an agent
playbook that drifts between the repo and the global refs means two agents
read different rules and neither is wrong.

    python3 .claude/hooks/sync-claude-config.py           # write the copies
    python3 .claude/hooks/sync-claude-config.py --check   # report drift, exit 1

`--check` is the gate-shaped form: it never writes, and exits non-zero when
any managed file differs. Wire it into CI or a SessionStart hook so drift is
LOUD rather than discovered the next time a hook mysteriously does not fire.

Only files listed in `_MANAGED` are touched. A destination outside that list
is never read, written, or deleted -- `~/.claude/` holds plenty that this
repo has no business owning, and a sync that cleaned "unmanaged" files would
be a foot-gun aimed at the user's own configuration.

NOTE ON DIRECTION: this never syncs global -> repo. If you edited the copy in
`~/.claude/` by hand, `--check` will report it and a sync will overwrite it.
That is intended. Edit the tracked file.
"""

import argparse
import shutil
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_HOME_CLAUDE = Path.home() / ".claude"

#: (repo-relative source, home-relative destination). Every managed file,
#: enumerated explicitly -- a glob here would silently start managing a file
#: nobody decided to manage.
_MANAGED: list[tuple[str, str]] = [
    (".claude/hooks/_shellscan.py", "hooks/_shellscan.py"),
    (".claude/hooks/frob-suggest.py", "hooks/frob-suggest.py"),
    (".claude/hooks/frob-timeout-guard.py", "hooks/frob-timeout-guard.py"),
    (".claude/hooks/diagnosis-nudge.py", "hooks/diagnosis-nudge.py"),
    (".claude/hooks/dispatch-telemetry.py", "hooks/dispatch-telemetry.py"),
    ("docs/guides/agent-playbook.md", "refs/agent-playbook.md"),
]

_BANNER = (
    "# GENERATED COPY -- DO NOT EDIT.\n"
    "# Canonical source: {source} in the frob repo.\n"
    "# Edit there, then: python3 .claude/hooks/sync-claude-config.py\n"
)


def _banner_for(source: str, dest: Path) -> str:
    """The do-not-edit banner, commented for the destination's file type.

    A generated file that does not SAY it is generated is how a careful
    person ends up making a careful edit that is silently discarded on the
    next sync."""
    if dest.suffix == ".md":
        return (
            f"<!-- GENERATED COPY -- DO NOT EDIT. Canonical source: {source} "
            "in the frob repo. Edit there, then run "
            "`python3 .claude/hooks/sync-claude-config.py`. -->\n\n"
        )
    return _BANNER.format(source=source)


def _rendered(source_rel: str, dest: Path) -> str | None:
    """The exact content the destination should hold, or `None` if the
    source is missing (reported, never silently skipped)."""
    source = _REPO / source_rel
    if not source.exists():
        return None
    return _banner_for(source_rel, dest) + source.read_text(encoding="utf-8")


def _plan() -> tuple[list[tuple[str, Path, str]], list[str]]:
    """`(actions, missing)` -- what the sync would do, decided without doing
    any of it.

    Split from `main` so the DECISION is separable from the WRITING and the
    REPORTING (ARCH103): the same plan drives both `--check` and a real
    sync, so the two can never disagree about what counts as drift."""
    actions: list[tuple[str, Path, str]] = []
    missing: list[str] = []
    for source_rel, dest_rel in _MANAGED:
        dest = _HOME_CLAUDE / dest_rel
        want = _rendered(source_rel, dest)
        if want is None:
            missing.append(source_rel)
            continue
        have = dest.read_text(encoding="utf-8") if dest.exists() else None
        if have == want:
            continue
        state = "absent" if have is None else "differs"
        actions.append((f"{dest_rel} ({state} vs {source_rel})", dest, want))
    return actions, missing


def _materialize(dest: Path, want: str) -> None:
    """Write `want` to `dest` atomically.

    Write-temp-then-replace, because a half-written hook does not fail
    once -- it fails to parse on every subsequent tool call."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    tmp.write_text(want, encoding="utf-8")
    shutil.move(str(tmp), str(dest))


def _report_check(actions: list[tuple[str, Path, str]], missing: list[str]) -> int:
    """`--check`'s reporting half: name every drifted path, never just a
    count. An error that does not name its own cause has cost this repo
    three separate fleet stalls."""
    for entry, _dest, _want in actions:
        print(f"DRIFT: {entry}", file=sys.stderr)
    if actions or missing:
        print(
            f"sync-claude-config --check: {len(actions)} drifted, "
            f"{len(missing)} missing -- run "
            "`python3 .claude/hooks/sync-claude-config.py` to reconcile",
            file=sys.stderr,
        )
        return 1
    print(f"sync-claude-config --check: {len(_MANAGED)} file(s) in sync")
    return 0


# frob:doc docs/guides/claude-hooks.md#sync-claude-configpy
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift without writing; exit 1 if any managed file differs",
    )
    args = parser.parse_args()

    actions, missing = _plan()
    for source_rel in missing:
        print(f"MISSING canonical source: {source_rel}", file=sys.stderr)
    if args.check:
        return _report_check(actions, missing)

    for entry, dest, want in actions:
        _materialize(dest, want)
        print(f"synced ~/.claude/{entry.split(' (')[0]}")
    if not actions:
        print(f"sync-claude-config: {len(_MANAGED)} file(s) already in sync")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())

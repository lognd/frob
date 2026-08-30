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

Only files listed in `MANAGED` are touched. A destination outside that list
is never read, written, or deleted -- `~/.claude/` holds plenty that this
repo has no business owning, and a sync that cleaned "unmanaged" files would
be a foot-gun aimed at the user's own configuration.

NOTE ON DIRECTION: this never syncs global -> repo. If you edited the copy in
`~/.claude/` by hand, `--check` will report it and a sync will overwrite it.
That is intended. Edit the tracked file.

T-3408: STALE-SOURCE GUARD. `~/.claude/` is materialized from WHICHEVER
worktree last ran this script -- every worktree carries its own copy of
`MANAGED`'s source files, and the destination is shared by every process on
the machine (every agent, the coordinator, any other session). A many-
writers/one-destination operation with no coordination means a worktree
that branched before a sibling's hook fix landed on `main` can run this
script and silently REVERT that fix globally, with no diff, no warning, no
record -- measured live 2026-08-29 (series EQ's sync clobbered series ER's
in-flight `frob-suggest.py` fix; the only reason it was caught was an agent
diffing by chance and restoring it by hand).

CHECKED FIRST, before adding anything (T-3408's own explicit requirement):
this script had NO staleness or diff guard at all before this ticket --
`plan()` compared source content to the CURRENT destination only, with no
notion of "behind" vs "ahead". Confirmed by reading the pre-T-3408 source,
not assumed.

POLICY CHOSEN: (b) from the ticket's own menu -- refuse to sync a specific
managed file when this worktree's own copy of it is BEHIND `main` (i.e.
unchanged by this worktree since it branched, while `main` has since moved
the file), via `stale_managed_sources`/`_is_source_stale_vs_main` below.
NOT (a) (refuse from any worktree, main only): that would cost every agent
the ability to test a hook change in place before landing it, which is a
real and common workflow this repo relies on. NOT bare (c) (diff-and-
confirm against the destination, with an override flag): the destination
can ALSO be behind main (e.g. nobody has synced in a while) with no fix
"lost" at all, in which case a source-vs-destination diff would demand an
override flag for a perfectly safe forward sync -- checking against `main`
directly (not just the destination) is the more precise question, and it
is what actually happened in the measured incident (the worktree's source
was behind `main`, not merely behind whatever the destination happened to
hold). (c)'s OWN escape hatch is folded in regardless: `--allow-stale`
overrides the refusal explicitly, per file, for the rare case a worktree
truly needs to push its own (reviewed) version through anyway -- refusing
silently with no way out would just invite `--allow-stale`-shaped hand
edits to this script itself. A worktree's OWN edit to a managed file is
NEVER treated as stale, no matter how far `main` has moved on that same
file -- that is ordinary in-place testing (MUST-STAY-QUIET), not the
failure this guard exists for.

Deliberately NOT a lock (the ticket's own explicit "do not"): serializing
two writers still lets the stale one win once it is its turn -- the
problem here was never concurrency, it was that nothing ever asked
whether the writer's OWN copy was current before writing.

T-1808: this script stays the CANONICAL, dependency-free implementation on
purpose -- stdlib only, no `frob` import -- because the SessionStart hook in
`.claude/settings.json` invokes it with a bare `python3` before any `frob`
venv is necessarily on `PYTHONPATH`. `frob claude sync` (`frob.app.
claude_runner`) is a thin CLI adapter that loads THIS file by path and calls
`plan()`/`main()` directly, so there is exactly one implementation of the
sync/drift logic, not two that can desync (NO DUPLICATION). `MANAGED` and
`plan()` are public (no leading underscore) specifically so that adapter --
and `frob check`'s own drift gate (T-1809) -- can import them without
reaching into "private" script internals.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_HOME_CLAUDE = Path.home() / ".claude"

#: How long a single `git` probe (`_git_show`/`_git_merge_base`, T-3408) is
#: allowed to run before this script gives up on it and treats that ONE
#: reading as unknown -- best-effort, never a hang: a stuck git process must
#: never block a sync (or a `--check`) indefinitely.
_GIT_PROBE_TIMEOUT_S = 10

#: (repo-relative source, home-relative destination). Every managed file,
#: enumerated explicitly -- a glob here would silently start managing a file
#: nobody decided to manage. Public (T-1808): `frob.app.claude_runner` and
#: `frob`'s claude-config drift gate (T-1809) both read this same list, so
#: "what is managed" can never desync between the standalone script and
#: frob's own CLI/gate.
# frob:doc docs/guides/claude-hooks.md#sync-claude-configpy
MANAGED: list[tuple[str, str]] = [
    (".claude/hooks/_shellscan.py", "hooks/_shellscan.py"),
    (".claude/hooks/frob-suggest.py", "hooks/frob-suggest.py"),
    (".claude/hooks/frob-timeout-guard.py", "hooks/frob-timeout-guard.py"),
    (".claude/hooks/root-write-guard.py", "hooks/root-write-guard.py"),
    (".claude/hooks/_agent_context.py", "hooks/_agent_context.py"),
    (
        ".claude/hooks/root-cleanliness-detector.py",
        "hooks/root-cleanliness-detector.py",
    ),
    (".claude/hooks/diagnosis-nudge.py", "hooks/diagnosis-nudge.py"),
    (".claude/hooks/dispatch-telemetry.py", "hooks/dispatch-telemetry.py"),
    ("docs/guides/agent-playbook.md", "refs/agent-playbook.md"),
]

# frob:ticket T-3408
def _git_show(ref: str, path: str) -> str | None:
    """`git show <ref>:<path>`'s stdout, or `None` on ANY failure (not a
    git repo, `ref` unresolvable, `path` absent at `ref`, `git` missing
    from `PATH`, or the probe exceeding `_GIT_PROBE_TIMEOUT_S`) -- a
    single best-effort read, never raises. `None` is read by every caller
    here as 'cannot determine', never as 'the file does not exist' or any
    other conclusion."""
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(_REPO), "show", f"{ref}:{path}"],
            capture_output=True,
            text=True,
            timeout=_GIT_PROBE_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


# frob:ticket T-3408
# frob:waive ARCH103 reason="single atomic unit: run one subprocess and classify its \
# failure modes (spawn error/timeout/nonzero exit/empty output) into the one \
# None-vs-sha contract callers rely on -- same shape and same waiver text as this \
# repo's own src/frob/app/_version_guard.py precedent for an identical git-subprocess- \
# to-Optional[str] read; splitting the subprocess call from its own failure \
# classification would separate an operation from the branches that interpret it, not \
# reduce real complexity"
def _git_merge_base(ref_a: str, ref_b: str) -> str | None:
    """`git merge-base <ref_a> <ref_b>`'s stdout (a commit sha), stripped,
    or `None` on any failure -- same best-effort contract as `_git_show`."""
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(_REPO), "merge-base", ref_a, ref_b],
            capture_output=True,
            text=True,
            timeout=_GIT_PROBE_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha or None


# frob:ticket T-3408
# frob:tests tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestIsSourceStaleVsMain.test_unmodified_source_behind_main_is_stale  # noqa: E501
# frob:tests tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestIsSourceStaleVsMain.test_worktree_own_edit_is_never_stale_even_if_main_also_moved  # noqa: E501
# frob:tests tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestIsSourceStaleVsMain.test_source_matches_main_is_not_stale  # noqa: E501
# frob:tests tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestIsSourceStaleVsMain.test_unknown_git_readings_fail_open  # noqa: E501
def _is_source_stale_vs_main(
    source_text: str, main_text: str | None, merge_base_text: str | None
) -> bool:
    """T-3408's policy-(b) decision, as a pure function (no git, no I/O) so
    it is directly unit-testable against synthetic content: `True` exactly
    when THIS worktree's copy of a managed source file is BEHIND `main` --
    unmodified by the worktree since it branched (`source_text ==
    merge_base_text`) while `main` has since changed the file (`main_text
    != merge_base_text`). A worktree that has itself edited the file since
    branching (`source_text != merge_base_text`) is NEVER stale by this
    definition, no matter how far `main` has moved on the same file in the
    meantime -- that is ordinary in-place hook testing, the exact workflow
    policy (a) (main-only) would have cost, and this ticket's own MUST-
    STAY-QUIET fixture. Any unknown git reading (`None` for either `main_
    text` or `merge_base_text`) returns `False` -- fail OPEN, matching
    every other best-effort git read in this module; a guard that cannot
    read git must never treat that as proof of staleness."""
    if main_text is None or merge_base_text is None:
        return False
    if source_text != merge_base_text:
        return False
    return main_text != merge_base_text


# frob:doc docs/guides/claude-hooks.md#sync-claude-configpy
# frob:ticket T-3408
# frob:tests tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestStaleManagedSourcesAndWriteRefusal.test_stale_file_skipped_forward_file_synced  # noqa: E501
# frob:tests tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestStaleManagedSourcesAndWriteRefusal.test_allow_stale_overrides_the_refusal  # noqa: E501
def stale_managed_sources(
    managed: list[tuple[str, str]] | None = None,
) -> list[str]:
    """Repo-relative source paths, from `managed` (default: `MANAGED`),
    that are BEHIND `main` per `_is_source_stale_vs_main` -- the set
    `main`'s write path (T-3408) refuses to sync unless `--allow-stale`
    is given. One shared `git merge-base main HEAD` covers every managed
    file (they all live in the same worktree, branched at the same
    point); each file's own `main`/merge-base content is then read
    individually so one file's staleness never depends on another's.
    Best-effort throughout (`_git_show`/`_git_merge_base`'s own
    contracts): a source file missing from disk is skipped (not this
    function's concern -- `plan()`'s own `missing` already covers that),
    and any git failure degrades that ONE file's reading to 'unknown',
    never 'stale'. `managed` is parameterized (not read from the module
    global directly) purely for test isolation -- production callers
    always pass `None`."""
    if managed is None:
        managed = MANAGED
    merge_base = _git_merge_base("main", "HEAD")
    stale: list[str] = []
    for source_rel, _dest_rel in managed:
        source_path = _REPO / source_rel
        if not source_path.exists():
            continue
        source_text = source_path.read_text(encoding="utf-8")
        main_text = _git_show("main", source_rel)
        merge_base_text = _git_show(merge_base, source_rel) if merge_base else None
        if _is_source_stale_vs_main(source_text, main_text, merge_base_text):
            stale.append(source_rel)
    return stale


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


# frob:doc docs/guides/claude-hooks.md#sync-claude-configpy
def plan() -> tuple[list[tuple[str, Path, str]], list[str]]:
    """`(actions, missing)` -- what the sync would do, decided without doing
    any of it.

    Split from `main` so the DECISION is separable from the WRITING and the
    REPORTING (ARCH103): the same plan drives both `--check` and a real
    sync, so the two can never disagree about what counts as drift. Public
    (T-1808): `frob.app.claude_runner`'s drift check calls this directly
    rather than re-deriving it."""
    actions: list[tuple[str, Path, str]] = []
    missing: list[str] = []
    for source_rel, dest_rel in MANAGED:
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
    print(f"sync-claude-config --check: {len(MANAGED)} file(s) in sync")
    return 0


# frob:doc docs/guides/claude-hooks.md#sync-claude-configpy
# frob:waive ARCH103 reason="the CLI dispatch entrypoint's one job IS parsing argv, \
# running the plan, and reporting/writing the outcome -- T-3408 added the per-file \
# stale-skip branch to that same single report-and-act loop rather than a second pass \
# over actions, which would be two loops over the same list instead of fewer \
# decisions; same posture src/frob/app/app.py's own ARCH103 waiver already takes for \
# an identical CLI-entrypoint shape"
def main(argv: list[str] | None = None) -> int:
    """Entry point for both the bare `python3 sync-claude-config.py [--check]`
    CLI and `frob claude sync [--check]` (T-1808, `frob.app.claude_runner`,
    which calls this with an explicit `argv` list instead of the ambient
    `sys.argv` a bare CLI invocation reads).

    T-3408: the WRITE path (not `--check`, which never writes and already
    reports its own drift) refuses to sync a managed file whose source is
    behind `main` per `stale_managed_sources` -- see this module's own
    docstring ("STALE-SOURCE GUARD") for the measured incident and the
    reasoning behind choosing this policy over the alternatives. `--allow-
    stale` overrides the refusal explicitly; other, non-stale files in the
    same run are unaffected either way (MUST-STAY-QUIET) -- staleness is
    decided and refused per file, never for the whole batch."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift without writing; exit 1 if any managed file differs",
    )
    parser.add_argument(
        "--allow-stale",
        action="store_true",
        help=(
            "T-3408: sync a managed file even when this worktree's own "
            "source is behind main for it (the staleness guard's own "
            "explicit override -- see the module docstring)"
        ),
    )
    args = parser.parse_args(argv)

    actions, missing = plan()
    for source_rel in missing:
        print(f"MISSING canonical source: {source_rel}", file=sys.stderr)
    if args.check:
        return _report_check(actions, missing)

    stale = set() if args.allow_stale else set(stale_managed_sources())
    dest_to_source = {dest_rel: source_rel for source_rel, dest_rel in MANAGED}
    any_stale_skipped = False
    for entry, dest, want in actions:
        dest_rel = str(dest.relative_to(_HOME_CLAUDE))
        source_rel = dest_to_source.get(dest_rel)
        if source_rel is not None and source_rel in stale:
            any_stale_skipped = True
            print(
                f"STALE, SKIPPED: {entry} -- this worktree's {source_rel} "
                "is behind main for this file (T-3408); land/merge main's "
                "own change into this worktree first, or pass "
                "--allow-stale to force this specific file through",
                file=sys.stderr,
            )
            continue
        _materialize(dest, want)
        print(f"synced ~/.claude/{entry.split(' (')[0]}")
    if not actions:
        print(f"sync-claude-config: {len(MANAGED)} file(s) already in sync")
    return 1 if (missing or any_stale_skipped) else 0


if __name__ == "__main__":
    sys.exit(main())

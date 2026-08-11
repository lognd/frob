"""T-1720: `frob ticket land`'s post-land auto-sync step
(`_auto_sync_worktree_onto_main`) -- closes the repeated by-hand `git
merge main` every multi-ticket series worktree agent performed after
each successful land in one measured session (six for six occurrences).
Real git fixture repos, matching `tests/test_ticket_work_and_land_finish.
py`'s own style for this module family.

T-2173: this file (and the function under test) used `git rebase` from
T-1720 through most of one session, until that rebase failed identically
on four separate real lands in one day, always conflicting on a ledger
file, always cleared by a by-hand `git merge main` instead.
`TestAutoSyncWorktreeOntoMain.test_squash_then_rebase_conflicts_but_merge_
does_not` is the acceptance test for that incident -- it reproduces the
classic "rebase a branch after its own content was already squash-merged"
conflict class directly (confirmed FAILING against a `git rebase`-based
implementation, passing against `git merge`), independent of the
`tickets.md`/`tickets-archive.md` merge driver, which a separate direct
test (not in this file -- see this ticket's Done report) already ruled
out as the actual mechanism."""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.app.ticket_runner._land_cmd import _auto_sync_worktree_onto_main


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _is_ancestor(worktree: Path, ancestor_ref: str, descendant_ref: str) -> bool:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(worktree),
            "merge-base",
            "--is-ancestor",
            ancestor_ref,
            descendant_ref,
        ],
        cwd=str(worktree),
    )
    return result.returncode == 0


def _rev_parse(worktree: Path, rev: str = "HEAD") -> str:
    return subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", rev],
        capture_output=True,
        text=True,
    ).stdout.strip()


def _status(worktree: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(worktree), "status", "--porcelain"],
        capture_output=True,
        text=True,
    ).stdout


class TestAutoSyncWorktreeOntoMain:
    def _seed(self, tmp_path: Path) -> tuple[Path, Path]:
        repo = tmp_path / "main"
        _git_init(repo)
        (repo / "src").mkdir()
        (repo / "src" / "feature.py").write_text("# landed feature\n")
        _commit_all(repo, "init")

        wt = tmp_path / "wt"
        _run(["git", "worktree", "add", "-b", "series-a", str(wt)], repo)
        return repo, wt

    def test_merges_the_worktree_onto_the_new_main_tip(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain.test_merges_the_worktree_onto_the_new_main_tip  # noqa: E501
        repo, wt = self._seed(tmp_path)

        # The worktree's own branch commits something (standing in for
        # the ticket this land just squash-applied).
        (wt / "src" / "own.py").write_text("# this branch's own work\n")
        _commit_all(wt, "own work")

        # main independently advances (the squash-apply this land just
        # produced, or any other already-landed sibling).
        (repo / "src" / "other.py").write_text("# unrelated, already landed\n")
        _commit_all(repo, "unrelated main-side land")

        pre_sync_own_tip = _rev_parse(wt)

        _auto_sync_worktree_onto_main(repo, wt, "T-1720")

        # The worktree's branch now descends from main's current tip --
        # exactly what the manual `git merge main` this ticket automates
        # used to produce.
        assert _is_ancestor(wt, "main", "HEAD")
        # The worktree's OWN content survives the merge.
        assert (wt / "src" / "own.py").read_text() == "# this branch's own work\n"
        assert (wt / "src" / "other.py").read_text() == "# unrelated, already landed\n"
        assert _rev_parse(wt) != pre_sync_own_tip  # a merge commit was made

    def test_squash_then_rebase_conflicts_but_merge_does_not(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain.test_squash_then_rebase_conflicts_but_merge_does_not  # noqa: E501
        """T-2173's own acceptance test: a land whose worktree branch
        diverged on ledger-shaped files (several separate commits walking
        one file through a state sequence, mirroring `frob ticket
        scope`/`start`/`evidence`/`done-report`'s own auto-commits) must
        leave that worktree current with main afterwards -- FAILS against
        a `git rebase`-based implementation of this function (conflicts on
        the first replayed commit even though final content is identical
        to main's post-squash tip), passes against `git merge`."""
        repo = tmp_path / "main"
        _git_init(repo)
        (repo / "tickets" / "T-0001").mkdir(parents=True)
        (repo / "tickets" / "T-0001" / "ticket.md").write_text("state: queued\n")
        _commit_all(repo, "init")

        wt = tmp_path / "wt"
        _run(["git", "worktree", "add", "-b", "t-0001", str(wt)], repo)

        # The worktree's branch walks the SAME file through several
        # separate commits -- exactly the shape `frob ticket
        # scope`/`start`/`evidence`/`done-report` each auto-commit.
        ticket_path = wt / "tickets" / "T-0001" / "ticket.md"
        ticket_path.write_text("state: planned\n")
        _commit_all(wt, "plan")
        ticket_path.write_text("state: in-progress\n")
        _commit_all(wt, "start")
        ticket_path.write_text("state: in-progress\nevidence: [test_x]\n")
        _commit_all(wt, "evidence")
        ticket_path.write_text("state: done\nevidence: [test_x]\n")
        _commit_all(wt, "close")

        # main receives the SAME final content as ONE squash-applied
        # commit -- exactly what `frob ticket land` does.
        (repo / "tickets" / "T-0001" / "ticket.md").write_text(
            "state: done\nevidence: [test_x]\n"
        )
        _commit_all(repo, "land: squash-applied T-0001")

        _auto_sync_worktree_onto_main(repo, wt, "T-0001")

        # The real acceptance property: the worktree is current with main
        # afterwards -- not left behind, not mid-conflict.
        assert _is_ancestor(wt, "main", "HEAD")
        assert ticket_path.read_text() == "state: done\nevidence: [test_x]\n"
        assert _status(wt).strip() == ""
        assert not (wt / ".git" / "rebase-merge").exists()
        assert not (wt / ".git" / "rebase-apply").exists()
        assert not (wt / ".git" / "MERGE_HEAD").exists()

    def test_a_real_conflict_aborts_cleanly_and_does_not_fail_the_land(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain.test_a_real_conflict_aborts_cleanly_and_does_not_fail_the_land  # noqa: E501
        repo, wt = self._seed(tmp_path)

        # Both sides edit the SAME line of the SAME file differently --
        # a genuine, unresolvable conflict.
        (wt / "src" / "feature.py").write_text("# worktree's own conflicting edit\n")
        _commit_all(wt, "worktree-side conflicting edit")

        (repo / "src" / "feature.py").write_text("# main's own conflicting edit\n")
        _commit_all(repo, "main-side conflicting edit")

        pre_attempt_tip = _rev_parse(wt)

        # Must not raise -- best-effort, never fails the caller.
        _auto_sync_worktree_onto_main(repo, wt, "T-1720")

        # The worktree is left exactly as it was: not mid-merge, tip
        # unchanged, clean working tree.
        assert _status(wt).strip() == ""
        assert not (wt / ".git" / "MERGE_HEAD").exists()
        assert _rev_parse(wt) == pre_attempt_tip

    def test_dirty_worktree_is_skipped_rather_than_merged_into(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain.test_dirty_worktree_is_skipped_rather_than_merged_into  # noqa: E501
        """T-2173 safety property: a worktree with UNCOMMITTED changes is
        never merged into -- an agent's own in-progress edit must survive
        untouched, even when main has genuinely diverged in a way that
        would otherwise auto-sync cleanly."""
        repo, wt = self._seed(tmp_path)

        (repo / "src" / "other.py").write_text("# unrelated, already landed\n")
        _commit_all(repo, "unrelated main-side land")

        # An agent's own in-progress, UNCOMMITTED edit.
        (wt / "src" / "feature.py").write_text("# mid-diagnosis, not committed\n")

        pre_attempt_tip = _rev_parse(wt)

        _auto_sync_worktree_onto_main(repo, wt, "T-1720")

        # Untouched: no merge attempted, the uncommitted edit survives
        # exactly as written, tip unchanged.
        assert _rev_parse(wt) == pre_attempt_tip
        assert (
            wt / "src" / "feature.py"
        ).read_text() == "# mid-diagnosis, not committed\n"
        assert not (wt / ".git" / "MERGE_HEAD").exists()

"""T-1720: `frob ticket land`'s auto-rebase step
(`_auto_rebase_worktree_onto_main`) -- closes the repeated by-hand `git
rebase main` every multi-ticket series worktree agent performed after
each successful land in one measured session (six for six occurrences).
Real git fixture repos, matching `tests/test_ticket_work_and_land_finish.
py`'s own style for this module family."""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.app.ticket_runner._land_cmd import _auto_rebase_worktree_onto_main


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


class TestAutoRebaseWorktreeOntoMain:
    def _seed(self, tmp_path: Path) -> tuple[Path, Path]:
        repo = tmp_path / "main"
        _git_init(repo)
        (repo / "src").mkdir()
        (repo / "src" / "feature.py").write_text("# landed feature\n")
        _commit_all(repo, "init")

        wt = tmp_path / "wt"
        _run(["git", "worktree", "add", "-b", "series-a", str(wt)], repo)
        return repo, wt

    def test_rebases_the_worktree_onto_the_new_main_tip(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_auto_rebase.py::TestAutoRebaseWorktreeOntoMain.test_rebases_the_worktree_onto_the_new_main_tip  # noqa: E501
        repo, wt = self._seed(tmp_path)

        # The worktree's own branch commits something (standing in for
        # the ticket this land just squash-applied).
        (wt / "src" / "own.py").write_text("# this branch's own work\n")
        _commit_all(wt, "own work")

        # main independently advances (the squash-apply this land just
        # produced, or any other already-landed sibling).
        (repo / "src" / "other.py").write_text("# unrelated, already landed\n")
        _commit_all(repo, "unrelated main-side land")

        pre_rebase_own_tip = subprocess.run(
            ["git", "-C", str(wt), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        ).stdout.strip()

        _auto_rebase_worktree_onto_main(repo, wt, "T-1720")

        # The worktree's branch now descends from main's current tip --
        # exactly what the manual `git rebase main` this ticket replaces
        # used to produce.
        assert _is_ancestor(wt, "main", "HEAD")
        # The worktree's OWN content survives the rebase, just replayed
        # on top of the new base.
        assert (wt / "src" / "own.py").read_text() == "# this branch's own work\n"
        assert (wt / "src" / "other.py").read_text() == "# unrelated, already landed\n"
        new_tip = subprocess.run(
            ["git", "-C", str(wt), "rev-parse", "HEAD"], capture_output=True, text=True
        ).stdout.strip()
        assert new_tip != pre_rebase_own_tip  # replayed onto a new base

    def test_a_real_conflict_aborts_cleanly_and_does_not_fail_the_land(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_land_auto_rebase.py::TestAutoRebaseWorktreeOntoMain.test_a_real_conflict_aborts_cleanly_and_does_not_fail_the_land  # noqa: E501
        repo, wt = self._seed(tmp_path)

        # Both sides edit the SAME line of the SAME file differently --
        # a genuine, unresolvable-by-rebase conflict.
        (wt / "src" / "feature.py").write_text("# worktree's own conflicting edit\n")
        _commit_all(wt, "worktree-side conflicting edit")

        (repo / "src" / "feature.py").write_text("# main's own conflicting edit\n")
        _commit_all(repo, "main-side conflicting edit")

        pre_attempt_tip = subprocess.run(
            ["git", "-C", str(wt), "rev-parse", "HEAD"], capture_output=True, text=True
        ).stdout.strip()

        # Must not raise -- best-effort, never fails the caller.
        _auto_rebase_worktree_onto_main(repo, wt, "T-1720")

        # The worktree is left exactly as it was: not mid-rebase, tip
        # unchanged, clean working tree.
        status = subprocess.run(
            ["git", "-C", str(wt), "status", "--porcelain"],
            capture_output=True,
            text=True,
        ).stdout
        assert status.strip() == ""
        assert not (wt / ".git" / "rebase-merge").exists()
        assert not (wt / ".git" / "rebase-apply").exists()
        post_attempt_tip = subprocess.run(
            ["git", "-C", str(wt), "rev-parse", "HEAD"], capture_output=True, text=True
        ).stdout.strip()
        assert post_attempt_tip == pre_attempt_tip

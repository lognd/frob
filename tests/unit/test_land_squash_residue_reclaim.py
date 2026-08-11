"""T-2157: a land killed by its shell timeout mid-squash-merge (SIGKILL,
uncatchable -- see `reclaim_orphaned_squash_residue`'s own docstring for
why this cannot be fixed by trapping the signal in `land()` itself) used
to leave `root`'s real index/working tree staged and dirty forever, with
no safe way to tell that residue apart from a LIVE concurrent land's own
staging short of a human checking `/proc` for the recorded holder pid by
hand -- the exact DirtyMain trap that stalled four concurrent lands for
over an hour in the incident this ticket is filed from.

Self-contained fixture repos (mirrors `tests/unit/test_land_duplicate_
ticket_id.py`'s own precedent) rather than appending to `tests/test_
ticket_land.py`, which T-2114/T-2118 hold a lease on this session.
"""

from __future__ import annotations

import fcntl
import os
import subprocess
from pathlib import Path

from frob.tickets._land_git_ops import reclaim_orphaned_squash_residue
from frob.tickets._leases import LAND_LOCK_REL


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=str(cwd), check=True, capture_output=True, text=True)


def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    (root / ".gitignore").write_text(".frob/\n")


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _seed_root(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    _git_init(root)
    (root / "committed.txt").write_text("committed\n")
    _commit_all(root, "initial commit")
    return root


def _simulate_orphaned_squash_stage(root: Path) -> None:
    """Mimics what a killed `_squash_and_splice_ledger` leaves behind: a
    tracked file modified AND staged, plus an untracked file added but not
    staged -- both must be gone after a successful reclaim, matching what
    `git merge --squash --no-commit` really stages (modified/added tracked
    content is staged; some untracked scratch content is not, exactly like
    T-2157's own incident report's `git status --porcelain` listing showed
    a mix of `M `/`A ` and untouched paths)."""
    (root / "committed.txt").write_text("squash-modified\n")
    _run(["git", "add", "committed.txt"], root)
    (root / "untracked-scratch.txt").write_text("scratch\n")


class TestReclaimOrphanedSquashResidue:
    # frob:tests tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue.test_reclaims_when_no_live_land_holds_the_lock kind="unit"  # noqa: E501
    def test_reclaims_when_no_live_land_holds_the_lock(self, tmp_path: Path) -> None:
        """FAILS FIRST against current main (pre-fix): before this ticket,
        nothing in `_land_git_ops.py` could safely clear a killed land's
        staged residue at all -- `reclaim_orphaned_squash_residue` did not
        exist. This is the acceptance test: a land killed mid-squash-merge
        (simulated directly -- staged content in `root` with land.lock
        held by nobody, exactly what the kernel leaves behind the instant
        a SIGKILL'd holder exits, T-1515) must leave `git status
        --porcelain` in the shared root clean after reclaim."""
        root = _seed_root(tmp_path)
        _simulate_orphaned_squash_stage(root)

        pre = _run(["git", "status", "--porcelain"], root)
        assert pre.stdout.strip() != "", "fixture setup must actually dirty root"

        result = reclaim_orphaned_squash_residue(root, "T-9999")
        assert result.is_ok, result
        assert result.danger_ok is True

        post = _run(["git", "status", "--porcelain"], root)
        assert post.stdout.strip() == "", (
            f"root must be clean after reclaim, got: {post.stdout!r}"
        )
        assert (root / "committed.txt").read_text() == "committed\n"

    # frob:tests tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue.test_does_not_touch_a_live_lands_own_staging kind="unit"  # noqa: E501
    def test_does_not_touch_a_live_lands_own_staging(self, tmp_path: Path) -> None:
        """Safety property this ticket's own 'do not fix it this way'
        section demands: a GENUINELY live land (simulated by holding
        land.lock's flock ourselves, exactly as `_land_lock` would) must
        never be reset out from under it, no matter how dirty `root`
        looks -- distinguishing live from dead is the whole point, not an
        afterthought."""
        root = _seed_root(tmp_path)
        _simulate_orphaned_squash_stage(root)

        lock_path = root / LAND_LOCK_REL
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

            result = reclaim_orphaned_squash_residue(root, "T-9999")
            assert result.is_ok, result
            assert result.danger_ok is False

            post = _run(["git", "status", "--porcelain"], root)
            assert "committed.txt" in post.stdout, (
                "a live land's own staged content must survive untouched"
            )
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    # frob:tests tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue.test_clean_root_is_a_no_op kind="unit"  # noqa: E501
    def test_clean_root_is_a_no_op(self, tmp_path: Path) -> None:
        """A clean root (the common case -- no residue at all) must never
        acquire the lock or touch anything; `Ok(False)`, no side effect."""
        root = _seed_root(tmp_path)

        result = reclaim_orphaned_squash_residue(root, "T-9999")
        assert result.is_ok, result
        assert result.danger_ok is False

        post = _run(["git", "status", "--porcelain"], root)
        assert post.stdout.strip() == ""

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
import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

from frob.tickets._land_git_ops import (
    _land_repair_marker_path,
    reclaim_orphaned_squash_residue,
)
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


# frob:ticket T-2286
def _simulate_orphaned_squash_stage(root: Path, *, ticket_id: str = "T-9999") -> None:
    """Mimics what a killed `_squash_and_splice_ledger` leaves behind: a
    tracked file modified AND staged, plus an untracked file added but not
    staged -- both must be gone after a successful reclaim, matching what
    `git merge --squash --no-commit` really stages (modified/added tracked
    content is staged; some untracked scratch content is not, exactly like
    T-2157's own incident report's `git status --porcelain` listing showed
    a mix of `M `/`A ` and untouched paths).

    T-2286: a real killed squash-merge ALWAYS has a T-0907/T-1963
    land-repair marker on disk too -- `_write_land_repair_marker` in
    `frob.tickets._land` writes it strictly BEFORE `_land_squash_apply`
    starts mutating `root`, so this fixture now writes one as well, to
    stay a faithful "real killed-land shape" rather than a synthetic one
    that omits the exact positive-evidence signal the fix now requires."""
    marker_path = _land_repair_marker_path(root, ticket_id)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(
        json.dumps({"ticket_id": ticket_id, "pre_land_tip": "deadbeef"}) + "\n",
        encoding="utf-8",
    )
    (root / "committed.txt").write_text("squash-modified\n")
    _run(["git", "add", "committed.txt"], root)
    (root / "untracked-scratch.txt").write_text("scratch\n")


# frob:ticket T-2286
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

    # frob:ticket T-2286
    # frob:tests tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue.test_dirty_without_a_marker_is_never_reclaimed kind="unit"  # noqa: E501
    def test_dirty_without_a_marker_is_never_reclaimed(self, tmp_path: Path) -> None:
        """T-2286's own acceptance test: `root` dirty AND `land.lock` free
        is NOT, by itself, proof of orphaned squash residue -- a stray
        uncommitted file (a hand-edited `uv.lock`, `dirty.txt`, anything)
        must survive untouched with no T-0907/T-1963 land-repair marker on
        disk, since nothing ever proved a squash-merge staged it. FAILS
        against the pre-fix `reclaim_orphaned_squash_residue`, which reset
        ANY dirty-and-unlocked root unconditionally."""
        root = _seed_root(tmp_path)
        (root / "dirty.txt").write_text("uncommitted, unrelated to any land\n")

        result = reclaim_orphaned_squash_residue(root, "T-9999")
        assert result.is_ok, result
        assert result.danger_ok is False, (
            "a dirty root with no land-repair marker must never be reset -- "
            "that is arbitrary dirt, not proven squash residue"
        )

        post = _run(["git", "status", "--porcelain"], root)
        assert "dirty.txt" in post.stdout, (
            "genuine uncommitted content must survive when no marker proves "
            "it is dead-land residue"
        )


class TestLandCallsReclaimAtStartup:
    """T-2170: `reclaim_orphaned_squash_residue` (T-2157) had zero
    production callers -- correct, tested, and reached by NOTHING except
    its own tests above. `land()` must call it once, at the very top of
    its own body, BEFORE `_land_lock` is acquired (calling it from inside
    the lock would make its own non-blocking flock-on-the-same-file
    liveness probe always fail, since `land()` itself would already hold
    it)."""

    # frob:tests tests/unit/test_land_squash_residue_reclaim.py::TestLandCallsReclaimAtStartup.test_land_calls_reclaim_before_acquiring_its_own_lock  # noqa: E501
    def test_land_calls_reclaim_before_acquiring_its_own_lock(
        self, tmp_path: Path
    ) -> None:
        """FAILS FIRST against current main: `land()` never imports or
        calls `reclaim_orphaned_squash_residue` at all, so this mock is
        never invoked and the assertion below fails."""
        from frob.tickets._land import land

        root = _seed_root(tmp_path)
        worktree = tmp_path / "worktree"
        worktree.mkdir()

        from typani import Ok

        with patch(
            "frob.tickets._land.reclaim_orphaned_squash_residue"
        ) as mock_reclaim:
            mock_reclaim.return_value = Ok(False)
            land(root, "T-0000", worktree, dry_run=True)

        assert mock_reclaim.called, (
            "land() never called reclaim_orphaned_squash_residue -- the "
            "T-2157 primitive still has zero production callers"
        )
        assert mock_reclaim.call_args.args[0] == root, (
            "reclaim_orphaned_squash_residue must be called against root, "
            "the shared checkout it is meant to unwind, not the worktree"
        )

    # frob:tests tests/unit/test_land_squash_residue_reclaim.py::TestLandCallsReclaimAtStartup.test_orphaned_residue_from_a_dead_land_is_cleared_before_the_dirtymain_refusal  # noqa: E501
    def test_orphaned_residue_from_a_dead_land_is_cleared_before_the_dirtymain_refusal(  # noqa: E501
        self, tmp_path: Path
    ) -> None:
        """The real property (not a mock-import technicality): a land
        started against a `root` that already carries a DEAD land's
        orphaned squash residue (no live process holds `land.lock`) must
        find `root` reclaimed BEFORE `_refuse_if_main_dirty` ever runs --
        so this particular DirtyMain refusal, caused only by residue
        `reclaim_orphaned_squash_residue` can safely clear, never fires,
        and root ends up clean either way. FAILS FIRST against current
        main: with no wiring, `root` is still dirty the instant `land()`
        reaches `_refuse_if_main_dirty`, which refuses with `DirtyMain`
        and leaves the residue sitting there untouched -- exactly the
        fleet-blocking trap this ticket exists to close."""
        from frob.tickets._land import land

        root = _seed_root(tmp_path)
        worktree = tmp_path / "worktree"
        worktree.mkdir()
        _simulate_orphaned_squash_stage(root)

        pre = _run(["git", "status", "--porcelain"], root)
        assert pre.stdout.strip() != "", "fixture setup must actually dirty root"

        land(root, "T-0000", worktree, dry_run=True)

        post = _run(["git", "status", "--porcelain"], root)
        assert post.stdout.strip() == "", (
            "root still carries dead-land residue after a land() attempt -- "
            f"reclaim was never invoked, got: {post.stdout!r}"
        )

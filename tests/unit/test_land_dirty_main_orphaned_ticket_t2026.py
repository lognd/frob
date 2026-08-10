"""T-2026: `_refuse_if_main_dirty`'s new auto-heal for a single orphaned,
untracked `tickets/T-####/` directory left by an INTERRUPTED `frob ticket
new` (the process died between writing `ticket.md` to disk and its own
final ledger commit -- nothing is alive to finish that commit itself, so
this land-time check is the only place that ever will).

Mirrors the existing `_restore_lock_version_only_drift`/`_commit_rapid_
debt_only_drift` precedent tests in `tests/test_ticket_land.py` (T-0793/
T-1699) but stays self-contained: a bare git-only fixture, no full
`land()`/worktree machinery, since the behavior under test lives entirely
inside `_refuse_if_main_dirty` and its new helper.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.tickets._land import (
    _commit_orphaned_new_ticket_dir_only_drift,
    _refuse_if_main_dirty,
)
from frob.tickets._models import LandError


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", "main"], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    (root / ".gitignore").write_text(".frob/\n")
    (root / "tickets").mkdir()
    (root / "tickets" / ".keep").write_text("")
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", "init"], root)


def _status(root: Path) -> str:
    raw = _run(["git", "status", "--porcelain"], root).stdout.strip()
    lines = [line for line in raw.splitlines() if ".frob/" not in line]
    return "\n".join(lines)


_TICKET_MD = """\
---
id: T-2050
title: A well-formed orphaned ticket
state: queued
kind: bug
origin: agent
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope: []
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Body text.
"""


def _write_orphaned_ticket_dir(root: Path, ticket_id: str, text: str) -> None:
    d = root / "tickets" / ticket_id
    d.mkdir(parents=True)
    (d / "ticket.md").write_text(text)


class TestCommitOrphanedNewTicketDirOnlyDrift:
    """Direct tests of the new narrow-match helper (T-2026)."""

    def test_well_formed_orphaned_dir_is_committed(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift.test_well_formed_orphaned_dir_is_committed  # noqa: E501
        root = tmp_path / "repo"
        _git_init(root)
        _write_orphaned_ticket_dir(root, "T-2050", _TICKET_MD)

        assert _status(root) == "?? tickets/T-2050/"
        healed = _commit_orphaned_new_ticket_dir_only_drift(root, "T-9999")
        assert healed is True
        assert _status(root) == ""
        log = _run(["git", "log", "-1", "--pretty=%s"], root).stdout
        assert "T-2050" in log
        assert "T-2026" in log

    def test_malformed_ticket_md_is_never_committed(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift.test_malformed_ticket_md_is_never_committed  # noqa: E501
        """A torn/partial write (no frontmatter at all, the exact shape a
        process killed mid-`atomic_write` could leave) must NEVER be
        force-committed -- this is the criterion the coordinator asked to
        be verified above all else."""
        root = tmp_path / "repo"
        _git_init(root)
        _write_orphaned_ticket_dir(root, "T-2050", "not even frontmatter\n")

        healed = _commit_orphaned_new_ticket_dir_only_drift(root, "T-9999")
        assert healed is False
        # Nothing was staged or committed; the untracked dir is untouched.
        assert _status(root) == "?? tickets/T-2050/"

    def test_id_mismatch_between_dirname_and_frontmatter_is_never_committed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift.test_id_mismatch_between_dirname_and_frontmatter_is_never_committed  # noqa: E501
        root = tmp_path / "repo"
        _git_init(root)
        # Directory says T-2050, frontmatter says T-2051 -- never trust a
        # single signal when two disagree.
        mismatched = _TICKET_MD.replace("id: T-2050", "id: T-2051")
        _write_orphaned_ticket_dir(root, "T-2050", mismatched)

        healed = _commit_orphaned_new_ticket_dir_only_drift(root, "T-9999")
        assert healed is False
        assert _status(root) == "?? tickets/T-2050/"

    def test_extra_file_in_the_directory_is_never_committed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift.test_extra_file_in_the_directory_is_never_committed  # noqa: E501
        """A directory holding anything besides exactly `ticket.md` (e.g.
        a clipboard attachment written before the process died) is a
        shape this guard does not claim to understand -- refuse, not
        guess."""
        root = tmp_path / "repo"
        _git_init(root)
        _write_orphaned_ticket_dir(root, "T-2050", _TICKET_MD)
        (root / "tickets" / "T-2050" / "extra.txt").write_text("surprise\n")

        healed = _commit_orphaned_new_ticket_dir_only_drift(root, "T-9999")
        assert healed is False

    def test_a_second_dirty_path_blocks_the_auto_commit(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift.test_a_second_dirty_path_blocks_the_auto_commit  # noqa: E501
        """A genuinely human-dirty root (an unrelated edited/untracked
        file alongside the orphaned dir) must NOT have that unrelated
        change swept into the auto-heal commit -- assert no over-reach."""
        root = tmp_path / "repo"
        _git_init(root)
        _write_orphaned_ticket_dir(root, "T-2050", _TICKET_MD)
        (root / "other.txt").write_text("real uncommitted work\n")

        healed = _commit_orphaned_new_ticket_dir_only_drift(root, "T-9999")
        assert healed is False
        assert "?? tickets/T-2050/" in _status(root)
        assert "?? other.txt" in _status(root)

    def test_a_modified_tracked_ticket_md_is_not_this_guards_shape(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift.test_a_modified_tracked_ticket_md_is_not_this_guards_shape  # noqa: E501
        """T-2026 scopes itself to the UNTRACKED-new case only (the risk
        argument in the ticket): a MODIFIED, already-tracked ticket.md
        (git status `M `, not `??`) is a different failure shape this
        guard deliberately does not attempt to heal."""
        root = tmp_path / "repo"
        _git_init(root)
        _write_orphaned_ticket_dir(root, "T-2050", _TICKET_MD)
        _run(["git", "add", "-A"], root)
        _run(["git", "commit", "-q", "-m", "file T-2050"], root)
        (root / "tickets" / "T-2050" / "ticket.md").write_text(
            _TICKET_MD + "\nan edit\n"
        )

        healed = _commit_orphaned_new_ticket_dir_only_drift(root, "T-9999")
        assert healed is False


class TestRefuseIfMainDirtyOrphanedTicketHeal:
    """`_refuse_if_main_dirty` end to end: the acceptance criterion's own
    before/after shape."""

    def test_orphaned_ticket_dir_no_longer_refuses(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestRefuseIfMainDirtyOrphanedTicketHeal.test_orphaned_ticket_dir_no_longer_refuses  # noqa: E501
        """FAILS FIRST: before T-2026's wiring existed,
        `_refuse_if_main_dirty` refused with `DirtyMain` for exactly this
        state (verified by hand against the pre-fix code: removing the
        `_commit_orphaned_new_ticket_dir_only_drift` call from
        `_refuse_if_main_dirty` reproduces `Err(DirtyMain)` here). This
        asserts the NEW behavior: the orphan is healed and land proceeds
        past the dirty check."""
        root = tmp_path / "repo"
        _git_init(root)
        _write_orphaned_ticket_dir(root, "T-2050", _TICKET_MD)

        result = _refuse_if_main_dirty(root, root, "T-9999")
        assert result.is_ok, result
        assert _status(root) == ""

    def test_genuinely_human_dirty_root_still_refuses(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestRefuseIfMainDirtyOrphanedTicketHeal.test_genuinely_human_dirty_root_still_refuses  # noqa: E501
        """No over-reach: an ordinary edited source file must still
        refuse exactly as before this ticket -- swallowing real
        uncommitted work is far worse than the blockage T-2026 fixes."""
        root = tmp_path / "repo"
        _git_init(root)
        (root / "some_module.py").write_text("x = 1\n")

        result = _refuse_if_main_dirty(root, root, "T-9999")
        assert result.is_err
        assert result.danger_err == LandError.DirtyMain

    def test_orphaned_dir_alongside_real_dirt_still_refuses(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestRefuseIfMainDirtyOrphanedTicketHeal.test_orphaned_dir_alongside_real_dirt_still_refuses  # noqa: E501
        root = tmp_path / "repo"
        _git_init(root)
        _write_orphaned_ticket_dir(root, "T-2050", _TICKET_MD)
        (root / "some_module.py").write_text("x = 1\n")

        result = _refuse_if_main_dirty(root, root, "T-9999")
        assert result.is_err
        assert result.danger_err == LandError.DirtyMain
        # Neither path was touched -- the orphan is left exactly as found
        # for the next attempt, once the real dirt is dealt with.
        assert "?? tickets/T-2050/" in _status(root)

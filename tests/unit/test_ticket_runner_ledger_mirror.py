"""T-2563: a ledger-only ticket edit made from a worktree must be visible
on the PRIMARY checkout immediately, not only if some later land happens
to carry it.

The controls here are written to fail against the pre-T-2563 behaviour:
before the mirror existed, every `_visible_on_primary` assertion below
read `False` while the verb itself reported success -- the silent-zero
shape this ticket closes.
"""
# frob:ticket T-2563

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.app.ticket_runner._ledger_mirror import (
    MIRRORED_LEDGER_VERBS,
    mirror_ledger_change_to_primary,
)


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )


def _ticket_text(ticket_id: str) -> str:
    return f"---\nid: {ticket_id}\nstate: queued\n---\nbody\n"


# frob:ticket T-2563
def _setup(tmp_path: Path, ticket_id: str = "T-0001") -> tuple[Path, Path]:
    """A primary checkout carrying `ticket_id`, plus a linked worktree.

    Returns `(primary, worktree)`.
    """
    primary = tmp_path / "primary"
    primary.mkdir()
    _git("init", "-q", "-b", "main", cwd=primary)
    _git("config", "user.email", "t@example.com", cwd=primary)
    _git("config", "user.name", "T", cwd=primary)
    # Every real frob repo gitignores .frob/ (the lock/cache dir); without
    # it the mirror's own ledger_lock file reads as untracked noise and the
    # cleanliness control below would fail on a fixture artefact rather
    # than on anything the mirror did.
    (primary / ".gitignore").write_text(".frob/\n")
    ticket_dir = primary / "tickets" / ticket_id
    ticket_dir.mkdir(parents=True)
    (ticket_dir / "ticket.md").write_text(_ticket_text(ticket_id))
    _git("add", "-A", cwd=primary)
    _git("commit", "-q", "-m", "init", cwd=primary)

    worktree = tmp_path / "wt"
    added = _git("worktree", "add", "-q", "-b", "t-branch", str(worktree), "main", cwd=primary)
    assert added.returncode == 0, added.stdout + added.stderr
    return primary, worktree


def _visible_on_primary(primary: Path, needle: str, ticket_id: str = "T-0001") -> bool:
    """Does the PRIMARY checkout's committed ledger carry `needle`?

    Reads the committed tree (`git show HEAD:...`), never the working
    tree -- the whole defect was an edit that existed somewhere other
    than where the fleet looks, so an assertion that reads a loose file
    would not distinguish the fixed case from the broken one.
    """
    shown = _git("show", f"HEAD:tickets/{ticket_id}/ticket.md", cwd=primary)
    return shown.returncode == 0 and needle in shown.stdout


class TestLedgerMirrorReachesMain:
    # frob:ticket T-2563
    def test_scope_edit_from_worktree_is_visible_on_primary(self, tmp_path: Path) -> None:
        """The headline control: the edit must be readable on the primary
        checkout the moment the verb returns."""
        primary, worktree = _setup(tmp_path)
        path = worktree / "tickets" / "T-0001" / "ticket.md"
        path.write_text(path.read_text() + "scope:\n- src/mine.py\n")
        _git("commit", "-q", "-am", "scope edit", cwd=worktree)

        mirror_ledger_change_to_primary(worktree, "T-0001", "scope")

        assert _visible_on_primary(primary, "src/mine.py")

    # frob:ticket T-2563
    def test_block_edit_from_worktree_is_visible_on_primary(self, tmp_path: Path) -> None:
        """`block` is the verb whose invisibility left T-2374 looking
        like it had simply stopped for no reason."""
        primary, worktree = _setup(tmp_path)
        path = worktree / "tickets" / "T-0001" / "ticket.md"
        path.write_text(path.read_text() + "blocked_by:\n- T-9999\n")
        _git("commit", "-q", "-am", "block edit", cwd=worktree)

        mirror_ledger_change_to_primary(worktree, "T-0001", "block")

        assert _visible_on_primary(primary, "T-9999")

    # frob:ticket T-2563
    def test_attachment_file_reaches_primary(self, tmp_path: Path) -> None:
        """`attach` writes a NEW file inside the ticket directory, so the
        mirror has to carry whole directories, not just ticket.md."""
        primary, worktree = _setup(tmp_path)
        attachments = worktree / "tickets" / "T-0001" / "attachments"
        attachments.mkdir(parents=True)
        (attachments / "01-analysis.md").write_text("findings\n")
        _git("add", "-A", cwd=worktree)
        _git("commit", "-q", "-m", "attach", cwd=worktree)

        mirror_ledger_change_to_primary(worktree, "T-0001", "attach")

        shown = _git("show", "HEAD:tickets/T-0001/attachments/01-analysis.md", cwd=primary)
        assert shown.returncode == 0, shown.stdout + shown.stderr
        assert "findings" in shown.stdout


class TestLedgerMirrorCarriesNothingElse:
    # frob:ticket T-2563
    def test_worktree_source_changes_do_not_leak_to_primary(self, tmp_path: Path) -> None:
        """The must-NOT-fire control. An agent's in-progress source edits
        are the reason ledger edits were stranded in the first place;
        fixing that must not start publishing unlanded code as a side
        effect."""
        primary, worktree = _setup(tmp_path)
        (worktree / "src_secret.py").write_text("UNLANDED = True\n")
        _git("add", "-A", cwd=worktree)
        _git("commit", "-q", "-m", "unlanded source", cwd=worktree)
        path = worktree / "tickets" / "T-0001" / "ticket.md"
        path.write_text(path.read_text() + "priority: high\n")
        _git("commit", "-q", "-am", "priority", cwd=worktree)

        mirror_ledger_change_to_primary(worktree, "T-0001", "priority")

        assert _visible_on_primary(primary, "priority: high")
        assert not (primary / "src_secret.py").exists()
        listed = _git("show", "--stat", "--name-only", "HEAD", cwd=primary)
        assert "src_secret.py" not in listed.stdout

    # frob:ticket T-2563
    def test_primary_worktree_is_left_clean(self, tmp_path: Path) -> None:
        """A mirror that dirtied the shared root would DirtyMain-block
        every concurrent land -- the failure this repo pays for most
        often. The write must be committed, not left loose."""
        primary, worktree = _setup(tmp_path)
        path = worktree / "tickets" / "T-0001" / "ticket.md"
        path.write_text(path.read_text() + "kind: bug\n")
        _git("commit", "-q", "-am", "kind", cwd=worktree)

        mirror_ledger_change_to_primary(worktree, "T-0001", "kind")

        status = _git("status", "--porcelain", cwd=primary)
        assert status.stdout.strip() == "", status.stdout


class TestLedgerMirrorScope:
    # frob:ticket T-2563
    @pytest.mark.parametrize("verb", ["start", "close", "done-report", "evidence"])
    def test_state_machine_verbs_are_not_mirrored(self, tmp_path: Path, verb: str) -> None:
        """State transitions describe work that is still worktree-local
        and land carries them atomically with the code. Mirroring one
        would advance main's state machine ahead of the work itself."""
        assert verb not in MIRRORED_LEDGER_VERBS
        primary, worktree = _setup(tmp_path)
        path = worktree / "tickets" / "T-0001" / "ticket.md"
        path.write_text(path.read_text().replace("queued", "in-progress"))
        _git("commit", "-q", "-am", "state", cwd=worktree)

        mirror_ledger_change_to_primary(worktree, "T-0001", verb)

        assert not _visible_on_primary(primary, "in-progress")

    # frob:ticket T-2563
    def test_running_in_the_primary_checkout_is_a_no_op(self, tmp_path: Path) -> None:
        """The coordinator's own path must cost nothing: when the verb
        already ran in the primary checkout there is no second root to
        mirror onto, and no commit may be invented."""
        primary, _worktree = _setup(tmp_path)
        before = _git("rev-parse", "HEAD", cwd=primary).stdout.strip()

        mirror_ledger_change_to_primary(primary, "T-0001", "scope")

        assert _git("rev-parse", "HEAD", cwd=primary).stdout.strip() == before
        assert _git("status", "--porcelain", cwd=primary).stdout.strip() == ""

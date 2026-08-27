"""T-3108: TICK006's Tier-A auto-recovery (T-1544) filed two duplicate
tickets for citations of ids minted in SIBLING worktrees that had not yet
landed -- T-2197's own doctrine that a worktree-minted id is invisible on
`main` until that worktree lands. T-2400 already widened resolution to
`main`'s own landed ledger (`merge_target_ids`); this closes the remaining
gap, resolution against every OTHER live worktree's own local ledger.

Real git worktrees throughout (matching `tests/test_gates.py`'s own
`_tick006_repo` real-git-subprocess idiom for this same handler family) --
`git worktree list --porcelain` genuinely needs a real git repo with real
worktree entries, not a mock."""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

import pytest


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    )


# frob:ticket T-3108
def _base_repo(tmp_path: Path) -> Path:
    """A bare-bones git repo, real `tickets.md`/`tickets-archive.md`
    monofile placeholders (matching `tests/test_gates.py::_tick006_repo`'s
    own shape) so `write_ticket`'s v2 per-ticket-dir writes have a valid
    ledger root to write into."""
    root = tmp_path / "main"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    (root / "tickets.md").write_text("# Tickets\n\n", encoding="utf-8")
    (root / "tickets-archive.md").write_text("# Archive\n\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


# frob:ticket T-3108
def _write_active_ticket(root: Path, ticket_id: str) -> None:
    """A minimal non-terminal ticket, committed -- the shape a sibling
    worktree's own local ledger carries for an id it minted but has not
    yet landed."""
    from frob.tickets import Origin, Ticket, TicketKind, TicketState
    from frob.tickets._store import write_ticket

    ticket = Ticket(
        id=ticket_id,
        title=f"work tracked by {ticket_id}",
        state=TicketState.IN_PROGRESS,
        kind=TicketKind.BUG,
        origin=Origin.AGENT,
        created=date.today(),
        body="in progress, not yet landed",
    )
    result = write_ticket(root, ticket)
    assert result.is_ok
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", f"file {ticket_id}")


# frob:ticket T-3108
class TestSiblingWorktreeKnownIds:
    """`_sibling_worktree_known_ids` (T-3108): widens known-id resolution
    to every OTHER live git worktree's own local ledger."""

    def test_reads_an_active_id_from_another_worktree(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates_tick006_sibling_worktree.py::TestSiblingWorktreeKnownIds.tes\
        # t_reads_an_active_id_from_another_worktree
        from frob.gates._fix_engine import _sibling_worktree_known_ids

        main_repo = _base_repo(tmp_path)
        sibling = tmp_path / "sibling-wt"
        _git(main_repo, "worktree", "add", "-b", "sibling", str(sibling), "main")
        _write_active_ticket(sibling, "T-3107")

        found = _sibling_worktree_known_ids(main_repo)
        assert "T-3107" in found

    def test_excludes_root_itself(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates_tick006_sibling_worktree.py::TestSiblingWorktreeKnownIds.tes\
        # t_excludes_root_itself
        """`root`'s own ids must not double-count as a "sibling" find --
        callers already union `queue.tickets`/archive separately, so a
        self-match here would be redundant, never wrong, but the
        function's OWN contract (every OTHER worktree) is tested
        directly."""
        from frob.gates._fix_engine import _sibling_worktree_known_ids

        main_repo = _base_repo(tmp_path)
        _write_active_ticket(main_repo, "T-0001")

        found = _sibling_worktree_known_ids(main_repo)
        assert found == frozenset()

    def test_unreadable_worktree_is_skipped_not_fatal(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates_tick006_sibling_worktree.py::TestSiblingWorktreeKnownIds.tes\
        # t_unreadable_worktree_is_skipped_not_fatal
        """A worktree entry `git worktree list` still names but whose
        directory is gone (a raw `rm -rf`, never `git worktree remove`)
        must not raise or abort the whole scan -- best-effort, matching
        this function's own widening-only, never-strict posture."""
        from frob.gates._fix_engine import _sibling_worktree_known_ids

        main_repo = _base_repo(tmp_path)
        sibling = tmp_path / "sibling-wt"
        _git(main_repo, "worktree", "add", "-b", "sibling", str(sibling), "main")
        _write_active_ticket(sibling, "T-3107")

        import shutil

        shutil.rmtree(sibling)

        found = _sibling_worktree_known_ids(main_repo)  # must not raise
        assert found == frozenset()


# frob:ticket T-3108
class TestFixTick006ResolvesSiblingWorktreeCitations:
    """Integration acceptance (T-3108): `fix_tick006_phantom_refile`
    itself, not just the helper -- a citation to an id active in a
    sibling worktree must not file, and a genuinely nowhere-found id
    still does."""

    def test_citation_to_sibling_worktree_active_id_does_not_refile(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_gates_tick006_sibling_worktree.py::TestFixTick006ResolvesSiblingWo\
        # rktreeCitations.test_citation_to_sibling_worktree_active_id_does_not_refile
        """Must-stay-quiet: the T-3106/T-3107 shape -- a Done report
        cites an id that exists ONLY as a non-terminal ticket in a
        sibling, not-yet-landed worktree. Must not file a duplicate."""
        from frob.gates._fix_engine import fix_tick006_phantom_refile
        from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState
        from frob.tickets._store import write_ticket

        main_repo = _base_repo(tmp_path)
        sibling = tmp_path / "sibling-wt"
        _git(main_repo, "worktree", "add", "-b", "sibling", str(sibling), "main")
        _write_active_ticket(sibling, "T-3107")

        claiming = Ticket(
            id="T-0001",
            title="claiming ticket",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
            body="## Done report\n\nFiled T-3107 as a follow-up.\n",
        )
        write_result = write_ticket(main_repo, claiming)
        assert write_result.is_ok
        _git(main_repo, "add", "-A")
        _git(main_repo, "commit", "-q", "-m", "file claiming ticket")

        queue = TicketQueue(tickets={"T-0001": claiming})
        applied = fix_tick006_phantom_refile(main_repo, queue)
        assert applied == []

        from frob.tickets._store import load_all

        reloaded = load_all(main_repo)
        assert reloaded.is_ok
        # No new ticket was filed -- only the claiming ticket exists here.
        assert set(reloaded.danger_ok) == {"T-0001"}

    def test_genuinely_nonexistent_id_still_refiles(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_gates_tick006_sibling_worktree.py::TestFixTick006ResolvesSiblingWo\
        # rktreeCitations.test_genuinely_nonexistent_id_still_refiles
        """Must-fire: an id that exists NOWHERE -- not this worktree, not
        any sibling worktree -- is still detected and refiled. Do not
        solve T-3108 by never firing.

        `monkeypatch.delenv("FROB_WORKTREE", ...)`: this is the only test
        in this module that reaches `new_ticket` (every other test
        resolves the citation before ever calling it), and `new_ticket`
        runs `enforce_worktree_lease` (T-0431) -- when THIS test's own
        evidence is reverified by an agent already working inside a real
        leased worktree, `FROB_WORKTREE` is exported into the pytest
        subprocess and refuses `new_ticket(main_repo, ...)` (`main_repo`
        is an unrelated tmp_path fixture repo, never the leased
        worktree), a spurious failure with nothing to do with what this
        test verifies. Clearing it here isolates the test the same way
        `tests/test_gates.py:10445` clears/sets it explicitly to exercise
        the guard directly -- this test is not exercising the guard, so
        it must not be an accidental subject of it."""
        monkeypatch.delenv("FROB_WORKTREE", raising=False)
        from frob.gates._fix_engine import fix_tick006_phantom_refile
        from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState
        from frob.tickets._store import write_ticket

        main_repo = _base_repo(tmp_path)
        sibling = tmp_path / "sibling-wt"
        _git(main_repo, "worktree", "add", "-b", "sibling", str(sibling), "main")
        _write_active_ticket(sibling, "T-9999")  # unrelated to the citation below

        claiming = Ticket(
            id="T-0001",
            title="claiming ticket",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            created=date.today(),
            body=(
                "## Done report\n\nFiled T-draft-cafef00d (genuinely never "
                "filed anywhere) as a follow-up.\n"
            ),
        )
        write_result = write_ticket(main_repo, claiming)
        assert write_result.is_ok
        _git(main_repo, "add", "-A")
        _git(main_repo, "commit", "-q", "-m", "file claiming ticket")

        queue = TicketQueue(tickets={"T-0001": claiming})
        applied = fix_tick006_phantom_refile(main_repo, queue)
        assert len(applied) == 1
        assert applied[0].rule == "TICK006"
        assert "T-draft-cafef00d" in applied[0].detail

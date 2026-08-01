"""T-1356: regression tests for the two scope-lease deadlock fixes in
`frob.tickets._scope`:

1. `_scope_remove_orphans_evidence` now checks whether evidence stays
   COVERED by the ticket's REMAINING scope after a `--remove`, not
   whether the removed glob itself happened to cover it -- a real
   incident where a broader glob could not be narrowed to release a path
   a sibling ticket needed, even though a still-declared, narrower glob
   would have kept the evidence covered on its own.
2. `_scope_add_conflicts` no longer refuses an `--add` as a
   `ScopeLeaseConflict` when the colliding holder ticket is leased to the
   SAME worktree as the requesting ticket -- two tickets sharing one
   series worktree are one agent, not two agents racing.

Uses a real git-inited fixture repo (subprocess `git`, matching `tests/
test_ticket_land.py`'s own style) for the same-worktree case specifically,
since the cross-worktree lease side-channel (`record_lease`/
`read_all_leases`) only activates against a real git worktree."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets import (
    Origin,
    TicketKind,
    TicketState,
    load_queue,
    mutate_scope,
    new_ticket,
    transition,
)
from frob.tickets._models import TicketError, TicketSpec
from frob.tickets._scope import _scope_remove_orphans_evidence
from frob.tickets._store import atomic_write, ledger_path, load_all, write_ticket


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


# frob:waive DUP001 reason="fixture-repo git-init boilerplate already duplicated \
# verbatim across several land/ticket test modules (tests/ test_ticket_land.py, \
# tests/unit/test_land_cross_ticket_leakage.py, and others) -- each test module owns \
# its own tiny copy rather than importing across test files (the existing convention \
# this repo's test suite already follows for fixture helpers)"
def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    (root / ".gitignore").write_text(".frob/\n")


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _make_ticket(
    root: Path,
    *,
    scope: tuple[str, ...],
    state: TicketState = TicketState.QUEUED,
):
    spec = TicketSpec(
        title=f"scope lease deadlock fixture ({state})",
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        scope=scope,
    )
    created = new_ticket(root, spec)
    assert created.is_ok, created
    ticket = created.danger_ok
    if state is TicketState.IN_PROGRESS:
        planned = transition(root, ticket.id, TicketState.PLANNED)
        assert planned.is_ok, planned
        started = transition(root, ticket.id, TicketState.IN_PROGRESS)
        assert started.is_ok, started
        return started.danger_ok
    return ticket


class TestRemoveKeepsEvidenceCoveredByRemainingScope:
    """`--remove` is permitted when a REMAINING glob keeps evidence
    covered, refused only when removal would genuinely orphan it."""

    def test_remove_permitted_when_narrower_glob_still_covers_evidence(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_scope.py::_scope_remove_orphans_evidence kind="unit"  # noqa: E501
        ticket = _make_ticket(
            tmp_path,
            scope=("tests/unit/**", "tests/unit/test_kept.py"),
            state=TicketState.IN_PROGRESS,
        )
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        current = loaded.danger_ok[ticket.id]
        with_evidence = current.model_copy(
            update={"evidence": ("tests/unit/test_kept.py::test_ok",)}
        )
        assert write_ticket(tmp_path, with_evidence).is_ok

        # Removing the BROAD glob must be permitted: the narrower,
        # still-declared "tests/unit/test_kept.py" keeps the evidence
        # covered on its own.
        result = mutate_scope(
            tmp_path,
            ticket.id,
            remove=("tests/unit/**",),
            reason="narrowing to release tests/unit/** for a sibling ticket",
        )
        assert result.is_ok, result
        assert "tests/unit/**" not in result.danger_ok.scope
        assert "tests/unit/test_kept.py" in result.danger_ok.scope

    def test_remove_still_refused_when_evidence_would_be_orphaned(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_scope.py::_scope_remove_orphans_evidence kind="unit"  # noqa: E501
        ticket = _make_ticket(
            tmp_path,
            scope=("tests/unit/**",),
            state=TicketState.IN_PROGRESS,
        )
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        current = loaded.danger_ok[ticket.id]
        with_evidence = current.model_copy(
            update={"evidence": ("tests/unit/test_covered.py::test_ok",)}
        )
        assert write_ticket(tmp_path, with_evidence).is_ok

        # No other glob remains to cover the evidence -- must still refuse.
        result = mutate_scope(
            tmp_path,
            ticket.id,
            remove=("tests/unit/**",),
            reason="attempt to fully vacate scope",
        )
        assert result.is_err
        assert result.danger_err == TicketError.ScopeRemoveOrphansEvidence

    def test_unit_helper_directly_permits_when_remaining_covers(self) -> None:
        # frob:tests src/frob/tickets/_scope.py::_scope_remove_orphans_evidence kind="unit"  # noqa: E501
        from frob.tickets._models import Ticket

        ticket = Ticket.model_construct(
            evidence=("tests/unit/test_kept.py::test_ok",),
        )
        assert (
            _scope_remove_orphans_evidence(
                "tests/unit/**", ticket, ("tests/unit/test_kept.py",)
            )
            is False
        )
        assert (
            _scope_remove_orphans_evidence("tests/unit/**", ticket, ())
            is True
        )


class TestSameWorktreeLeaseIsNotAConflict:
    """`--add` into a path a SIBLING ticket in the SAME worktree holds is
    not refused as `ScopeLeaseConflict` -- one agent, not two racing."""

    def test_add_into_sibling_scope_same_worktree_is_permitted(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_scope.py::_scope_add_conflicts kind="unit"
        repo = tmp_path / "repo"
        _git_init(repo)
        atomic_write(ledger_path(repo), "# Tickets\n\n")
        _commit_all(repo, "init")

        # Both tickets are created AND transitioned in-progress from the
        # SAME worktree (repo itself) -- exactly the series-worktree shape.
        holder = _make_ticket(
            repo, scope=("src/frob/gates/**",), state=TicketState.IN_PROGRESS
        )
        agent = _make_ticket(repo, scope=("src/frob/other/**",))

        result = mutate_scope(
            repo,
            agent.id,
            add=("src/frob/gates/foo.py",),
            reason="need this file, held by a same-worktree sibling",
        )

        assert result.is_ok, result
        assert "src/frob/gates/foo.py" in result.danger_ok.scope
        # The holder is unaffected -- this is an exemption for the
        # REQUESTER, never a silent release of the holder's own lease.
        queue = load_queue(repo).danger_ok
        assert holder.id in queue.tickets
        assert "src/frob/gates/**" in queue.tickets[holder.id].scope

    def test_add_into_different_worktree_sibling_scope_still_refused(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/_scope.py::_scope_add_conflicts kind="unit"
        # Sanity check: a genuine DIFFERENT-worktree collision (the real
        # T-0453 hazard this lease model exists for) must still refuse.
        repo = tmp_path / "repo"
        _git_init(repo)
        atomic_write(ledger_path(repo), "# Tickets\n\n")
        _commit_all(repo, "init")

        holder = _make_ticket(
            repo, scope=("src/frob/gates/**",), state=TicketState.IN_PROGRESS
        )
        # Commit the holder's ticket so a worktree branched AFTER this
        # point actually sees it in its own local ledger -- mirroring how
        # a real second worktree only learns of a ticket via a shared
        # commit or the cross-worktree lease side-channel, never a purely
        # uncommitted sibling write.
        _commit_all(repo, "holder ticket in-progress")

        other_wt = tmp_path / "other-wt"
        _run(["git", "worktree", "add", "-b", "other-agent", str(other_wt)], repo)
        agent = _make_ticket(other_wt, scope=("src/frob/other/**",))

        result = mutate_scope(
            other_wt,
            agent.id,
            add=("src/frob/gates/foo.py",),
            reason="different worktree, real collision",
        )

        assert result.is_err
        assert result.danger_err == TicketError.ScopeLeaseConflict

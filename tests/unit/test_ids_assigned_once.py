# frob:ticket T-4658
"""Unit tests for T-4658: ids are assigned once at `frob ticket new`, and
renumbering (bulk or single-id) is refused unconditionally from inside a
`.claude/worktrees/` agent checkout -- kernel decoupling (T-4651/T-4652).

Measured this week: draft ids were renumbered INSIDE worktrees, and
concurrent agents raced each other's renumbers (T-4590/T-4596, T-4633,
T-4636/T-4642). `enforce_worktree_lease` alone does not catch this: a
worktree correctly leased to ITSELF passes that check fine and could still
renumber. `_refuse_renumber_inside_worktree` closes that gap structurally,
by path shape alone, independent of any lease state.
"""

from __future__ import annotations

import threading
from pathlib import Path

from typani.result import Result

from frob.tickets._models import Origin, Ticket, TicketError, TicketKind, TicketSpec
from frob.tickets._new_renumber import (
    _refuse_renumber_inside_worktree,
    new_ticket,
    renumber,
    renumber_one,
)
from frob.tickets._renumber_v2 import renumber_one_v2

_WORKTREE_REL = Path(".claude") / "worktrees" / "t-9999"


# frob:tests tests/unit/test_ids_assigned_once.py::test_renumber_refused_inside_worktree kind="unit"  # noqa: E501
def test_renumber_refused_inside_worktree(tmp_path: Path) -> None:
    """POSITIVE CONTROL (T-4658): `renumber` on a root path shaped like a
    `.claude/worktrees/<id>` agent checkout is refused with a named error
    before it ever touches the ledger. FAILS on dev today (the renumber
    succeeds and rewrites ids) and passes after this leaf."""
    worktree_root = tmp_path / _WORKTREE_REL
    worktree_root.mkdir(parents=True)
    (worktree_root / "tickets").mkdir()

    result = renumber(worktree_root)

    assert result.is_err
    assert result.danger_err == TicketError.WorktreeLeaseViolation
    # the refusal is structural (path-shape only) and happens before any
    # ledger I/O -- nothing was written.
    assert list((worktree_root / "tickets").iterdir()) == []


def test_renumber_one_refused_inside_worktree(tmp_path: Path) -> None:
    """Same refusal for the single-id rename entry point (`renumber_one`),
    which is the primitive draft promotion and `finalize_draft` build on
    top of."""
    worktree_root = tmp_path / _WORKTREE_REL
    worktree_root.mkdir(parents=True)
    (worktree_root / "tickets").mkdir()

    result = renumber_one(worktree_root, "T-draft-abc123", "T-0042")

    assert result.is_err
    assert result.danger_err == TicketError.WorktreeLeaseViolation


def test_renumber_one_v2_refused_inside_worktree(tmp_path: Path) -> None:
    """`renumber_one_v2` re-checks the same refusal defensively -- it is
    itself a public v2-mode entry point some caller could reach directly,
    not only via `renumber_one`'s dispatch."""
    worktree_root = tmp_path / _WORKTREE_REL
    worktree_root.mkdir(parents=True)
    (worktree_root / "tickets").mkdir()

    result = renumber_one_v2(worktree_root, "T-draft-abc123", "T-0042")

    assert result.is_err
    assert result.danger_err == TicketError.WorktreeLeaseViolation


def test_refusal_helper_allows_a_non_worktree_root(tmp_path: Path) -> None:
    """Companion control: the helper itself must not simply always refuse
    -- a root with no `.claude/worktrees/` segment in its path is allowed
    through, proving the check is discriminating on path shape rather than
    refusing everything."""
    assert _refuse_renumber_inside_worktree(tmp_path).is_ok


def test_concurrent_new_allocates_distinct_ids(tmp_path: Path) -> None:
    """Two concurrent `frob ticket new` calls in the (non-worktree) root
    receive distinct ids and neither rewrites the other's ticket -- the
    allocator lock `_allocate_and_write_new_ticket` already takes makes
    this safe; this test proves the property end to end rather than
    trusting the lock exists."""
    (tmp_path / "tickets").mkdir()

    def _spec(title: str) -> TicketSpec:
        return TicketSpec(title=title, kind=TicketKind.BUG, origin=Origin.HUMAN)

    results: list[Result[Ticket, TicketError] | None] = [None, None]

    def _run(index: int, title: str) -> None:
        results[index] = new_ticket(tmp_path, _spec(title))

    threads = [
        threading.Thread(target=_run, args=(0, "Concurrent ticket A")),
        threading.Thread(target=_run, args=(1, "Concurrent ticket B")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    first, second = results
    assert first is not None and first.is_ok
    assert second is not None and second.is_ok
    assert first.danger_ok.id != second.danger_ok.id

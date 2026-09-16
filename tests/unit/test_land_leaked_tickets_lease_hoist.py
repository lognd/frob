"""T-4492 (second defect, same worktree-workflow root cause):
`_find_leaked_tickets`'s per-candidate loop used to call `read_all_leases`
twice per OTHER open ticket (once via its own short-circuit call to
`_effective_leakage_scope`, once more inside `_leaked_hits_for_candidate`'s
own identical call) -- measured on this repo, `read_all_leases` costs
minutes and the loop runs ~800 times in one land precheck, so no land
ever finished. Fixed by hoisting ONE `read_all_leases(root)` call before
the loop and threading it through as a `leases` parameter.

This test asserts the hoist, not the leakage semantics themselves (those
stay covered by `tests/unit/test_land_cross_ticket_leakage.py` and
siblings) -- `read_all_leases` is monkeypatched with a call counter, and
`_find_leaked_tickets` is called directly with several OTHER candidate
tickets, all already `IN_PROGRESS` (so `is_effectively_in_progress`'s own
short-circuit on `ledger_state == IN_PROGRESS` never reaches ITS OWN
`read_all_leases` call either -- this test isolates the hoist this ticket
fixes, not that unrelated call site)."""

from __future__ import annotations

from pathlib import Path

import pytest

import frob.tickets._land as land_mod
from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    new_ticket,
    transition,
)
from frob.tickets._models import Ticket
from frob.tickets._store import atomic_write, ledger_path


def _spec(title: str, *, scope: tuple[str, ...] = ("src/some_file.py",)) -> TicketSpec:
    return TicketSpec(
        title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT, scope=scope
    )


class TestFindLeakedTicketsHoistsReadAllLeases:
    def test_read_all_leases_called_at_most_once_across_many_candidates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_land_leaked_tickets_lease_hoist.py::TestFindLeakedTicketsHoistsReadAllLeases.test_read_all_leases_called_at_most_once_across_many_candidates  # noqa: E501
        root = tmp_path / "root"
        root.mkdir()
        atomic_write(ledger_path(root), "# Tickets\n\n")

        worktree_tickets: dict[str, Ticket] = {}
        for i in range(8):
            created = new_ticket(root, _spec(f"Candidate {i}"))
            assert created.is_ok
            tid = created.danger_ok.id
            assert transition(root, tid, TicketState.PLANNED).is_ok
            in_progress = transition(root, tid, TicketState.IN_PROGRESS)
            assert in_progress.is_ok
            worktree_tickets[tid] = in_progress.danger_ok

        root_tickets = dict(worktree_tickets)

        call_count = 0
        real_read_all_leases = land_mod.read_all_leases

        def _counting_read_all_leases(*args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
            nonlocal call_count
            call_count += 1
            return real_read_all_leases(*args, **kwargs)

        monkeypatch.setattr(land_mod, "read_all_leases", _counting_read_all_leases)

        landing_id = "T-landing-not-a-candidate"
        # `changed_paths` empty -- every candidate's own hit computation
        # short-circuits to `None`/`()` immediately with no git spawn, so
        # this test isolates the `read_all_leases` call count from every
        # other side effect `_leaked_hits_for_candidate` could add.
        land_mod._find_leaked_tickets(
            root,
            root,
            landing_id,
            worktree_tickets,
            root_tickets,
            frozenset(),
            "HEAD",
        )

        assert call_count <= 1, (
            f"read_all_leases called {call_count} times across "
            f"{len(worktree_tickets)} candidates -- expected at most 1 "
            "(hoisted once before the loop, T-4492)"
        )

"""T-3315: `frob ticket sweep <id>` on a done/dropped ticket -- a
legitimate post-close scope correction (`frob ticket scope <id> --add
...` succeeds on an already-DONE ticket) left an operator who then tried
`sweep`, the verb every other stale-scope situation in this codebase
points at, with a hard FAST_EXIT1 refusal and no stated remedy: the
scope fix had already taken effect, but the tool demanded a command that
can never succeed for a terminal ticket. `sweep` on done/dropped is now
a genuine no-op success (exit 0); every other non-in-progress state
(queued/planned/blocked) still refuses -- those have a real remedy
`sweep` cannot substitute for."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import run as ticket_run
from frob.tickets import TicketState, drop_ticket, load_queue, transition


# frob:ticket T-3315
def _seed_ticket(tmp_path: Path) -> None:
    """A fresh queued ticket with a real scope file -- test helper only."""
    cfg = AppConfig(
        ticket_command="new",
        ticket_path=tmp_path,
        ticket_title="sweep terminal-state subject",
        ticket_kind="bug",
        ticket_scope=["src/frob/app/config.py"],
    )
    ticket_run(cfg)


# frob:ticket T-3315
class TestSweepOnTerminalState:
    """`frob ticket sweep <id>` (T-3315): a no-op success on done/dropped,
    unchanged refusal on every other non-in-progress state."""

    # frob:tests \
    # tests/unit/test_ticket_sweep_terminal_state.py::TestSweepOnTerminalState.\
    # test_sweep_on_done_ticket_is_a_quiet_success  # noqa: E501
    def test_sweep_on_done_ticket_is_a_quiet_success(
        self, tmp_path: Path, caplog
    ) -> None:
        """MUST-FIRE: `sweep` on a DONE ticket exits 0 (no SystemExit) and
        logs a plain 'nothing to sweep' line -- the exact post-close
        scope-correction dead end T-3315 exists to close.

        Writes the ticket straight to DONE via the store (not `frob
        ticket close`'s full gate suite) -- this test is about `sweep`'s
        OWN terminal-state branch, not close's evidence/mutation/
        scope-coverage guards."""
        from frob.tickets._store import write_ticket

        _seed_ticket(tmp_path)
        transition(tmp_path, "T-0001", TicketState.PLANNED)
        transition(tmp_path, "T-0001", TicketState.IN_PROGRESS)
        ticket = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        write_ticket(tmp_path, ticket.model_copy(update={"state": TicketState.DONE}))

        cfg = AppConfig(
            ticket_command="sweep", ticket_path=tmp_path, ticket_id="T-0001"
        )
        with caplog.at_level(logging.INFO):
            ticket_run(cfg)  # must NOT raise SystemExit
        assert "nothing to sweep" in caplog.text
        assert load_queue(tmp_path).danger_ok.tickets["T-0001"].state == (
            TicketState.DONE
        )

    # frob:tests \
    # tests/unit/test_ticket_sweep_terminal_state.py::TestSweepOnTerminalState.\
    # test_sweep_on_dropped_ticket_is_a_quiet_success  # noqa: E501
    def test_sweep_on_dropped_ticket_is_a_quiet_success(
        self, tmp_path: Path, caplog
    ) -> None:
        """MUST-FIRE: the same no-op success for DROPPED, the other
        terminal state."""
        _seed_ticket(tmp_path)
        transition(tmp_path, "T-0001", TicketState.PLANNED)
        transition(tmp_path, "T-0001", TicketState.IN_PROGRESS)
        dropped = drop_ticket(tmp_path, "T-0001", "superseded")
        assert dropped.is_ok, dropped

        cfg = AppConfig(
            ticket_command="sweep", ticket_path=tmp_path, ticket_id="T-0001"
        )
        with caplog.at_level(logging.INFO):
            ticket_run(cfg)  # must NOT raise SystemExit
        assert "nothing to sweep" in caplog.text

    # frob:tests \
    # tests/unit/test_ticket_sweep_terminal_state.py::TestSweepOnTerminalState.\
    # test_sweep_on_queued_ticket_still_refuses  # noqa: E501
    def test_sweep_on_queued_ticket_still_refuses(self, tmp_path: Path) -> None:
        """MUST-STAY-QUIET: `sweep` on a QUEUED ticket (never started)
        still refuses exactly as before -- only the two terminal states
        get the no-op, a not-yet-started ticket has a real "start it
        first" remedy `sweep` cannot substitute for."""
        _seed_ticket(tmp_path)
        cfg = AppConfig(
            ticket_command="sweep", ticket_path=tmp_path, ticket_id="T-0001"
        )
        with pytest.raises(SystemExit) as exc:
            ticket_run(cfg)
        assert exc.value.code == 1

    # frob:tests \
    # tests/unit/test_ticket_sweep_terminal_state.py::TestSweepOnTerminalState.\
    # test_sweep_on_in_progress_ticket_still_runs  # noqa: E501
    def test_sweep_on_in_progress_ticket_still_runs(
        self, tmp_path: Path, caplog
    ) -> None:
        """MUST-STAY-QUIET: `sweep` on an IN_PROGRESS ticket behaves
        exactly as today -- the real sweep runs, not the no-op path."""
        _seed_ticket(tmp_path)
        transition(tmp_path, "T-0001", TicketState.PLANNED)
        transition(tmp_path, "T-0001", TicketState.IN_PROGRESS)

        cfg = AppConfig(
            ticket_command="sweep", ticket_path=tmp_path, ticket_id="T-0001"
        )
        with caplog.at_level(logging.INFO):
            ticket_run(cfg)  # must NOT raise SystemExit
        assert "nothing to sweep" not in caplog.text
        assert "swept T-0001" in caplog.text

"""T-1387: end-to-end regression tests proving `own_obligations_clean`
(T-1384's guard clause) now has a live caller through the REAL `frob
ticket close`/`frob ticket reverify` paths, not just its own unit tests
(`tests/test_tickets_own_obligations.py`).

Reproduces the T-1377/T-1379/T-1381 residue class: a ticket closes clean,
then the very next unscoped `frob check` surprises with a COV001/
SELFAUDIT001/REL001 obligation this ticket's own diff left outstanding.
These tests monkeypatch the two real seams
(`frob.gitio.working_diff` and `frob.app.ticket_runner.
guarded_subprocess_run`) so no actual git diff or `frob check` spawn
happens, but otherwise drive the REAL `_close` entry point -- proving the
wiring, not re-testing the guard clause itself."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest
from typani.result import Err, Ok, Result

import frob.gitio as frob_gitio
from frob.gitio import Diff, Hunk, ProcResult

_DIRTY_COV_STDOUT = """frob check .  [FAIL]  1 errors  0 warnings

## Errors
  [gate:COV] src/frob/app/whatever.py:1  COV001  COV001: missing frob:doc edge

## Tool summary
  FAIL  gate-summary            1 errors, 0 warnings, 0 waived  [gates=1.00s]
"""

_DIRTY_SELFAUDIT_STDOUT = """frob check .  [FAIL]  1 errors  0 warnings

## Errors
  [gate:SELFAUDIT] src/frob/app/whatever.py:1  SELFAUDIT001  SELFAUDIT001: public test class not declared on testsuite

## Tool summary
  FAIL  gate-summary            1 errors, 0 warnings, 0 waived  [gates=1.00s]
"""

_CLEAN_STDOUT = """frob check .  [PASS]  0 errors  0 warnings

## Tool summary
  pass  gate-summary            0 errors, 0 warnings, 0 waived  [gates=1.00s]
"""

_TOUCHED_FILE = "src/frob/app/whatever.py"


def _diff_touching(file: str) -> Result[Diff, Any]:
    return Ok(Diff(base="abc123", hunks=(Hunk(file=file, span=(1, 5)),)))


def _write_closeable_ticket(root: Path, ticket_id: str = "T-0900") -> None:
    from frob.tickets import Origin, Ticket, TicketKind, TicketState
    from frob.tickets._store import _serialize_ticket

    ticket = Ticket(
        id=ticket_id,
        title="sample",
        state=TicketState.IN_PROGRESS,
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        evidence=("tests/test_thing.py::test_it",),
        body="## Description\nx\n\n## Done report\nDone.\n",
    )
    tickets_dir = root / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    (tickets_dir / f"{ticket_id}-sample.md").write_text(
        _serialize_ticket(ticket), encoding="utf-8"
    )


def _bypass_other_close_guards(monkeypatch: pytest.MonkeyPatch, ticket_runner) -> None:  # noqa: ANN001
    """Skip every close-time guard OTHER than T-1387's, isolating the
    refusal this test suite cares about to `own_obligations_clean` alone."""
    monkeypatch.setattr(
        ticket_runner, "_covers_scope_for_ticket", lambda root, ticket: None
    )
    monkeypatch.setattr(
        ticket_runner,
        "_close_mutation_evidence_for_ticket",
        lambda root, ticket, base_ref="main": None,
    )
    monkeypatch.setattr(
        ticket_runner, "_reverify_evidence_for_close", lambda root, ticket: None
    )
    monkeypatch.setattr(
        ticket_runner, "_close_gate_claims_for_ticket", lambda root, ticket: None
    )
    monkeypatch.setattr(
        ticket_runner, "_required_release_bump", lambda root, tid: Ok(None)
    )


class TestCloseOwnObligationsForTicket:
    """Unit-level coverage of `_close_own_obligations_for_ticket` itself."""

    def test_no_touched_files_skips_the_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket.test_no_touched_files_skips_the_check  # noqa: E501
        from frob.app import ticket_runner
        from frob.tickets import Origin, Ticket, TicketKind, TicketState

        monkeypatch.setattr(
            frob_gitio,
            "working_diff",
            lambda root, base: Ok(Diff(base="abc123", hunks=())),
        )

        def _fail_if_called(*a: Any, **k: Any) -> Any:
            raise AssertionError("no spawn expected when the diff touches nothing")

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fail_if_called)
        ticket = Ticket(
            id="T-0001",
            title="t",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            state=TicketState.IN_PROGRESS,
            evidence=("tests/test_x.py::test_x",),
        )
        result = ticket_runner._close_own_obligations_for_ticket(tmp_path, ticket)
        assert result is None

    def test_diff_unavailable_skips_the_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket.test_diff_unavailable_skips_the_check  # noqa: E501
        from frob.app import ticket_runner
        from frob.gitio import GitError
        from frob.tickets import Origin, Ticket, TicketKind, TicketState

        monkeypatch.setattr(
            frob_gitio, "working_diff", lambda root, base: Err(GitError.NotARepo)
        )
        ticket = Ticket(
            id="T-0001",
            title="t",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            state=TicketState.IN_PROGRESS,
            evidence=("tests/test_x.py::test_x",),
        )
        result = ticket_runner._close_own_obligations_for_ticket(tmp_path, ticket)
        assert result is None

    def test_dirty_cov001_under_touched_file_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket.test_dirty_cov001_under_touched_file_returns_false  # noqa: E501
        from frob.app import ticket_runner
        from frob.tickets import Origin, Ticket, TicketKind, TicketState

        monkeypatch.setattr(
            frob_gitio, "working_diff", lambda root, base: _diff_touching(_TOUCHED_FILE)
        )
        monkeypatch.setattr(
            ticket_runner, "_required_release_bump", lambda root, tid: Ok(None)
        )

        def _fake(argv: list[str], **kwargs: Any) -> Result[ProcResult, Any]:
            return Ok(
                ProcResult(
                    argv=tuple(argv), returncode=1, stdout=_DIRTY_COV_STDOUT, stderr=""
                )
            )

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)
        ticket = Ticket(
            id="T-0001",
            title="t",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            state=TicketState.IN_PROGRESS,
            evidence=("tests/test_x.py::test_x",),
        )
        result = ticket_runner._close_own_obligations_for_ticket(tmp_path, ticket)
        assert result is False

    def test_dirty_selfaudit001_under_touched_file_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket.test_dirty_selfaudit001_under_touched_file_returns_false  # noqa: E501
        from frob.app import ticket_runner
        from frob.tickets import Origin, Ticket, TicketKind, TicketState

        monkeypatch.setattr(
            frob_gitio, "working_diff", lambda root, base: _diff_touching(_TOUCHED_FILE)
        )
        monkeypatch.setattr(
            ticket_runner, "_required_release_bump", lambda root, tid: Ok(None)
        )

        def _fake(argv: list[str], **kwargs: Any) -> Result[ProcResult, Any]:
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=1,
                    stdout=_DIRTY_SELFAUDIT_STDOUT,
                    stderr="",
                )
            )

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)
        ticket = Ticket(
            id="T-0001",
            title="t",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            state=TicketState.IN_PROGRESS,
            evidence=("tests/test_x.py::test_x",),
        )
        result = ticket_runner._close_own_obligations_for_ticket(tmp_path, ticket)
        assert result is False

    def test_rel001_bump_outstanding_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket.test_rel001_bump_outstanding_returns_false  # noqa: E501
        from frob.app import ticket_runner
        from frob.tickets import Origin, Ticket, TicketKind, TicketState

        monkeypatch.setattr(
            frob_gitio, "working_diff", lambda root, base: _diff_touching(_TOUCHED_FILE)
        )
        monkeypatch.setattr(
            ticket_runner, "_required_release_bump", lambda root, tid: Ok("1.2.0")
        )

        def _fake(argv: list[str], **kwargs: Any) -> Result[ProcResult, Any]:
            return Ok(
                ProcResult(
                    argv=tuple(argv), returncode=0, stdout=_CLEAN_STDOUT, stderr=""
                )
            )

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)
        ticket = Ticket(
            id="T-0001",
            title="t",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            state=TicketState.IN_PROGRESS,
            evidence=("tests/test_x.py::test_x",),
        )
        result = ticket_runner._close_own_obligations_for_ticket(tmp_path, ticket)
        assert result is False

    def test_clean_diff_and_no_bump_returns_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket.test_clean_diff_and_no_bump_returns_true  # noqa: E501
        from frob.app import ticket_runner
        from frob.tickets import Origin, Ticket, TicketKind, TicketState

        monkeypatch.setattr(
            frob_gitio, "working_diff", lambda root, base: _diff_touching(_TOUCHED_FILE)
        )
        monkeypatch.setattr(
            ticket_runner, "_required_release_bump", lambda root, tid: Ok(None)
        )

        def _fake(argv: list[str], **kwargs: Any) -> Result[ProcResult, Any]:
            return Ok(
                ProcResult(
                    argv=tuple(argv), returncode=0, stdout=_CLEAN_STDOUT, stderr=""
                )
            )

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)
        ticket = Ticket(
            id="T-0001",
            title="t",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            state=TicketState.IN_PROGRESS,
            evidence=("tests/test_x.py::test_x",),
        )
        result = ticket_runner._close_own_obligations_for_ticket(tmp_path, ticket)
        assert result is True


# frob:ticket T-1387
class TestCloseRefusesOwnObligationsEndToEnd:
    """Drives the REAL `frob ticket close` entry point against a ticket
    whose own diff leaves a COV001 obligation outstanding -- the T-1377/
    T-1379/T-1381 residue class: attempt to close through the real close
    path and confirm it now refuses, where before T-1387 it silently
    closed done."""

    def test_close_refuses_when_own_diff_leaves_cov001_outstanding(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseRefusesOwnObligationsEndToEnd.test_close_refuses_when_own_diff_leaves_cov001_outstanding  # noqa: E501
        from frob.app import ticket_runner
        from frob.app.config import AppConfig
        from frob.tickets import TicketState, load_all

        _write_closeable_ticket(tmp_path)
        _bypass_other_close_guards(monkeypatch, ticket_runner)
        monkeypatch.setattr(
            frob_gitio, "working_diff", lambda root, base: _diff_touching(_TOUCHED_FILE)
        )
        monkeypatch.setattr(
            ticket_runner,
            "guarded_subprocess_run",
            lambda argv, **k: Ok(
                ProcResult(
                    argv=tuple(argv), returncode=1, stdout=_DIRTY_COV_STDOUT, stderr=""
                )
            ),
        )
        cfg = AppConfig(ticket_id="T-0900")
        with pytest.raises(SystemExit):
            ticket_runner._close(tmp_path, cfg)
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0900"].state == TicketState.IN_PROGRESS

    def test_close_succeeds_once_the_diff_is_actually_clean(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseRefusesOwnObligationsEndToEnd.test_close_succeeds_once_the_diff_is_actually_clean  # noqa: E501
        from frob.app import ticket_runner
        from frob.app.config import AppConfig
        from frob.tickets import TicketState, load_all

        _write_closeable_ticket(tmp_path)
        _bypass_other_close_guards(monkeypatch, ticket_runner)
        monkeypatch.setattr(
            frob_gitio, "working_diff", lambda root, base: _diff_touching(_TOUCHED_FILE)
        )
        monkeypatch.setattr(
            ticket_runner,
            "guarded_subprocess_run",
            lambda argv, **k: Ok(
                ProcResult(
                    argv=tuple(argv), returncode=0, stdout=_CLEAN_STDOUT, stderr=""
                )
            ),
        )
        cfg = AppConfig(ticket_id="T-0900")
        ticket_runner._close(tmp_path, cfg)
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0900"].state == TicketState.DONE

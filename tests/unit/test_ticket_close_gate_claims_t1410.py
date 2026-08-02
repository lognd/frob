"""T-1410: end-to-end regression tests proving `gate_claims_verified`
(T-1399's guard clause) now has a live caller through the REAL `frob
ticket close`/`frob ticket land` paths, not just its own unit tests
(`tests/test_tickets_gate_claim_evidence.py`).

Reproduces the T-1276 shape precisely: an acceptance criterion asserting
"0 TEST005 findings under src/frob/app/**" bound to a passing but
UNRELATED evidence id. Before this fix, `_close_guards_for_ticket`/
`land()` never computed `gate_claims_verified` at all (always `None`,
fully permissive) -- T-1276 itself closed done and landed (LAND-PROOF
verified) against 116 live TEST005 findings under that exact glob. These
tests monkeypatch the one real subprocess seam
(`frob.app.ticket_runner.guarded_subprocess_run`) so no actual `frob
check` spawn happens, but otherwise drive the REAL `_close`/`land` entry
points -- proving the wiring, not re-testing the guard clause itself."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest
from typani.result import Err, Ok, Result

from frob.gitio import ProcResult

_T1276_CRITERION_TEXT = (
    "GIVEN the app package at the 75%/70% floors WHEN frob check --only "
    "test runs THEN it reports 0 TEST005 findings under src/frob/app/**"
)

_UNRELATED_EVIDENCE = "tests/unit/test_doctor_runner_t1276.py::test_smoke"

_DIRTY_GATES_STDOUT = """frob check .  [FAIL]  1 errors  0 warnings

## Errors
  [gate:TEST] src/frob/app/whatever.py:1  TEST005  TEST005: undercovered

## Tool summary
  FAIL  gate-summary            1 errors, 0 warnings, 0 waived  [gates=1.00s]
"""

_CLEAN_GATES_STDOUT = """frob check .  [PASS]  0 errors  0 warnings

## Tool summary
  pass  gate-summary            0 errors, 0 warnings, 0 waived  [gates=1.00s]
"""


def _write_t1276_shaped_ticket(root: Path, ticket_id: str = "T-0900") -> None:
    """A ticket carrying T-1276's exact criterion shape, closeable on
    every OTHER guard (non-security kind, has evidence + Done report,
    acceptance bound to an unrelated-but-passing evidence id)."""
    from frob.tickets import (
        AcceptanceCriterion,
        Origin,
        Ticket,
        TicketKind,
        TicketState,
    )
    from frob.tickets._store import _serialize_ticket

    criterion = AcceptanceCriterion(
        text=_T1276_CRITERION_TEXT, evidence=(_UNRELATED_EVIDENCE,)
    )
    ticket = Ticket(
        id=ticket_id,
        title="sample",
        state=TicketState.IN_PROGRESS,
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        evidence=(_UNRELATED_EVIDENCE,),
        acceptance=(criterion,),
        body="## Description\nx\n\n## Done report\nDone.\n",
    )
    tickets_dir = root / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    (tickets_dir / f"{ticket_id}-sample.md").write_text(
        _serialize_ticket(ticket), encoding="utf-8"
    )


def _bypass_other_close_guards(monkeypatch: pytest.MonkeyPatch, ticket_runner) -> None:  # noqa: ANN001
    """Skip every close-time guard OTHER than T-1410's, isolating the
    refusal this test suite cares about to `gate_claims_verified` alone."""
    monkeypatch.setattr(
        ticket_runner, "_covers_scope_for_ticket", lambda root, ticket: None
    )
    monkeypatch.setattr(
        ticket_runner, "_close_mutation_evidence_for_ticket", lambda root, ticket: None
    )
    monkeypatch.setattr(
        ticket_runner, "_reverify_evidence_for_close", lambda root, ticket: None
    )


class TestCloseGateClaimsForTicket:
    """Unit-level coverage of `_close_gate_claims_for_ticket` itself: the
    T-1410 helper `_close_guards_for_ticket` now always computes."""

    def _patch_spawn(
        self,
        monkeypatch: pytest.MonkeyPatch,
        ticket_runner,
        stdout: str,  # noqa: ANN001
    ) -> None:
        def _fake(argv: list[str], **kwargs: Any) -> Result[ProcResult, Any]:
            assert argv[-2:] == ["--only", "gates"]
            return Ok(
                ProcResult(argv=tuple(argv), returncode=0, stdout=stdout, stderr="")
            )

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fake)

    def test_no_gate_claim_criterion_skips_the_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseGateClaimsForTicket.test_no_gate_claim_criterion_skips_the_check  # noqa: E501
        from frob.app import ticket_runner
        from frob.tickets import (
            AcceptanceCriterion,
            Origin,
            Ticket,
            TicketKind,
            TicketState,
        )

        def _fail_if_called(*a: Any, **k: Any) -> Any:
            raise AssertionError(
                "no spawn expected when no gate-claim criterion exists"
            )

        monkeypatch.setattr(ticket_runner, "guarded_subprocess_run", _fail_if_called)
        ticket = Ticket(
            id="T-0001",
            title="t",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            state=TicketState.IN_PROGRESS,
            evidence=("tests/test_x.py::test_x",),
            acceptance=(AcceptanceCriterion(text="an ordinary criterion"),),
        )
        result = ticket_runner._close_gate_claims_for_ticket(tmp_path, ticket)
        assert result is None

    def test_live_finding_under_the_named_glob_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseGateClaimsForTicket.test_live_finding_under_the_named_glob_returns_false  # noqa: E501
        from frob.app import ticket_runner
        from frob.tickets import (
            AcceptanceCriterion,
            Origin,
            Ticket,
            TicketKind,
            TicketState,
        )

        self._patch_spawn(monkeypatch, ticket_runner, _DIRTY_GATES_STDOUT)
        ticket = Ticket(
            id="T-0001",
            title="t",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            state=TicketState.IN_PROGRESS,
            evidence=(_UNRELATED_EVIDENCE,),
            acceptance=(
                AcceptanceCriterion(
                    text=_T1276_CRITERION_TEXT, evidence=(_UNRELATED_EVIDENCE,)
                ),
            ),
        )
        result = ticket_runner._close_gate_claims_for_ticket(tmp_path, ticket)
        assert result is False

    def test_no_matching_finding_returns_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseGateClaimsForTicket.test_no_matching_finding_returns_true  # noqa: E501
        from frob.app import ticket_runner
        from frob.tickets import (
            AcceptanceCriterion,
            Origin,
            Ticket,
            TicketKind,
            TicketState,
        )

        self._patch_spawn(monkeypatch, ticket_runner, _CLEAN_GATES_STDOUT)
        ticket = Ticket(
            id="T-0001",
            title="t",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            state=TicketState.IN_PROGRESS,
            evidence=(_UNRELATED_EVIDENCE,),
            acceptance=(
                AcceptanceCriterion(
                    text=_T1276_CRITERION_TEXT, evidence=(_UNRELATED_EVIDENCE,)
                ),
            ),
        )
        result = ticket_runner._close_gate_claims_for_ticket(tmp_path, ticket)
        assert result is True

    def test_refused_spawn_fails_closed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseGateClaimsForTicket.test_refused_spawn_fails_closed  # noqa: E501
        from frob.app import ticket_runner
        from frob.process._guard import ProcessGuardError
        from frob.tickets import (
            AcceptanceCriterion,
            Origin,
            Ticket,
            TicketKind,
            TicketState,
        )

        monkeypatch.setattr(
            ticket_runner,
            "guarded_subprocess_run",
            lambda *a, **k: Err(ProcessGuardError.ExecDisabled),
        )
        ticket = Ticket(
            id="T-0001",
            title="t",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            state=TicketState.IN_PROGRESS,
            evidence=(_UNRELATED_EVIDENCE,),
            acceptance=(
                AcceptanceCriterion(
                    text=_T1276_CRITERION_TEXT, evidence=(_UNRELATED_EVIDENCE,)
                ),
            ),
        )
        result = ticket_runner._close_gate_claims_for_ticket(tmp_path, ticket)
        assert result is False


# frob:ticket T-1410
class TestCloseRefusesT1276ShapeEndToEnd:
    """Drives the REAL `frob ticket close` entry point (`ticket_runner.
    _close`) against a T-1276-shaped ticket -- the acceptance test this
    series exists for: attempt to close a ticket carrying an unmet "0
    findings" criterion through the real close path and confirm it now
    refuses, where before T-1410 it silently closed done."""

    def test_close_refuses_when_live_findings_remain_under_the_glob(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseRefusesT1276ShapeEndToEnd.test_close_refuses_when_live_findings_remain_under_the_glob  # noqa: E501
        from frob.app import ticket_runner
        from frob.app.config import AppConfig
        from frob.tickets import TicketState, load_all

        _write_t1276_shaped_ticket(tmp_path)
        _bypass_other_close_guards(monkeypatch, ticket_runner)
        monkeypatch.setattr(
            ticket_runner,
            "guarded_subprocess_run",
            lambda argv, **k: Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=1,
                    stdout=_DIRTY_GATES_STDOUT,
                    stderr="",
                )
            ),
        )
        cfg = AppConfig(ticket_id="T-0900")
        with pytest.raises(SystemExit):
            ticket_runner._close(tmp_path, cfg)
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0900"].state == TicketState.IN_PROGRESS

    def test_close_succeeds_once_the_glob_is_actually_clean(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseRefusesT1276ShapeEndToEnd.test_close_succeeds_once_the_glob_is_actually_clean  # noqa: E501
        from frob.app import ticket_runner
        from frob.app.config import AppConfig
        from frob.tickets import TicketState, load_all

        _write_t1276_shaped_ticket(tmp_path)
        _bypass_other_close_guards(monkeypatch, ticket_runner)
        monkeypatch.setattr(
            ticket_runner,
            "guarded_subprocess_run",
            lambda argv, **k: Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=0,
                    stdout=_CLEAN_GATES_STDOUT,
                    stderr="",
                )
            ),
        )
        cfg = AppConfig(ticket_id="T-0900")
        ticket_runner._close(tmp_path, cfg)
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0900"].state == TicketState.DONE

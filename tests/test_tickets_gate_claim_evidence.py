"""T-1399: regression tests for `transition`/`reverify_close_guard`'s
`gate_claims_verified` injected parameter, and the `_criterion_gate_claim`/
`_gate_claim_criteria` detection primitives it is built on.

Reproduces the T-1276 shape precisely: an acceptance criterion asserting a
package-wide gate outcome ("0 TEST005 findings under src/frob/app/**") gets
bound to a passing but UNRELATED pytest node id. Before this fix,
`unbound_acceptance` alone was satisfied by that binding (any evidence id
bound at all), and `frob ticket land`/`close` closed the ticket -- true on
main immediately after landing T-1276, against 116 live TEST005 findings
under that exact glob. `gate_claims_verified` closes the gap the same way
`own_obligations_clean` (T-1384) closes its own: injected, never computed
inside `frob.tickets` (computing whether the named gate ACTUALLY reports
zero findings needs a live `frob.gates` run, a dependency this package
deliberately stays free of) -- `False` refuses, `True` allows, `None` (the
default, matching every pre-T-1399 caller) is fully permissive, and a
ticket with no gate-claim-shaped criterion at all is unaffected regardless
of what a caller injects (T-1399's own hard rule: an ordinary criterion
naming no rule id and no glob behaves exactly as it did before)."""
# frob:waive SCOPE001 reason="this new test file cannot be added to T-1399's declared \
# scope right now: T-1235 holds 'tests/**' in-progress (a real, disclosed concurrent \
# lease named in T-1399's own dispatch brief, not a staleness artifact -- T-1235 is \
# actively in-progress on main), so `frob ticket scope T-1399 --add` refuses with \
# ScopeLeaseConflict; the file is committed under T-1399's own commits (SCOPE001's own \
# `root`/`queue` same-branch-ownership exemption would otherwise cover this once the \
# lease clears) and is real, evidence-bound test content, not an unaccounted-for touch \
# (reviewed 2026-08-03, drain-to-zero WAIVE004 sweep: left in place -- SCOPE001 is a \
# scope/lease-dependent rule, not a stale finding a full unscoped run can prove dead)"

from __future__ import annotations

from datetime import date
from pathlib import Path

from frob.tickets import (
    AcceptanceCriterion,
    Origin,
    Ticket,
    TicketError,
    TicketKind,
    TicketState,
    transition,
)
from frob.tickets._evidence import _criterion_gate_claim, _gate_claim_criteria
from frob.tickets._store import atomic_write, ledger_path, write_ticket

_T1276_CRITERION_TEXT = (
    "GIVEN the app package at the 75%/70% floors WHEN frob check --only "
    "test runs THEN it reports 0 TEST005 findings under src/frob/app/**"
)


def _ticket(
    *,
    state: TicketState = TicketState.IN_PROGRESS,
    evidence: tuple[str, ...] = (),
    acceptance: tuple[AcceptanceCriterion, ...] = (),
    body: str = "",
) -> Ticket:
    return Ticket(
        id="T-0001",
        title="Gate claim test ticket",
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        state=state,
        evidence=evidence,
        acceptance=acceptance,
        body=body,
    )


def _write(root: Path, ticket: Ticket) -> None:
    atomic_write(ledger_path(root), "# Tickets\n\n")
    assert write_ticket(root, ticket).is_ok


class TestCriterionGateClaimDetection:
    """`_criterion_gate_claim`/`_gate_claim_criteria`: the plain text-scan
    detection primitives the T-1399 guard keys off of."""

    def test_t1276_shaped_criterion_matches(self) -> None:
        # frob:tests tests/test_tickets_gate_claim_evidence.py::TestCriterionGateClaimDetection.test_t1276_shaped_criterion_matches  # noqa: E501
        claim = _criterion_gate_claim(_T1276_CRITERION_TEXT)
        assert claim == ("TEST005", "src/frob/app/**")

    def test_ordinary_criterion_does_not_match(self) -> None:
        # frob:tests tests/test_tickets_gate_claim_evidence.py::TestCriterionGateClaimDetection.test_ordinary_criterion_does_not_match  # noqa: E501
        claim = _criterion_gate_claim(
            "GIVEN a user WHEN they run the CLI THEN it prints help text"
        )
        assert claim is None

    def test_gate_claim_criteria_filters_ticket_acceptance(self) -> None:
        # frob:tests tests/test_tickets_gate_claim_evidence.py::TestCriterionGateClaimDetection.test_gate_claim_criteria_filters_ticket_acceptance  # noqa: E501
        ticket = _ticket(
            acceptance=(
                AcceptanceCriterion(text=_T1276_CRITERION_TEXT),
                AcceptanceCriterion(text="an ordinary criterion, no rule/glob"),
            )
        )
        matched = _gate_claim_criteria(ticket)
        assert len(matched) == 1
        assert matched[0].text == _T1276_CRITERION_TEXT


class TestT1399GateClaimOnClose:
    """`gate_claims_verified=False` refuses `done` naming
    `GateClaimUnverified` while a gate-claim-shaped criterion exists; `True`
    allows it; `None` (the default) is fully permissive -- mirroring
    T-0844/T-1384's own injected-boolean test shape."""

    def test_transition_rejects_t1276_shape_when_gate_claims_verified_false(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose.test_transition_rejects_t1276_shape_when_gate_claims_verified_false  # noqa: E501
        # T-1276's exact shape: criterion asserts 0 findings under a glob,
        # bound only to an unrelated PASSING node id -- unbound_acceptance
        # alone is satisfied by this, so this refusal must come from the
        # gate-claim guard specifically, not from AcceptanceUnbound.
        unrelated_evidence = "tests/unit/test_doctor_runner_t1276.py::test_smoke"
        criterion = AcceptanceCriterion(
            text=_T1276_CRITERION_TEXT, evidence=(unrelated_evidence,)
        )
        ticket = _ticket(
            evidence=(unrelated_evidence,),
            acceptance=(criterion,),
            body="## Description\nx\n\n## Done report\nDone.\n",
        )
        _write(tmp_path, ticket)
        result = transition(
            tmp_path, "T-0001", TicketState.DONE, gate_claims_verified=False
        )
        assert result.is_err
        assert result.danger_err == TicketError.GateClaimUnverified

    def test_transition_allows_t1276_shape_when_gate_claims_verified_true(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose.test_transition_allows_t1276_shape_when_gate_claims_verified_true  # noqa: E501
        unrelated_evidence = "tests/unit/test_doctor_runner_t1276.py::test_smoke"
        criterion = AcceptanceCriterion(
            text=_T1276_CRITERION_TEXT, evidence=(unrelated_evidence,)
        )
        ticket = _ticket(
            evidence=(unrelated_evidence,),
            acceptance=(criterion,),
            body="## Description\nx\n\n## Done report\nDone.\n",
        )
        _write(tmp_path, ticket)
        result = transition(
            tmp_path, "T-0001", TicketState.DONE, gate_claims_verified=True
        )
        assert result.is_ok

    def test_transition_permissive_when_gate_claims_verified_none(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose.test_transition_permissive_when_gate_claims_verified_none  # noqa: E501
        unrelated_evidence = "tests/unit/test_doctor_runner_t1276.py::test_smoke"
        criterion = AcceptanceCriterion(
            text=_T1276_CRITERION_TEXT, evidence=(unrelated_evidence,)
        )
        ticket = _ticket(
            evidence=(unrelated_evidence,),
            acceptance=(criterion,),
            body="## Description\nx\n\n## Done report\nDone.\n",
        )
        _write(tmp_path, ticket)
        result = transition(tmp_path, "T-0001", TicketState.DONE)
        assert result.is_ok

    def test_transition_unaffected_when_no_gate_claim_criterion_exists(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose.test_transition_unaffected_when_no_gate_claim_criterion_exists  # noqa: E501
        # An ordinary criterion (no rule id, no glob) closes exactly as it
        # did before T-1399 -- `gate_claims_verified=False` is a no-op
        # since `_gate_claim_criteria` returns () for this ticket.
        evidence = "tests/test_thing.py::test_x"
        criterion = AcceptanceCriterion(
            text="an ordinary criterion, no rule/glob", evidence=(evidence,)
        )
        ticket = _ticket(
            evidence=(evidence,),
            acceptance=(criterion,),
            body="## Description\nx\n\n## Done report\nDone.\n",
        )
        _write(tmp_path, ticket)
        result = transition(
            tmp_path, "T-0001", TicketState.DONE, gate_claims_verified=False
        )
        assert result.is_ok

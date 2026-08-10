"""T-1556: `_close_failure_hint`'s extended `TicketError` coverage --
EvidenceScopeUnbound/EvidenceNotPassing/OwnObligationsUnclean/
GateClaimUnverified/LiveTrackerCited/NewGateRuleUnaccepted all used to
fall through to the generic "<verb> failed: <err>" line with no concrete
next command, unlike InvalidTransition/MissingEvidence/AcceptanceUnbound/
MissingApprovedReview/EvidenceConfirmatoryOnly, which already had one.
Each case here proves the hint names a real `frob ticket <verb>` command
line (not just echoing the raw error), and that the generic fallback
still applies to anything not explicitly handled."""

from __future__ import annotations

from frob.app.ticket_runner._close_cmd import _close_failure_hint
from frob.tickets import TicketError, TicketState


def test_evidence_scope_unbound_names_evidence_and_scope_commands() -> None:
    hint = _close_failure_hint(
        "T-0001", TicketState.IN_PROGRESS, TicketError.EvidenceScopeUnbound
    )
    assert "frob ticket evidence T-0001" in hint
    assert "frob ticket scope T-0001" in hint


def test_evidence_not_passing_names_evidence_command() -> None:
    hint = _close_failure_hint(
        "T-0001", TicketState.IN_PROGRESS, TicketError.EvidenceNotPassing
    )
    assert "frob ticket evidence T-0001" in hint
    assert "frob ticket close T-0001" in hint


def test_own_obligations_unclean_names_check_delta_command() -> None:
    hint = _close_failure_hint(
        "T-0001", TicketState.IN_PROGRESS, TicketError.OwnObligationsUnclean
    )
    assert "frob check --delta --ticket T-0001" in hint


def test_gate_claim_unverified_names_close_retry() -> None:
    hint = _close_failure_hint(
        "T-0001", TicketState.IN_PROGRESS, TicketError.GateClaimUnverified
    )
    assert "frob ticket close T-0001" in hint


def test_live_tracker_cited_names_successor_ticket_remedy() -> None:
    hint = _close_failure_hint(
        "T-0001", TicketState.IN_PROGRESS, TicketError.LiveTrackerCited
    )
    assert "file a successor ticket" in hint
    assert "frob ticket close T-0001" in hint


def test_new_gate_rule_unaccepted_names_accept_and_evidence_commands() -> None:
    hint = _close_failure_hint(
        "T-0001", TicketState.IN_PROGRESS, TicketError.NewGateRuleUnaccepted
    )
    assert "frob ticket accept T-0001" in hint
    assert "frob ticket evidence T-0001" in hint


def test_reverify_verb_is_threaded_through_new_cases() -> None:
    hint = _close_failure_hint(
        "T-0001",
        TicketState.DONE,
        TicketError.OwnObligationsUnclean,
        verb="reverify",
    )
    assert "frob ticket reverify T-0001" in hint
    assert "reverify failed" in hint


def test_unhandled_error_still_falls_back_to_generic_message() -> None:
    """A case this function does NOT special-case (e.g. NotFound, never
    reachable from close/reverify in practice) must still produce SOME
    message rather than raising -- the generic fallback stays live."""
    hint = _close_failure_hint("T-0001", TicketState.QUEUED, TicketError.NotFound)
    assert "close failed" in hint
    assert "NotFound" in hint or str(TicketError.NotFound) in hint

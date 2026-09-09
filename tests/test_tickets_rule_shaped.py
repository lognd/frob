"""Unit tests for T-4037: `rule_shaped_findings_unresolved` -- a ticket
whose `findings` name a rule id absent from the loaded gate/policy
registry (`frob.gates.known_gate_rule_ids`) is rule-shaped-but-unshipped,
the exact T-3942 failure mode (an audit finding whose remediation is a
policy/gate rule, closed by hand-fixing the cited instances instead of
shipping the rule) this function exists to surface.
"""

from __future__ import annotations

from datetime import date

from frob.gates import known_gate_rule_ids
from frob.tickets import Origin, Ticket, TicketKind, TicketState
from frob.tickets._models import rule_shaped_findings_unresolved


def _ticket(*, findings: tuple[tuple[str, str], ...] = ()) -> Ticket:
    """One minimal, valid `Ticket` with `findings` set -- every other field
    at its ordinary default, since only `findings` is under test here."""
    return Ticket(
        id="T-0001",
        title="rule-shaped subject",
        state=TicketState.IN_PROGRESS,
        kind=TicketKind.SECURITY,
        origin=Origin.AGENT,
        created=date(2026, 1, 1),
        findings=findings,
    )


class TestRuleShapedFindingsUnresolved:
    """`rule_shaped_findings_unresolved` -- T-4037's close-time mechanism."""

    def test_empty_is_ok(self) -> None:
        """MUST-STAY-QUIET: no `findings` at all -- an ordinary ticket,
        not rule-shaped, never blocked by this check."""
        assert rule_shaped_findings_unresolved(_ticket()) == ()

    def test_loaded_resolves(self) -> None:
        """MUST-STAY-QUIET: a `findings` entry naming a rule id that IS in
        the loaded registry resolves cleanly -- a real gate rule id (any
        stable, always-loaded one) picked from the live registry itself
        so this test never hardcodes a rule id that could be renamed."""
        known = known_gate_rule_ids()
        assert known, "known_gate_rule_ids() must not be empty in this repo"
        real_rule_id = sorted(known)[0]
        ticket = _ticket(findings=((real_rule_id, "src/frob/x.py"),))
        assert rule_shaped_findings_unresolved(ticket) == ()

    def test_unloaded_unresolved(self) -> None:
        """MUST-FIRE: a `findings` entry naming a rule id NOT in the
        loaded registry (a made-up id no gate/policy could ever emit)
        comes back as unresolved -- the T-4037 refusal signal."""
        fake_rule_id = "ZZZZ999"
        assert fake_rule_id not in known_gate_rule_ids()
        ticket = _ticket(findings=((fake_rule_id, "src/frob/x.py"),))
        assert rule_shaped_findings_unresolved(ticket) == (fake_rule_id,)

    def test_mixed_findings_reports_only_the_unresolved_ones(self) -> None:
        """A ticket citing BOTH a real and a fake rule id: the result names
        only the fake one, sorted, de-duplicated -- not the whole set."""
        known = known_gate_rule_ids()
        real_rule_id = sorted(known)[0]
        ticket = _ticket(
            findings=(
                (real_rule_id, "src/frob/a.py"),
                ("ZZZZ998", "src/frob/b.py"),
                ("ZZZZ998", "src/frob/c.py"),
            )
        )
        assert rule_shaped_findings_unresolved(ticket) == ("ZZZZ998",)

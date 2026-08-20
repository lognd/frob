"""T-1549: `_reverify_gate_findings_by_identity` must never treat the
`GateError.QueueUnavailable` sentinel Diagnostic (`Diagnostic(file=
"tickets.md", ...)`, no `code=`, produced by `frob.check._python.
_gates_error_result`) as a real gate finding.

Real incident this reproduces: a ticket burned FOUR land attempts on a
`ClaimDivergence` refusal naming an EMPTY rule id against `tickets.md`.
`scope_matches` treats `tickets.md`/`LEDGER_PATH` as implicitly in scope
for every ticket, so this identity-less sentinel used to reach
`scoped_new` unconditionally and refuse EVERY land while the ticket
queue happened to fail to load -- an unmeasurable upstream failure, not
a stale claim, so the documented `frob ticket done-report` recap recipe
(T-1531) could never fix it (the refresh's own capture run hits the
identical queue failure).
"""

from __future__ import annotations

from pathlib import Path

from frob.tickets import Origin, TicketKind, new_ticket
from frob.tickets._land_verify import _reverify_gate_findings_by_identity
from frob.tickets._models import DoneReportClaims, TicketSpec


def _make_ticket(tmp_path: Path, *, scope: tuple[str, ...]):
    """Seed a single real, queued ticket with the given scope -- mirrors
    the `_make_ticket` fixture pattern already used across this repo's
    test suite (see tests/unit/test_ticket_file_flags.py)."""
    spec = TicketSpec(
        title="seed",
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        scope=scope,
    )
    return new_ticket(tmp_path, spec).danger_ok


class TestQueueUnavailableSentinelIsExcludedFromDivergence:
    # frob:tests tests/unit/test_land_verify_claim_divergence_sentinel.py::TestQueueUnavailableSentinelIsExcludedFromDivergence.test_sentinel_alone_does_not_refuse  # noqa: E501
    # frob:tests src/frob/tickets/_land_verify.py::_reverify_gate_findings_by_identity kind="unit"  # noqa: E501
    # frob:ticket T-1549
    def test_sentinel_alone_does_not_refuse(self, tmp_path: Path) -> None:
        """Positive control for the fix: the exact sentinel shape
        (empty rule id, file="tickets.md") as the ONLY new finding must
        NOT refuse the land."""
        ticket = _make_ticket(tmp_path, scope=("src/frob/tickets/**",))
        claims = DoneReportClaims(
            test_count=1,
            evidence_count=1,
            gate_errors=0,
            gate_warnings=0,
            gate_waived=0,
            error_findings=frozenset(),
        )
        result = _reverify_gate_findings_by_identity(
            ticket,
            claims,
            ticket.id,
            check_gate_findings=lambda: frozenset({("", "tickets.md")}),
        )
        assert result is not None
        assert result.is_ok

    # frob:tests tests/unit/test_land_verify_claim_divergence_sentinel.py::TestQueueUnavailableSentinelIsExcludedFromDivergence.test_real_new_in_scope_finding_still_refuses  # noqa: E501
    def test_real_new_in_scope_finding_still_refuses(self, tmp_path: Path) -> None:
        """Negative control: a REAL new in-scope finding (a non-empty
        rule id) must still refuse -- the sentinel filter must not
        mask a genuine regression."""
        ticket = _make_ticket(tmp_path, scope=("src/frob/tickets/**",))
        claims = DoneReportClaims(
            test_count=1,
            evidence_count=1,
            gate_errors=0,
            gate_warnings=0,
            gate_waived=0,
            error_findings=frozenset(),
        )
        result = _reverify_gate_findings_by_identity(
            ticket,
            claims,
            ticket.id,
            check_gate_findings=lambda: frozenset(
                {("ARCH001", "src/frob/tickets/_land.py")}
            ),
        )
        assert result is not None
        assert result.is_err

    # frob:tests tests/unit/test_land_verify_claim_divergence_sentinel.py::TestQueueUnavailableSentinelIsExcludedFromDivergence.test_sentinel_plus_real_finding_still_refuses_on_the_real_one  # noqa: E501
    def test_sentinel_plus_real_finding_still_refuses_on_the_real_one(
        self, tmp_path: Path
    ) -> None:
        """Both at once: the sentinel is excluded, but a genuine
        co-occurring finding still refuses -- the filter narrows what
        counts as a finding, it does not disable the check."""
        ticket = _make_ticket(tmp_path, scope=("src/frob/tickets/**",))
        claims = DoneReportClaims(
            test_count=1,
            evidence_count=1,
            gate_errors=0,
            gate_warnings=0,
            gate_waived=0,
            error_findings=frozenset(),
        )
        result = _reverify_gate_findings_by_identity(
            ticket,
            claims,
            ticket.id,
            check_gate_findings=lambda: frozenset(
                {
                    ("", "tickets.md"),
                    ("ARCH001", "src/frob/tickets/_land.py"),
                }
            ),
        )
        assert result is not None
        assert result.is_err


# frob:ticket T-2684
class TestQueue001CodedSentinelIsAlsoExcluded:
    """T-2684: `_gates_error_result` now sets a real `code="QUEUE001"`
    (and `file=None`) on the QueueUnavailable sentinel instead of the
    old empty-rule-id/`file="tickets.md"` shape -- the exclusion above
    must recognize this new shape too, or T-2684's own fix silently
    reintroduces the T-1549 bug it is supposed to leave fixed."""

    # frob:tests \
    # tests/unit/test_land_verify_claim_divergence_sentinel.py::TestQueue001CodedSentinelIsAlsoExcluded.test_queue001_coded_sentinel_does_not_refuse  # noqa: E501
    def test_queue001_coded_sentinel_does_not_refuse(self, tmp_path: Path) -> None:
        """Positive control (T-2684 shape): a `("QUEUE001", "")` finding
        as the ONLY new finding must NOT refuse the land, same as the old
        empty-rule-id shape did before this ticket."""
        ticket = _make_ticket(tmp_path, scope=("src/frob/tickets/**",))
        claims = DoneReportClaims(
            test_count=1,
            evidence_count=1,
            gate_errors=0,
            gate_warnings=0,
            gate_waived=0,
            error_findings=frozenset(),
        )
        result = _reverify_gate_findings_by_identity(
            ticket,
            claims,
            ticket.id,
            check_gate_findings=lambda: frozenset({("QUEUE001", "")}),
        )
        assert result is not None
        assert result.is_ok

"""Tests for frob.gates._mutation_evidence (T-0755): TEST016 severity
resolution over `frob.tickets._mutation_evidence.check_ticket_mutation_evidence`
results."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

from typani import Ok

from frob.gates import mutation_evidence_violations
from frob.tickets._models import Origin, Ticket, TicketKind, TicketState
from frob.tickets._mutation_evidence import ConfirmatoryFinding


def _ticket(kind: TicketKind) -> Ticket:
    return Ticket(
        id="T-0900",
        title="sample",
        state=TicketState.IN_PROGRESS,
        kind=kind,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        blocked_by=(),
        parent=None,
        scope=("m.py",),
        evidence=("test_m.py::test_add",),
        attachments=(),
        body="## Description\nsomething\n",
    )


_FINDING = ConfirmatoryFinding(
    ticket_id="T-0900",
    file="m.py",
    tests=("test_m.py::test_add",),
    mutants_total=2,
)


class TestMutationEvidenceViolations:
    def test_confirmatory_finding_is_warn_for_feature_kind(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_confirmatory_finding_is_warn_for_feature_kind  # noqa: E501
        ticket = _ticket(TicketKind.FEATURE)
        with patch(
            "frob.gates._mutation_evidence.check_ticket_mutation_evidence",
            return_value=Ok((_FINDING,)),
        ):
            violations = mutation_evidence_violations(tmp_path, ticket, "main")
        assert len(violations) == 1
        assert violations[0].rule == "TEST016"
        assert violations[0].severity == "warn"

    def test_confirmatory_finding_is_error_for_security_kind(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_confirmatory_finding_is_error_for_security_kind  # noqa: E501
        ticket = _ticket(TicketKind.SECURITY)
        with patch(
            "frob.gates._mutation_evidence.check_ticket_mutation_evidence",
            return_value=Ok((_FINDING,)),
        ):
            violations = mutation_evidence_violations(tmp_path, ticket, "main")
        assert len(violations) == 1
        assert violations[0].severity == "error"

    def test_confirmatory_finding_is_error_for_bug_kind(self, tmp_path: Path) -> None:
        ticket = _ticket(TicketKind.BUG)
        with patch(
            "frob.gates._mutation_evidence.check_ticket_mutation_evidence",
            return_value=Ok((_FINDING,)),
        ):
            violations = mutation_evidence_violations(tmp_path, ticket, "main")
        assert violations[0].severity == "error"

    def test_no_findings_no_violations(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_no_findings_no_violations  # noqa: E501
        ticket = _ticket(TicketKind.SECURITY)
        with patch(
            "frob.gates._mutation_evidence.check_ticket_mutation_evidence",
            return_value=Ok(()),
        ):
            violations = mutation_evidence_violations(tmp_path, ticket, "main")
        assert violations == ()

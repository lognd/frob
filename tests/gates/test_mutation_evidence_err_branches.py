"""T-1279 TEST005 burn-down: `frob.gates._mutation_evidence.
mutation_evidence_violations`'s `Err` branch (the exec-disabled degrade)
was previously untested -- only the `Ok` paths (confirmatory finding
present/absent, per-kind severity) had coverage in
tests/test_gates_mutation_evidence.py. It must degrade to NO violations
rather than raising or silently going green through an unrelated code
path; this test pins that explicitly. (`MutationEvidenceError` currently
has exactly one member, `ExecDisabled` -- the function's second
`return ()` for a hypothetical non-`ExecDisabled` `Err` is unreachable
dead code under today's `ErrorSet`, not a distinct behavior to test.)"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

from typani import Err

from frob.gates import mutation_evidence_violations
from frob.tickets._models import Origin, Ticket, TicketKind, TicketState
from frob.tickets._mutation_evidence import MutationEvidenceError


def _ticket(kind: TicketKind) -> Ticket:
    return Ticket(
        id="T-0901",
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


class TestMutationEvidenceErrBranches:
    def test_exec_disabled_degrades_to_no_violations(self, tmp_path: Path) -> None:
        # frob:tests tests/gates/test_mutation_evidence_err_branches.py::TestMutationEvidenceErrBranches.test_exec_disabled_degrades_to_no_violations  # noqa: E501
        ticket = _ticket(TicketKind.SECURITY)
        with patch(
            "frob.gates._mutation_evidence.check_ticket_mutation_evidence",
            return_value=Err(MutationEvidenceError.ExecDisabled),
        ):
            violations = mutation_evidence_violations(tmp_path, ticket, "main")
        assert violations == ()

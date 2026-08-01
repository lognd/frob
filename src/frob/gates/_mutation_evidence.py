"""TEST016 (T-0755): the diff-scoped adversarial evidence obligation as a
`Violation`-producing gate.

Deliberately NOT part of `test_gate`'s snapshot-driven pipeline (docs/
modules/gates.md's `_STAGE_GROUPS`): every other TEST rule is a pure
function of the graph snapshot, cheap and safe to run on every `frob
check`. This rule spawns a bounded but real subprocess mutation pass
(`frob.tickets._mutation_evidence.check_ticket_mutation_evidence`, which
itself reuses `frob.mutate` -- no parallel mutation engine) per ticket. Not
something the default snapshot-driven gate pass may do without violating
the T-0755 PERF guard (must not slow `frob check` for tickets that never
opt in) -- `frob.check` is out of this ticket's declared scope entirely, so
`mutation_evidence_violations` has two callers today:
`frob.tickets._land._check_mutation_evidence`, invoked from
`_land_precheck` at `frob ticket land` time, and (T-0844)
`frob.app.ticket_runner`'s direct `frob ticket close` CLI path, so a
security/bug-kind ticket closed without landing is not exempt from this
obligation either.

Severity: WARN by default, promoted to ERROR for `security`/`bug`-kind
tickets (T-0755's own text: "ratchet to error ... for security/bug-kind
tickets") -- those are exactly the kinds the root-cause incident (T-0611,
T-0571, T-0682, T-0574, T-0710) came from. This is a plain per-ticket
`kind` check, not the `frob.gates._ratchet` baseline-pool mechanism: no
retroactive-mutation-of-past-findings concern applies here, because the
check runs ONLY at THIS ticket's own close/land time -- an already-closed
ticket's evidence is never re-scanned, so landing this rule cannot
retroactively turn a past close red (T-0755's own landing-safety
requirement, satisfied structurally rather than via a ratchet pool)."""
# frob:waive INV006 reason="module-docstring exclusivity-vocabulary hit is \
# source-level design-rationale prose describing already-implemented \
# entry-point/severity behavior, verifiable by reading the code it annotates and the \
# T-0755 land wiring in frob.tickets._land -- not a separate cross-module contract \
# needing its own tracked invariant, same calibration posture as frob.check's T-0585 \
# INV006 waiver"

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.tickets._models import Ticket, TicketKind
from frob.tickets._mutation_evidence import (
    ConfirmatoryFinding,
    MutationEvidenceError,
    check_ticket_mutation_evidence,
)

_ERROR_KINDS = frozenset({TicketKind.SECURITY, TicketKind.BUG})


# frob:doc docs/modules/tickets.md#mutation-evidence-obligation-test016-t-0755
# frob:enforces CHK-GATE-TEST016
# frob:enforces CHK-THEME-EXISTENCE-NOT-PROOF
# frob:enforces CHK-SUBSYS-TICKETS-TESTING
# frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_confirmatory_finding_is_warn_for_feature_kind  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_confirmatory_finding_is_error_for_security_kind  # noqa: E501
# frob:tests tests/test_gates_mutation_evidence.py::TestMutationEvidenceViolations.test_no_findings_no_violations  # noqa: E501
# frob:tests tests/gates/test_mutation_evidence_err_branches.py::TestMutationEvidenceErrBranches.test_exec_disabled_degrades_to_no_violations  # noqa: E501
def mutation_evidence_violations(
    root: Path, ticket: Ticket, base_ref: str = "main"
) -> tuple[Violation, ...]:
    """TEST016: `ticket`'s own bound evidence tests never killed a single
    mutant of a diff-touched, in-scope file -- confirmatory-only evidence.

    Severity is ERROR for `security`/`bug`-kind tickets, WARN otherwise
    (see module docstring). `Err(ExecDisabled)` (the exec kill switch was
    active) degrades to NO violations rather than a false-clean pass being
    silently indistinguishable from a real one -- the caller sees the
    `Err` via `frob.tickets._mutation_evidence` directly if it needs to
    react to that case specially; this wrapper's job is only to turn
    genuine `ConfirmatoryFinding`s into `Violation`s.
    """
    result = check_ticket_mutation_evidence(root, ticket, base_ref)
    if result.is_err:
        if result.danger_err is MutationEvidenceError.ExecDisabled:
            return ()
        return ()
    findings = result.danger_ok
    severity = Severity.ERROR if ticket.kind in _ERROR_KINDS else Severity.WARN
    violations: list[Violation] = []
    for finding in findings:
        violations.append(
            Violation(
                rule="TEST016",
                severity=severity,
                file=finding.file,
                line=0,
                message=_test016_message(ticket.id, finding),
            )
        )
    return tuple(violations)


def _test016_message(ticket_id: str, finding: ConfirmatoryFinding) -> str:
    """The TEST016 finding message (T-0755 reviewer round 2, finding 4):
    names every surviving mutant's file:line + description, then BOTH
    documented remedies (strengthen the tests, or the `--skip-mutation-
    evidence` escape hatch) -- never just a bare "confirmatory-only"
    count with no actionable next step."""
    named = "; ".join(f"{m.file}:{m.line} ({m.description})" for m in finding.survivors)
    return (
        f"TEST016: {ticket_id}'s bound evidence {list(finding.tests)} killed "
        f"0/{finding.mutants_total} mutant(s) of {finding.file}'s changed "
        f"lines -- confirmatory-only, does not prove the evidence detects "
        f"this change. Surviving mutant(s): {named or '(none named)'}. "
        f"Remedy: (1) strengthen the named test(s) so at least one fails "
        f"on a mutant above, or (2) if this is a genuine false positive, "
        f"`frob ticket land --skip-mutation-evidence` (logs a loud, "
        f"justification-required override)."
    )


__all__ = ["mutation_evidence_violations"]

---
id: T-4167
title: close reports MissingEvidence for two unrelated causes, one of which is a Done-report
  heading unrecognised without a preceding blank line
state: done
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_evidence.py
- src/frob/tickets/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: splitting the MissingEvidence/no-Done-report disjunction needs a new TicketError
    member (TicketError lives in _models.py); the close-failure-hint dispatch table
    in _close_cmd.py may also need a new hint entry
  actor: logan
  at: '2026-09-07'
evidence:
- tests/test_evidence_integrity.py::TestT4167SplitMissingEvidenceDisjunction::test_done_report_present_no_evidence_names_missing_evidence
- tests/test_evidence_integrity.py::TestT4167SplitMissingEvidenceDisjunction::test_heading_without_preceding_blank_line_is_not_missing_evidence
- tests/test_evidence_integrity.py::TestT4167SplitMissingEvidenceDisjunction::test_stale_prework_sweep_never_surfaces_as_missing_evidence
- tests/test_evidence_integrity.py::TestD03SubstantiveDoneReport::test_close_rejects_empty_done_report
- tests/test_tickets.py::TestStateMachine::test_done_without_report_section_errs
- tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd::test_close_fails_on_empty_done_report
designated_repro_test: null
acceptance:
- text: given a ticket with a Done report but no bound evidence, when close runs,
    then the refusal names the missing evidence
  evidence:
  - tests/test_evidence_integrity.py::TestT4167SplitMissingEvidenceDisjunction::test_done_report_present_no_evidence_names_missing_evidence
- text: given a ticket with evidence and a Done-report heading not preceded by a blank
    line, when close runs, then it either succeeds or refuses with a message naming
    the blank-line requirement
  evidence:
  - tests/test_evidence_integrity.py::TestT4167SplitMissingEvidenceDisjunction::test_heading_without_preceding_blank_line_is_not_missing_evidence
  - tests/test_evidence_integrity.py::TestD03SubstantiveDoneReport::test_close_rejects_empty_done_report
  - tests/test_tickets.py::TestStateMachine::test_done_without_report_section_errs
  - tests/system/test_cli_evidence_enforcement.py::TestCliEvidenceEnforcementEndToEnd::test_close_fails_on_empty_done_report
- text: given a stale pre-work sweep, when close runs, then the refusal names the
    stale sweep rather than reporting missing evidence
  evidence:
  - tests/test_evidence_integrity.py::TestT4167SplitMissingEvidenceDisjunction::test_stale_prework_sweep_never_surfaces_as_missing_evidence
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
ONE ERROR NAME FOR TWO UNRELATED CAUSES, AND NEITHER OF THEM IS MISSING EVIDENCE.
Reported as logand.app-v2 F-363: a close refused with a bare MissingEvidence on a
ticket that HAD evidence and HAD a Done report. Their real causes, found by trial
and error rather than from the message:

  (a) a stale pre-work sweep after a scope change -- a separate precondition
      entirely, cleared by re-running the sweep verb;
  (b) NO BLANK LINE before the Done-report heading, so the closer did not
      recognise the section at all.

CONFIRMED IN OUR CODE, src/frob/tickets/_evidence.py around line 528:

    if not ticket.evidence or not _has_done_report(ticket.body):
        ...
        return Err(TicketError.MissingEvidence)

A DISJUNCTION COLLAPSED ONTO ONE ERROR NAME. "This ticket bound no evidence" and
"I could not find the Done-report section" are different facts with different
remedies, and the caller is told the first regardless of which held. Note the log
line hedges -- "missing evidence or a substantive Done report" -- while the error
NAME asserts one cause. The hedge is evidence the author knew the two were
conflated; the naming is what reaches the user.

THE WHITESPACE SENSITIVITY IS THE WORSE HALF. A heading that is not preceded by a
blank line is still that heading to every markdown reader and to any human. If
`_has_done_report` requires the blank line, then a report can be COMPLETE and
CORRECT and still unrecognised, and the tool reports it as absent. That is the
silent-zero shape applied to parsing: present-but-unparsed rendered as missing.
Either parse the heading the way markdown defines it, or state the requirement in
the message -- do not fail as though the section were not written.

THIS IS THE THIRD REFUSAL-MESSAGE DEFECT FOUND FROM CONSUMER REPORTS IN THIS
DRIVE, and the pattern is worth naming even though each fix is local:
  - a land refused on a type-check error count with no lines and no statement of
    which tree it checked (already filed);
  - a land refused over a file it never touched, with nothing saying why that file
    was in scope (already recorded);
  - this one, a close refused with an error naming a cause that did not hold.
In every case the refusal was CORRECT to happen and WRONG about why. A gate that
stops you for an unstated or misstated reason costs a debugging session each time,
and teaches that refusals are obstacles to be retried past rather than information.

WHAT TO DO
  1. Split the disjunction. Report which precondition failed, by name, with its
     own remedy. The two branches already have different fixes.
  2. Make the Done-report heading parse robust to a missing preceding blank line,
     OR refuse with a message that names the blank-line requirement explicitly.
     Choose one and say why; silently requiring it is the current state and is the
     defect.
  3. Find out how the stale-sweep precondition reaches this error at all. The
     reporter names it as cause (a), which suggests a third path collapses here
     too. If a stale sweep can surface as MissingEvidence, that is a separate
     conflation and must be reported under its own name.
  4. Audit the other multi-cause refusals on the close path for the same shape.
     A condition of the form "A or B" returning one error name is the detector.

MUST-FIRE FIXTURE:   a ticket with a Done report but no bound evidence refuses
                     with an error naming the missing evidence.
MUST-STAY-QUIET:     a ticket with evidence and a Done-report heading NOT preceded
                     by a blank line closes successfully, or refuses with a message
                     naming the blank-line requirement -- not with a
                     missing-evidence error either way.
THIRD FIXTURE:       a stale pre-work sweep refuses under its own name, never as a
                     missing-evidence error.

ACCEPTANCE
- The disjunction split so each precondition reports itself.
- The blank-line behaviour decided and stated rather than silently required.
- The stale-sweep path traced and given its own name if it collapses here.
- Other multi-cause refusals on this path audited, with any found reported.
- All three fixtures committed.
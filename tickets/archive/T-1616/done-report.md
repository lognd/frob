## Done report

Gave refactor/deletion-shaped work filed as kind=bug/security an honest,
mechanically-checked evidence obligation instead of a skip/reclassify
dodge, and made post-hoc kind reclassification visible at land time.

1. `frob:no-behavior-change reason="..."` (ticket body directive, same
   scan/precedent as the existing `frob:waive BUG002` regex) INVERTS
   BUG002's obligation rather than skipping it: the designated evidence
   test must PASS at the parent commit (proving nothing changed there
   either), and a genuine FAILURE at the parent is now the violation --
   it falsifies the ticket's own "nothing behavioral changed" claim.
   NO_VERDICT still degrades to no violation either way. Implemented in
   src/frob/gates/_mutation_evidence.py (_no_behavior_change_reason,
   _no_behavior_change_message, the swap branch in bug_repro_violations).

2. `Ticket.kind_history` (src/frob/tickets/_models.py): append-only audit
   trail. `set_kind` (src/frob/tickets/_setters.py) appends an entry
   ("<date> <old>-><new> evidence=<n> done_report=<yes/no>") whenever the
   new kind differs from the old AND the ticket already carries bound
   evidence and/or a substantive Done report -- a fresh, pre-work
   reclassification stays silent, matching pre-T-1616 behavior exactly.
   `frob ticket land` (_warn_kind_history_at_land in
   src/frob/tickets/_land.py, called from _land_precheck) logs a loud
   WARNING for every kind_history entry a landing ticket carries.

Docs: docs/modules/gates.md's BUG002 section documents both the inversion
mechanism and the kind_history/land-notice mechanism; docs/modules/
tickets.md#data-models documents the new field.

Filed T-1670 (renumbers at land) for the evidence-validation
follow-up (designated-repro-order visibility + node-id shape validation
at bind time) named in the dispatch brief -- kept separate since it is
independent CLI-surface work, not part of BUG002's own obligation shape.

Cut: no new `refactor` TicketKind was added (weighed against the body-
text-directive approach and the directive was chosen -- no CLI/model
surface expansion needed, and it stays consistent with the existing
frob:waive BUG002 precedent in the same file). If a future need arises
for a `refactor` kind as a first-class TEST016/other-gate signal beyond
BUG002 specifically, that is a new ticket, not silently folded in here.

### Changed
```
 tickets.md | 75 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 73 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates_mutation_evidence.py::TestNoBehaviorChange::test_reason_present_recognized` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestNoBehaviorChange::test_bare_directive_without_reason_not_recognized` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugReproViolationsNoBehaviorChange::test_passed_at_parent_no_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugReproViolationsNoBehaviorChange::test_failed_at_parent_is_error_violation` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugReproViolationsNoBehaviorChange::test_no_verdict_no_violation` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestKindHistory::test_change_before_any_work_not_recorded` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestKindHistory::test_change_after_evidence_recorded` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestKindHistory::test_change_after_done_report_recorded` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestKindHistory::test_history_is_append_only` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestKindHistoryLandNotice::test_notice_logged_at_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_evidence.py::TestKindHistoryLandNotice::test_no_history_no_notice` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 0 error(s), 6110 warning(s), 711 waived
- error-findings: none (measured, zero errors)

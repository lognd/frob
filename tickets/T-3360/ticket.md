---
id: T-3360
title: T-3266's stale-claims guard wrongly blocks reverify's own post-close evidence-add
  flow
state: done
kind: bug
origin: human
created: '2026-08-29'
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
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: 'AFFECT001: reverify_close_guard''s affects()-closure doc target'
  actor: logan
  at: '2026-08-29'
evidence:
- tests/test_ticket_reverify.py::TestReverifyCli::test_reruns_verification_and_refreshes_recap_state_unchanged
- tests/test_tickets.py::TestStaleClaimsGuard::test_zero_claims_with_real_evidence_refused
- tests/test_tickets.py::TestStaleClaimsGuard::test_wrong_nonzero_claims_refused
- tests/test_tickets.py::TestStaleClaimsGuard::test_matching_claims_not_flagged
- tests/test_tickets.py::TestStaleClaimsGuard::test_no_claims_section_not_flagged
designated_repro_test: null
acceptance:
- text: given a done ticket with new evidence bound via frob ticket reverify --evidence,
    when the structural guard runs before the recap refresh, then reverify succeeds
    instead of refusing with StaleClaimsInDoneReport
  evidence:
  - tests/test_ticket_reverify.py::TestReverifyCli::test_reruns_verification_and_refreshes_recap_state_unchanged
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Same-day regression from T-3266 (commit 886eec895). T-3266 wired _stale_claims_reason into _done_transition_structural_guard, which both transition()/close and reverify_close_guard share via _done_transition_guard. For close this is correct: the operator is expected to have already run frob ticket done-report before closing, so a stale Captured-claims count is a real defect signal. For reverify it is not: reverify's entire purpose (churn item 6, docs/audits/coordination-churn.md) is to accept NEW evidence post-close (via --evidence/--evidence-cmd or a prior frob ticket evidence call) and, ONLY AFTER the guard suite passes, refresh the Done report's Captured-claims section to match (frob.app.ticket_runner._reverify, recover_done_report_why + set_done_report). Because the recap refresh happens strictly after the guard, the guard now always sees the OLD (pre-refresh) claims count against the NEW evidence count and refuses -- reverify can never succeed when evidence was added, which is the only scenario it exists for. Reproduced live: tests/test_ticket_reverify.py::TestReverifyCli::test_reruns_verification_and_refreshes_recap_state_unchanged fails with StaleClaimsInDoneReport on current main. Confirmed via git show 886eec895 and by re-running the guard chain: transition() (close) -> _done_transition_guard -> _done_transition_structural_guard (T-3266 check included); reverify_close_guard -> same _done_transition_guard, so reverify inherits the check unconditionally. Fix direction: thread a way for reverify_close_guard's call into _done_transition_guard/_done_transition_structural_guard to skip (or defer) T-3266's stale-claims check, since reverify's caller always refreshes the recap immediately after a guard pass and the check is therefore never protective there, only blocking. Do NOT weaken the check for close -- T-3266 fixed a measured defect (206 of 1934 done-reports on main disagreeing with their own evidence) and close's own contract requires the operator to refresh before closing.
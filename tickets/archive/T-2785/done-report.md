## Done report

Changed:
- src/frob/tickets/_setters.py::_refuse_write_if_land_in_progress (new
  shared pre-write guard, mirrors _reconcile._refuse_apply_if_land_in_progress
  T-2291)
- src/frob/tickets/_setters.py::_set_ticket_field (calls the guard before
  any lease/lock/write; this is the shared home for set_priority, set_kind,
  set_tier, set_component, set_runs_last, set_milestone, set_sprint)
- src/frob/tickets/_setters.py::set_parent (calls the guard; also fixed
  the no-op audit-noise defect -- parent_id == current parent now returns
  the loaded ticket unchanged, no TriageChangeEntry, no write)
- src/frob/tickets/_setters.py::set_body, set_runs_last_parallel_safe,
  set_scope_breadth_ack, set_no_scope_declared, set_designated_repro_test
  (each has its own inline lease/lock/write flow, not funneled through
  _set_ticket_field, so each got its own call to the same guard)
- Return type annotations widened from Result[Ticket, TicketError] to
  Result[Ticket, TicketError | LeaseError] on every function above (the
  CLI dispatch layer -- src/frob/app/ticket_runner/_mutate.py -- logs
  result.danger_err generically on any Err, confirmed by reading it, so
  this is a non-breaking, purely-additive widening)

Sibling setters named in the ticket -- verified vs assumed:
- priority, kind, tier, component, runs-last, milestone: VERIFIED they
  funnel through _set_ticket_field (read every one of their bodies in
  src/frob/tickets/_setters.py; each is a one-line forward). One of them
  (priority) is independently covered by a new land-in-progress test
  (TestSetPriorityLandInProgressGuard); the guard is the SAME function
  call for the other four, not a separate copy, so fixing it once fixes
  all six without per-setter tests.
- label: VERIFIED ABSENT from this file (grepped set_label/add_label/
  remove_label across src/frob/tickets/*.py -- no match; label mutation
  lives outside this ticket's scope, not touched).
- body: VERIFIED to have its own separate inline lease/lock/write flow
  (does not call _set_ticket_field) -- fixed with its own guard call,
  not covered by a new test (existing test_tickets.py body tests still
  pass unmodified, confirming no regression).

Also fixed (not named in the sibling list but sharing the exact same
vulnerable shape, found while reading the file end to end):
set_runs_last_parallel_safe, set_scope_breadth_ack, set_no_scope_declared,
set_designated_repro_test -- each VERIFIED to have the same lease+lock+
write shape and each got the same guard call. None of these have a new
dedicated land-in-progress test; existing tests for each still pass
unmodified.

set_sprint: VERIFIED to funnel through _set_ticket_field (one-line
forward), same as priority/kind/tier/component/runs-last/milestone.

Evidence:
- tests/test_tickets_parent.py::TestSetParentNoOp.test_reparenting_to_current_value_is_a_clean_noop
- tests/test_tickets_parent.py::TestSetParentNoOp.test_reparenting_to_a_new_value_still_writes_exactly_one_entry
- tests/test_tickets_parent.py::TestSetParentLandInProgressGuard.test_refuses_and_writes_nothing_while_land_lock_held
- tests/test_tickets_parent.py::TestSetParentLandInProgressGuard.test_succeeds_normally_once_no_land_is_in_progress
- tests/test_tickets_priority.py::TestSetPriorityLandInProgressGuard.test_refuses_and_writes_nothing_while_land_lock_held
- Full existing test_tickets_parent.py (11/11), test_tickets_priority.py
  (12/12 plus the new ones), test_tickets_organization.py,
  test_tickets_no_scope.py, test_tickets_tiers.py, test_tickets.py, and
  test_ticket_evidence.py all still pass -- 277 passed, 1 failed
  (tests/test_ticket_evidence.py::TestEvidenceCmdCwd::test_relative_probe_only_succeeds_from_worktree,
  confirmed pre-existing and unrelated: reproduces identically on the
  unmodified worktree HEAD before this ticket's commit, is a `test -f`
  evidence-cmd silently refused by T-1892's own empty-stdout guard, and
  touches _evidence.py, not _setters.py).

Filed: none.

Gates: gate:SCOPE clean (0 errors) after `frob ticket scope --add` legally
extended scope to the two test files this fix's own tests live in
(reason recorded on the ticket). Could NOT extend scope to
src/frob/tickets/_models.py (attempted first, for a new TicketError
variant) -- refused with ScopeLeaseConflict, held by in-progress T-2771 --
so the fix reuses the existing LeaseError.LandInProgress directly
(Result[Ticket, TicketError | LeaseError]) instead of adding a new
TicketError member, confirmed safe because the CLI dispatch layer
(_mutate.py) logs any Err generically rather than pattern-matching on
TicketError specifically. gate:PRE001 reads stale in an unscoped
`--only gates-fast` invocation after `frob ticket sweep T-2785`, the
same check-invocation quirk already recorded in T-2779's Done report,
not a defect in this ticket's own state.

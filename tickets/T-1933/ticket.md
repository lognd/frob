---
id: T-1933
title: 'post-land sweep regression from T-1556: 3 new error(s) (ARCH001, DOC001, SEC110)'
state: done
kind: bug
origin: agent
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/design/cli-hygiene.md
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_new.py
- docs/index.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/index.md
  reason: T-1933's DOC001 fix links docs/design/cli-hygiene.md from docs/index.md's
    design-docs list
  actor: logan
  at: '2026-08-09'
evidence:
- tests/unit/test_close_failure_hint_t1556.py::test_evidence_scope_unbound_names_evidence_and_scope_commands
- tests/unit/test_close_failure_hint_t1556.py::test_evidence_not_passing_names_evidence_command
- tests/unit/test_close_failure_hint_t1556.py::test_own_obligations_unclean_names_check_delta_command
- tests/unit/test_close_failure_hint_t1556.py::test_gate_claim_unverified_names_close_retry
- tests/unit/test_close_failure_hint_t1556.py::test_live_tracker_cited_names_successor_ticket_remedy
- tests/unit/test_close_failure_hint_t1556.py::test_new_gate_rule_unaccepted_names_accept_and_evidence_commands
- tests/unit/test_close_failure_hint_t1556.py::test_reverify_verb_is_threaded_through_new_cases
- tests/unit/test_close_failure_hint_t1556.py::test_unhandled_error_still_falls_back_to_generic_message
- tests/unit/test_scope_closure_warning_collapse_t1556.py::TestEmitScopeClosureWarnings::test_few_warnings_logged_individually
- tests/unit/test_scope_closure_warning_collapse_t1556.py::TestEmitScopeClosureWarnings::test_many_warnings_collapse_to_counted_summary
- tests/unit/test_scope_closure_warning_collapse_t1556.py::TestEmitScopeClosureWarnings::test_verbose_env_var_disables_collapse
- tests/unit/test_scope_closure_warning_collapse_t1556.py::TestEmitScopeClosureWarnings::test_no_warnings_logs_nothing
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1556 at commit 16880d5170a24b81f8c1993eaae15b2812307640 found 3 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- ARCH001  src/frob/app/ticket_runner/_close_cmd.py
- DOC001  docs/design/cli-hygiene.md
- SEC110  src/frob/app/ticket_runner/_new.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH001  src/frob/app/ticket_runner/_close_cmd.py  -> attributed to T-1556 (commit 16880d5170a2, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_close_cmd.py::_close_failure_hint
- DOC001  docs/design/cli-hygiene.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SEC110  src/frob/app/ticket_runner/_new.py  -> attributed to T-1556 (commit 16880d5170a2, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_mutate.py::_scope -> src/frob/app/ticket_runner/_new.py::_emit_scope_closure_warnings -> src/frob/app/ticket_runner/_new.py::_SCOPE_CLOSURE_WARNING_COLLAPSE_THRESHOLD

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:no-behavior-change reason="all three findings are static-gate/doc fixes with zero runtime behavior change: ARCH001 is fixed by splitting _close_failure_hint into per-error _hint_* helpers that return byte-for-byte the same remedy strings for every TicketError case (verified via the existing test_close_failure_hint_t1556.py suite, which passes unmodified against both old and new code since the observable output is identical); DOC001 is fixed by linking an already-existing doc from docs/index.md plus a frob:describes/frob:doc anchor pair, no code path changed; SEC110 is fixed by adding a frob:waive comment only, no code changed at all"
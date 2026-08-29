---
id: T-2606
title: waiver reasons promising a follow-up ticket should be enforced
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
- tests/test_gates.py
- tests/test_waive_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/modules/gates.md
  reason: T-2377 holds live in-progress lease on docs/modules/gates.md; narrowing
    to src file only, will coordinate/re-add doc scope once free
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/test_gates.py
  reason: test coverage for new waiver-ticket-check lives here
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/test_waive_gate.py
  reason: dedicated WAIVE-family gate test file
  actor: logan
  at: '2026-08-19'
evidence:
- tests/test_waive_gate.py::TestWaive009Violations::test_promise_with_no_ticket_id_errors
- tests/test_waive_gate.py::TestWaive009Violations::test_promise_with_resolvable_ticket_id_still_errors
- tests/test_waive_gate.py::TestWaive009Violations::test_promise_with_unresolvable_ticket_id_errors
- tests/test_waive_gate.py::TestWaive009Violations::test_promise_with_draft_ticket_id_still_errors
- tests/test_waive_gate.py::TestWaive009Violations::test_no_promise_phrase_untouched
- tests/test_waive_gate.py::TestWaive009Violations::test_known_gate_rule_ids_includes_waive009
- tests/test_waive_gate.py::TestWaive009PromisePhraseDetection::test_follow_up_ticket_phrasing_promises
- tests/test_waive_gate.py::TestWaive009PromisePhraseDetection::test_once_x_clears_phrasing_promises
- tests/test_waive_gate.py::TestWaive009PromisePhraseDetection::test_will_file_phrasing_promises
- tests/test_waive_gate.py::TestWaive009PromisePhraseDetection::test_ordinary_reason_does_not_promise
- tests/test_waive_gate.py::TestWaive009PromisePhraseDetection::test_historical_ticket_mention_does_not_promise
- tests/test_waive_gate.py::TestWaive009TicketIdExtraction::test_extracts_bare_mention
- tests/test_waive_gate.py::TestWaive009TicketIdExtraction::test_extracts_multiple
- tests/test_waive_gate.py::TestWaive009TicketIdExtraction::test_no_mention_yields_empty
designated_repro_test: tests/test_waive_gate.py::TestWaive009Violations::test_promise_with_no_ticket_id_errors
evidence_changes:
- old_node: tests/test_waive_gate.py::TestWaive009Violations::test_draft_ticket_id_resolves
  new_node: tests/test_waive_gate.py::TestWaive009Violations::test_promise_with_draft_ticket_id_still_errors
  reason: T-3295 renamed these test methods (WAIVE009 no longer treats a resolvable/draft
    ticket citation as passing)
  actor: logan
  at: '2026-08-29'
- old_node: tests/test_waive_gate.py::TestWaive009Violations::test_promise_with_resolvable_ticket_id_passes
  new_node: tests/test_waive_gate.py::TestWaive009Violations::test_promise_with_resolvable_ticket_id_still_errors
  reason: T-3295 renamed this test method (WAIVE009 no longer treats a resolvable
    ticket citation as passing)
  actor: logan
  at: '2026-08-29'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 9f0c8562e924b4f168410f3eaa3fc0b013015562
---
T-2598 found a waiver (AFFECT001 on src/frob/app/cycle_runner.py:32) whose reason promised
a follow-up ticket that was never filed -- the only record of owed work lived inside the
comment suppressing the finding that would have surfaced it.

Consider whether WAIVE001 (or a new rule) should require a real ticket id in any waiver
reason that names future/deferred work ("a follow-up ticket will...", "once X clears..."),
so a promised-but-unfiled follow-up cannot hide behind a waiver indefinitely. Investigate
feasibility (a waiver reason is free text; detecting "promises future work" reliably may
need a narrow phrase/pattern check rather than full NLP) before committing to an approach.
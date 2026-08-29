---
id: T-3361
title: fix stale mock signature in test_ticket_close_bug002_t1427
state: done
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_ticket_close_bug002_t1427.py
- tests/unit/test_ticket_runner_designate_repro.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_runner_designate_repro.py
  reason: same T-3104 env_absent kwarg drift affects this file's assert_called_once_with
    expectations too -- one root cause, group the fix
  actor: logan
  at: '2026-08-29'
body_changes:
- mode: append
  reason: grouping the second file's identical root cause into this ticket per its
    own scope expansion
  actor: logan
  at: '2026-08-29'
  old_length: 448
  new_length: 744
evidence:
- tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd::test_close_refuses_when_evidence_passes_at_parent
- tests/unit/test_ticket_close_bug002_t1427.py::TestCloseRefusesBug002ShapeEndToEnd::test_close_succeeds_when_evidence_fails_at_parent
- tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_repro_timeout_s_is_forwarded
- tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro::test_no_node_id_resolves_designated_test
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: a5b80af0e8b8919eb712b2e437f32a5567a438eb
---
T-3104 added a keyword-only env_absent param to frob.gates._bug_repro._bug_repro_outcome_at_ref. TestCloseRefusesBug002ShapeEndToEnd's two monkeypatch lambdas still have the OLD 3-positional-arg signature (root, test_id, base_ref), so the real call site (which now passes env_absent=...) raises TypeError: got an unexpected keyword argument 'env_absent'. Test-only drift, not a product defect -- widen the lambda signatures to accept the new kwarg.

Also fixed tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro.test_repro_timeout_s_is_forwarded and .test_no_node_id_resolves_designated_test -- same T-3104 env_absent kwarg drift, this time in mock.assert_called_once_with's expected call (matched with unittest.mock.ANY).
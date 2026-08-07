---
id: T-0949
title: root-cause and finish isolated test_gate profile (T-0928 Finding 5)
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: T-0927
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/audits/check-performance.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/audits/check-performance.md
  reason: dispatch explicitly requires appending this ticket's root-cause+fix to the
    audit's own remediation log (T-0929 precedent)
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gates.py::TestTest014AmbiguousConventionMatch::test_fires_on_cross_file_same_test_collision
- tests/test_gates.py::TestTest014AmbiguousConventionMatch::test_silent_when_symbol_has_explicit_edge
- tests/test_gates.py::TestTest014AmbiguousConventionMatch::test_silent_when_no_leaf_name_collision
- tests/test_gates.py::TestTest015VacuousCredit::test_fires_on_no_op_test_body
- tests/test_gates.py::TestTest015VacuousCredit::test_silent_when_any_matching_test_asserts
- tests/test_gates.py::TestTest015VacuousCredit::test_silent_when_no_test_matches_at_all
- tests/test_gates.py::TestTestGate::test_test003_satisfied_by_parametrized_test_node_id
- tests/test_gates.py::TestTestGate::test_test003_satisfied_by_parametrized_case_with_dot_in_case_id
- tests/test_gates.py::TestTestGate::test_test002_parametrized_test_counts_each_case
- tests/test_gates.py::TestTestGate::test_test002_noop_parametrize_does_not_inflate_case_count
- tests/test_gates.py::TestTestGate::test_case_count_root_aware_caps_noop_parametrize
designated_repro_test: null
threat: null
component: null
---
Found while working T-0928 (frob-check-performance audit). An attempt to
isolate test_gate's real per-function cost (bypassing the thread pool via a
direct in-process call: `_load_inputs(GateConfig(root='.'))` then
`test_gate(...)` under cProfile) did not complete within a 100s budget --
markedly slower than the 12.36-13.68s gate-summary reports for the SAME
gate inside a real `--only test` run. test_gate is this repo's single
largest unresolved hot-path row (13.68s / 15% of the ranked table's total,
docs/audits/check-performance.md row 2). Root-cause the isolated-call vs
in-context-call discrepancy (candidate: GateConfig(root='.') defaults
diverging from the real check runner's resolved config, e.g. ticket/base
resolution taking a different path with no ticket bound) and complete the
isolated profile to identify the actual dominating TEST00x helper
(candidates: _test003's alpha-interface derivation, _test005's coverage
cross-reference). See docs/audits/check-performance.md Finding 5.
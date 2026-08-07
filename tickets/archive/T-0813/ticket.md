---
id: T-0813
title: 'graph: production entrypoint wiring mark_unresolved=True into compute_protocol_summaries
  (opt-in flag currently invoked by nothing)'
state: done
kind: feature
origin: auditor
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- src/frob/gates/**
- docs/modules/gates.md
- docs/modules/graph.md
- tests/test_gates.py
- tests/test_graph.py
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: 'T-0813: adding doc anchors for the new gate (docs/modules/gates.md rule
    catalog + PROTO001 subsection) and updating docs/modules/graph.md production-entrypoint
    note -- required companion documentation for the new PROTO001 gate this ticket
    wires in, not out-of-scope discovery.'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/modules/graph.md
  reason: 'T-0813: adding doc anchors for the new gate (docs/modules/gates.md rule
    catalog + PROTO001 subsection) and updating docs/modules/graph.md production-entrypoint
    note -- required companion documentation for the new PROTO001 gate this ticket
    wires in, not out-of-scope discovery.'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_gates.py
  reason: 'T-0813: adding tests/test_gates.py and tests/test_graph.py to scope --
    the deterministic unit tests this ticket added for the new PROTO001 gate and the
    callgraph false-positive exemption live here; narrow file-level entries (not tests/**)
    to avoid colliding with any other tickets leasing the broader tests/ tree.'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_graph.py
  reason: 'T-0813: adding tests/test_gates.py and tests/test_graph.py to scope --
    the deterministic unit tests this ticket added for the new PROTO001 gate and the
    callgraph false-positive exemption live here; narrow file-level entries (not tests/**)
    to avoid colliding with any other tickets leasing the broader tests/ tree.'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'T-0813: adding CHK-GATE-PROTO001 registry entry for the new PROTO001 gate
    rule this ticket wires in -- required to keep missing_gate_rule_ids/REG010 clean,
    per T-0779/T-0808 precedent.'
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates.py::TestProtocolSummaryGate::test_unresolved_callee_poisons_a_protocol_tagged_symbol
- tests/test_gates.py::TestProtocolSummaryGate::test_clean_protocol_tagged_symbol_is_not_flagged
- tests/test_gates.py::TestProtocolSummaryGate::test_untagged_symbol_with_unresolved_call_is_not_flagged
- tests/test_gates.py::TestProtocolSummaryGate::test_real_repo_scan_runs_end_to_end_without_crashing
- tests/test_graph.py::TestCallGraph::test_build_call_graph_exempts_attribute_call_on_foreign_receiver_from_unresolved
- tests/test_graph.py::TestCallGraph::test_build_call_graph_exempts_super_dunder_call_from_unresolved
- tests/test_graph.py::TestCallGraph::test_build_call_graph_still_marks_unresolved_self_attribute_call
designated_repro_test: null
acceptance:
- text: GIVEN a real repo scan through the protocol-summary entrypoint WHEN a private-convention
    callee has no candidates THEN the summary shows UNRESOLVED_CALLEE poisoning end
    to end; the dunder/cross-package private-method false-positive class (obj._method,
    super().__init__ with zero in-paths candidates) has a recorded disposition (filtered
    or documented)
  evidence:
  - tests/test_gates.py::TestProtocolSummaryGate::test_unresolved_callee_poisons_a_protocol_tagged_symbol
  - tests/test_gates.py::TestProtocolSummaryGate::test_clean_protocol_tagged_symbol_is_not_flagged
  - tests/test_gates.py::TestProtocolSummaryGate::test_untagged_symbol_with_unresolved_call_is_not_flagged
  - tests/test_gates.py::TestProtocolSummaryGate::test_real_repo_scan_runs_end_to_end_without_crashing
  - tests/test_graph.py::TestCallGraph::test_build_call_graph_exempts_attribute_call_on_foreign_receiver_from_unresolved
  - tests/test_graph.py::TestCallGraph::test_build_call_graph_exempts_super_dunder_call_from_unresolved
  - tests/test_graph.py::TestCallGraph::test_build_call_graph_still_marks_unresolved_self_attribute_call
threat: null
component: null
---
T-0809 reviewer condition (a): mark_unresolved is tested but production-dead (no src/ caller passes True; compute_protocol_summaries itself has no production consumer yet). Wire a real entrypoint when the T-0739-family verifier lands, or earlier as a frob graph subcommand. Note the reviewer's residual false-positive class in the heuristic for adjudication at wiring time.
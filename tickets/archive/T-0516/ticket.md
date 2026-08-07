---
id: T-0516
title: burn down residual 89 COV006 findings after T-0506 wrapper-reachability fix
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov006_silent_when_test_reaches_via_two_hop_wrapper_chain
- tests/test_gates.py::TestCoverageGate::test_cov006_silent_when_wrapper_called_via_import_alias
- tests/test_gates.py::TestCoverageGate::test_cov006_silent_when_test_reaches_via_same_file_public_wrapper
- tests/test_gates.py::TestCoverageGate::test_cov006_still_fires_when_no_public_wrapper_reaches_the_target
- tests/test_gates.py::TestProcessPoolGates::test_process_job_runs_in_a_separate_process
- tests/test_gates.py::TestGateOrderSetEquality::test_canonical_gate_order_matches_all_gates
designated_repro_test: null
threat: null
component: null
---
T-0506 extended COV006 with a one-hop same-file public-wrapper rescue, reducing the finding count from 98 to 89 (measured via frob check before/after on this worktree). The residual 89 are either genuinely broken frob:tests bindings needing a real bound symbol, or FP shapes not covered by the wrapper rescue (e.g. cross-file wrapper, two-hop chains, or a test calling the private symbol via an attribute/instance rather than a bare call token). Triage the residual list from a fresh frob check run and either bind real tests, fix wrong directives, or narrow to a documented remaining FP class.
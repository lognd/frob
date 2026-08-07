---
id: T-0506
title: 'COV006 false-positive class: extend reachability through same-file public
  wrappers before burndown of the ~97 findings'
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov006_silent_when_test_reaches_via_same_file_public_wrapper
- tests/test_gates.py::TestCoverageGate::test_cov006_still_fires_when_no_public_wrapper_reaches_the_target
- tests/test_gates.py::TestCoverageGate::test_cov006_flags_test_with_no_call_graph_reachability
- tests/test_gates.py::TestCoverageGate::test_cov006_silent_when_test_calls_the_bound_symbol
- tests/test_gates.py::TestCoverageGate::test_cov006_never_fires_for_a_public_target
designated_repro_test: null
threat: null
component: null
---
T-0483's COV006 (frob:tests edge to a private symbol with no call-graph reachability from the test) has a disclosed common FP shape: the call graph never records edges INTO public callees, so a test calling a same-file public wrapper that itself calls the bound private helper reads as unreachable. Before hand-burning down the ~97 COV006 / ~61 COV007 warn findings, extend the reachability check one hop through same-file public wrappers (or record public-callee edges for this check's purposes). Scope: src/frob/gates/__init__.py (COV006 helpers), tests/test_gates.py.
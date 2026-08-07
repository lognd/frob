---
id: T-0841
title: wire Rust/C++/TypeScript language-excuse discharge into a real call-graph scan
state: done
kind: feature
origin: human
created: '2026-07-23'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_protocol_summary.py
- src/frob/graph/callgraph.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestProtocolVerificationGate::test_rust_file_state_never_established_is_an_error
- tests/test_gates.py::TestProtocolVerificationGate::test_rust_drop_impl_discharges_the_requirement
- tests/test_gates.py::TestProtocolVerificationGate::test_typescript_using_discharges_the_requirement
- tests/test_graph.py::TestCallGraph::test_build_call_graph_resolves_a_rust_private_callee_by_pub_keyword
- tests/test_graph.py::TestCallGraph::test_build_call_graph_does_not_resolve_a_rust_pub_callee
designated_repro_test: null
threat: null
component: null
---
T-0746 disclosure: frob.arch._protocol_excuse's per-language discharge
predicates (rust_drop_discharge, cpp_raii_discharge,
typescript_using_discharge, gc_finalizer_discharge) are built and
directly unit-tested, but only python_with_discharge is wired into the
real repo-scan protocol_summary_gate today -- because
frob.graph.callgraph.build_call_graph is Python-only (the same
disclosed limitation PROTO001 already carries, and DEAD001 before it).
Wiring Rust/C++/TypeScript discharge into a real cross-file scan needs
those languages to get build_call_graph support first (or an
equivalent per-language call-graph substrate); this is deliberately
NOT built here to avoid a second, unreviewed call-graph implementation
per language, mirroring T-0745's own T-0809 disclosure pattern.
Scope: src/frob/gates/_protocol_summary.py, src/frob/graph/callgraph.py.
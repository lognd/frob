---
id: T-0583
title: COV006 reachability opaque through memoize_per_run wrappers -- decorator indirection
  loses static callee edges
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
- tests/test_lang.py::TestParsePython::test_directive_binds_across_two_blank_lines
- tests/test_lang.py::TestErrors::test_syntax_error_logs_partial_tree_warning
- tests/test_graph.py::TestCallGraph::test_build_call_graph_sees_through_memoize_per_run_wrapper
designated_repro_test: null
threat: null
component: null
---
T-0410 wrapped frob.lang.parse_file in memoize_per_run (first-call-deferred wrapper); the static call graph then lost parse_file's edges to its private helpers (_warn_if_partial_tree, _find_following_symbol), erroring two previously-sound frob:tests bindings the moment COV006 was promoted to error. Teach reachability to see through memoize_per_run/functools.wraps-style decorators (resolve the wrapped underlying function's edges), then remove the two waivers in tests/test_lang.py. Scope: src/frob/graph/callgraph.py, src/frob/gates/__init__.py COV006 helpers, tests/test_lang.py, tests/test_gates.py.
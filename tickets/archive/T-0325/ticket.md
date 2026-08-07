---
id: T-0325
title: 'doc-drift digest graph: warm ''what code/docs must update when X changes''
  query (the north-star)'
state: done
kind: feature
origin: human
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- src/frob/serve/**
- tickets.md
- docs/modules/graph.md
- tests/test_graph_affects.py
- tests/test_serve.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/graph.md
  reason: T-0325 graph work maps to docs/modules/graph.md
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_graph_affects.py
  reason: evidence for T-0325's affects() and frob_affects tool lives in these test
    files
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/test_serve.py
  reason: evidence for T-0325's affects() and frob_affects tool lives in these test
    files
  actor: logan
  at: '2026-07-22'
evidence:
- tests/test_graph_affects.py::TestAffects::test_no_edges_is_empty_set
- tests/test_graph_affects.py::TestAffects::test_direct_doc_and_test_edges
- tests/test_graph_affects.py::TestAffects::test_transitive_uses_contract_chain
- tests/test_graph_affects.py::TestAffects::test_cycle_guarded
- tests/test_graph_affects.py::TestAffects::test_truncated_at_max_depth
- tests/test_graph_affects.py::TestAffects::test_truncated_at_max_nodes
- tests/test_serve.py::TestAffects::test_direct_symbol_no_dependents
- tests/test_serve.py::TestAffects::test_transitive_dependent_docs_included
- tests/test_serve.py::TestAffects::test_unknown_symbol_is_err
designated_repro_test: null
threat: null
component: null
---
The user's original vision (CLAUDE.md): every function/class/etc. carries a digest in .frob/, every doc is connected, and frob answers -- without running a test, like a static type-checker for docs -- 'X's digest changed, here is the transitively-affected doc + code set that must be reviewed/updated.' Only practical if the graph is kept WARM (frob daemon epic). Query surface: graph.affects(symbol) -> impacted docs+symbols; a gate that fails when a touched symbol's dependents' digests weren't acked. This is the same project as the daemon; file so the digest-graph work is tracked as its own deliverable.
---
id: T-0917
title: MCP tool mirror for frob perf hot (T-0712 follow-up)
state: done
kind: feature
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/serve/**
- tests/test_serve.py
- docs/modules/serve.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_serve.py
  reason: add coverage for the new frob_perf_hot MCP tool
  actor: logan
  at: '2026-07-26'
- op: add
  glob: docs/modules/serve.md
  reason: AFFECT001 requires updating the tools doc for the new frob_perf_hot tool
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_serve.py::TestPerfHot::test_empty_store_is_empty_list
- tests/test_serve.py::TestPerfHot::test_ranks_by_default_p50xcount
- tests/test_serve.py::TestPerfHot::test_by_p90_ranks_by_p90_instead
- tests/test_serve.py::TestPerfHot::test_top_truncates_results
- tests/test_serve.py::TestBuildServer::test_registers_all_five_tools
- tests/integration/test_interfaces.py::TestInterfaces::test_serve_tools
designated_repro_test: null
threat: null
component: null
---
T-0712 shipped frob perf hot (query surface over the hot-graph sketch store) but its acceptance text also called for an MCP tool mirror for agents; src/frob/serve/_tools.py is outside T-0712's declared scope (src/frob/perf/**, src/frob/app/**, src/frob/gates/**, docs/modules/perf.md), so this was filed rather than expanding scope. Add a frob_perf_hot(root, top, by) MCP tool mirroring frob perf hot's list_sketches query, following the existing frob_graph_query/frob_stale_docs pattern in src/frob/serve/_tools.py.
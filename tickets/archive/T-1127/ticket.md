---
id: T-1127
title: 'serve: RPC surface for exports/stats proxying (T-1106 residual; outline/map/xref
  moot pending T-0802 sunset)'
state: done
kind: feature
origin: agent
created: '2026-07-28'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/serve/_tools.py
- src/frob/app/**
- docs/modules/serve.md
- src/frob/serve/_socketd.py
- src/frob/serve/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/serve/_socketd.py
  reason: 'T-1127: wiring frob_exports/frob_stats requires adding both to _socketd._TOOL_DISPATCH,
    not just defining the _tools.py functions'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/serve/__init__.py
  reason: 'T-1127: exporting frob_exports/frob_stats from serve/__init__.py to match
    the existing frob_affects/frob_graph_query re-export convention'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_app_daemon_proxy.py::TestDifferentialParity::test_exports_json_daemon_matches_in_process
- tests/test_app_daemon_proxy.py::TestDifferentialParity::test_stats_json_daemon_matches_in_process
- tests/unit/test_app_runners.py::TestExportsRunner::test_json_mode_logs_result
designated_repro_test: null
acceptance:
- text: GIVEN a running daemon WHEN frob exports or frob stats runs THEN it is served
    warm through the proxy with differential parity against in-process execution,
    matching the T-1093/T-1106 pattern
  evidence:
  - tests/test_app_daemon_proxy.py::TestDifferentialParity::test_exports_json_daemon_matches_in_process
  - tests/test_app_daemon_proxy.py::TestDifferentialParity::test_stats_json_daemon_matches_in_process
threat: null
component: null
---
T-0321's close disclosed: outline/map/xref/exports/stats have no frob.serve._tools RPC surface at all, so T-1106 could not proxy them. outline/map/xref (and docs-search) are scheduled for REMOVAL by T-0802's 2026-10-01 navigation-command sunset -- do NOT build RPC for those; only exports and stats warrant a surface. If T-0802 executes first, re-scope to exports/stats only (already assumed here).
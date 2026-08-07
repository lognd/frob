---
id: T-0361
title: 'arch: fix or waive long-function/god-class findings on SRC'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0359
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_app_runner_map
- tests/system/test_cli_vet.py::TestHookMode::test_old_package_passes
- tests/test_dup_inline.py::TestCallGraphBounds::test_call_edge
- tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_honors_graph_excludes
- tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_skips_builtin_skip_dirs
- tests/test_gates.py::TestPreworkSweepBounds::test_sweep_ticket_xref_hits_are_real_symbols
- tests/test_gates.py::test_gates_run_gates_integration
- tests/test_graph.py::TestLoadGraph::test_cache_stale_after_edit
- tests/test_graph.py::test_graph_build_lock_drift_integration
- tests/test_ticket_land.py::TestPreworkSweepRefresh::test_land_refreshes_stale_sweep_after_unrelated_main_change
- tests/unit/test_arch.py::test_arch_end_to_end_analyze_then_render
- tests/unit/test_dup.py::test_dup_end_to_end_scan_then_render
designated_repro_test: null
threat: null
component: null
---
T-0204 family 3 (~20 warnings): real long-function/god-class findings on production src/. Disposition: refactor down, or add a per-finding reasoned frob:waive (no blanket waiver). Acceptance: 0 unwaived long-function/god findings on src/; every waiver has a written reason; honest summary line.
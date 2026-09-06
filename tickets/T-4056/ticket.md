---
id: T-4056
title: 'Windows CI cluster C: CYCLE001 node ids use bare str() not as_posix, cycle
  detection finds nothing on Windows'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/_python.py
- tests/unit/test_cycle_waiver.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_cycle_waiver.py
  reason: add test-file for Windows node-id posix regression test
  actor: logan
  at: '2026-09-06'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3936 cluster C: tests/unit/test_cycle_waiver.py's three cases (including the unwaived positive control) all report zero findings on Windows. Root cause: frob.check._python._build_import_graph builds node ids with bare str(path.relative_to(scan_root)) (backslash-separated on Windows) but resolve_local_import always returns as_posix() (forward-slash) edge targets. So on Windows every add_edge(rel, resolved) links a backslash node id to a forward-slash node id that never equals it -- Tarjan sees only isolated singleton nodes, no cycle of size>1 is ever found, detector silently reports no cycles. This is the SAME shape frob.app.cycle_runner._process_path already fixed at T-3786 (rel_path.as_posix()) -- _build_import_graph in _python.py is a second, unfixed copy of the same node-identity logic. Fix: use rel_path.as_posix() in _build_import_graph, matching cycle_runner.
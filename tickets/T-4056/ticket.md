---
id: T-4056
title: 'Windows CI cluster C: CYCLE001 node ids use bare str() not as_posix, cycle
  detection finds nothing on Windows'
state: in-progress
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
- tests/system/test_cli_check.py
- tests/unit/test_capability_and_deploy_cycle_regression.py
- tests/unit/test_check.py
- tests/unit/test_check_gates_summary.py
- tests/unit/test_check_tool_unavailable.py
- tests/unit/test_dup_pipeline_cycle_regression.py
- tests/unit/test_gates_lang_graph_cycle_regression.py
- tests/unit/test_process_guard.py
- tests/unit/test_vet_cycle_regression.py
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
- op: add
  glob: docs/modules/gates.md
  reason: 'scope closure: _python.py''s pre-existing frob:doc/frob:tests edges from
    unrelated symbols in the same module require these files in scope (SCOPE002),
    not new work introduced by this ticket'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/system/test_cli_check.py
  reason: 'scope closure: _python.py''s pre-existing frob:doc/frob:tests edges from
    unrelated symbols in the same module require these files in scope (SCOPE002),
    not new work introduced by this ticket'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_capability_and_deploy_cycle_regression.py
  reason: 'scope closure: _python.py''s pre-existing frob:doc/frob:tests edges from
    unrelated symbols in the same module require these files in scope (SCOPE002),
    not new work introduced by this ticket'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_check.py
  reason: 'scope closure: _python.py''s pre-existing frob:doc/frob:tests edges from
    unrelated symbols in the same module require these files in scope (SCOPE002),
    not new work introduced by this ticket'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_check_gates_summary.py
  reason: 'scope closure: _python.py''s pre-existing frob:doc/frob:tests edges from
    unrelated symbols in the same module require these files in scope (SCOPE002),
    not new work introduced by this ticket'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_check_tool_unavailable.py
  reason: 'scope closure: _python.py''s pre-existing frob:doc/frob:tests edges from
    unrelated symbols in the same module require these files in scope (SCOPE002),
    not new work introduced by this ticket'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_dup_pipeline_cycle_regression.py
  reason: 'scope closure: _python.py''s pre-existing frob:doc/frob:tests edges from
    unrelated symbols in the same module require these files in scope (SCOPE002),
    not new work introduced by this ticket'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_gates_lang_graph_cycle_regression.py
  reason: 'scope closure: _python.py''s pre-existing frob:doc/frob:tests edges from
    unrelated symbols in the same module require these files in scope (SCOPE002),
    not new work introduced by this ticket'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_process_guard.py
  reason: 'scope closure: _python.py''s pre-existing frob:doc/frob:tests edges from
    unrelated symbols in the same module require these files in scope (SCOPE002),
    not new work introduced by this ticket'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_vet_cycle_regression.py
  reason: 'scope closure: _python.py''s pre-existing frob:doc/frob:tests edges from
    unrelated symbols in the same module require these files in scope (SCOPE002),
    not new work introduced by this ticket'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: docs/modules/gates.md
  reason: 'revert: docs/modules/gates.md''s own scope closure recurses into ~470 unrelated
    gates-module symbols, far outside this ticket''s actual change; treating _diag_severity/_unresolved_count''s
    pre-existing doc edge as inherited scope debt instead'
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
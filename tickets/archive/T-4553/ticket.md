---
id: T-4553
title: 'rapid --files direct dependents are always 0: frob.graph.affects follows only
  frob:uses-contract edges, so the scoped land check never includes callers of a changed
  symbol'
state: done
kind: feature
origin: agent
created: '2026-09-17'
priority: high
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/affects.py
- src/frob/app/ticket_runner/_land_cmd.py
- tests/unit/test_check_scoped_files.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_check_scoped_files.py::TestCallerDependentFiles::test_direct_caller_files_found
- tests/unit/test_check_scoped_files.py::TestRapidCheckScopeFilesCallerDependents::test_three_callers_of_a_changed_function_are_included
- tests/unit/test_check_scoped_files.py::TestRapidCheckScopeFilesCallerDependents::test_falls_back_and_logs_info_when_callgraph_unavailable
designated_repro_test: null
acceptance:
- text: GIVEN a one-file diff that changes a function with 3 callers in other files
    WHEN the rapid land computes its --files scope THEN the 3 caller files are included
    as direct dependents via the callgraph (frob.graph.callgraph), not only uses-contract
    edges
  evidence:
  - tests/unit/test_check_scoped_files.py::TestCallerDependentFiles::test_direct_caller_files_found
  - tests/unit/test_check_scoped_files.py::TestRapidCheckScopeFilesCallerDependents::test_three_callers_of_a_changed_function_are_included
- text: GIVEN the callgraph is unavailable WHEN scoping THEN the land logs the reason
    at INFO and falls back to touched files only
  evidence:
  - tests/unit/test_check_scoped_files.py::TestRapidCheckScopeFilesCallerDependents::test_falls_back_and_logs_info_when_callgraph_unavailable
- text: GIVEN a one-file diff that changes a function with 3 callers in other files
    WHEN the rapid land computes its --files scope THEN the 3 caller files are included
    as direct dependents via the callgraph (frob.graph.callgraph), not only uses-contract
    edges
  evidence:
  - tests/unit/test_check_scoped_files.py::TestRapidCheckScopeFilesCallerDependents::test_three_callers_of_a_changed_function_are_included
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-17 by the T-4547 implementer: _rapid_check_scope_files reports '0 direct-dependent' for every land because frob.graph.affects only follows frob:uses-contract directive edges (documented, intentional for affects), so T-4413's 'diff plus direct dependents' promise is unmet; a scoped check that omits callers can miss a signature-change regression that CI would catch hours later. Use build_call_graph / closure (already used by frob.vet._capability_python) for one hop of callers, dedupe with the uses-contract set, cap the added files (e.g. 200) with a WARN when capped.
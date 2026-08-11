---
id: T-2156
title: Sweep finding identities carry ABSOLUTE paths so commit attribution always
  fails, every finding reads unattributed, and that raises the quarantine which switches
  deferred landing off fleet-wide
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/graph/callgraph.py
- src/frob/verify/_attribution.py
- tests/unit/test_callgraph_module_scoped.py
- tests/unit/verify/test_attribution_module_scope.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/verify/
  reason: 'Premise falsified by frob verify explain: attribution failure is NOT caused
    by absolute-vs-relative path shape (a repo-relative finding attributed too, and
    wrongly). Real mechanism is _ordered_private_callees (callgraph.py:443) resolving
    callees through a codebase-wide SHORT-NAME index, so a test defining _run/_commit_all
    gets edges to all 17/18 same-named private helpers across the tree, producing
    false attribution and -- via _attribution.py''s own more-than-one-reaching=unattributed
    rule -- the commit=None findings. Re-scoping to the real files.'
  actor: logan
  at: '2026-08-11'
- op: add
  glob: src/frob/graph/callgraph.py
  reason: 'Premise falsified by frob verify explain: attribution failure is NOT caused
    by absolute-vs-relative path shape (a repo-relative finding attributed too, and
    wrongly). Real mechanism is _ordered_private_callees (callgraph.py:443) resolving
    callees through a codebase-wide SHORT-NAME index, so a test defining _run/_commit_all
    gets edges to all 17/18 same-named private helpers across the tree, producing
    false attribution and -- via _attribution.py''s own more-than-one-reaching=unattributed
    rule -- the commit=None findings. Re-scoping to the real files.'
  actor: logan
  at: '2026-08-11'
- op: add
  glob: src/frob/verify/_attribution.py
  reason: 'Premise falsified by frob verify explain: attribution failure is NOT caused
    by absolute-vs-relative path shape (a repo-relative finding attributed too, and
    wrongly). Real mechanism is _ordered_private_callees (callgraph.py:443) resolving
    callees through a codebase-wide SHORT-NAME index, so a test defining _run/_commit_all
    gets edges to all 17/18 same-named private helpers across the tree, producing
    false attribution and -- via _attribution.py''s own more-than-one-reaching=unattributed
    rule -- the commit=None findings. Re-scoping to the real files.'
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tests/unit/test_callgraph_module_scoped.py
  reason: 'Adding dedicated new test files rather than appending to tests/test_graph.py

    or tests/unit/verify/test_attribution.py -- both are large, frequently-

    touched shared files in this repo; a dedicated file avoids any lease

    collision, matching the precedent tests/unit/test_land_duplicate_ticket_id.py

    and tests/unit/test_land_squash_residue_reclaim.py already established this

    session for the same reason.

    '
  actor: logan
  at: '2026-08-11'
- op: add
  glob: tests/unit/verify/test_attribution_module_scope.py
  reason: 'Adding dedicated new test files rather than appending to tests/test_graph.py

    or tests/unit/verify/test_attribution.py -- both are large, frequently-

    touched shared files in this repo; a dedicated file avoids any lease

    collision, matching the precedent tests/unit/test_land_duplicate_ticket_id.py

    and tests/unit/test_land_squash_residue_reclaim.py already established this

    session for the same reason.

    '
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_callgraph_module_scoped.py::TestBuildReferenceGraphModuleScoped::test_does_not_cross_wire_same_named_helpers_in_unrelated_files
- tests/unit/test_callgraph_module_scoped.py::TestBuildReferenceGraphModuleScoped::test_resolves_a_genuine_cross_file_import
- tests/unit/test_callgraph_module_scoped.py::TestBuildReferenceGraphModuleScoped::test_same_file_candidate_always_resolves
- tests/unit/verify/test_attribution_module_scope.py::TestAttributionDoesNotCrossFileOnSameNamedHelper::test_finding_in_file_a_does_not_attribute_through_unrelated_file_bs_same_named_helper
designated_repro_test: tests/unit/verify/test_attribution_module_scope.py::TestAttributionDoesNotCrossFileOnSameNamedHelper::test_finding_in_file_a_does_not_attribute_through_unrelated_file_bs_same_named_helper
threat: null
component: null
anchor: false
anchor_reason: null
---

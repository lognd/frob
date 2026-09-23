---
id: T-4560
title: 'callgraph resolves callers only for PRIVATE callees (T-0841 rule): the rapid
  --files dependents miss every caller of a changed PUBLIC symbol'
state: done
kind: feature
origin: agent
created: '2026-09-17'
priority: high
parent: T-4410
tier: ticket
sprint: null
runs_last: false
milestone: 0.532.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/callgraph.py
- src/frob/graph/affects.py
- tests/unit/test_check_scoped_files.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.532.0
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.535.0
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
evidence:
- tests/unit/test_check_scoped_files.py::TestPublicCallerDependentFiles::test_public_callee_caller_is_found_through_import_binding
- tests/unit/test_check_scoped_files.py::TestPublicCallerDependentFiles::test_same_named_private_helpers_in_different_modules_stay_unlinked
designated_repro_test: null
acceptance:
- text: GIVEN a public function changed in module A and imported by modules B and
    C WHEN the rapid land computes caller dependents THEN B and C are included, resolved
    through their import bindings (from A import f / import A; A.f), never by bare
    short name repo-wide
  evidence:
  - tests/unit/test_check_scoped_files.py::TestPublicCallerDependentFiles::test_public_callee_caller_is_found_through_import_binding
- text: GIVEN two modules each defining a same-named private helper WHEN callers are
    resolved THEN no cross-module false edge is produced (the T-0841 safety stays)
  evidence:
  - tests/unit/test_check_scoped_files.py::TestPublicCallerDependentFiles::test_same_named_private_helpers_in_different_modules_stay_unlinked
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-4560
branch: t-4560
---
Disclosed by the T-4553 implementer 2026-09-17: build_call_graph resolves callees by bare short name and, for safety (T-0841, the shared-graph-wrong-for-second-consumer lesson), only links PRIVATE callees; so caller_dependent_files finds callers of changed private symbols only, and the scoped land check still omits every caller of a changed public API. Add import-binding-aware resolution for public symbols (the alias table frob.vet._capability_python already builds per file) so dependents are found without the repo-wide short-name hazard.
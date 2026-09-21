---
id: T-4581
title: 'Capability matrix: csharp/net cell is both patterned and excused after Unity
  net APIs landed (T-4514)'
state: dropped
kind: bug
origin: human
created: '2026-09-18'
priority: medium
parent: null
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability_registry/_matrix.py
- tests/test_capability_registry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_capability_registry/_matrix.py
  reason: 'fix: exclude csharp from generated net excuse (T-4514 patterned it)'
  actor: logan
  at: '2026-09-18'
- op: add
  glob: tests/test_capability_registry.py
  reason: existing test proves the fix (test_no_cell_is_both_patterned_and_excused)
  actor: logan
  at: '2026-09-18'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
evidence:
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_cell_is_both_patterned_and_excused
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_unexcused_empty_cells
designated_repro_test: null
acceptance:
- text: 'bound([''tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_cell_is_both_patterned_and_excused'',
    ''tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_unexcused_empty_cells'']):
    the generated csharp/net excuse is removed and no matrix cell is both patterned
    and excused, while every cell remains patterned or excused'
  evidence:
  - tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_cell_is_both_patterned_and_excused
  - tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_unexcused_empty_cells
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-4581
branch: t-4581
---
## Drop reason
- 2026-09-21: T-4514's land already removed the stale generated csharp/net excuse; TestMatrixExhaustiveness passes unmodified against current dev, nothing left to fix (absorbed by T-4514)
---
id: T-draft-0ab8e38c
title: Wire layout_gate into frob check + register LAYOUT001-003 in _KNOWN_GATE_RULES
state: in-progress
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: T-5747
tier: ticket
sprint: layout-gate
runs_last: false
milestone: 0.537.0
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-draft-0ab8e38c
branch: t-draft-0ab8e38c
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- tests/system/test_cli_check_layout_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/system/test_cli_check_layout_gate.py
  reason: 'positive control: planted unreviewed manifest entry surfaces via frob check,
    frob:waive LAYOUT001 accepted'
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: parent
  old_value: null
  new_value: T-5747
  reason: wiring leaf for the LAYOUT review gate story, filed while working T-5767
  actor: logan
  at: '2026-09-24'
- field: milestone
  old_value: null
  new_value: 0.537.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-24'
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
- field: sprint
  old_value: null
  new_value: layout-gate
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-5767: layout_gate/layout_findings (LAYOUT001-003) are fully implemented and tested in src/frob/gates/_layout_gate.py and src/frob/webapp/_layout_structure.py, but T-5767's own declared scope did not include src/frob/gates/__init__.py (process-job table wiring) or src/frob/gates/_waive.py (_KNOWN_GATE_RULES registration) -- this ticket wires the gate into frob check's actual pipeline and registers its rule ids so frob:waive can recognize them.
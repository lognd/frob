---
id: T-3068
title: 'TDD commit protocol: test-first commit marks the test xfail(strict=True),
  implementation commit removes it; a surviving xfail is tracked debt'
state: in-progress
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: T-3004
tier: ticket
sprint: strata-vmodel
runs_last: false
milestone: 0.535.0
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-3068
branch: t-3068
scope:
- src/frob/gates/_tdd_order.py
- tests/gates/test_tdd_order.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_tdd_order.py
  reason: 'TDD commit protocol: xfail(strict=True) marks test-first, its removal marks
    implementation'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/gates/test_tdd_order.py
  reason: 'TDD commit protocol: xfail(strict=True) marks test-first, its removal marks
    implementation'
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/gates.md
  reason: extend TDD001's own gates.md entry with a TDD002 subsection
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: parent
  old_value: null
  new_value: T-3004
  reason: TDD commit protocol is the mechanism behind T-3004 section 7 enforced test-first
    development
  actor: logan
  at: '2026-08-26'
- field: milestone
  old_value: 1.1.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
- field: sprint
  old_value: null
  new_value: strata-vmodel
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Unblock log
- 2026-09-24: unblocked by T-3067 -- coordinator directive 2026-09-24: build on top of branch t-3067 merged in, diffs kept separable; T-3067 already queued, its own land is independent

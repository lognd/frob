---
id: T-5465
title: 'gates-security stage-group golden drifted: extra a11y member'
state: done
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
flavour: null
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5465
branch: t-5465
scope:
- tests/system/test_cli_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/system/test_cli_check.py
  reason: T-5323 legitimately added a11y to gates-security; update the byte-identical
    migration golden per its own docstring's anticipated drift procedure
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
evidence:
- tests/system/test_cli_check.py::TestCheckStageGroups::test_gate_stage_group_migration_is_byte_identical
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing:
tests/system/test_cli_check.py::TestCheckStageGroups::test_gate_stage_group_migration_is_byte_identical

_STAGE_GROUPS["gates-security"] now contains an extra 'a11y' entry versus
its golden/expected set (AssertionError: extra item 'a11y' in the left
set). A gate's stage-group membership drifted from the byte-identical
migration golden this test guards.

Needs: locate the stage-group registration (NOT src/frob/gates/_a11y_gate.py
itself, which is out of touch-scope -- this is the general stage-group
list/golden file) and either update the golden to include 'a11y' if the
membership change was intentional, or remove 'a11y' from gates-security if
it was not.
---
id: T-5483
title: 'test_sys_gate_zero_violations vs SYS119 positive control: structurally conflicting
  acceptance criteria'
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-5463 (CI drain cluster A+E, run 35951365410).

tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_
zero_violations asserts `sys_gate(_REPO_ROOT, ...)` returns literally zero
violations against this repo's own real tree. This directly includes
SELFAUDIT001 SYS119 (templated-assume) findings via `_selfaudit_
violations` -> `_templated_assume_violations`.

tests/gates_suite/test_sys_assume_template.py::TestSelfaudit001
TemplatedAssume::test_red_on_todays_design_frob_strata is a MANDATORY
positive control (per its own docstring and T-5105's ticket body) that
requires SYS119 to ALWAYS fire against this same real design/frob.strata
-- currently 7 SF-08 boilerplate clusters, 37 assume ids.

These two tests assert mutually exclusive states on the SAME real file:
one requires SYS119 findings to exist, the other requires zero SYS
violations of any kind. They cannot both be green simultaneously as
currently written. This is NOT a new regression from the CI run this
ticket was filed to investigate -- SYS119 was added to sys_gate's output
by T-5105, and test_sys_gate_zero_violations has apparently tolerated
this before via a mechanism not present today, OR it has been silently
red since T-5105 landed (its sibling test test_fragments_module_fs_read_
is_declared_not_selfaudit001's own docstring already documents test_sys_
gate_zero_violations as known to trip on "unrelated, pre-existing SYS101/
GATERULE001 findings" and narrows its own scope specifically to avoid
being masked by that -- i.e. this repo's own tests already know test_
sys_gate_zero_violations is not reliably clean).

Needs an owner decision, not a mechanical fix: either (a) test_sys_gate_
zero_violations should filter out SYS119/SYS120 (the family's own docstring
calls these "ship-at-WARN-with-a-ratchet... so the fleet is not blocked",
i.e. deliberately tolerated, not zero-tolerance), or (b) SYS119's mandatory-
positive-control test should be retired/changed once the fleet actually
de-templates the boilerplate assumes, or (c) some other reconciliation.
T-5463 only fixed the mechanical count drift (6->7 clusters, 34->37 ids)
in the positive-control test; it did NOT touch test_sys_gate_zero_
violations, which remains red for this same reason (and was red before
this ticket touched anything, per the analysis above).

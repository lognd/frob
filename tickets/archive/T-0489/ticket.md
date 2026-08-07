---
id: T-0489
title: T-0416 evidence no longer collects (COV003)
state: dropped
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/strata/test_code_binding.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Dropped (2026-07-21): stale-base worktree artifact -- the T-0416 evidence node collects and passes on main (verified via pytest --collect-only after T-0416 landed at 5dba2d7); the filing worktree had merged main before that landing.

found while working T-0425: frob check reports COV003 for T-0416 (done) -- its recorded evidence tests/unit/strata/test_code_binding.py::TestBindCode::test_nested_git_checkout_pruned_even_when_not_covered_by_exclude_globs no longer collects (pytest --collect-only: 'not found', no match in TestBindCode). Either the test was renamed/removed since T-0416 closed, or something broke collection for it. Out of scope for T-0425 (src/frob/gates/, frob.toml, docs/modules/gates.md, tests/test_gates.py only).
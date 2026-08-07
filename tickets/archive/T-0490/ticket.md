---
id: T-0490
title: T-0416 evidence test_nested_git_checkout_pruned_even_when_not_covered_by_exclude_globs
  does not resolve (COV003)
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
Dropped (2026-07-21): duplicate of T-draft-5443bd5e, same stale-base worktree artifact -- T-0416 evidence collects on main.

found while working T-0472: frob check --ticket T-0472 reports COV003 for T-0416 (already closed/done) -- its recorded evidence id tests/unit/strata/test_code_binding.py::TestBindCode::test_nested_git_checkout_pruned_even_when_not_covered_by_exclude_globs does not exist anywhere in the repo (grep -rn finds nothing), even after deleting .frob/pytest-collect.json to force a cache rebuild. Either the test was removed/renamed after T-0416 closed, or the evidence id was never real. Unrelated to T-0472's scope; filing separately per the playbook out-of-scope rule.
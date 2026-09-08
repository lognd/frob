---
id: T-4296
title: claude_hooks node's SYS101 capability declarations no longer match observed
  capabilities (SELFAUDIT001)
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
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
Found while landing T-4279 (unrelated diff: src/frob/graph/__init__.py only). tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations fails on main (confirmed pre-existing, reproduced with zero diff to .claude/hooks or design/frob.strata's claude_hooks node) with 4 SELFAUDIT001/SYS101 findings: env.read, exec, fs.write, and fs.read are all declared on the claude_hooks node but none are currently observed in src under that node's code= binding. This means either the declared capabilities are stale (the code that used to need them was removed/changed) or the self-audit scanner's observation pass is no longer finding real, still-present call sites (a scanner regression) -- needs investigation to tell which. Confirmed via repeated frob check --only sys runs during T-4282 and T-4279 work: the same 4 findings appeared identically both times with completely different (and non-overlapping) diffs, and git log -1 -- .claude/hooks shows no change since before those tickets started, so this is not caused by either of those tickets' own work.
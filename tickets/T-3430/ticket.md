---
id: T-3430
title: 'SYS100: testsuite fs.read undeclared for tests/unit/test_arch_srp.py'
state: queued
kind: bug
origin: human
created: '2026-08-29'
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
found while working T-3409: tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant fails with 2 new SYS100 violations unrelated to T-3409/T-3416's fs.read declarations: capability 'fs.read' observed at tests/unit/test_arch_srp.py:616 and :650 but not declared on the testsuite node. This surfaced after T-3416 landed and while working T-3409 in a worktree based on main post-T-3416 -- appears to be new drift from a concurrent land on main (not caused by T-3409's or T-3416's own changes, which only touch the core node's fs.read via-list). Fix direction: add tests/unit/test_arch_srp.py to design/frob.strata's testsuite node may fs.read via declaration (or determine the real root cause if it traces to a recent split/refactor of that test file).
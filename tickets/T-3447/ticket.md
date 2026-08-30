---
id: T-3447
title: 'SYS111 ratchet: core fs.read via-list grew to 35 sites, failing test_sys_gate_zero_violations'
state: in-progress
kind: bug
origin: agent
created: '2026-08-29'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
- frob-ratchet.lock.json
- tests/system/test_frob_self_model.py
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: the real SYS111 capability-ratchet lock file this ticket must edit -- the
    originally declared frob-ratchet.lock.json is an unrelated ratchet with no core/testsuite
    entries
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED on GitHub Actions run 33282540898 (ubuntu-latest, HEAD b94cea5d0, 2026-08-30) -- the first run that completed to 100% (20 failures of 12689). This failure is in the cross-platform set (fails on macOS too unless noted). Reproduce locally by node id with -p no:xdist first; if it passes locally, the defect is an environment dependency (git identity, tmp path shape, missing tool, timing) and the fix must make the test hermetic, not skip it.

FAILING: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
    SELFAUDIT001: self-audit family SYS111 node=core: fs.read via-list on core grew to 35 site(s) ...
The SYS111 growth ratchet on the core node fs.read via-list tripped after T-3416/T-3409/T-3429/T-3430 added sites. Read the SYS111 doctrine in docs/ (git grep SYS111 -- docs) and apply the sanctioned resolution: either re-baseline the ratchet with a recorded reason, or move sites off the core node. Do not waive. Verify test_sys_gate_zero_violations passes.

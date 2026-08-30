---
id: T-3484
title: 'SYS100: tests/unit/verify/test_bisect.py (T-1691) undeclared fs.read/exec
  re-breaks the four live-repo self-conformance tests'
state: done
kind: bug
origin: agent
created: '2026-08-30'
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
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED on GitHub Actions run 33308245923 (ubuntu-latest, HEAD 355eb4468, 2026-08-30): suite completed in 16.3 min with 6 failures of 12816. Reproduce by node id with -p no:xdist first.

FAILING (5 tests, one cause): tests/unit/strata/test_selfconform.py::TestRealGateGreen, ::TestCoverageTotality::test_repo_unrestricted_scan_is_clean, tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap, tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
    SYS100 testsuite: capability fs.read observed at tests/unit/verify/test_bisect.py:32 but not declared; also exec at the same file.
T-1691 landed tests/unit/verify/test_bisect.py (real git repos + worktree snapshots) without adding it to design/frob.strata testsuite via-lists. THIRD occurrence this drive (T-3465, T-3450 were the others). Declare every site this test file needs (run TestRealGateGreen on main and declare exactly what it lists; bump the SYS111 ratchet entries in docs/design/registry/capability-via-ratchet.lock.json with reasons). Then, so this class stops reaching CI: T-3324 (queued) asks for landing-time enforcement of the live-repo self-conformance tests -- work T-3324 immediately after this ticket.
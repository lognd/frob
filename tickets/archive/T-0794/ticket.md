---
id: T-0794
title: 'arch: discharge self-join-deadlock advisory on vet/_scan.py::_run_with_timeout
  (same shape as T-0767)'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_scan.py
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestForkPoolHazards::test_self_join_deadlock_discharges_on_real_repo_vet_scan
designated_repro_test: null
acceptance:
- text: GIVEN main WHEN frob check runs THEN zero self-join-deadlock warnings on src/frob/vet
    while the timeout behavior is preserved and a regression test locks the discharge
  evidence:
  - tests/unit/test_arch.py::TestForkPoolHazards::test_self_join_deadlock_discharges_on_real_repo_vet_scan
threat: null
component: null
---
Promotion of T-0767's worktree draft 1910bd1a: the T-0695 self-join-deadlock advisory fires on vet/_scan.py::_run_with_timeout (unwaivable channel). Restructure the join ownership the same way T-0767 discharged _run_combined_jobs. Required for zero-warnings.
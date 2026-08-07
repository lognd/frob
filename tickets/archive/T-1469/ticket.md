---
id: T-1469
title: make coverage doctor precondition dies on stale leases a finished agent left;
  auto-reconcile instead
state: done
kind: bug
origin: agent
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- Makefile
- src/frob/app/doctor_runner.py
- tests/unit/test_makefile_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: acceptance[0]'s pytest evidence must live in the same test file T-1526 already
    uses for coverage-recipe assertions, matching every other coverage/Makefile ticket's
    own test-location convention
  actor: logan
  at: '2026-08-05'
evidence:
- tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_reconciles_before_doctor
- tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_fast_reconciles_before_doctor
designated_repro_test: null
acceptance:
- text: GIVEN a stale in-progress hold with no live lease WHEN make coverage runs
    THEN the hold is auto-requeued with a logged line and the suite proceeds
  evidence:
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_reconciles_before_doctor
  - tests/unit/test_makefile_coverage.py::TestCoverageRecipeReconcilesStaleLeasesBeforeDoctor::test_coverage_fast_reconciles_before_doctor
threat: null
component: null
---
Third occurrence 2026-08-02: an agent session ends leaving an in-progress hold with no live lease; the next make coverage aborts at its frob doctor precondition (exit 1, before pytest ever runs) and the whole suite run is lost -- twice this cost a full run slot, and the footgun FAST_EXIT1 detector now flags it but cannot fix it. Stale leases are mechanically healable (frob ticket reconcile --apply does exactly this). Fix: either the coverage recipe runs reconcile --apply before doctor, or doctor gains --heal-stale-leases (auto-requeue with a logged line) for exactly this class while still failing hard on the non-healable conditions (missing natives, corrupt derived state).
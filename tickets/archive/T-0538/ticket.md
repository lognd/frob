---
id: T-0538
title: make coverage clobbers maturin natives (uv sync) then fails on strata_core
  imports -- guard the target
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- Makefile
- docs/modules/testing.md
- tests/test_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: Makefile
  reason: declare scope from ticket prose, needed to add Makefile-target dry-run test
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/modules/testing.md
  reason: declare scope from ticket prose, needed to add Makefile-target dry-run test
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_coverage.py
  reason: declare scope from ticket prose, needed to add Makefile-target dry-run test
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_coverage.py::TestCoverageTargetNativesGuard::test_coverage_target_restores_and_verifies_natives_before_pytest
- tests/test_coverage.py::TestCoverageTargetNativesGuard::test_coverage_fast_incremental_branch_restores_and_verifies_natives
designated_repro_test: null
threat: null
component: null
---
Incident (2026-07-22): make coverage removed the editable strata_core/frob_core natives mid-run (the known uv-sync clobber, same family as the uv build --wheel gotcha), then died collecting tests/system/test_frob_self_model.py and left 44 phantom errors in frob check (SYS004 native-missing, 16 COV003 unresolvable kernel-property evidence, DRIFT fallout) until make core was re-run. Fix: the coverage target must either pin/exclude the natives from sync or run make core (cheap no-op when fresh) before pytest, and frob doctor's native check should run first so the failure is one clear line. Scope: Makefile, docs/modules/testing.md.
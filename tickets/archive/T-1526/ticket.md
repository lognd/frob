---
id: T-1526
title: 'coverage: make make coverage/coverage-fast a thin wrapper over native_coverage_refresh'
state: done
kind: feature
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- Makefile
- tests/unit/test_makefile_coverage.py
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: rewriting coverage-fast into a thin wrapper obsoletes tests/unit/test_makefile_coverage.py's
    own recipe-content assertions about the old inline xargs/rc logic; must update
    them in the same change, and testing.md documents the make-target contract
  actor: logan
  at: '2026-08-05'
- op: add
  glob: docs/modules/testing.md
  reason: rewriting coverage-fast into a thin wrapper obsoletes tests/unit/test_makefile_coverage.py's
    own recipe-content assertions about the old inline xargs/rc logic; must update
    them in the same change, and testing.md documents the make-target contract
  actor: logan
  at: '2026-08-05'
evidence:
- tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc
- tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_still_rebuilds_natives_first
- tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_coverage_xml_invocations_pass_ignore_errors
designated_repro_test: null
threat: null
component: null
---
T-1205 acceptance[3] asks for make coverage to become a thin optional wrapper around the frob-native orchestration. T-1516 added native_coverage_refresh and rewired run_coverage_wait's default onto it, but the Makefile coverage/coverage-fast targets themselves were left untouched (they still run the full ~300-line shell recipe independently). Rewrite them to delegate their common-path work to native_coverage_refresh, keeping only the xdist-crash-recovery/rerun-deadline shell logic (or whatever that becomes once T-1524 lands) as the part that stays Makefile-side, or is itself ported.
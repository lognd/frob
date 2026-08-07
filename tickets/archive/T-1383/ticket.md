---
id: T-1383
title: 'T-1381 follow-through: frob:doc edge on stamp and testsuite sync for the guard
  tests'
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/release/__init__.py
- docs/modules/release.md
- design/frob.strata
- tests/unit/test_release_stamp_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_release_stamp_guard.py
  reason: the evidence test lives here; covers_scope needs it in scope
  actor: logan
  at: '2026-08-01'
evidence:
- tests/unit/test_release_stamp_guard.py::TestStampRefusesUnbumped::test_refuses_when_api_changed_and_version_not_bumped
designated_repro_test: null
acceptance:
- text: GIVEN main WHEN frob check --only gates runs THEN gate:COV and the SYS104
    self-audit report 0 errors
  evidence:
  - tests/unit/test_release_stamp_guard.py::TestStampRefusesUnbumped::test_refuses_when_api_changed_and_version_not_bumped
threat: null
component: null
---
T-1381 closed leaving three gate obligations: stamp is public and now carries a changed contract (it can refuse) with no frob:doc edge, and the two new public test classes are undeclared on the testsuite strata node. Same class of residue as T-1380 carried for T-1377/T-1379.